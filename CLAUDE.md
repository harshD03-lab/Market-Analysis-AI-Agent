# CLAUDE.md — Market Analysis AI Agent

## Project overview

Autonomous multi-agent system for market research, strategy generation, backtesting, and iterative optimization.
Uses an **AutoResearch loop**: agents collaborate in cycles until a convergence criterion is met or iteration budget exhausted.

## Architecture at a glance

```
User query
    │
    ▼
Orchestrator Agent  ──► ResearchAgent ──► StrategyAgent ──► BacktestAgent ──► OptimizationAgent
        ▲                                                                              │
        └──────────────────── AutoResearch loop (feedback) ───────────────────────────┘
                                        │
                              Shared Memory (ChromaDB + Redis)
                                        │
                              FastAPI  (REST + WebSocket)
                                        │
                  ┌──────────┬──────────┼──────────┐
               Reports    Dashboard  Alerts     Export
```

## Repository layout

```
market-agent/
├── CLAUDE.md                    ← you are here
├── pyproject.toml               ← single source of truth for deps + tools
├── .env.example                 ← copy to .env before running
├── README.md
│
├── agents/
│   ├── base.py                  ← BaseAgent ABC with tool-call scaffolding
│   ├── orchestrator.py          ← plans tasks, routes to specialist agents
│   ├── research.py              ← fetches price data, news, filings
│   ├── strategy.py              ← generates trading strategies via Claude
│   ├── backtest.py              ← simulates strategies on historical data
│   └── optimizer.py             ← iterative refinement + convergence check
│
├── core/
│   ├── auto_research_loop.py    ← main loop: runs agents, checks convergence
│   ├── memory.py                ← ChromaDB vector store + Redis pub/sub
│   ├── message_bus.py           ← typed inter-agent messages
│   ├── tools/
│   │   ├── market_data.py       ← yfinance, Alpha Vantage wrappers
│   │   ├── web_search.py        ← Anthropic web_search tool wrapper
│   │   ├── technical.py         ← TA indicators (RSI, MACD, Bollinger)
│   │   └── news_sentiment.py    ← sentiment scoring via Claude
│   └── prompts/
│       ├── research.py
│       ├── strategy.py
│       ├── backtest.py
│       └── optimizer.py
│
├── backtest/
│   ├── engine.py                ← vectorized event-driven backtester
│   ├── metrics.py               ← Sharpe, Sortino, max-drawdown, VaR
│   └── visualizer.py            ← equity curve + trade chart (plotly)
│
├── api/
│   ├── main.py                  ← FastAPI app factory
│   ├── routes/
│   │   ├── analysis.py          ← POST /analysis/run, GET /analysis/{id}
│   │   ├── strategies.py        ← CRUD for saved strategies
│   │   └── backtests.py         ← GET /backtests/{id}/report
│   ├── schemas.py               ← Pydantic v2 models
│   ├── deps.py                  ← shared FastAPI dependencies
│   └── ws.py                    ← WebSocket streaming endpoint
│
├── config/
│   └── settings.py              ← pydantic-settings BaseSettings
│
├── tests/
│   ├── conftest.py
│   ├── test_agents/
│   ├── test_backtest/
│   └── test_api/
│
└── docker/
    ├── Dockerfile
    └── docker-compose.yml
```

## Core commands

```bash
# Install
uv sync                          # preferred (uses pyproject.toml lock)
# or: pip install -e ".[dev]"

# Run API server
uvicorn api.main:app --reload --port 8000

# Run a one-shot analysis (CLI)
python -m market_agent analyze --ticker AAPL --period 90d

# Run tests
pytest -x -q

# Lint + type-check
ruff check . && mypy .

# Docker (full stack)
docker compose up --build
```

## Environment variables

Copy `.env.example` → `.env` before running.

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Claude API key |
| `ALPHA_VANTAGE_KEY` | optional | Richer fundamental data |
| `REDIS_URL` | optional | Defaults to `redis://localhost:6379` |
| `CHROMADB_PATH` | optional | Defaults to `./data/chroma` |
| `LOG_LEVEL` | optional | `DEBUG` / `INFO` / `WARNING` |
| `MAX_LOOP_ITERATIONS` | optional | AutoResearch loop budget (default 5) |

