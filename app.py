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

st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}
.metric-card {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 14px;
    padding: 16px 18px;
    min-height: 138px;
    background: white;
}
.metric-label {
    font-size: 0.95rem;
    color: #475569;
    margin-bottom: 0.35rem;
    font-weight: 600;
}
.metric-value {
    font-size: 2rem;
    line-height: 1.15;
    font-weight: 700;
    color: #0f172a;
    word-break: break-word;
}
.metric-sub {
    margin-top: 0.7rem;
    font-size: 0.93rem;
    color: #64748b;
    line-height: 1.35;
}
.section-note {
    font-size: 0.94rem;
    color: #64748b;
    margin-top: -6px;
    margin-bottom: 10px;
}
.explain-box {
    background: #f8fafc;
    padding: 12px 14px;
    border-radius: 10px;
    border: 1px solid rgba(128,128,128,.18);
    margin-top: 10px;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

PAIR_INFO = {
    "growth_value": {
        "label": "성장주 vs 가치주 (IWF / IWD)",
        "meaning": "선이 올라가면 성장주가 가치주보다 강합니다.",
        "left": "성장주",
        "right": "가치주",
    },
    "large_small": {
        "label": "대형주 vs 소형주 (IWB / IWM)",
        "meaning": "선이 올라가면 대형주가 소형주보다 강합니다.",
        "left": "대형주",
        "right": "소형주",
    },
    "cap_equal": {
        "label": "시총가중 vs 동일가중 (SPY / RSP)",
        "meaning": "선이 올라가면 시총가중이 동일가중보다 강합니다.",
        "left": "시총가중",
        "right": "동일가중",
    },
    "small_value_large_growth": {
        "label": "소형가치 vs 대형성장 (IWN / IWF)",
        "meaning": "선이 올라가면 소형가치가 대형성장보다 강합니다.",
        "left": "소형가치",
        "right": "대형성장",
    },
    "us_developed_ex_us": {
        "label": "미국 vs 선진국(미국 제외) (VTI / VEA)",
        "meaning": "선이 올라가면 미국이 선진국(미국 제외)보다 강합니다.",
        "left": "미국",
        "right": "선진국(미국 제외)",
    },
    "developed_em": {
        "label": "선진국 vs 신흥국 (VEA / VWO)",
        "meaning": "선이 올라가면 선진국이 신흥국보다 강합니다.",
        "left": "선진국",
        "right": "신흥국",
    },
    "cyclical_defensive": {
        "label": "경기민감주 vs 방어주",
        "meaning": "선이 올라가면 경기민감주가 방어주보다 강합니다.",
        "left": "경기민감주",
        "right": "방어주",
    },
}

US_SECTOR = {
    "XLK": "XLK (기술)",
    "XLF": "XLF (금융)",
    "XLI": "XLI (산업재)",
    "XLE": "XLE (에너지)",
    "XLB": "XLB (소재)",
    "XLY": "XLY (경기소비재)",
    "XLP": "XLP (필수소비재)",
    "XLV": "XLV (헬스케어)",
    "XLU": "XLU (유틸리티)",
    "XLRE": "XLRE (부동산)",
    "XLC": "XLC (커뮤니케이션서비스)",
}

GLOBAL_SECTOR = {
    "IXN": "IXN (글로벌 기술)",
    "IXG": "IXG (글로벌 금융)",
    "EXI": "EXI (글로벌 산업재)",
    "IXC": "IXC (글로벌 에너지)",
    "MXI": "MXI (글로벌 소재)",
    "RXI": "RXI (글로벌 경기소비재)",
    "KXI": "KXI (글로벌 필수소비재)",
    "IXJ": "IXJ (글로벌 헬스케어)",
    "JXI": "JXI (글로벌 유틸리티)",
    "REET": "REET (글로벌 부동산)",
    "IXP": "IXP (글로벌 커뮤니케이션서비스)",
}

REGION_MAP = {
    "VTI": "VTI (미국)",
    "VEA": "VEA (선진국, 미국 제외)",
    "VWO": "VWO (신흥국)",
    "VGK": "VGK (유럽)",
    "EWJ": "EWJ (일본)",
    "MCHI": "MCHI (중국)",
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
        return f"63일: {r.get('leader_63','—')} · 21일: {r.get('leader_21','—')}"
    return "—"

def strongest_change(style_df):
    if not has_rows(style_df):
        return ("—", "—")
    changed = style_df[style_df["change_state"].isin(["WATCH","ROTATING","CONFIRMED"])]
    if len(changed) == 0:
        return ("안정", "뚜렷한 변화 없음")
    priority = {"CONFIRMED": 3, "ROTATING": 2, "WATCH": 1}
    changed = changed.assign(_p=changed["change_state"].map(priority).fillna(0))
    rr = changed.sort_values("_p", ascending=False).iloc[0]
    return str(rr["change_state"]), PAIR_INFO.get(rr["pair_id"], {}).get("label", rr["pair_id"])

def state_to_kor(x):
    mapping = {
        "STABLE": "안정",
        "WATCH": "관찰",
        "ROTATING": "회전",
        "CONFIRMED": "확인",
        "LEADER": "주도",
        "EMERGING": "부상",
        "WEAKENING": "약화",
        "NEUTRAL": "중립",
    }
    return mapping.get(x, x)

def style_overall_comment(row):
    state = str(row.get("change_state", ""))
    leader21 = str(row.get("leader_21", "—"))
    leader63 = str(row.get("leader_63", "—"))
    leader126 = str(row.get("leader_126", "—"))

    if leader21 == leader63 == leader126:
        return f"단기·중기·반기 흐름이 모두 {leader63} 쪽으로 정렬돼 있습니다."
    if leader21 != leader63 and leader63 == leader126:
        return f"단기 흐름은 {leader21} 쪽으로 흔들리지만, 아직 중심축은 {leader63} 쪽에 있습니다."
    if leader21 == leader63 and leader63 != leader126:
        return f"최근 1~3개월 흐름이 {leader21} 쪽으로 맞춰지며, 이전 추세와 다른 방향으로 전환이 진행 중입니다."
    if state == "ROTATING":
        return f"최근 흐름이 {leader21} 쪽으로 빠르게 이동하고 있어 회전 가능성을 주의해서 볼 구간입니다."
    if state == "CONFIRMED":
        return f"최근 흐름이 이전과 다른 축으로 넘어가는 신호가 비교적 분명합니다."
    return f"단기·중기·장기 신호가 엇갈려 있어 아직 방향을 단정하기 이릅니다."

def style_selected_comment(row, pair_id):
    info = PAIR_INFO[pair_id]
    t21 = f"21일: {row.get('leader_21','—')} 우위"
    t63 = f"63일: {row.get('leader_63','—')} 우위"
    t126 = f"126일: {row.get('leader_126','—')} 우위"
    state = state_to_kor(row.get("change_state", ""))
    overall = style_overall_comment(row)
    return info["meaning"], t21, t63, t126, state, overall

def prep_style_table(style):
    wanted = [
        "growth_value","large_small","cap_equal","small_value_large_growth",
        "us_developed_ex_us","developed_em","cyclical_defensive"
    ]
    df = style[style["pair_id"].isin(wanted)].copy()
    df["비교축"] = df["pair_id"].map(lambda x: PAIR_INFO.get(x, {}).get("label", x))
    df = df[[
        "비교축","leader_21","leader_63","leader_126",
        "freq_21","freq_63","freq_126","rs_return_21","rs_return_63","rs_return_126","change_state"
    ]].rename(columns={
        "leader_21":"21일",
        "leader_63":"63일",
        "leader_126":"126일",
        "freq_21":"빈도 21일",
        "freq_63":"빈도 63일",
        "freq_126":"빈도 126일",
        "rs_return_21":"상대강도 21일",
        "rs_return_63":"상대강도 63일",
        "rs_return_126":"상대강도 126일",
        "change_state":"상태"
    })
    for c in ["빈도 21일","빈도 63일","빈도 126일","상대강도 21일","상대강도 63일","상대강도 126일"]:
        df[c] = pd.to_numeric(df[c], errors="coerce") * 100
    df["상태"] = df["상태"].map(state_to_kor)
    return df

def prep_table(df, mapping, benchmark_label):
    x = df.copy().sort_values(["rank_21", "rank_63"])
    x["대상"] = x["ticker"].map(lambda z: mapping.get(z, z))
    x["비교기준"] = benchmark_label
    x = x[[
        "대상","비교기준","rank_21","rank_63","rank_126",
        "rank_change_21_vs_63","freq_21","freq_63","excess_21","excess_63","trend_label"
    ]].rename(columns={
        "rank_21":"순위 21일",
        "rank_63":"순위 63일",
        "rank_126":"순위 126일",
        "rank_change_21_vs_63":"순위 변화",
        "freq_21":"빈도 21일",
        "freq_63":"빈도 63일",
        "excess_21":"초과수익 21일",
        "excess_63":"초과수익 63일",
        "trend_label":"상태",
    })
    for c in ["빈도 21일","빈도 63일","초과수익 21일","초과수익 63일"]:
        x[c] = pd.to_numeric(x[c], errors="coerce") * 100
    x["상태"] = x["상태"].map(state_to_kor)
    return x

def concise_sector_comment(df, mapping):
    if not has_rows(df):
        return "데이터가 없습니다."
    top = df.sort_values(["rank_21", "rank_63"]).head(2)["ticker"].tolist()
    emerging = df[df["trend_label"].eq("EMERGING")].sort_values("rank_21")["ticker"].tolist()
    weakening = df[df["trend_label"].eq("WEAKENING")].sort_values("rank_21")["ticker"].tolist()

    parts = []
    if top:
        parts.append("상위권은 " + ", ".join(mapping.get(x, x) for x in top) + "입니다.")
    if emerging:
        parts.append("최근에는 " + ", ".join(mapping.get(x, x) for x in emerging[:2]) + " 쪽이 올라오는 모습입니다.")
    if weakening:
        parts.append("반대로 " + ", ".join(mapping.get(x, x) for x in weakening[:2]) + " 쪽은 힘이 둔화됐습니다.")
    return " ".join(parts)

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
    st.warning("아직 데이터가 충분히 생성되지 않았습니다. GitHub Actions 실행 여부를 먼저 확인해 주세요.")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if has_rows(regime):
        r = regime.iloc[-1]
        card("시장 국면", str(r.get("mechanical_state","—")).replace(" / ", " / "), f"ATH 대비 {pct(r.get('spy_drawdown_from_ath'))}")
    else:
        card("시장 국면", "—", "")

with c2:
    if has_rows(fisher):
        r = fisher.iloc[-1]
        card("Fisher 공개 시각", str(r.get("stage_label","—")), f"기준일: {r.get('source_date','—')}")
    else:
        card("Fisher 공개 시각", "—", "")

with c3:
    if has_rows(author_view):
        r = author_view.iloc[-1]
        card("현재 해석", str(r.get("stage_label","—")), f"확신도: {r.get('confidence','—')}")
    else:
        card("현재 해석", "—", "")

with c4:
    card("핵심 스타일", current_style_leader(style), "성장주 vs 가치주 기준")

with c5:
    state, axis = strongest_change(style)
    card("변화 포착", state_to_kor(state), axis)

st.divider()

# ---------- Style ----------
st.subheader("1. 스타일 리더십")
st.markdown('<div class="section-note">무엇이 최근 시장을 이끄는지 보는 핵심 영역입니다.</div>', unsafe_allow_html=True)

if has_rows(style):
    style_table = prep_style_table(style)
    st.dataframe(
        style_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "비교축": st.column_config.TextColumn(width="medium"),
            "빈도 21일": st.column_config.NumberColumn(format="%.1f%%"),
            "빈도 63일": st.column_config.NumberColumn(format="%.1f%%"),
            "빈도 126일": st.column_config.NumberColumn(format="%.1f%%"),
            "상대강도 21일": st.column_config.NumberColumn(format="%.2f%%"),
            "상대강도 63일": st.column_config.NumberColumn(format="%.2f%%"),
            "상대강도 126일": st.column_config.NumberColumn(format="%.2f%%"),
        }
    )

    st.markdown("""
    <div class="explain-box">
    21일은 단기, 63일은 현재 중심축, 126일은 더 넓은 맥락입니다.
    </div>
    """, unsafe_allow_html=True)

    if has_rows(style_hist):
        hist = style_hist.copy()
        hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
        options = hist["pair_id"].dropna().unique().tolist()
        default_idx = options.index("growth_value") if "growth_value" in options else 0

        choice = st.selectbox(
            "설명할 항목 선택",
            options,
            index=default_idx,
            format_func=lambda x: PAIR_INFO.get(x, {}).get("label", x)
        )

        selected_now = style[style["pair_id"].eq(choice)].iloc[0]
        meaning, t21, t63, t126, state_kor, overall = style_selected_comment(selected_now, choice)

        st.markdown("#### 선택 항목 해석")
        st.markdown(
            f"""
- 기준: {meaning}
- {t21}
- {t63}
- {t126}
- 상태: {state_kor}
- 종합: {overall}
            """
        )

        chart = hist[hist["pair_id"].eq(choice)].sort_values("date").copy()
        if len(chart):
            chart[["rs_return_21","rs_return_63","rs_return_126"]] = chart[["rs_return_21","rs_return_63","rs_return_126"]] * 100
            chart = chart.set_index("date")
            st.line_chart(chart[["rs_return_21","rs_return_63","rs_return_126"]], use_container_width=True)
            st.caption("선이 위로 갈수록 왼쪽 항목이 상대적으로 강해졌다는 뜻입니다.")

st.divider()

# ---------- Global ----------
st.subheader("2. 글로벌 리더십")
st.markdown('<div class="section-note">미국만 보지 않고 지역과 글로벌 섹터까지 함께 확인합니다.</div>', unsafe_allow_html=True)

g1, g2 = st.columns(2)

with g1:
    st.markdown("#### 지역 비교")
    if has_rows(region):
        region_table = prep_table(region, REGION_MAP, "글로벌 시장(VT) 대비")
        st.dataframe(
            region_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "대상": st.column_config.TextColumn(width="medium"),
                "비교기준": st.column_config.TextColumn(width="small"),
                "빈도 21일": st.column_config.NumberColumn(format="%.1f%%"),
                "빈도 63일": st.column_config.NumberColumn(format="%.1f%%"),
                "초과수익 21일": st.column_config.NumberColumn(format="%.2f%%"),
                "초과수익 63일": st.column_config.NumberColumn(format="%.2f%%"),
            }
        )
        st.caption("각 지역이 글로벌 전체 시장보다 얼마나 강했는지 보여줍니다.")
        st.markdown(concise_sector_comment(region, REGION_MAP))

