"""A-stock unique data tools: profit_forecast, northbound_flow, concept_blocks, lockup_expiry.
Direct HTTP implementations (no akshare dependency)."""

import pandas as pd
import requests
import json
import os
import csv
import re
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Annotated
from langchain_core.tools import tool
from tradingagents.dataflows.config import get_config


# ── helpers ──────────────────────────────────────────────────────────

def _normalize_ticker(symbol: str) -> str:
    s = symbol.strip().upper()
    s = re.sub(r'\s+', '', s)
    s = s.replace('.SS', '.SH')
    if re.match(r'^\d{6}$', s):
        return s
    m = re.match(r'^(\d{6})\.(SH|SZ)$', s)
    if m:
        return m.group(1)
    return s


def _tencent_quote(codes: list[str]) -> dict[str, dict]:
    """Batch real-time quotes from Tencent Finance qt.gtimg.cn."""
    if not codes:
        return {}
    # Convert to Tencent format: sh600519, sz000001
    tencodes = []
    for c in codes:
        c = _normalize_ticker(c)
        if c.startswith('6') or c.startswith('9'):
            tencodes.append(f"sh{c}")
        else:
            tencodes.append(f"sz{c}")
    url = f"http://qt.gtimg.cn/q={'/'.join(tencodes)}"
    try:
        r = requests.get(url, timeout=10)
        r.encoding = 'gbk'
        result = {}
        for line in r.text.strip().split('\n'):
            if not line.strip():
                continue
            try:
                parts = line.split('~')
                if len(parts) < 5:
                    continue
                code_full = parts[0].split('=')[0].strip('"').strip()
                code_num = re.sub(r'^(sh|sz)', '', code_full, flags=re.I)
                name = parts[1]
                price = parts[3]
                pe = parts[39]
                pb = parts[40]
                mr = parts[44] if len(parts) > 44 else '0'
                result[code_num] = {
                    'name': name, 'price': price,
                    'pe': pe, 'pb': pb, 'market_cap': mr
                }
            except Exception:
                continue
        return result
    except Exception:
        return {}


def _eastmoney_datacenter(report_name: str, params: dict) -> list[dict]:
    """Generic Eastmoney datacenter-web API query."""
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    default_params = {
        "reportName": report_name,
        "sortColumns": "NOTICE_DATE",
        "sortTypes": -1,
        "pageSize": 50,
        "pageNumber": 1,
        "source": "WEB",
        "client": "WEB",
        "filter": "",
    }
    default_params.update(params)
    try:
        r = requests.get(url, params=default_params, timeout=15,
                         headers={"User-Agent": "Mozilla/5.0",
                                  "Accept": "application/json"})
        data = r.json()
        if data.get("code") == 0 and data.get("result"):
            return data["result"].get("data", [])
        return []
    except Exception:
        return []


# ── 1. get_profit_forecast ──────────────────────────────────────────

@tool
def get_profit_forecast(
    ticker: Annotated[str, "A-stock code, e.g. 688017"],
) -> str:
    """获取机构一致预期盈利预测（EPS），含前向PE/PEG/估值消化年数。
    数据来源：同花顺10jqka。"""
    code = _normalize_ticker(ticker)
    try:
        url = f"https://basic.10jqka.com.cn/new/{code}/worth.html"
        r = requests.get(url, timeout=15,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = 'utf-8'
        tables = pd.read_html(StringIO(r.text))
        eps_table = None
        for t in tables:
            cols = [str(c).strip() for c in t.columns]
            if any("每股收益" in c or "均值" in c or "EPS" in c.upper() for c in cols):
                eps_table = t
                break
        if eps_table is None:
            return "未找到盈利预测数据（可能覆盖率过低或无机构覆盖）"

        # Format EPS data
        lines = ["机构一致盈利预测（来源：同花顺）:"]
        lines.append(eps_table.to_string(index=False))

        # Compute forward PE
        quote = _tencent_quote([code])
        q = quote.get(code, {})
        if q.get("price") and str(q["price"]).replace('.', '').isdigit():
            price = float(q["price"])
            # Find current-year EPS from table
            eps_val = None
            for col in eps_table.columns:
                col_s = str(col).strip()
                if "均值" in col_s or "平均" in col_s:
                    series = eps_table[col]
                    for val in series:
                        try:
                            v = float(str(val).strip())
                            eps_val = v
                            break
                        except (ValueError, TypeError):
                            continue
                    break
            if eps_val and eps_val > 0:
                fpe = round(price / eps_val, 2)
                lines.append(f"\n前向PE: {fpe} (当前价 {price} / EPS {eps_val})")
                if fpe > 0 and eps_val > 0:
                    peg = round(fpe / (eps_val * 100), 2) if eps_val > 0 else "N/A"
                    digest_years = round(fpe / 30, 1) if fpe > 0 else "N/A"
                    lines.append(f"前向PEG: {peg}")
                    lines.append(f"估值消化至30x所需年数: {digest_years}")
            else:
                lines.append(f"\n当前价: {price} (EPS数据不足，无法计算前向PE)")

        return "\n".join(lines)
    except Exception as e:
        return f"获取盈利预测失败: {e}"


# ── 2. get_northbound_flow ──────────────────────────────────────────

_NORTHBOUND_CACHE_FILE = "northbound_cache.csv"

def _northbound_cache_path() -> str:
    d = get_config().get("project_dir", os.path.expanduser("~"))
    return os.path.join(d, "dataflows", "data_cache", _NORTHBOUND_CACHE_FILE)


def _save_northbound_snapshot(date_str: str, hgt: float, sgt: float) -> None:
    p = _northbound_cache_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    exists = os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["date", "hgt", "sgt"])
        w.writerow([date_str, hgt, sgt])


