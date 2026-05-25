# Multi-Coin Paper Lab Design

## Goal

Add a separate paper-trading experiment path for testing many crypto symbols at once without changing the existing bot manager, bot configuration behavior, or strategy implementations.

## Scope

The first version is backend-only and focused on the experiment engine. It provides deterministic primitives that can later be exposed through API and UI:

- Split an experiment budget equally across selected symbols.
- Track symbol-specific cash, open positions, and closed trades.
- Evaluate daily experiment windows using Korea time from 09:00 to the next 09:00.
- Summarize daily realized and unrealized results so the user can inspect results every morning and iterate.

## Non-Goals

- Do not modify the existing `backend/bot_manager.py` live loop.
- Do not modify existing strategy files.
- Do not enable real trading.
- Do not claim guaranteed profit.
- Do not build the frontend UI in this first slice.

## Architecture

Create a new isolated package under `backend/core/paper_lab/`.

- `allocator.py`: validates symbols and splits capital equally.
- `daily_window.py`: returns the KST 09:00 experiment window for a timestamp.
- `engine.py`: in-memory experiment engine for paper fills and mark-to-market summaries.

This isolates the experiment from production bot behavior while giving us a tested foundation for later persistence, API routes, and dashboards.

## Success Criteria

- Four symbols and 1,000,000 KRW produce four 250,000 KRW budgets.
- Buying one symbol cannot spend another symbol's budget.
- Buying all selected symbols can open one position per symbol using only that symbol's allocation.
- Selling a position records realized PnL and returns cash to that same symbol bucket.
- Daily windows are aligned to 09:00 KST.