with g2:
    st.markdown("#### 글로벌 섹터 비교")
    if has_rows(global_sector):
        gsec_table = prep_table(global_sector, GLOBAL_SECTOR, "글로벌 시장(VT) 대비")
        st.dataframe(
            gsec_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "대상": st.column_config.TextColumn(width="medium"),
                "비교기준": st.column_config.TextColumn(width="small"),
                "빈도 21일": st.column_config.NumberColumn(format="%.1f%%"),
                "빈도 63일": st.column_config.NumberColumn(format="%.1f%%"),
                "초과수익 21일": st.column_config.NumberColumn(format="%.2f%%"),
                "초과수익 63일": st.column_config.NumberColumn(format="%.2f%%"),
            }
        )
        st.caption("글로벌 섹터가 글로벌 전체 시장보다 강했는지 보는 영역입니다.")
        st.markdown(concise_sector_comment(global_sector, GLOBAL_SECTOR))

st.divider()

# ---------- US sector ----------
st.subheader("3. 미국 섹터")
st.markdown('<div class="section-note">미국 각 섹터가 S&P500 전체(SPY)보다 강했는지를 봅니다.</div>', unsafe_allow_html=True)

if has_rows(sector):
    us_table = prep_table(sector, US_SECTOR, "미국 시장(SPY) 대비")
    st.dataframe(
        us_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "대상": st.column_config.TextColumn(width="medium"),
            "비교기준": st.column_config.TextColumn(width="small"),
            "빈도 21일": st.column_config.NumberColumn(format="%.1f%%"),
            "빈도 63일": st.column_config.NumberColumn(format="%.1f%%"),
            "초과수익 21일": st.column_config.NumberColumn(format="%.2f%%"),
            "초과수익 63일": st.column_config.NumberColumn(format="%.2f%%"),
        }
    )

    st.markdown(concise_sector_comment(sector, US_SECTOR))

    chart_df = sector.copy().sort_values(["rank_21", "rank_63"])
    chart_df["대상"] = chart_df["ticker"].map(lambda x: US_SECTOR.get(x, x))
    chart_df["excess_21"] = pd.to_numeric(chart_df["excess_21"], errors="coerce") * 100
    chart_df = chart_df.set_index("대상")[["excess_21"]]
    st.bar_chart(chart_df, use_container_width=True)
    st.caption("막대가 높을수록 최근 21일 동안 SPY보다 강했습니다.")

