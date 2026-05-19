FROM ghcr.io/kylinmountain/tradingagents-ashare:latest

# Replace frontend dist with rebuilt (token-only login, no sponsor/thanks)
COPY frontend/dist /app/frontend/dist

# Patch auth service with fixed token support
COPY api/services/auth_service.py /app/api/services/auth_service.py

# Copy new agent files (policy_analyst, hot_money_tracker, lockup_watcher)
COPY tradingagents/agents/analysts/policy_analyst.py /app/tradingagents/agents/analysts/policy_analyst.py
COPY tradingagents/agents/analysts/hot_money_tracker.py /app/tradingagents/agents/analysts/hot_money_tracker.py
COPY tradingagents/agents/analysts/lockup_watcher.py /app/tradingagents/agents/analysts/lockup_watcher.py

# Copy signal data tools
COPY tradingagents/agents/utils/signal_data_tools.py /app/tradingagents/agents/utils/signal_data_tools.py

# Copy modified init, agent_utils, trading_graph, setup
COPY tradingagents/agents/__init__.py /app/tradingagents/agents/__init__.py
COPY tradingagents/agents/utils/agent_utils.py /app/tradingagents/agents/utils/agent_utils.py
COPY tradingagents/graph/trading_graph.py /app/tradingagents/graph/trading_graph.py
COPY tradingagents/graph/setup.py /app/tradingagents/graph/setup.py

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "tradingagents-api"]
