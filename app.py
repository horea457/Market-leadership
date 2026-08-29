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
.block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1450px;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 14px;
    padding: 14px 16px;
}
.small-note {font-size: 0.85rem; opacity: 0.72;}
.section-note {font-size: 0.92rem; opacity: .75; margin-top:-6px;}
</style>
""", unsafe_allow_html=True)

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

def num(x, digits=2):
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return "—"

# ---------- Load ----------
style = read_csv("style_leadership_latest.csv")
style_hist = read_csv("style_leadership_history.csv")
sector = read_csv("sector_leadership_latest.csv")
sector_hist = read_csv("sector_leadership_history.csv")
breadth = read_csv("breadth_latest.csv")
breadth_hist = read_csv("breadth_history.csv")
sentiment = read_csv("sentiment_market_proxy_latest.csv")
regime = read_csv("market_regime_latest.csv")
bounce = read_csv("bounce_context_latest.csv")

fisher = read_csv("fisher_public_view.csv", REFERENCE)
kasugano = read_csv("kasugano_current_view.csv", REFERENCE)

# ---------- Header ----------
st.title("Market Leadership Dashboard")
st.caption("최근 1~6개월 리더십 변화 · Fisher sentiment cycle · Kasugano methodology")

data_ready = has_rows(style) and has_rows(sector)

if not data_ready:
    st.warning(
        "아직 가격 기반 계산 데이터가 생성되지 않았습니다. "
        "GitHub의 Actions → Update market leadership data → Run workflow 를 한 번 실행한 뒤 "
        "완료되면 Streamlit 앱을 새로고침하세요."
    )

# ---------- Top cards ----------
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if has_rows(regime):
        r = regime.iloc[-1]
        st.metric("Market regime", str(r.get("mechanical_state", "—")))
        st.caption(f"ATH 대비 {pct(r.get('spy_drawdown_from_ath'))}")
    else:
        st.metric("Market regime", "—")

with c2:
    if has_rows(fisher):
        r = fisher.iloc[-1]
        st.metric("Fisher public view", str(r.get("stage_label", "—")))
        st.caption(f"Source: {r.get('source_date','—')}")
    else:
        st.metric("Fisher public view", "—")

with c3:
    if has_rows(kasugano):
        r = kasugano.iloc[-1]
        st.metric("Kasugano view", str(r.get("stage_label", "—")))
        st.caption(f"Confidence: {r.get('confidence','—')}")
    else:
        st.metric("Kasugano view", "—")

with c4:
    if has_rows(style):
        gv = style[style["pair_id"].eq("growth_value")]
        if len(gv):
            r = gv.iloc[-1]
            st.metric("Core style leader", str(r.get("leader_63", "—")))
            st.caption(f"21D: {r.get('leader_21','—')} · 126D: {r.get('leader_126','—')}")
        else:
            st.metric("Core style leader", "—")
    else:
        st.metric("Core style leader", "—")

with c5:
    if has_rows(style):
        changed = style[style["change_state"].isin(["WATCH","ROTATING","CONFIRMED"])]
        if len(changed):
            priority = {"CONFIRMED":3,"ROTATING":2,"WATCH":1}
            changed = changed.assign(_p=changed["change_state"].map(priority).fillna(0))
            rr = changed.sort_values("_p", ascending=False).iloc[0]
            st.metric("Leadership change", str(rr["change_state"]))
            st.caption(str(rr["pair_id"]).replace("_"," / "))
        else:
            st.metric("Leadership change", "STABLE")
    else:
        st.metric("Leadership change", "—")

st.divider()

# ---------- Style leadership ----------
st.subheader("1. Style leadership")
st.markdown(
    '<div class="section-note">21D = 변화 탐지 · 63D = 현재 리더 · 126D = 기존 추세 확인</div>',
    unsafe_allow_html=True
)

if has_rows(style):
    wanted = [
        "growth_value","large_small","cap_equal",
        "small_value_large_growth","cyclical_defensive",
        "us_developed_ex_us","developed_em"
    ]
    view = style[style["pair_id"].isin(wanted)].copy()
    cols = [
        "pair_id","leader_21","leader_63","leader_126",
        "freq_21","freq_63","freq_126",
        "rs_return_21","rs_return_63","rs_return_126",
        "change_state"
    ]
    cols = [c for c in cols if c in view.columns]
    view = view[cols]
    rename = {
        "pair_id":"Axis","leader_21":"21D","leader_63":"63D","leader_126":"126D",
        "freq_21":"Freq 21D","freq_63":"Freq 63D","freq_126":"Freq 126D",
        "rs_return_21":"RS 21D","rs_return_63":"RS 63D","rs_return_126":"RS 126D",
        "change_state":"State"
    }
    view = view.rename(columns=rename)
    for c in ["Freq 21D","Freq 63D","Freq 126D","RS 21D","RS 63D","RS 126D"]:
        if c in view:
            view[c] = pd.to_numeric(view[c], errors="coerce")
    st.dataframe(
        view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Freq 21D": st.column_config.NumberColumn(format="%.1f%%"),
            "Freq 63D": st.column_config.NumberColumn(format="%.1f%%"),
            "Freq 126D": st.column_config.NumberColumn(format="%.1f%%"),
            "RS 21D": st.column_config.NumberColumn(format="%.2f%%"),
            "RS 63D": st.column_config.NumberColumn(format="%.2f%%"),
            "RS 126D": st.column_config.NumberColumn(format="%.2f%%"),
        }
    )

    if has_rows(style_hist):
        hist = style_hist.copy()
        hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
        axis_options = hist["pair_id"].dropna().unique().tolist()
        default_idx = axis_options.index("growth_value") if "growth_value" in axis_options else 0
        selected_axis = st.selectbox("차트 축", axis_options, index=default_idx)
        chart = hist[hist["pair_id"].eq(selected_axis)].sort_values("date")
        if len(chart):
            chart = chart.set_index("date")
            plot_cols = [c for c in ["rs_return_21","rs_return_63","rs_return_126"] if c in chart.columns]
            if plot_cols:
                st.line_chart(chart[plot_cols], use_container_width=True)
else:
    st.info("Style leadership 데이터 생성 대기 중")

st.divider()

# ---------- Sector leadership ----------
st.subheader("2. US sector rotation")
st.markdown(
    '<div class="section-note">현재 1등보다 21D rank와 63D rank의 변화가 핵심입니다.</div>',
    unsafe_allow_html=True
)

if has_rows(sector):
    sector_view = sector.copy()
    display_cols = [
        "ticker","sector","rank_21","rank_63","rank_126",
        "rank_change_21_vs_63","freq_21","freq_63",
        "excess_21","excess_63","trend_label"
    ]
    display_cols = [c for c in display_cols if c in sector_view.columns]
    sector_view = sector_view[display_cols].rename(columns={
        "ticker":"ETF","sector":"Sector",
        "rank_21":"Rank 21D","rank_63":"Rank 63D","rank_126":"Rank 126D",
        "rank_change_21_vs_63":"Rank Δ",
        "freq_21":"Freq 21D","freq_63":"Freq 63D",
        "excess_21":"Excess 21D","excess_63":"Excess 63D",
        "trend_label":"Signal"
    })
    for c in ["Freq 21D","Freq 63D","Excess 21D","Excess 63D"]:
        if c in sector_view:
            sector_view[c] = pd.to_numeric(sector_view[c], errors="coerce")

    st.dataframe(
        sector_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Freq 21D": st.column_config.NumberColumn(format="%.1f%%"),
            "Freq 63D": st.column_config.NumberColumn(format="%.1f%%"),
            "Excess 21D": st.column_config.NumberColumn(format="%.2f%%"),
            "Excess 63D": st.column_config.NumberColumn(format="%.2f%%"),
        }
    )

    rank_chart = sector.copy()
    if "rank_change_21_vs_63" in rank_chart.columns:
        rank_chart = rank_chart.sort_values("rank_change_21_vs_63", ascending=False)
        rank_chart = rank_chart.set_index("ticker")[["rank_change_21_vs_63"]]
        st.bar_chart(rank_chart, use_container_width=True)
else:
    st.info("Sector leadership 데이터 생성 대기 중")

st.divider()

# ---------- Breadth & sentiment ----------
left, right = st.columns(2)

with left:
    st.subheader("3. Breadth")
    st.caption("S&P 500 구성종목 중 같은 기간 SPY를 outperform한 비율")
    if has_rows(breadth):
        b = breadth.copy()
        b["breadth_pct"] = pd.to_numeric(b["breadth_pct"], errors="coerce")
        b = b.sort_values("window")
        b_display = b[["window","breadth_pct","n_valid"]].copy()
        b_display["breadth_pct"] = b_display["breadth_pct"] * 100
        st.dataframe(
            b_display.rename(columns={"window":"Window","breadth_pct":"Breadth","n_valid":"Valid stocks"}),
            use_container_width=True,
            hide_index=True,
            column_config={"Breadth": st.column_config.NumberColumn(format="%.1f%%")}
        )
    if has_rows(breadth_hist):
        bh = breadth_hist.copy()
        bh["date"] = pd.to_datetime(bh["date"], errors="coerce")
        win = st.selectbox("Breadth window", sorted(bh["window"].dropna().unique()), index=1 if len(bh["window"].dropna().unique()) > 1 else 0)
        x = bh[bh["window"].eq(win)].sort_values("date").set_index("date")
        if len(x):
            st.line_chart(x[["breadth_pct"]], use_container_width=True)

with right:
    st.subheader("4. Sentiment cycle")
    if has_rows(sentiment):
        s = sentiment.iloc[-1]
        score = s.get("proxy_score", None)
        stage = s.get("proxy_stage", "—")
        try:
            st.metric("Market-implied proxy", f"{float(score):.0f} / 100", str(stage))
            st.progress(min(max(float(score)/100, 0), 1))
        except Exception:
            st.metric("Market-implied proxy", "—")
        st.caption("보조 프록시일 뿐 Fisher의 실제 proprietary model이 아닙니다.")

        detail = pd.DataFrame({
            "Component":[
                "VIX warmth","HY OAS warmth","SPY trend warmth","SPY momentum warmth"
            ],
            "Score":[
                s.get("vix_warmth"),s.get("hy_oas_warmth"),
                s.get("spy_trend_warmth"),s.get("spy_momentum_warmth")
            ]
        })
        st.dataframe(detail, hide_index=True, use_container_width=True)
    else:
        st.info("Sentiment proxy 데이터 생성 대기 중")

st.divider()

# ---------- Qualitative interpretation ----------
st.subheader("5. Qualitative sentiment anchors")

q1, q2 = st.columns(2)
with q1:
    st.markdown("#### Fisher public view")
    if has_rows(fisher):
        for _, r in fisher.tail(3).iloc[::-1].iterrows():
            st.markdown(f"**{r.get('source_date','')} · {r.get('stage_label','')}**")
            st.write(r.get("dashboard_interpretation", r.get("public_view","")))
    else:
        st.write("—")

with q2:
    st.markdown("#### Kasugano current view")
    if has_rows(kasugano):
        r = kasugano.iloc[-1]
        st.markdown(f"**{r.get('stage_label','—')}**")
        st.write(r.get("evidence",""))
        st.caption(f"경계 trigger: {r.get('warning_trigger','—')}")
    else:
        st.write("—")

# ---------- Bounce effect ----------
if has_rows(bounce):
    with st.expander("Bounce effect check"):
        cols = [c for c in [
            "ticker","group","subgroup","max_drawdown_252",
            "max_drawdown_126","rebound_from_126d_low","current_drawdown_from_126d_high"
        ] if c in bounce.columns]
        st.dataframe(bounce[cols], use_container_width=True, hide_index=True)

st.caption("Methodology v2 · Weekly refresh after the US Friday close")
