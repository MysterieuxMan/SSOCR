Use RTK for all Git commands and file reads
Please explain your understanding of each assignment I give you, and ask questions if anything is still unclear.

if you wanna run python, use miniconda
if you wanna run node, use pnpm
if you want to use command `find`, use fd
dont commit code to git by yourself, i will do that

# AGENTS.md — 12-rule template

These rules apply to every task in this project unless explicitly overridden.
Bias: caution over speed on non-trivial work. Use judgment on trivial tasks.

## Rule 1 — Think Before Coding
State assumptions explicitly. If uncertain, ask rather than guess.
Present multiple interpretations when ambiguity exists.
Push back when a simpler approach exists.
Stop when confused. Name what's unclear.

## Rule 2 — Simplicity First
Minimum code that solves the problem. Nothing speculative.
No features beyond what was asked. No abstractions for single-use code.
Test: would a senior engineer say this is overcomplicated? If yes, simplify.

## Rule 3 — Surgical Changes
Touch only what you must. Clean up only your own mess.
Don't "improve" adjacent code, comments, or formatting.
Don't refactor what isn't broken. Match existing style.

## Rule 4 — Goal-Driven Execution
Define success criteria. Loop until verified.
Don't follow steps. Define success and iterate.
Strong success criteria let you loop independently.

## Rule 5 — Use the model only for judgment calls
Use me for: classification, drafting, summarization, extraction.
Do NOT use me for: routing, retries, deterministic transforms.
If code can answer, code answers.


## Rule 7 — Surface conflicts, don't average them
If two patterns contradict, pick one (more recent / more tested).
Explain why. Flag the other for cleanup.
Don't blend conflicting patterns.

## Rule 8 — Read before you write
Before adding code, read exports, immediate callers, shared utilities.
"Looks orthogonal" is dangerous. If unsure why code is structured a way, ask.

## Rule 9 — Tests verify intent, not just behavior
Tests must encode WHY behavior matters, not just WHAT it does.
A test that can't fail when business logic changes is wrong.

## Rule 10 — Checkpoint after every significant step
Summarize what was done, what's verified, what's left.
Don't continue from a state you can't describe back.
If you lose track, stop and restate.

## Rule 11 — Match the codebase's conventions, even if you disagree
Conformance > taste inside the codebase.
If you genuinely think a convention is harmful, surface it. Don't fork silently.

## Rule 12 — Fail loud
"Completed" is wrong if anything was skipped silently.
"Tests pass" is wrong if any were skipped.
Default to surfacing uncertainty, not hiding it.

---

The code that you made will be review by codex openai. So please make sure the code is clean, well-documented, and follows the best practices of software development.

---

## Project: IDX AI Trading Research Assistant

### Architecture
- 8-agent async pipeline per stock, sequentially chained via `PipelineContext`
- Tiered Universe:
  - **Tier 1 (Core Liquid)**: 70 tickers (JII70 / liquid universe), fires every 15 min during regular continuous trading (09:00–15:50 WIB) with `asyncio.Semaphore(5)`
  - **Tier 2 (Broad Universe)**: 509 tickers, fires daily at EOD (16:15 WIB) with `asyncio.Semaphore(8)`
- BEI market-hours guard with full holiday calendar + pre-closing awareness (intraday continuous alerts stop at 15:49:59 WIB)
- Distributed Leader Lock (Redis / Postgres) preventing duplicate scheduler & Telegram execution on scale-out
- Telegram fires only when classification changes AND score ≥ threshold (default 75) during active continuous trading

### Key source locations
- `src/main.py` — CLI entry point, startup, migrations, scheduler
- `src/api_main.py` — FastAPI gateway with distributed leader lock & lifespan
- `src/scheduler/pipeline.py` — per-ticker orchestration + Telegram trigger
- `src/scheduler/scheduler.py` — APScheduler + market-hours guard + tiered cycles
- `src/core/idx_rules.py` & `src/core/idx_holidays.py` — BEI trading session state machine & official holiday calendar
- `src/infrastructure/clustering/leader.py` — distributed leader lock for horizontal scale-out
- `src/agents/*/agent.py` — 8 agents (market_data, technical_analysis, fundamental_analysis, news_sentiment, market_flow, broker_flow, macro_economy, risk_management, decision)
- `src/core/events.py` — `AgentResult` dataclass
- `src/core/models/pipeline.py` — `PipelineContext`
- `src/infrastructure/` — yfinance, newsapi, deepseek, telegram, redis, postgres
- `config/settings.py` — Pydantic BaseSettings (loads `.env`)
- `config/watchlist.yaml` — 579 total tickers (70 core liquid, 509 broad)
- `config/schedule.yaml` — market hours, tiered intervals, and concurrency limits

### Run commands
```bash
# Development (miniconda)
conda activate base
pip install -e ".[dev]"
cp .env.example .env  # fill in secrets
docker compose up -d postgres redis
python -m src.main

# Docker (all services)
docker compose up -d

# Tests
pytest tests/unit/

# Migrations
alembic upgrade head
```

### Agent decision weights
technical_analysis=0.30, fundamental_analysis=0.25, market_flow=0.15,
broker_flow=0.10, macro_economy=0.10, risk_management=0.10 (news_sentiment=0.00, informational only)

### Classification thresholds
≥80 Strong Bullish | ≥62 Bullish | ≥38 Neutral | ≥20 Bearish | else Strong Bearish