import { FormEvent, useState } from 'react'
import { ArrowRight, Loader2, LockKeyhole, Radar, ShieldCheck, Sparkles, TrendingUp } from 'lucide-react'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'

const SIGNALS = [
    { label: '研究框架', value: '14-Agent' },
    { label: '工作区', value: '私有' },
    { label: '报告流', value: '实时' },
]

const AGENT_GROUPS = [
    {
        title: '分析团队',
        count: '6',
        items: ['市场分析', '舆情分析', '新闻分析', '基本面分析', '宏观分析', '主力资金'],
        description: '围绕行情、情绪、新闻、财务、宏观与资金流建立初始判断。',
    },
    {
        title: '研究团队',
        count: '3',
        items: ['多头研究', '空头研究', '研究总监'],
        description: '组织多空辩论，收敛成投资计划与核心分歧。',
    },
    {
        title: '交易与风控',
        count: '4',
        items: ['交易员', '激进风控', '中性风控', '稳健风控'],
        description: '生成执行方案，并从不同风险偏好给出约束。',
    },
    {
        title: '组合决策',
        count: '1',
        items: ['组合经理'],
        description: '综合研究与风控结论，输出最终决策。',
    },
]

export default function Login() {
    const navigate = useNavigate()
    const { setAuth } = useAuthStore()
    const [token, setToken] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleLogin = async (e: FormEvent) => {
        e.preventDefault()
        if (!token.trim()) return
        setLoading(true)
        setError(null)
        try {
            const res = await api.verifyLoginCode('Kovisun@88.com', token.trim())
            setAuth(res.access_token, res.user)
            navigate('/analysis', { replace: true })
        } catch (err) {
            setError(err instanceof Error ? err.message : '登录失败，请检查 Token')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="flex min-h-screen flex-col overflow-hidden bg-[radial-gradient(circle_at_0%_0%,rgba(34,211,238,0.16),transparent_28%),radial-gradient(circle_at_100%_0%,rgba(37,99,235,0.16),transparent_24%),linear-gradient(180deg,#f6f8fb_0%,#edf2f7_100%)] px-5 py-8 dark:bg-[radial-gradient(circle_at_0%_0%,rgba(34,211,238,0.18),transparent_22%),radial-gradient(circle_at_100%_0%,rgba(59,130,246,0.18),transparent_24%),linear-gradient(180deg,#020617_0%,#0b1120_100%)] md:px-10">
            <div className="mx-auto grid flex-1 max-w-7xl grid-cols-1 gap-10 lg:grid-cols-[1.12fr_0.88fr] lg:gap-0">
                <section className="relative flex flex-col justify-between px-2 py-4 lg:px-8 lg:py-10">
                    <div className="absolute left-0 top-0 h-72 w-72 rounded-full bg-cyan-400/10 blur-3xl dark:bg-cyan-400/10" />
                    <div className="absolute bottom-10 right-16 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl dark:bg-blue-500/10" />
                    <div className="relative">
                        <div className="inline-flex items-center gap-2 rounded-full border border-slate-200/80 bg-white/85 px-3 py-1.5 text-xs tracking-[0.22em] text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-900/80 dark:text-slate-400">
                            <Radar className="h-3.5 w-3.5 text-cyan-500" />
                            A 股多智能体研究系统
                        </div>
                        <div className="mt-10 max-w-3xl">
                            <h1 className="text-5xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-white md:text-7xl">
                                为投研决策
                                <span className="mt-2 block bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 bg-clip-text text-transparent">
                                    设计的智能工作台
                                </span>
                            </h1>
                            <p className="mt-6 max-w-2xl text-base leading-8 text-slate-600 dark:text-slate-300 md:text-lg">
                                从市场、舆情、新闻、基本面、宏观、主力资金到风控与组合决策，将 14 个 Agent 的协作过程沉淀为可追踪、可复盘、可持续更新的研究链路。
                            </p>
                        </div>
                        <div className="mt-10 grid gap-3 sm:grid-cols-3">
                            {SIGNALS.map((item) => (
                                <div key={item.label} className="rounded-[28px] border border-slate-200/80 bg-white/88 p-5 shadow-[0_14px_40px_rgba(15,23,42,0.06)] backdrop-blur-sm dark:border-slate-800/90 dark:bg-slate-950 dark:shadow-[0_18px_44px_rgba(2,6,23,0.32)]">
                                    <div className="text-[11px] tracking-[0.18em] text-slate-400 dark:text-slate-500">{item.label}</div>
                                    <div className="mt-3 text-2xl font-semibold text-slate-900 dark:text-slate-50">{item.value}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>
                <section className="flex items-center px-2 py-4 lg:justify-end lg:px-8 lg:py-10">
                    <div className="w-full max-w-md">
                        <div className="rounded-[36px] border border-slate-200/80 bg-white/92 p-7 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur-xl dark:border-slate-800/90 dark:bg-slate-950 dark:shadow-[0_28px_88px_rgba(2,6,23,0.56)]">
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="text-[11px] tracking-[0.22em] text-slate-400 dark:text-slate-500">身份验证</div>
                                    <h2 className="mt-2 text-2xl font-semibold text-slate-950 dark:text-white">进入个人研究空间</h2>
                                </div>
                                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500 via-blue-500 to-indigo-600 text-white shadow-[0_12px_30px_rgba(37,99,235,0.28)]">
                                    <ShieldCheck className="h-6 w-6" />
                                </div>
                            </div>
                            <form onSubmit={handleLogin} className="mt-6 space-y-4">
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-600 dark:text-slate-400">访问令牌</label>
                                    <div className="relative">
                                        <LockKeyhole className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                                        <input type="text" value={token} onChange={(e) => setToken(e.target.value)}
                                            className="input h-12 w-full rounded-2xl pl-11 tracking-[0.2em]"
                                            placeholder="输入访问令牌" required autoFocus />
                                    </div>
                                </div>
                                {error && (
                                    <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/12 dark:text-rose-200">{error}</div>
                                )}
                                <button type="submit" disabled={loading || !token.trim()} className="btn-primary flex h-12 w-full items-center justify-center gap-2 rounded-2xl">
                                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                                    进入研究终端
                                </button>
                            </form>
                            <div className="mt-6 rounded-2xl bg-slate-100/90 px-4 py-3 text-xs leading-6 text-slate-500 dark:border dark:border-slate-800/80 dark:bg-slate-900 dark:text-slate-400">
                                输入访问令牌即可使用。账户将独占保存报告历史、模型密钥与分析上下文。
                            </div>
                        </div>
                    </div>
                </section>
            </div>
            <footer className="mx-auto max-w-7xl pb-4 pt-2 text-center text-xs text-slate-400 dark:text-slate-500">
                <p>&copy; {new Date().getFullYear()} TradingAgents &middot; 内网部署</p>
            </footer>
        </div>
    )
}
