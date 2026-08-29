from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PROCESSED = DATA / "processed"
REFERENCE = DATA / "reference"

st.set_page_config(
    page_title="Market Leadership Dashboard",
    page_icon="📈",
    layout="wide",
)

# ---------- Styling ----------
st.markdown("""
<style>
.block-container {
    padding-top: 1.0rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}
.metric-card {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 14px;
    padding: 16px 18px;
    min-height: 142px;
    background: white;
}
.metric-label {
    font-size: 0.95rem;
    color: #475569;
    margin-bottom: 0.35rem;
    font-weight: 600;
}
.metric-value {
    font-size: 2.05rem;
    line-height: 1.15;
    font-weight: 700;
    color: #0f172a;
    word-break: break-word;
}
.metric-sub {
    margin-top: 0.75rem;
    font-size: 0.94rem;
    color: #64748b;
    line-height: 1.35;
}
.section-note {
    font-size: 0.94rem;
    color: #64748b;
    margin-top: -6px;
    margin-bottom: 8px;
}
.insight-box {
    border-left: 4px solid #2563eb;
    background: #f8fafc;
    padding: 12px 14px;
    border-radius: 8px;
    margin-top: 10px;
    margin-bottom: 8px;
}
.explain-box {
    background: #f8fafc;
    padding: 11px 13px;
    border-radius: 10px;
    border: 1px solid rgba(128,128,128,.18);
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

PAIR_LABELS = {
    "growth_value": "Growth vs Value (IWF / IWD)",
    "large_small": "Large vs Small (IWB / IWM)",
    "cap_equal": "Cap-weight vs Equal-weight (SPY / RSP)",
    "small_value_large_growth": "Small Value vs Large Growth (IWN / IWF)",
    "us_developed_ex_us": "US vs Developed ex-US (VTI / VEA)",
    "developed_em": "Developed vs Emerging (VEA / VWO)",
    "cyclical_defensive": "Cyclical vs Defensive basket",
}

PAIR_BENCHMARK_LOGIC = {
    "growth_value": "선이 올라가면 Growth(IWF)가 Value(IWD)보다 강합니다.",
    "large_small": "선이 올라가면 Large(IWB)가 Small(IWM)보다 강합니다.",
    "cap_equal": "선이 올라가면 Cap-weight(SPY)가 Equal-weight(RSP)보다 강합니다.",
    "small_value_large_growth": "선이 올라가면 Small Value(IWN)가 Large Growth(IWF)보다 강합니다.",
    "us_developed_ex_us": "선이 올라가면 US(VTI)가 Developed ex-US(VEA)보다 강합니다.",
    "developed_em": "선이 올라가면 Developed(VEA)가 Emerging(VWO)보다 강합니다.",
    "cyclical_defensive": "선이 올라가면 경기민감주 바스켓이 방어주 바스켓보다 강합니다.",
}

SECTOR_NAMES = {
    "XLK": "XLK (Technology)",
    "XLF": "XLF (Financials)",
    "XLI": "XLI (Industrials)",
    "XLE": "XLE (Energy)",
    "XLB": "XLB (Materials)",
    "XLY": "XLY (Consumer Discretionary)",
    "XLP": "XLP (Consumer Staples)",
    "XLV": "XLV (Health Care)",
    "XLU": "XLU (Utilities)",
    "XLRE": "XLRE (Real Estate)",
    "XLC": "XLC (Communication Services)",
}

GLOBAL_SECTOR_NAMES = {
    "IXN": "IXN (Global Technology)",
    "IXG": "IXG (Global Financials)",
    "EXI": "EXI (Global Industrials)",
    "IXC": "IXC (Global Energy)",
    "MXI": "MXI (Global Materials)",
    "RXI": "RXI (Global Consumer Discretionary)",
    "KXI": "KXI (Global Consumer Staples)",
    "IXJ": "IXJ (Global Health Care)",
    "JXI": "JXI (Global Utilities)",
    "REET": "REET (Global Real Estate)",
    "IXP": "IXP (Global Communication Services)",
}

REGION_NAMES = {
    "VTI": "VTI (US Total Market)",
    "VEA": "VEA (Developed ex-US)",
    "VWO": "VWO (Emerging Markets)",
    "VGK": "VGK (Europe)",
    "EWJ": "EWJ (Japan)",
    "MCHI": "MCHI (China)",
}

def read_csv(name, folder=PROCESSED):
    p = folder / name
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()

def has_rows(df):
    return isinstance(df, pd.DataFrame) and len(df) > 0

def pct(x, digits=1):
    try:
        return f"{float(x)*100:.{digits}f}%"
    except Exception:
        return "—"

def card(label, value, sub=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def current_style_leader(style_df):
    x = style_df[style_df["pair_id"].eq("growth_value")]
    if len(x):
        r = x.iloc[0]
        return f"63D: {r.get('leader_63','—')} · 21D: {r.get('leader_21','—')}"
    return "—"

def strongest_change(style_df):
    if not has_rows(style_df):
        return ("—", "—")
    changed = style_df[style_df["change_state"].isin(["WATCH","ROTATING","CONFIRMED"])]
    if len(changed) == 0:
        return ("STABLE", "뚜렷한 회전 신호 없음")
    priority = {"CONFIRMED":3, "ROTATING":2, "WATCH":1}
    changed = changed.assign(_p=changed["change_state"].map(priority).fillna(0))
    rr = changed.sort_values("_p", ascending=False).iloc[0]
    return str(rr["change_state"]), PAIR_LABELS.get(rr["pair_id"], rr["pair_id"])

def style_insight(style_df):
    if not has_rows(style_df):
        return "데이터가 없습니다."
    order = ["growth_value","large_small","cap_equal","cyclical_defensive","us_developed_ex_us","developed_em"]
    lines = []
    for pid in order:
        x = style_df[style_df["pair_id"].eq(pid)]
        if len(x) == 0:
            continue
        r = x.iloc[0]
        lines.append(
            f"- **{PAIR_LABELS.get(pid,pid)}**: 63일 기준 리더는 **{r.get('leader_63','—')}**, "
            f"21일 기준은 **{r.get('leader_21','—')}**, 상태는 **{r.get('change_state','—')}**."
        )
    return "\n".join(lines)

def sector_insight(df, mapping):
    if not has_rows(df):
        return "데이터가 없습니다."
    top = df.sort_values(["rank_21","rank_63"]).head(3)
    emerging = df[df["trend_label"].eq("EMERGING")].sort_values("rank_21")
    weakening = df[df["trend_label"].eq("WEAKENING")].sort_values("rank_21")
    parts = []
    if len(top):
        parts.append("- 최근 상위권: **" + ", ".join(mapping.get(x, x) for x in top["ticker"].tolist()) + "**")
    if len(emerging):
        parts.append("- 최근 떠오르는 축(EMERGING): **" + ", ".join(mapping.get(x, x) for x in emerging["ticker"].tolist()) + "**")
    if len(weakening):
        parts.append("- 최근 약해지는 축(WEAKENING): **" + ", ".join(mapping.get(x, x) for x in weakening["ticker"].tolist()) + "**")
    return "\n".join(parts)

def prep_style_table(style):
    wanted = [
        "growth_value","large_small","cap_equal","small_value_large_growth",
        "us_developed_ex_us","developed_em","cyclical_defensive"
    ]
    df = style[style["pair_id"].isin(wanted)].copy()
    df["Comparison"] = df["pair_id"].map(lambda x: PAIR_LABELS.get(x, x))
    df["Meaning"] = df["pair_id"].map(lambda x: PAIR_BENCHMARK_LOGIC.get(x, ""))
    df = df[[
        "Comparison","Meaning","leader_21","leader_63","leader_126",
        "freq_21","freq_63","freq_126","rs_return_21","rs_return_63","rs_return_126","change_state"
    ]].rename(columns={
        "leader_21":"21D","leader_63":"63D","leader_126":"126D",
        "freq_21":"Freq 21D","freq_63":"Freq 63D","freq_126":"Freq 126D",
        "rs_return_21":"RS 21D","rs_return_63":"RS 63D","rs_return_126":"RS 126D",
        "change_state":"State"
    })
    for c in ["Freq 21D","Freq 63D","Freq 126D","RS 21D","RS 63D","RS 126D"]:
        df[c] = pd.to_numeric(df[c], errors="coerce") * 100
    return df

def prep_sector_table(df, mapping, benchmark_label):
    x = df.copy().sort_values(["rank_21", "rank_63"])
    x["ETF / Group"] = x["ticker"].map(lambda z: mapping.get(z, z))
    x["Benchmark"] = benchmark_label
    x = x[[
        "ETF / Group","Benchmark","rank_21","rank_63","rank_126",
        "rank_change_21_vs_63","freq_21","freq_63","excess_21","excess_63","trend_label"
    ]].rename(columns={
        "rank_21":"Rank 21D","rank_63":"Rank 63D","rank_126":"Rank 126D",
        "rank_change_21_vs_63":"Rank Δ",
        "freq_21":"Freq 21D","freq_63":"Freq 63D",
        "excess_21":"Excess 21D","excess_63":"Excess 63D",
        "trend_label":"Signal"
    })
    for c in ["Freq 21D","Freq 63D","Excess 21D","Excess 63D"]:
        x[c] = pd.to_numeric(x[c], errors="coerce") * 100
    return x

# ---------- Load ----------
style = read_csv("style_leadership_latest.csv")
style_hist = read_csv("style_leadership_history.csv")
sector = read_csv("sector_leadership_latest.csv")
global_sector = read_csv("global_sector_leadership_latest.csv")
region = read_csv("region_leadership_latest.csv")
breadth = read_csv("breadth_latest.csv")
breadth_hist = read_csv("breadth_history.csv")
sentiment = read_csv("sentiment_market_proxy_latest.csv")
regime = read_csv("market_regime_latest.csv")
bounce = read_csv("bounce_context_latest.csv")

fisher = read_csv("fisher_public_view.csv", REFERENCE)
author_view = read_csv("kasugano_current_view.csv", REFERENCE)

# ---------- Header ----------
st.title("Market Leadership Dashboard")
st.caption("최근 1~6개월 리더십 변화 · Fisher sentiment cycle 기반")

if not (has_rows(style) and has_rows(sector)):
    st.warning(
        "아직 가격 기반 계산 데이터가 충분히 생성되지 않았습니다. "
        "GitHub Actions가 성공적으로 끝났는지 확인한 뒤 새로고침하세요."
    )

# ---------- Top cards ----------
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if has_rows(regime):
        r = regime.iloc[-1]
        card("Market regime", str(r.get("mechanical_state","—")), f"ATH 대비 {pct(r.get('spy_drawdown_from_ath'))}")
    else:
        card("Market regime", "—", "")

with c2:
    if has_rows(fisher):
        r = fisher.iloc[-1]
        card("Fisher public view", str(r.get("stage_label","—")), f"Source: {r.get('source_date','—')}")
    else:
        card("Fisher public view", "—", "")

with c3:
    if has_rows(author_view):
        r = author_view.iloc[-1]
        card("Current methodology view", str(r.get("stage_label","—")), f"Confidence: {r.get('confidence','—')}")
    else:
        card("Current methodology view", "—", "")

with c4:
    card("Core style leader", current_style_leader(style), "Growth vs Value 기준")

with c5:
    state, axis = strongest_change(style)
    card("Leadership change", state, axis)

st.divider()

# ---------- Style ----------
st.subheader("1. Style leadership")
st.markdown('<div class="section-note">무엇과 무엇을 비교하는지, 그리고 누가 최근 강한지를 가장 먼저 보는 영역입니다.</div>', unsafe_allow_html=True)

if has_rows(style):
    style_table = prep_style_table(style)
    st.dataframe(
        style_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Comparison": st.column_config.TextColumn(width="medium"),
            "Meaning": st.column_config.TextColumn(width="large"),
            "Freq 21D": st.column_config.NumberColumn(format="%.1f%%"),
            "Freq 63D": st.column_config.NumberColumn(format="%.1f%%"),
            "Freq 126D": st.column_config.NumberColumn(format="%.1f%%"),
            "RS 21D": st.column_config.NumberColumn(format="%.2f%%"),
            "RS 63D": st.column_config.NumberColumn(format="%.2f%%"),
            "RS 126D": st.column_config.NumberColumn(format="%.2f%%"),
        }
    )

    st.markdown("""
    <div class="explain-box">
    <b>이 표를 어떻게 읽나?</b><br>
    - <b>Comparison</b>: 무엇과 무엇을 비교하는지<br>
    - <b>Meaning</b>: 선이 올라갈 때 어느 쪽이 강한지<br>
    - <b>21D / 63D / 126D</b>: 최근 1개월 / 3개월 / 6개월 기준 리더<br>
    - <b>Freq</b>: 그 기간 동안 더 자주 이긴 비율<br>
    - <b>RS</b>: 상대수익률 변화<br>
    - <b>State</b>: STABLE / WATCH / ROTATING / CONFIRMED
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="insight-box">{style_insight(style)}</div>', unsafe_allow_html=True)

    if has_rows(style_hist):
        hist = style_hist.copy()
        hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
        options = hist["pair_id"].dropna().unique().tolist()
        default_idx = options.index("cap_equal") if "cap_equal" in options else 0

        choice = st.selectbox(
            "차트 축",
            options,
            index=default_idx,
            format_func=lambda x: PAIR_LABELS.get(x, x)
        )

        chart = hist[hist["pair_id"].eq(choice)].sort_values("date").copy()
        if len(chart):
            chart[["rs_return_21","rs_return_63","rs_return_126"]] = chart[["rs_return_21","rs_return_63","rs_return_126"]] * 100
            chart = chart.set_index("date")
            st.line_chart(chart[["rs_return_21","rs_return_63","rs_return_126"]], use_container_width=True)
            st.caption(
                f"{PAIR_LABELS.get(choice, choice)} · {PAIR_BENCHMARK_LOGIC.get(choice, '')} "
                "21D/63D/126D 선은 각각 최근 1/3/6개월 기준 상대강도 추세를 보여줍니다."
            )

st.divider()

# ---------- Global / regional ----------
st.subheader("2. Global leadership")
st.markdown('<div class="section-note">미국만 보는 대신, 미국 vs 비미국 / 선진국 vs 신흥국 / 글로벌 섹터까지 같이 봅니다.</div>', unsafe_allow_html=True)

g1, g2 = st.columns(2)

with g1:
    st.markdown("#### 2-1. Region leadership")
    if has_rows(region):
        region_table = prep_sector_table(region, REGION_NAMES, "vs VT (Global Market)")
        st.dataframe(
            region_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ETF / Group": st.column_config.TextColumn(width="medium"),
                "Benchmark": st.column_config.TextColumn(width="small"),
                "Freq 21D": st.column_config.NumberColumn(format="%.1f%%"),
                "Freq 63D": st.column_config.NumberColumn(format="%.1f%%"),
                "Excess 21D": st.column_config.NumberColumn(format="%.2f%%"),
                "Excess 63D": st.column_config.NumberColumn(format="%.2f%%"),
            }
        )
        st.caption("각 지역 ETF가 글로벌 주식시장(VT)보다 최근 얼마나 강했는지 보는 표입니다.")
        st.markdown(f'<div class="insight-box">{sector_insight(region, REGION_NAMES)}</div>', unsafe_allow_html=True)