def _load_northbound_history(n: int = 20) -> list[tuple[str, float, float]]:
    p = _northbound_cache_path()
    if not os.path.exists(p):
        return []
    rows = []
    with open(p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append((row["date"], float(row["hgt"]), float(row["sgt"])))
            except (ValueError, KeyError):
                continue
    return rows[-n:]


@tool
def get_northbound_flow(
    curr_date: Annotated[str, "Date YYYY-MM-DD"],
    include_history: Annotated[bool, "Include 20-day history"] = False,
) -> str:
    """获取北向资金（沪深股通）当日分钟级净买入数据及历史趋势。
    数据来源：同花顺 hsgtApi。"""
    try:
        # Fetch real-time northbound data
        url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/params/"
        params = {"securityId": "1.000001.HGT"}
        r = requests.get(url, params=params, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0",
                                  "Referer": "https://data.hexin.cn/"})
        data = r.json()
        lines = ["北向资金（沪深股通）实时数据:"]
        hgt_total, sgt_total = 0.0, 0.0

        # Try to parse HGT data
        if isinstance(data, dict) and "data" in data:
            series = data["data"].get("series", [])
            for s in series:
                if s.get("securityId") == "1.000001.HGT":
                    for point in s.get("points", []):
                        hgt_total = float(point.get("total", 0))
                if s.get("securityId") == "1.000002.SGT":
                    for point in s.get("points", []):
                        sgt_total = float(point.get("total", 0))

        # Fallback: try Eastmoney API
        if hgt_total == 0 and sgt_total == 0:
            em_url = "https://push2.eastmoney.com/api/qt/kamt.kline/get"
            em_params = {"fields1": "f1,f2,f3,f4", "fields2": "f51,f52,f53,f54,f55",
                         "klt": 1, "lmt": 1, "secid": "1.000001.HGT"}
            try:
                r2 = requests.get(em_url, params=em_params, timeout=10,
                                  headers={"User-Agent": "Mozilla/5.0"})
                d2 = r2.json()
                if d2.get("data") and d2["data"].get("klines"):
                    k = d2["data"]["klines"][0].split(",")
                    hgt_total = float(k[1]) if len(k) > 1 else 0
            except Exception:
                pass

        # Convert from yuan to 100 million yuan
        hgt_yi = round(hgt_total / 100000000, 2) if hgt_total > 10000 else round(hgt_total, 2)
        sgt_yi = round(sgt_total / 100000000, 2) if sgt_total > 10000 else round(sgt_total, 2)
        total_yi = round(hgt_yi + sgt_yi, 2)

        lines.append(f"  沪股通净买入: {hgt_yi} 亿")
        lines.append(f"  深股通净买入: {sgt_yi} 亿")
        lines.append(f"  北向合计净买入: {total_yi} 亿")

        # Cache today's snapshot
        _save_northbound_snapshot(curr_date, hgt_total, sgt_total)

        if include_history:
            history = _load_northbound_history(20)
            if history:
                lines.append(f"\n近{len(history)}日北向资金历史趋势:")
                lines.append("日期        | 沪股通(亿) | 深股通(亿) | 合计(亿)")
                lines.append("-" * 50)
                for d, h, s in reversed(history):
                    hy = round(h / 100000000, 2) if h > 10000 else round(h, 2)
                    sy = round(s / 100000000, 2) if s > 10000 else round(s, 2)
                    ty = round(hy + sy, 2)
                    lines.append(f"{d} | {hy:>9} | {sy:>9} | {ty:>7}")

        return "\n".join(lines)
    except Exception as e:
        return f"获取北向资金数据失败: {e}"


