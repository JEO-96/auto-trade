# Intraday Scalping Telegram Alert Design

Date: 2026-05-13
Status: Approved for implementation planning

## Summary

Build a Telegram alert system that scans the Korean stock market during regular trading hours and sends only high-quality intraday scalping scenarios. The system does not place orders. It sends a conditional trading scenario with an entry range, dynamic stop, first target, second target, and the evidence behind the signal.

The target user wants a small number of useful alerts, not a noisy feed. The MVP should aim for 3 to 10 alerts per trading day.

## User Decisions

- Market style: intraday scalping / same-day trading.
- Alert scope: not only watchlist stocks; scan the broader Korean market.
- Alert content: include entry price, sell targets, and stop price.
- Stop style: dynamic per signal, based on market structure and volatility.
- Target style: risk/reward based, with context-aware adjustment.
- Alert volume: only the best 3 to 10 opportunities per day.

## Goals

- Find strong short-term momentum candidates from KOSPI/KOSDAQ during the day.
- Send concise Telegram alerts with actionable price levels.
- Favor quality over quantity through strict scoring, cooldowns, and liquidity filters.
- Avoid automatic order execution in the MVP.
- Make every alert explain why the scenario exists and when it becomes invalid.

## Non-Goals

- No automatic buying or selling.
- No promise or implication of guaranteed profit.
- No personalized investment advice based on a user's assets, risk profile, or financial condition.
- No low-liquidity pump-style alerting.
- No unlimited real-time monitoring of every listed instrument in the first version.

## Recommended Approach

Use a strict two-stage scanner.

Stage 1 narrows the market into a small candidate pool using ranking-style data such as trading value, price change, volume spike, and execution strength. Stage 2 watches those candidates in real time using trade and order book data, then emits alerts only when the full setup is clean.

This is preferred over a purely aggressive breakout scanner because the user is not a stock expert and wants few alerts. A stricter system will miss some moves, but it reduces false positives and makes the messages easier to act on.

## Data Sources

Primary real-time source:
- A brokerage OpenAPI that supports Korean stock ranking, real-time trade, and real-time order book data. Korea Investment OpenAPI is a strong fit because its public API catalog includes domestic stock ranking analysis and real-time quote/trade channels.

Optional supporting source:
- Open DART for disclosure/event filters, such as major filings, securities issuance, or other events that can explain abnormal movement.

Existing project assets to reuse:
- Telegram delivery through `backend/notifications.py`.
- Existing backend scheduling/task patterns.
- Existing stock and adapter groundwork where useful, while recognizing that the current `StockDataFetcher` is daily OHLCV-oriented and not sufficient for scalping signals by itself.

## Architecture

### Components

`StockUniverseProvider`

Maintains the tradable universe. The MVP default is KOSPI/KOSDAQ common stocks. It excludes suspended stocks, extremely low-liquidity stocks, ETFs/ETNs/ELWs, SPACs, and preferred shares unless explicitly enabled later.

`CandidateRanker`

Runs during market hours and refreshes a candidate pool from ranking APIs. The first version should track roughly 20 to 50 candidates at a time, selected from trading value, price change, volume spike, and execution strength.

`RealtimeWatcher`

Subscribes to real-time trade and order book streams for the current candidate pool. It maintains short rolling windows for 1-minute and 3-minute price/volume behavior, VWAP, recent highs/lows, spread, and order book imbalance.

`SignalEngine`

Scores each candidate and calculates the scenario:

- Entry range
- Dynamic stop
- 1R target
- 1.5R to 2R target
- Invalid condition
- Evidence summary
- Risk labels such as "VI caution" or "chase caution"

`AlertLimiter`

Prevents noise. It enforces daily alert limits, per-symbol cooldowns, duplicate suppression, and minimum quality thresholds.

`TelegramAlertFormatter`

Creates a concise Korean message that is readable on mobile. The language must frame alerts as conditional scenarios, not guaranteed buy recommendations.

## Signal Logic

A candidate can alert only when these groups are mostly aligned:

- Momentum: short-term price expansion, intraday high reclaim or breakout, and positive slope.
- Liquidity: strong trading value and enough order book depth.
- Participation: volume spike or execution strength compared with recent baseline.
- Price structure: price above VWAP or reclaiming VWAP with strength.
- Tradeability: acceptable spread, no obvious thin order book, and no excessive gap between current price and stop.

The system should exclude signals when:

- Stop distance is greater than 3 percent from entry.
- Spread or order book depth makes execution unrealistic.
- Trading value is too low.
- The stock is already too extended from VWAP or recent base.
- The same symbol already alerted recently.
- VI or halt conditions make the setup hard to execute safely.

## Price Level Calculation

Entry range:

- Based on the current breakout/reclaim area.
- Use a range rather than a single exact price because Telegram delivery and human reaction introduce delay.
- Keep the range narrow enough to preserve the intended risk/reward.

Dynamic stop:

The stop is the price where the scenario is considered wrong. It should be selected from the strongest nearby invalidation level:

- Below the just-broken intraday high or pivot.
- Below the most recent pullback low.
- Below VWAP when VWAP is part of the setup.
- Below a volatility-adjusted 1-minute or 3-minute ATR band.

If the calculated stop is too far away, the system should skip the alert instead of sending a bad trade.

Targets:

- First target: near 1R, adjusted down if a clear nearby resistance exists.
- Second target: 1.5R to 2R, adjusted to the next intraday resistance or round-number area.
- If the setup cannot offer at least a reasonable 1R first target after adjustment, skip it.

## Telegram Message Format

Example:

```text
[초단타 A급 후보] 종목명 / 코드

진입가: 12,350 ~ 12,430원
손절가: 12,180원 (-1.7%)
1차 매도: 12,620원 (+1.6%, 1R)
2차 매도: 12,850원 (+3.4%, 2R)

근거:
- 거래대금 급증
- VWAP 상회
- 당일 고점 재돌파
- 체결강도 우위
- 호가 스프레드 양호

무효:
12,180원 이탈 또는 VWAP 하회 지속

주의:
조건부 시나리오이며 수익을 보장하지 않습니다.
```

## Compliance And Safety

The product should avoid wording like "buy now to make money" or guaranteed-profit language. Alerts should be framed as conditional market scenarios with risk levels and invalidation points.

If this becomes a paid or public feature, legal review is required before launch. Korean capital markets rules can treat business-like investment judgment advice as regulated activity, and similar investment advisory services have advertising and conduct restrictions.

## Error Handling

- If the real-time stream disconnects, reconnect with backoff and suppress alerts until enough fresh data is rebuilt.
- If ranking data is stale, pause candidate refresh and send no alerts.
- If Telegram delivery fails, log the alert and retry within a short bounded window.
- If market status is closed, do not emit new scalping signals.
- If data quality is incomplete for a symbol, skip that symbol.

## Testing Plan

Unit tests:

- Dynamic stop calculation from pivot, VWAP, pullback low, and volatility inputs.
- Target calculation from risk distance and resistance adjustments.
- Signal scoring and exclusion rules.
- Duplicate suppression and daily alert limit.
- Telegram formatting.

Fixture/backtest-style tests:

- Replay historical intraday samples and verify that the engine emits a small number of high-score alerts.
- Confirm that low-liquidity or overly extended symbols are filtered out.

Manual dry run:

- Run for at least several market sessions with Telegram disabled or redirected to an admin chat.
- Compare alerts against charts after market close.
- Adjust thresholds before exposing to users.

## MVP Acceptance Criteria

- Sends no more than 10 alerts per trading day by default.
- Each alert includes entry range, stop, first target, second target, evidence, and invalidation rule.
- No order execution is connected.
- Alerts are suppressed outside regular market hours.
- Same symbol cannot alert repeatedly without cooldown.
- The system can run in dry-run mode and log every candidate rejection reason.
- Tests cover core price-level calculation and alert throttling.

## Implementation Notes

Implementation should start as an internal/admin-only scanner. It should reuse existing Telegram delivery and backend task infrastructure, but the scalping signal logic should live in a separate module so it does not tangle with the existing crypto bot manager.

The first implementation plan should focus on data ingestion, signal calculation, and dry-run logging before enabling real Telegram alerts.