st.divider()

# ---------- Breadth and sentiment ----------
left, right = st.columns(2)

with left:
    st.subheader("4. 시장 참여 폭")
    st.caption("S&P 500 구성종목 중 같은 기간 SPY를 이긴 비율")
    if has_rows(breadth):
        b = breadth.copy()
        b["breadth_pct"] = pd.to_numeric(b["breadth_pct"], errors="coerce") * 100
        b = b.sort_values("window")
        st.dataframe(
            b[["window","breadth_pct","n_valid"]].rename(columns={"window":"기간","breadth_pct":"참여 폭","n_valid":"유효 종목 수"}),
            use_container_width=True,
            hide_index=True,
            column_config={"참여 폭": st.column_config.NumberColumn(format="%.1f%%")}
        )
        st.markdown("숫자가 높을수록 소수 종목이 아니라 시장 전반이 함께 움직였다는 뜻입니다.")

        if has_rows(breadth_hist):
            bh = breadth_hist.copy()
            bh["date"] = pd.to_datetime(bh["date"], errors="coerce")
            window_options = sorted([int(x) for x in bh["window"].dropna().unique().tolist()])
            default_idx = 1 if len(window_options) > 1 else 0
            w = st.selectbox("시장 참여 폭 기간", window_options, index=default_idx)
            x = bh[bh["window"].eq(w)].sort_values("date").copy()
            x["breadth_pct"] = pd.to_numeric(x["breadth_pct"], errors="coerce") * 100
            x = x.set_index("date")
            st.line_chart(x[["breadth_pct"]], use_container_width=True)
            st.caption("선이 올라갈수록 상승 참여가 넓어졌다는 뜻입니다.")