with g2:
    st.markdown("#### 2-2. Global sector leadership")
    if has_rows(global_sector):
        gsec_table = prep_sector_table(global_sector, GLOBAL_SECTOR_NAMES, "vs VT (Global Market)")
        st.dataframe(
            gsec_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ETF / Group": st.column_config.TextColumn(width="medium"),
                "Benchmark": st.column_config.TextColumn(width="small"),
                "Freq 21D": st.column_config.NumberColumn(format="%.1f%%"),
                "Freq 63D": st.column_config.NumberColumn(format="%.1f%%"),
                "Excess 21D": st.column_config.NumberColumn(format="%.2f%%"),
                "Excess 63D": st.column_config.NumberColumn(format="%.2f%%"),
            }
        )
        st.caption("글로벌 섹터 ETF가 글로벌 시장(VT) 대비 얼마나 강한지 보는 표입니다.")
        st.markdown(f'<div class="insight-box">{sector_insight(global_sector, GLOBAL_SECTOR_NAMES)}</div>', unsafe_allow_html=True)

st.divider()

# ---------- US sectors ----------
st.subheader("3. US sector rotation")
st.markdown('<div class="section-note">미국 섹터는 모두 <b>SPY 대비</b>로 계산합니다. 즉, "미국 시장 전체보다 어느 섹터가 더 강한가?"를 보는 표입니다.</div>', unsafe_allow_html=True)

