"""TradingAgents → 交易引擎 下单客户端
Agent 分析完成后调用此模块发指令到交易引擎执行。"""

import json
import logging
import os
from typing import Optional
from datetime import datetime

import requests

logger = logging.getLogger("trade_client")

# 交易引擎地址
ENGINE_URL = os.getenv("TRADING_ENGINE_URL", "http://10.2.2.2:9687")


def place_order(
    symbol: str,
    direction: str,         # "LONG"=买入 "SHORT"=卖出
    price: float,           # 限价，0=市价
    volume: int,            # 股数
    exchange: str = "SSE",
    order_type: str = "LIMIT",
    stop_loss_price: Optional[float] = None,
    take_profit_price: Optional[float] = None,
    confidence: Optional[float] = None,
    reason: Optional[str] = None,
    client_order_id: Optional[str] = None,
) -> dict:
    """发送下单指令到交易引擎

    参数:
        symbol: 股票代码 600519
        direction: LONG=买入 SHORT=卖出
        price: 下单价格
        volume: 数量（股）
        stop_loss_price: 止损价（可选）
        take_profit_price: 止盈价（可选）
        confidence: Agent 置信度
        reason: Agent 下单理由
        client_order_id: 自定义订单号

    返回:
        {"vt_orderid": "...", "risk": {...}}
    """
    if not client_order_id:
        client_order_id = f"TA-{datetime.now().strftime('%Y%m%d%H%M%S')}-{symbol}"

    payload = {
        "symbol": symbol,
        "exchange": exchange,
        "direction": direction,
        "price": price,
        "volume": volume,
        "order_type": order_type,
        "stop_loss_price": stop_loss_price,
        "take_profit_price": take_profit_price,
        "client_order_id": client_order_id,
        "strategy": "TradingAgents",
        "confidence": confidence,
        "reason": reason,
    }

    try:
        resp = requests.post(
            f"{ENGINE_URL}/order",
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code == 200:
            result = resp.json()
            logger.info(f"Order placed: {direction} {symbol} x{volume} @{price} -> {result.get('vt_orderid')}")
            return result
        else:
            error = resp.text
            logger.error(f"Order failed ({resp.status_code}): {error}")
            return {"error": error, "status_code": resp.status_code}
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to trading engine at {ENGINE_URL}")
        return {"error": f"Cannot connect to {ENGINE_URL}"}
    except Exception as e:
        logger.error(f"Order error: {e}")
        return {"error": str(e)}


def cancel_order(vt_orderid: str) -> dict:
    """撤单"""
    try:
        resp = requests.post(
            f"{ENGINE_URL}/order/cancel",
            params={"vt_orderid": vt_orderid},
            timeout=10,
        )
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        return {"error": str(e)}


def get_positions() -> list:
    """查询当前持仓"""
    try:
        resp = requests.get(f"{ENGINE_URL}/position", timeout=10)
        return resp.json() if resp.status_code == 200 else []
    except Exception:
        return []


def get_account() -> list:
    """查询账户"""
    try:
        resp = requests.get(f"{ENGINE_URL}/account", timeout=10)
        return resp.json() if resp.status_code == 200 else []
    except Exception:
        return []


def get_orders() -> list:
    """查询委托"""
    try:
        resp = requests.get(f"{ENGINE_URL}/order/list", timeout=10)
        return resp.json() if resp.status_code == 200 else []
    except Exception:
        return []


def health_check() -> dict:
    """检查交易引擎状态"""
    try:
        resp = requests.get(f"{ENGINE_URL}/health", timeout=5)
        return resp.json() if resp.status_code == 200 else {"status": "unreachable"}
    except Exception:
        return {"status": "unreachable"}
