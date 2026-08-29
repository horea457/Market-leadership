# Kasugano × Ken Fisher Leadership Dashboard — Methodology v2

## Dashboard objective

This is **not** a long-term factor backtest dashboard.

The default view answers only:
1. Where is leadership now?
2. Is leadership changing over the last 1-6 months?
3. Is the apparent rotation a genuine change or a countertrend/bounce?
4. Where does market sentiment sit in the Fisher cycle?

Default price windows:
- 21 trading days: fast change detection
- 63 trading days: current leadership
- 126 trading days: context
- chart display: ~126 trading days

## Important corrections from v1

### 1. Leadership must be interpreted inside the broad market regime

Do not say "value bear market" or "growth bear market" merely because one style underperforms.
The author's framework treats true bear markets primarily as **broad/global equity-market events**.

Therefore `market_regime_latest.csv` is a mandatory top-level context file.

The regime flag is deliberately mechanical:
- drawdown <= -20%: BEAR_DRAWDOWN
- drawdown <= -10%: CORRECTION
- otherwise use 200DMA / advance context

It is context, not a perfect bear-market classifier.

### 2. Add up-day AND down-day leadership

Raw period return is insufficient.

For every style pair the pipeline now records:
- all-day frequency and magnitude
- SPY up-day frequency and magnitude
- SPY down-day frequency and magnitude

Why:
A category can look weak in aggregate because it falls harder on bad days yet still be the category that repeatedly leads market advances.
This is especially useful for Growth/Tech in a bull-market context.

### 3. Add direct Small Value vs Large Growth contrast

`IWN / IWF` is added as a high-priority pair.

This is not a claim that these are permanent factor premia.
It is a **cycle diagnostic**:
- post-bear / early-bull rebounds often favor beaten-down Small Value
- mature bull phases can favor Large Growth

### 4. Add bounce-effect context

`bounce_context_latest.csv` stores:
- 252D max drawdown
- 126D max drawdown
- rebound from 126D low
- current drawdown from 126D high

A sudden leader should be tested against prior damage:
"Is this new durable leadership, or simply the category that had been hit hardest?"

### 5. Add global context

US sector leadership alone is insufficient.

New layers:
- US vs developed ex-US
- Developed vs EM
- Europe / Japan / China context
- Global sector ETFs vs VT

This matters because the author often separates US Tech leadership from non-US Financials and other global leaders.

### 6. Separate price leadership from structural durability

The main dashboard stays fast:
- RS
- Frequency
- Magnitude
- Rank change
- Breadth
- Up/down-day behavior

Do **not** mix slow structural variables into the same score.

Slow structural overlays should be used to explain durability:
- security/IPO supply
- capital investment / industry capacity
- gross-margin / business quality characteristics
- expectations versus realized results

### 7. Sentiment needs equity supply and expectation error

A VIX-only or valuation-only "euphoria score" is not faithful to the framework.

Sentiment should have five components:
1. Worry/fear residue
2. Expectations gap
3. Equity supply
4. Speculative behavior
5. Positioning / skeptic capitulation

Equity supply receives the largest default weight.

Examples:
- IPO count and proceeds
- SPAC issuance
- follow-on equity issuance
- unprofitable IPO share
- first-day IPO pops
- margin debt / leveraged flows
- consensus forecast error / economic surprise
- earnings revision breadth
- evidence that established bears are capitulating

The automatic market proxy remains a **proxy only**.
Keep qualitative Fisher and Kasugano views separate.

## Current qualitative anchors (as of 2026-08-29)

### Fisher public view
Use `data/reference/fisher_public_view.csv`.

Broad interpretation:
- Optimism -> early euphoria
- AI / Tech exhibit euphoria signs
- but late euphoria is not yet a broad-market conclusion
- skepticism persists elsewhere

### Kasugano current view
Use `data/reference/kasugano_current_view.csv`.

Most recent explicit stage:
- Late Optimism

Additional nuance:
- rate/valuation fear and uncertainty remain
- disappearance of skepticism / visible capitulation by pessimists is a warning trigger

These two views may differ.
**Do not average them into one fake-precision number.**

## Recommended dashboard top row

1. Market regime
2. Fisher public sentiment view
3. Kasugano current sentiment view
4. Current style leader
5. Leadership-change status
6. Breadth

## Recommended leadership interpretation hierarchy

1. Broad-market regime
2. Style leadership
3. US sector leadership
4. Global / regional confirmation
5. Breadth
6. Bounce-effect check
7. Sentiment / supply overlay

## Suggested change labels

### STABLE
21D = 63D = 126D leader

### WATCH
21D conflicts with 63D, but evidence is weak

### ROTATING
21D conflicts with 63D and short-window frequency is >= 60%

### CONFIRMED
21D and 63D agree on the new leader while 126D still reflects the old leader

These are transparent heuristic labels, not statistically optimized trading rules.
