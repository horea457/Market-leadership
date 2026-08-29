# Market Leadership Dashboard — Data Layer v2

> **2026-08-29 methodology review:** the repository was expanded after reviewing the author's DCInside posts on style leadership, leading sectors, bounce effects, equity supply and sentiment.

## What changed in v2

- Added **SPY up-day / down-day leadership asymmetry**
- Added **Small Value vs Large Growth** (`IWN/IWF`)
- Added **Cyclical vs Defensive** synthetic equal-weight baskets
- Added **global / regional leadership** and global sector context
- Added **broad-market regime context**
- Added **bounce-effect diagnostics**
- Upgraded sentiment inputs to include **IPO/SPAC/follow-on supply, expectations gap and skeptic capitulation**
- Added separate `Fisher Public View` and `Kasugano Current View`
- Added a sourced post tracker: `data/reference/kasugano_sources.csv`
- Full rationale: `methodology/METHODOLOGY_V2.md`

The main dashboard should remain focused on the latest **1-6 months**. The new files are context layers, not reasons to make the first screen more complicated.

---

최근 **1~6개월의 리더십 변화**를 빠르게 보기 위한 GitHub 데이터 레이어입니다.

핵심 관찰 창:
- **21D**: 변화 탐지
- **63D**: 현재 리더십 판정
- **126D**: 기존 추세 / countertrend 구분
- 대시보드 차트 기본 표시: 최근 약 **6개월(126 거래일)**

## 1. 핵심 파일

대시보드에서는 아래 파일만 읽으면 됩니다.

| 파일 | 용도 |
|---|---|
| `data/processed/style_leadership_latest.csv` | Growth/Value, Large/Small, Cap/Equal 현재 상태 |
| `data/processed/style_leadership_history.csv` | 최근 6개월 스타일 리더십 시계열 |
| `data/processed/sector_leadership_latest.csv` | 11개 섹터 최근 랭킹 / Emerging / Weakening |
| `data/processed/sector_leadership_history.csv` | 최근 6개월 섹터 변화 |
| `data/processed/breadth_latest.csv` | Fisher식 breadth: 시장보다 outperform하는 종목 비율 |
| `data/processed/breadth_history.csv` | Breadth 시계열 |
| `data/processed/sentiment_market_proxy_latest.csv` | 자동 계산 시장심리 프록시 |
| `data/reference/fisher_public_view.csv` | Ken Fisher/Fisher Investments의 실제 공개 sentiment view |

## 2. 리더십 논리

### Style
- Growth / Value = `IWF / IWD`
- Large / Small = `IWB / IWM`
- Cap / Equal = `SPY / RSP`

### 핵심 값
- `rs_return_21/63/126`: 상대가격비율 변화
- `freq_21/63/126`: 두 자산 중 numerator가 일별 수익률에서 이긴 빈도
- `magnitude_21/63/126`: 평균 일별 초과수익
- `upday_freq_*`: SPY 상승일에 numerator가 더 강했던 빈도
- `change_state`: `STABLE / WATCH / ROTATING / CONFIRMED`

### Sector
11개 Select Sector SPDR를 동일한 SPY benchmark에 비교합니다.
현재 순위 자체보다 **21D rank와 63D rank의 변화**를 더 중요하게 봅니다.

`rank_change_21_vs_63 = rank_63 - rank_21`

- 양수: 최근 순위 상승
- 음수: 최근 순위 하락

## 3. Breadth

Fisher Investments가 자주 사용하는 정의에 맞춰:

> S&P 500 구성종목 중 같은 기간 S&P 500을 outperform한 종목 비율

을 계산합니다.

참고:
https://www.fisherinvestments.com/en-us/insights/market-commentary/bad-breadth-doesnt-stop-bull-markets

## 4. Sentiment: Pessimism → Skepticism → Optimism → Euphoria

두 층으로 분리합니다.