## Coding conventions

### Python style
- **Python 3.11+** — use `match`, `tomllib`, native `asyncio.TaskGroup`
- **Type hints everywhere** — `mypy --strict` must pass
- Use `ruff` for linting (configured in `pyproject.toml`)
- No bare `except:` — always catch specific exceptions

### Agent design
- Every agent extends `BaseAgent` and exposes an `async def run(ctx: AgentContext) -> AgentResult`
- Agents **never** call the Anthropic API directly — use `self.llm_call(prompt, tools)` from `BaseAgent`
- Agent results are always `AgentResult` dataclasses (not raw dicts)
- Pass state via `AgentContext`, never via global variables

### Tool calls
- All Claude tool-use responses are handled by `BaseAgent._handle_tool_call()`
- New tools go in `core/tools/` and are registered in `BaseAgent.TOOL_REGISTRY`
- Tools must be **pure functions** — no side effects, easy to unit-test

### AutoResearch loop
- Loop lives in `core/auto_research_loop.py`
- Max iterations controlled by `MAX_LOOP_ITERATIONS` env var (default 5)
- Convergence is declared when `OptimizationAgent` returns `converged=True`
  or Sharpe ratio improvement < 0.02 between iterations

### Memory
- Use `memory.store(key, value, metadata)` to persist agent outputs
- Use `memory.search(query, k=5)` for semantic retrieval
- Never store raw PII in memory — hash ticker+date as the key

### API
- All endpoints are `async`
- Long-running analyses return a `task_id` immediately; poll `/analysis/{id}/status`
- WebSocket endpoint `/ws/{task_id}` streams agent events in real time
- Auth is JWT-based (`config/settings.py` → `SECRET_KEY`)

### Error handling
- Agent failures are `AgentError` subclasses — never leak tracebacks to API consumers
- Retry transient failures (network, rate limits) with `tenacity` — max 3 retries, exponential backoff
- Log structured JSON to stdout: `{"event": "agent_done", "agent": "research", "elapsed_ms": 412}`

### Backtesting rules
- No look-ahead bias: indicators computed only on data available at signal time
- Slippage default: 0.1% per trade; commission: $1 flat
- Walk-forward validation preferred over simple train/test split

## Adding a new agent

1. Create `agents/my_agent.py` extending `BaseAgent`
2. Implement `async def run(ctx: AgentContext) -> AgentResult`
3. Register in `agents/__init__.py`
4. Add to `orchestrator.py` routing table
5. Write tests in `tests/test_agents/test_my_agent.py`

## Adding a new tool

1. Create `core/tools/my_tool.py` — a plain async function
2. Define the Anthropic tool schema in `TOOL_SCHEMA` dict at module level
3. Register in `BaseAgent.TOOL_REGISTRY` in `agents/base.py`
4. Write unit tests (mock the external API call)

## Common debugging

```bash
# See all agent messages in real time
LOG_LEVEL=DEBUG python -m market_agent analyze --ticker TSLA

# Replay a saved run without hitting APIs
python -m market_agent replay --run-id <uuid>

# Inspect ChromaDB contents
python -c "from core.memory import Memory; m=Memory(); print(m.list_collections())"
```

## External API rate limits

| API | Free limit | Handled by |
|---|---|---|
| Anthropic | 5 req/min (free tier) | `tenacity` retry in `BaseAgent` |
| Alpha Vantage | 25 req/day (free) | `core/tools/market_data.py` cache |
| yfinance | ~2000/hr (unofficial) | Local disk cache (`joblib.Memory`) |

## Testing philosophy
- Unit-test every tool function with mocked HTTP responses (`pytest-httpx`)
- Integration-test each agent with a real small prompt (marked `@pytest.mark.integration`)
- Backtest engine tested against known strategy results (golden-file tests)
- Run `pytest -m "not integration"` in CI for fast feedback
