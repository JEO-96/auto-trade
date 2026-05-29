# AGENTS.md — 멀티 에이전트 하네스 엔지니어링 가이드

## 개요

Backtested 프로젝트는 4개의 전담 에이전트로 구성된 하네스 시스템을 사용합니다.
각 에이전트는 독립적 역할과 행동 제약을 가지며, 피드백 루프로 연결됩니다.

## 에이전트 구조

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Coder     │────▶│   Tester    │────▶│  Reviewer   │
│  코드 작성   │     │  테스트/검증  │     │  품질 리뷰   │
│             │◀────│             │◀────│             │
│  .claude/   │실패  │  .claude/   │변경  │  .claude/   │
│  agents/    │피드백 │  agents/    │요청  │  agents/    │
│  coder.md   │     │  tester.md  │     │  reviewer.md│
└─────────────┘     └─────────────┘     └─────────────┘
       │
       │ 전략 관련 작업 시
       ▼
┌─────────────┐
│ Strategist  │
│ 전략 분석    │
│  .claude/   │
│  agents/    │
│strategist.md│
└─────────────┘
```

## 워크플로우

### 일반 개발 (기능 구현, 버그 수정)
```
1. Coder: 코드 작성 → 변경 사항 보고
2. Tester: 빌드 검증 + 코드 품질 + 기능 테스트 → 결과 보고
3. 실패 시 → Coder에게 피드백 → 1로 돌아감
4. 통과 시 → Reviewer: 아키텍처/보안/일관성 리뷰
5. 변경 요청 시 → Coder에게 피드백 → 1로 돌아감
6. 승인 시 → 커밋 + 푸시
```

### 전략 개발
```
1. Strategist: 데이터 분석 + 전략 설계
2. Coder: 전략 클래스 구현 + 등록
3. Tester: 백테스트 실행 + 성과 검증
4. 성과 미달 시 → Strategist에게 결과 전달 → 1로 돌아감
5. 성과 통과 시 → Reviewer: 코드 리뷰
6. 승인 시 → 커밋 + 푸시
```

### 프론트엔드 작업
```
1. Coder: UI 구현 (테마 토큰 필수)
2. Tester: 타입체크 + 컴파일 + 스크린샷 + 접근성
3. 실패 시 → Coder 피드백
4. 통과 시 → Reviewer: 디자인 시스템 일관성 리뷰
5. 승인 시 → 커밋 + 푸시
```

## 에이전트별 파일

| 에이전트 | 파일 | 역할 | 도구 |
|---------|------|------|------|
| Coder | `.claude/agents/coder.md` | 코드 작성 | Edit, Write, Bash |
| Tester | `.claude/agents/tester.md` | 테스트/검증 | Bash, Grep, Read |
| Reviewer | `.claude/agents/reviewer.md` | 코드 리뷰 | Read, Grep |
| Strategist | `.claude/agents/strategist.md` | 전략 분석 | Bash, Read, Write |

## 공유 컨텍스트

모든 에이전트가 참조하는 파일:
- `CLAUDE.md` — 프로젝트 규칙, 아키텍처, 컨벤션
- `.impeccable.md` — 디자인 컨텍스트 (브랜드, 팔레트, 원칙)
- `.github/copilot-instructions.md` — 외부 AI 도구용 가이드

## 품질 게이트

커밋 전 반드시 통과해야 하는 조건:

### 프론트엔드
- [ ] `npx tsc --noEmit` 통과
- [ ] 변경된 페이지 HTTP 200
- [ ] 서버 컴파일 에러 없음
- [ ] 하드코딩 색상 0건
- [ ] console.error 0건

### 백엔드
- [ ] `python -c "import main"` 성공
- [ ] 기존 테스트 통과
- [ ] API 엔드포인트 응답 확인

### 전략
- [ ] BaseStrategy 상속 확인
- [ ] current_idx >= 200 조건 확인
- [ ] 백테스트 최소 20회 거래 발생
- [ ] 수익 팩터 > 1.0
- [ ] 최대 낙폭 < 30%
- [ ] Paper Lab changes: run `cd backend && python -m pytest tests/test_paper_lab_engine.py tests/test_paper_lab_runtime.py tests/test_paper_lab_selector.py tests/test_paper_lab_service.py -q`

---

## Paper Lab Operating Notes

When reviewing daily auto-trading results, do not use git commits as the trading record.
Use the production database tables:

- `paper_lab_daily_snapshots`: daily paper-lab performance windows.
- `paper_lab_run_states`: current paper-lab state, current positions, candidates, provider stats, rebalance history.
- `trade_logs` joined with `bot_configs.paper_trading_mode = TRUE`: regular bot paper-trading SELL logs. For the multi-coin paper lab, losses may be unrealized and stored only in snapshots/state.

Daily paper-lab windows are KST 09:00 to next-day 09:00. A calendar date review should mention the exact window, for example `2026-05-27 09:00 ~ 2026-05-28 09:00 KST`.

As of commit `2da626d`, paper-lab snapshots must include symbol-level `positions` with `symbol`, `qty`, `entry_price`, `mark_price`, `position_value`, `unrealized_pnl`, `return_pct`, and `realized_pnl`.

Paper-lab risk defaults are intentionally conservative:

- `DEFAULT_INTRADAY_REBALANCE_MIN_MINUTES = 180`
- `DEFAULT_INTRADAY_SCORE_IMPROVEMENT = 0.50`

Do not loosen these defaults without checking recent `rebalance_history` and daily snapshots. The 2026-05-27 review showed that frequent candidate rotation made root-cause analysis harder and may amplify chase-entry risk.

After deploy, verify the server commit and runtime defaults from the backend container.