### A. `sentiment_market_proxy_latest.csv`
자동 업데이트용 **시장 내재 프록시**입니다.

현재 버전 구성:
- VIX 5년 percentile 역산
- US High Yield OAS 5년 percentile 역산
- SPY 200일 이동평균 대비 위치
- SPY 63일 momentum percentile

0~100으로 변환하지만 **Ken Fisher의 실제 모델이라고 간주하면 안 됩니다.**

### B. `fisher_public_view.csv`
Fisher가 실제로 공개한 qualitative 판단입니다.

현재 기준:
- **2026-05-28:** Ken Fisher — optimism에서 **early stages of euphoria**로 이동 중
- **2026-08-05 / 08-19:** AI/Tech에는 euphoria 징후가 있으나 **late euphoria까지는 멀고**, 다른 영역의 skepticism이 일부 균형을 제공
- **2026-08-21:** US stocks에서 **budding euphoria** 일부 관찰

Sources:
https://www.fisherinvestments.com/en-us/insights/videos/what-ai-tech-stocks-are-signaling-about-this-bull
https://www.fisherinvestments.com/en-us/insights/institutional-investing/executive-summary-q2-2026
https://www.fisherinvestments.com/en-us/insights/institutional-investing/global-market-outlook-and-review-q2-2026
https://www.fisherinvestments.com/en-us/insights/market-commentary/escape-from-cape-fears

대시보드에서는 두 값을 같이 보여주는 것을 권장합니다.

예:
- `Fisher public view: Early euphoria / uneven`
- `Market proxy: 71 / Optimism`

서로 다르면 그 차이 자체가 분석 포인트입니다.

## 5. 현재 공개자료 기반 market context

`data/reference/current_market_context.csv`에는 2026-08-18 Fisher Investments 기사에서 인용한 YTD 시장 데이터를 넣었습니다.

특히:
- S&P 500 Equal Weight 16.3% vs S&P 500 14.0%
- Russell 2000 24.1% vs Nasdaq 100 19.2%
- Energy 41.5%, Technology 24.1%, Industrials 20.8%, Materials 14.8%

즉 최근 시장은 단순한 Mega-cap Tech 단독 leadership으로만 보기 어렵다는 public-data context를 제공합니다.

Source:
https://www.fisherinvestments.com/en-us/insights/market-commentary/a-midsummer-check-in-on-global-stocks

## 6. 최초 실행

```bash
pip install -r requirements.txt
python run_pipeline.py
```

실행 후 `data/raw/`와 `data/processed/`에 실제 최신 CSV가 채워집니다.

## 7. GitHub 자동 업데이트

`.github/workflows/update-data.yml` 포함.

- **매주 금요일 22:30 UTC 자동 실행** (한국시간 토요일 오전 7:30)
- 미국 금요일 장 마감 후 주 1회 전체 리더십 지표 재계산
- 변경된 CSV를 자동 commit / push
- `workflow_dispatch`가 있어 Actions 화면에서 수동 실행 가능

따라서 GitHub에 올린 직후 **Actions → Update market leadership data → Run workflow** 한 번 실행하면 최신 데이터가 생성됩니다.

## 8. 왜 Raw는 5년인가?

대시보드에는 최근 6개월만 보여주지만:
- 리더십 계산은 21/63/126D
- sentiment percentile에는 더 긴 비교구간 필요

때문에 ETF 가격 원천데이터는 5년을 저장합니다.
대시보드 UI는 126 거래일만 잘라서 표시하면 됩니다.

## 9. 다음 대시보드 화면 권장

첫 화면 네 카드:
1. Fisher Sentiment Stage
2. Current Style Leadership
3. Breadth
4. Leadership Change

아래:
- Style 3축 6개월 차트
- Sector rank-change heatmap
- Breadth 21/63/126D
- Emerging / Weakening sector list

`dashboard_contract.json`에 프런트엔드가 읽을 파일과 기본값을 정리해 두었습니다.