with right:
    st.subheader("5. 심리 지표")
    if has_rows(sentiment):
        s = sentiment.iloc[-1]
        score = s.get("proxy_score", None)
        stage = s.get("proxy_stage", "—")
        try:
            st.metric("시장 암시 점수", f"{float(score):.0f} / 100", str(stage))
            st.progress(min(max(float(score)/100, 0), 1))
        except Exception:
            st.metric("시장 암시 점수", "—")
        st.caption("보조 지표입니다. 단독으로 보기보다 리더십 변화와 함께 해석하는 게 좋습니다.")
        detail = pd.DataFrame({
            "항목":["VIX","하이일드 스프레드","SPY 추세","SPY 모멘텀"],
            "점수":[s.get("vix_warmth"),s.get("hy_oas_warmth"),s.get("spy_trend_warmth"),s.get("spy_momentum_warmth")]
        })
        st.dataframe(detail, hide_index=True, use_container_width=True)

st.divider()

# ---------- Qualitative anchors ----------
st.subheader("6. 해석 메모")
q1, q2 = st.columns(2)

with q1:
    st.markdown("#### Fisher 공개 시각")
    if has_rows(fisher):
        r = fisher.iloc[-1]
        st.markdown(f"**{r.get('source_date','')} · {r.get('stage_label','')}**")
        st.write(r.get("dashboard_interpretation", r.get("public_view","")))

with q2:
    st.markdown("#### 현재 해석")
    if has_rows(author_view):
        r = author_view.iloc[-1]
        st.markdown(f"**{r.get('stage_label','—')}**")
        st.write(r.get("evidence",""))
        st.caption(f"경계 신호: {r.get('warning_trigger','—')}")

if has_rows(bounce):
    with st.expander("7. 반등 효과 점검"):
        cols = [c for c in ["ticker","group","subgroup","max_drawdown_252","max_drawdown_126","rebound_from_126d_low","current_drawdown_from_126d_high"] if c in bounce.columns]
        show = bounce[cols].copy()
        for c in ["max_drawdown_252","max_drawdown_126","rebound_from_126d_low","current_drawdown_from_126d_high"]:
            if c in show.columns:
                show[c] = pd.to_numeric(show[c], errors="coerce") * 100
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.caption("최근 강세가 추세 전환인지, 큰 낙폭 뒤 반등인지 구분할 때 참고합니다.")

st.caption("매주 미국 금요일 장 마감 후 자동 업데이트")
