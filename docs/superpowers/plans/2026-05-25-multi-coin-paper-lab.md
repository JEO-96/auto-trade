# Multi-Coin Paper Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a separate backend paper-trading lab for equal-budget multi-coin experiments without changing existing bot behavior.

**Architecture:** Add a new `backend/core/paper_lab/` package with small, tested modules for allocation, KST daily windows, and an in-memory experiment engine. Existing bot, strategy, and UI code remain untouched in this first slice.

**Tech Stack:** Python 3.12, pytest, dataclasses, standard-library `zoneinfo`.

---

### Task 1: Equal Capital Allocator

**Files:**
- Create: `backend/core/paper_lab/__init__.py`
- Create: `backend/core/paper_lab/allocator.py`
- Test: `backend/tests/test_paper_lab_allocator.py`

- [ ] Write failing tests for equal allocation, duplicate symbol rejection, empty symbol rejection, and non-positive capital rejection.
- [ ] Run `cd backend && pytest tests/test_paper_lab_allocator.py -v` and verify tests fail because the module does not exist.
- [ ] Implement `allocate_equal_capital(symbols, total_capital)` returning a `dict[str, float]`.
- [ ] Run the allocator tests and verify they pass.

### Task 2: KST 09:00 Daily Window

**Files:**
- Create: `backend/core/paper_lab/daily_window.py`
- Test: `backend/tests/test_paper_lab_daily_window.py`

- [ ] Write failing tests for timestamps before 09:00 KST, after 09:00 KST, and UTC input conversion.
- [ ] Run `cd backend && pytest tests/test_paper_lab_daily_window.py -v` and verify tests fail because the module does not exist.
- [ ] Implement `kst_daily_window(now)` returning `(start, end)` timezone-aware datetimes.
- [ ] Run the daily-window tests and verify they pass.

### Task 3: In-Memory Paper Experiment Engine

**Files:**
- Create: `backend/core/paper_lab/engine.py`
- Test: `backend/tests/test_paper_lab_engine.py`

- [ ] Write failing tests proving each symbol has an isolated budget bucket.
- [ ] Write failing tests proving all selected symbols can open positions using equal budgets.
- [ ] Write failing tests proving sell returns cash to the same symbol and records realized PnL.
- [ ] Write failing tests proving daily summary includes total equity, realized PnL, unrealized PnL, and open position count.
- [ ] Run `cd backend && pytest tests/test_paper_lab_engine.py -v` and verify tests fail because the module does not exist.
- [ ] Implement `PaperLabEngine`, `PaperLabState`, `PaperPosition`, `PaperTrade`, and `SymbolBucket`.
- [ ] Run the engine tests and verify they pass.

### Task 4: Focused Verification

**Files:**
- Verify only.

- [ ] Run `cd backend && pytest tests/test_paper_lab_allocator.py tests/test_paper_lab_daily_window.py tests/test_paper_lab_engine.py -v`.
- [ ] Run `cd backend && python -c "from core.paper_lab.engine import PaperLabEngine; print('ok')"`.
- [ ] Run `git diff --check`.
