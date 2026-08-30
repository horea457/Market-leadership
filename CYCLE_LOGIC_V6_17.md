# 시장 심리 사이클 판정 로직 V6.17

이 분류기는 수동 `stage_label`을 읽지 않습니다. 현재 대시보드 데이터를 조건식으로 판정합니다.

## 단계
- 비관
- 회의
- 낙관
- 후기 낙관
- 후기 낙관 → 초기 유포리아 후보
- 후기 유포리아: 현재 자동 확정 금지

## 모듈
1. Market Regime: Bull / 조정 / Bear
2. Wall of Worry: VIX + HY spread
3. Expectations Gap: 현재 미연결
4. Equity Supply: 미국 / 글로벌 ex-US 기존 상장기업 발행주식수 변화
5. Speculation: 성장·시총가중·기술 리더십 + 심리 proxy (부분 측정)
6. Leadership / Breadth: 21D breadth + SPY/RSP

## 핵심 원칙
- 점수를 합산해 기계적으로 70점=유포리아로 판정하지 않는다.
- Bull이 아니면 낙관/유포리아 단계로 올라가지 않는다.
- 후기 낙관은 Bull이 진행된 상태에서 공급 증가·뜨거운 리더십·낙관 심리 중 일부가 나타날 때 가능하다.
- 초기 유포리아 후보는 일부 과열 포켓 + 공급 증가 + 걱정의 벽 약화/잔존이 동시에 필요하다.
- 후기 유포리아는 IPO/SPAC·저품질 신규공급·expectations gap가 연결되기 전까지 확정하지 않는다.