if has_rows(sector):
    us_table = prep_sector_table(sector, SECTOR_NAMES, "vs SPY (US market)")
    st.dataframe(
        us_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ETF / Group": st.column_config.TextColumn(width="medium"),
            "Benchmark": st.column_config.TextColumn(width="small"),
            "Freq 21D": st.column_config.NumberColumn(format="%.1f%%"),
            "Freq 63D": st.column_config.NumberColumn(format="%.1f%%"),
            "Excess 21D": st.column_config.NumberColumn(format="%.2f%%"),
            "Excess 63D": st.column_config.NumberColumn(format="%.2f%%"),
        }
    )

    st.markdown("""
    <div class="explain-box">
    <b>이 표를 어떻게 읽나?</b><br>
    - <b>Benchmark = SPY</b>: 미국 시장 전체를 이겼는지 여부<br>
    - <b>Rank 21D</b>: 최근 1개월 순위, 1이 가장 강함<br>
    - <b>Rank Δ</b>: 최근 순위 변화. 양수면 최근 개선, 음수면 약화<br>
    - <b>Excess</b>: SPY 대비 초과수익률<br>
    - <b>Signal</b>: LEADER / EMERGING / WEAKENING / NEUTRAL
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="insight-box">{sector_insight(sector, SECTOR_NAMES)}</div>', unsafe_allow_html=True)

    chart_df = sector.copy().sort_values(["rank_21","rank_63"])
    chart_df["ETF / Sector"] = chart_df["ticker"].map(lambda x: SECTOR_NAMES.get(x, x))
    chart_df["excess_21"] = pd.to_numeric(chart_df["excess_21"], errors="coerce") * 100
    chart_df = chart_df.set_index("ETF / Sector")[["excess_21"]]
    st.bar_chart(chart_df, use_container_width=True)
    st.caption("막대가 높을수록 최근 21일 동안 SPY 대비 더 강했습니다. 최근 강한 섹터 순으로 위쪽에 배치됩니다.")

st.divider()

# ---------- Breadth and sentiment ----------
left, right = st.columns(2)

with left:
    st.subheader("4. Breadth")
    st.caption("S&P 500 구성종목 중 같은 기간 SPY를 outperform한 비율")
    if has_rows(breadth):
        b = breadth.copy()
        b["breadth_pct"] = pd.to_numeric(b["breadth_pct"], errors="coerce") * 100
        b = b.sort_values("window")
        st.dataframe(
            b[["window","breadth_pct","n_valid"]].rename(columns={"window":"Window","breadth_pct":"Breadth","n_valid":"Valid stocks"}),
            use_container_width=True,
            hide_index=True,
            column_config={"Breadth": st.column_config.NumberColumn(format="%.1f%%")}
        )
        st.markdown("""
        <div class="explain-box">
        Breadth가 높을수록 소수 대형주만 오른 것이 아니라 시장 전반의 상승 참여가 넓다는 뜻입니다.
        </div>
        """, unsafe_allow_html=True)

        if has_rows(breadth_hist):
            bh = breadth_hist.copy()
            bh["date"] = pd.to_datetime(bh["date"], errors="coerce")
            window_options = sorted([int(x) for x in bh["window"].dropna().unique().tolist()])
            default_idx = 1 if len(window_options) > 1 else 0
            w = st.selectbox("Breadth window", window_options, index=default_idx)
            x = bh[bh["window"].eq(w)].sort_values("date").copy()
            x["breadth_pct"] = pd.to_numeric(x["breadth_pct"], errors="coerce") * 100
            x = x.set_index("date")
            st.line_chart(x[["breadth_pct"]], use_container_width=True)
            st.caption(f"{w}일 기준 breadth 추이입니다. 선이 올라갈수록 상승 참여 폭이 넓어졌다는 뜻입니다.")

with right:
    st.subheader("5. Sentiment cycle")
    if has_rows(sentiment):
        s = sentiment.iloc[-1]
        score = s.get("proxy_score", None)
        stage = s.get("proxy_stage", "—")
        try:
            st.metric("Market-implied proxy", f"{float(score):.0f} / 100", str(stage))
            st.progress(min(max(float(score)/100, 0), 1))
        except Exception:
            st.metric("Market-implied proxy", "—")
        st.caption("보조 프록시일 뿐, Fisher의 실제 proprietary model은 아닙니다.")
        detail = pd.DataFrame({
            "Component":["VIX warmth","HY OAS warmth","SPY trend warmth","SPY momentum warmth"],
            "Score":[s.get("vix_warmth"),s.get("hy_oas_warmth"),s.get("spy_trend_warmth"),s.get("spy_momentum_warmth")]
        })
        st.dataframe(detail, hide_index=True, use_container_width=True)
        st.markdown("""
        <div class="explain-box">
        점수가 높을수록 위험선호와 낙관이 강하다는 뜻입니다. 다만 이 숫자 하나보다 위의 리더십 변화와 함께 해석하는 것이 더 중요합니다.
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ---------- Qualitative anchors ----------
st.subheader("6. Qualitative sentiment anchors")
q1, q2 = st.columns(2)

with q1:
    st.markdown("#### Fisher public view")
    if has_rows(fisher):
        for _, r in fisher.tail(3).iloc[::-1].iterrows():
            st.markdown(f"**{r.get('source_date','')} · {r.get('stage_label','')}**")
            st.write(r.get("dashboard_interpretation", r.get("public_view","")))
    st.caption("공개 인터뷰/코멘트 기준 Fisher 시각")

with q2:
    st.markdown("#### Current methodology view")
    if has_rows(author_view):
        r = author_view.iloc[-1]
        st.markdown(f"**{r.get('stage_label','—')}**")
        st.write(r.get("evidence",""))
        st.caption(f"경계 trigger: {r.get('warning_trigger','—')}")
    st.caption("현재 방법론상 요약된 시각")

if has_rows(bounce):
    with st.expander("7. Bounce effect check"):
        cols = [c for c in ["ticker","group","subgroup","max_drawdown_252","max_drawdown_126","rebound_from_126d_low","current_drawdown_from_126d_high"] if c in bounce.columns]
        show = bounce[cols].copy()
        for c in ["max_drawdown_252","max_drawdown_126","rebound_from_126d_low","current_drawdown_from_126d_high"]:
            if c in show.columns:
                show[c] = pd.to_numeric(show[c], errors="coerce") * 100
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.caption("최근 강세가 새로운 리더십인지, 아니면 직전 큰 낙폭 이후 반등인지 판별하는 보조 표입니다.")

st.caption("Methodology v2 · Weekly refresh after the US Friday close")
