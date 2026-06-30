# CLAUDE.md — Market Analysis AI Agent

## Project Overview

This is an autonomous multi-agent system for market research, data analysis, strategy generation, backtesting, and reporting. It uses an **AutoResearch loop** in `main.py` that cycles through these steps, iteratively updating and looking for convergence based on backtesting results.

## Repository Layout

```
Market-Analysis-AI-Agent/
├── CLAUDE.md                  ← You are here
├── README.md                  ← Project documentation
├── main.py                    ← Entry point; runs the AutoResearch orchestrator loop
├── requirements.txt           ← Python package dependencies
│
├── agents/
│   ├── data_agent.py          ← Fetches historical asset and index prices via yfinance
│   ├── analysis_agent.py      ← Analyzes market data (technical/fundamental indicators)
│   ├── strategy_agent.py      ← Generates trading strategies
│   ├── backtesting_agent.py   ← Simulates strategy performance on historical data
│   └── reporting_agent.py     ← Compiles reports and saves them
│
├── config/
│   └── config.yaml            ← Configuration settings (tickers, indicators, backtest params, loop threshold)
│
├── utils/
│   ├── config.py              ← Configuration loader utility
│   └── logger.py              ← Setup for console and daily file-based logging (using loguru)
│
├── data/                      ← Data folder containing processed, raw, and results subdirectories
└── logs/                      ← Daily log files
```

## Core Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the AutoResearch loop
python main.py
```

## Environment & Configuration

All system configurations are read from `config/config.yaml`. Notable settings include:
- `data_collection.symbols`: List of tickers to research (defaults to AAPL, MSFT, GOOGL, AMZN, TSLA).
- `autoresearch.max_iterations`: Maximum loop iterations (default 10).
- `autoresearch.convergence_threshold`: Minimum performance metric change required to continue (default 0.01).
- `autoresearch.performance_metric`: Metric used for evaluation (default `sharpe_ratio`).

## Logging

Logs are formatted and written to both stdout and rotating daily files in the `logs/` folder using `loguru`.