# ── 3. get_concept_blocks ───────────────────────────────────────────

@tool
def get_concept_blocks(
    ticker: Annotated[str, "A-stock code, e.g. 600519"],
) -> str:
    """获取股票所属概念板块、行业板块、地区板块（来源：百度股市通）。"""
    code = _normalize_ticker(ticker)
    market = "ab" if code.startswith("6") or code.startswith("9") else "ab"
    try:
        url = "https://finance.pae.baidu.com/api/getrelatedblock"
        params = {
            "stock": json.dumps([{"code": code, "market": market, "type": "stock"}]),
            "finClientType": "pc",
        }
        r = requests.get(url, params=params, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0",
                                  "Host": "finance.pae.baidu.com",
                                  "Referer": "https://finance.pae.baidu.com/"})
        data = r.json()
        lines = [f"概念板块分析 - {ticker}:"]
        blocks = data.get("data", {}).get("blocks", []) if isinstance(data, dict) else []
        if not blocks and isinstance(data, list):
            blocks = data

        has_data = False
        for cat in ["industry", "concept", "region"]:
            items = []
            for b in (blocks if isinstance(blocks, list) else []):
                if isinstance(b, dict) and b.get("type") == cat:
                    items.append(b)
            if items:
                has_data = True
                cat_name = {"industry": "行业", "concept": "概念", "region": "地区"}.get(cat, cat)
                lines.append(f"\n【{cat_name}板块】")
                for item in items:
                    name = item.get("name", "")
                    chg = item.get("change", "")
                    chg_str = f"({chg}%)" if chg else ""
                    lines.append(f"  {name} {chg_str}")

        if not has_data:
            lines.append("  未找到板块归属信息")

        return "\n".join(lines)
    except Exception as e:
        return f"获取概念板块失败: {e}"


# ── 4. get_lockup_expiry ───────────────────────────────────────────

@tool
def get_lockup_expiry(
    ticker: Annotated[str, "A-stock code, e.g. 688017"],
    curr_date: Annotated[str, "Current date YYYY-MM-DD"],
    forward_days: Annotated[int, "Look forward days"] = 90,
) -> str:
    """获取限售解禁数据：历史解禁记录 + 未来解禁日历。
    数据来源：东方财富 datacenter。"""
    code = _normalize_ticker(ticker)
    market = "SH" if code.startswith(("6", "9")) else "SZ"
    secucode = f"{code}.{market}"
    lines = [f"限售解禁分析 - {ticker}:"]

    try:
        # Future lockup expirations
        end_date = (datetime.strptime(curr_date, "%Y-%m-%d") + timedelta(days=forward_days)).strftime("%Y-%m-%d")
        params = {
            "reportName": "RPT_LIFT_STAGE",
            "filter": f'(SECURITY_CODE="{secucode}")',
            "pageSize": 20,
        }
        data = _eastmoney_datacenter("RPT_LIFT_STAGE", params)

        if data:
            upcoming = [d for d in data if d.get("LIFT_DATE", "") >= curr_date]
            historical = [d for d in data if d.get("LIFT_DATE", "") < curr_date]

            if upcoming:
                lines.append(f"\n未来解禁（{forward_days}天内）:")
                for d in upcoming[:5]:
                    date = d.get("LIFT_DATE", "")
                    qty = d.get("LIFT_QUANTITY", 0)
                    ratio = d.get("LIFT_RATIO", 0)
                    desc = d.get("LIFT_REASON_DESC", "")
                    try:
                        qty_f = round(float(qty) / 10000, 2) if qty else 0
                    except (ValueError, TypeError):
                        qty_f = qty
                    lines.append(f"  {date} 解禁{ratio}% ({qty_f}万股) {desc}")
            else:
                lines.append(f"\n未来{forward_days}天内无解禁")

            if historical:
                lines.append(f"\n历史解禁记录:")
                for d in historical[:5]:
                    date = d.get("LIFT_DATE", "")
                    ratio = d.get("LIFT_RATIO", 0)
                    desc = d.get("LIFT_REASON_DESC", "")
                    lines.append(f"  {date} 解禁{ratio}% {desc}")
        else:
            lines.append("  未获取到解禁数据")

        return "\n".join(lines)
    except Exception as e:
        return f"获取解禁数据失败: {e}"
