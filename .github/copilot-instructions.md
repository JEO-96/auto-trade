## Design Context

### Users
- 주 사용자: 암호화폐 모의투자에 관심 있는 한국인 투자자 (초보~중급)
- 핵심 Job: "내 전략이 실제로 돈을 벌 수 있는지 데이터로 검증하고 싶다"

### Brand Personality
- 3단어: 친근 · 심플 · 접근성
- 레퍼런스: TradingView (데이터 중심이면서 접근 가능)

### Design Principles
1. 데이터가 주인공이다 — 장식보다 정보
2. 한 화면에 한 가지 결정 — 복잡성은 점진적 공개
3. 검증이 투자의 시작 — 백테스트 → 모의투자 → 실매매 흐름
4. 실수를 방지하되 막지 않는다
5. 테마 토큰 우선 — 하드코딩 색상 금지, CSS 변수 기반 시맨틱 토큰 사용

### Tech Stack
- Next.js 14, TypeScript, Tailwind CSS, Radix UI, Lucide, Recharts
- 다크 모드 기본 + 라이트 모드, CSS 변수 테마 시스템
- 팔레트: Blue(#3B82F6), Green(#10B981), Purple(#8B5CF6), Red(#EF4444)
- 폰트: Plus Jakarta Sans (제목), Inter (본문)
