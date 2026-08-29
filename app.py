from pathlib import Path
import json
import pandas as pd
import streamlit as st

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PROCESSED = DATA / "processed"
REFERENCE = DATA / "reference"

st.set_page_config(
    page_title="시장 리더십 대시보드",
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
    font-size: 1.9rem;
    line-height: 1.22;
    font-weight: 700;
    color: #0f172a;
    word-break: keep-all;
}
.metric-value-compact {
    font-size: 1.02rem;
    line-height: 1.48;
    font-weight: 600;
    color: #0f172a;
    white-space: normal;
}
.metric-sub-compact {
    margin-top: 0.55rem;
    font-size: 0.86rem;
    color: #64748b;
    line-height: 1.3;
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
.gpt-insight {
    background: #fbfdff;
    border: 1px solid rgba(37,99,235,.16);
    border-left: 4px solid #2563eb;
    padding: 12px 14px;
    border-radius: 10px;
    margin-top: 10px;
    margin-bottom: 14px;
    line-height: 1.55;
}
.gpt-insight p, .gpt-insight ul {
    margin-top: 0.25rem;
    margin-bottom: 0.25rem;
}
.gpt-title {
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 0.35rem;
    font-weight: 600;
}
.explain-box {
    background: #f8fafc;
    padding: 12px 14px;
    border-radius: 10px;
    border: 1px solid rgba(128,128,128,.18);
    margin-top: 10px;
    margin-bottom: 8px;
}
.small-chip {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    background: #eff6ff;
    color: #1d4ed8;
    font-size: 0.82rem;
    margin-right: 6px;
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

PAIR_INFO = {
    "growth_value": {
        "label": "성장주 vs 가치주 (IWF / IWD)",
        "meaning": "선이 올라가면 성장주가 가치주보다 강합니다.",
    },
    "large_small": {
        "label": "대형주 vs 소형주 (IWB / IWM)",
        "meaning": "선이 올라가면 대형주가 소형주보다 강합니다.",
    },
    "cap_equal": {
        "label": "시총가중 vs 동일가중 (SPY / RSP)",
        "meaning": "선이 올라가면 시총가중이 동일가중보다 강합니다.",
    },
    "small_value_large_growth": {
        "label": "소형가치 vs 대형성장 (IWN / IWF)",
        "meaning": "선이 올라가면 소형가치가 대형성장보다 강합니다.",
    },
    "us_developed_ex_us": {
        "label": "미국 vs 선진국(미국 제외) (VTI / VEA)",
        "meaning": "선이 올라가면 미국이 선진국(미국 제외)보다 강합니다.",
    },
    "developed_em": {
        "label": "선진국 vs 신흥국 (VEA / VWO)",
        "meaning": "선이 올라가면 선진국이 신흥국보다 강합니다.",
    },
    "cyclical_defensive": {
        "label": "경기민감주 vs 방어주",
        "meaning": "선이 올라가면 경기민감주가 방어주보다 강합니다.",
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

# ---------- utilities ----------
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
        return round(float(x), digits)
    except Exception:
        return None


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


def compact_card(label, lines, sub=""):
    html_lines = "<br>".join(lines)
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value-compact">{html_lines}</div>
            <div class="metric-sub-compact">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def leader_to_kor(x):
    mapping = {
        "Growth": "성장주",
        "Value": "가치주",
        "Large": "대형주",
        "Small": "소형주",
        "Cap-weight": "시총가중",
        "Equal-weight": "동일가중",
        "Small Value": "소형가치",
        "Large Growth": "대형성장",
        "US": "미국",
        "Developed ex-US": "선진국(미국 제외)",
        "Developed": "선진국",
        "Emerging": "신흥국",
        "Cyclical": "경기민감주",
        "Defensive": "방어주",
    }
    return mapping.get(x, x)


def regime_to_kor(x):
    mapping = {
        "ADVANCE / NEAR-BULL CONTEXT": "상승 진행 / 강세장 근접 국면",
        "ADVANCE": "상승 진행",
        "NEAR-BULL CONTEXT": "강세장 근접 국면",
        "BULL": "강세장",
        "CORRECTION": "조정 국면",
        "BEAR": "약세장",
    }
    return mapping.get(x, x)


def fisher_stage_to_kor(x):
    mapping = {
        "Budding euphoria": "초기 유포리아 조짐",
        "Late Optimism": "후기 낙관",
        "Optimism → Early Euphoria": "낙관 → 초기 유포리아",
        "Euphoria signs, not late euphoria": "유포리아 조짐, 그러나 후기 유포리아는 아님",
        "Skepticism": "회의",
        "Pessimism": "비관",
        "Optimism": "낙관",
        "Euphoria": "유포리아",
        "Early Euphoria": "초기 유포리아",
        "Late Euphoria": "후기 유포리아",
        "Budding Optimism": "낙관 조짐",
    }
    return mapping.get(x, x)


def confidence_to_kor(x):
    mapping = {
        "low": "낮음",
        "medium": "보통",
        "medium-high": "중상",
        "high": "높음",
    }
    return mapping.get(str(x).strip().lower(), x)


def translate_free_text(x):
    if not isinstance(x, str):
        return x
    exact = {
        "Supports early-euphoria monitoring rather than an imminent bear-market call.": "당장 약세장을 경고하기보다, 초기 유포리아 진입 여부를 점검해야 한다는 뜻입니다.",
        "Use as a qualitative anchor, not a mechanical score.": "기계적 점수보다 정성적 참고 신호로 보는 것이 적절합니다.",
        "Overall regime: late optimism / early euphoria with uneven sentiment.": "전체적으로는 후기 낙관~초기 유포리아 구간이지만, 시장 내부 심리는 아직 고르지 않다는 뜻입니다.",
        "Do not label the whole market 'late euphoria'.": "시장 전체를 후기 유포리아로 단정하긴 이르다는 의미입니다.",
        "More visible capitulation by established pessimists / disappearance of the wall of worry.": "기존 비관론자들의 뚜렷한 항복, 그리고 '걱정의 벽' 약화가 주요 경계 신호입니다.",
        "2026-07-31 post explicitly calls the phase late optimism; 2026-08-23 post says rate/valuation fear and uncertainty remain important and historically constructive.": "7월 31일 글에서는 현재 국면을 '후기 낙관'으로 명시했고, 8월 23일 글에서는 금리·밸류에이션 우려와 불확실성이 여전히 남아 있으며 이것이 역사적으로는 오히려 건설적일 수 있다고 봤습니다.",
    }
    if x in exact:
        return exact[x]
    repl = [
        ("late optimism", "후기 낙관"),
        ("Late Optimism", "후기 낙관"),
        ("Budding euphoria", "초기 유포리아 조짐"),
        ("budding euphoria", "초기 유포리아 조짐"),
        ("early euphoria", "초기 유포리아"),
        ("Early Euphoria", "초기 유포리아"),
        ("late euphoria", "후기 유포리아"),
        ("Late Euphoria", "후기 유포리아"),
        ("euphoria", "유포리아"),
        ("Euphoria", "유포리아"),
        ("valuation", "밸류에이션"),
        ("fear", "우려"),
        ("uncertainty", "불확실성"),
    ]
    for a, b in repl:
        x = x.replace(a, b)
    return x


def format_state_badge(text):
    return f'<span class="small-chip">{text}</span>'


def current_leadership_summary(style_df, sector_df, region_df):
    lines = []
    if has_rows(style_df):
        mapping = [
            ("growth_value", "성장/가치"),
            ("cap_equal", "가중방식"),
            ("us_developed_ex_us", "지역"),
        ]
        for pid, label in mapping:
            x = style_df[style_df["pair_id"].eq(pid)]
            if len(x):
                r = x.iloc[0]
                lines.append(f"{label}: 63일 {leader_to_kor(r.get('leader_63'))} · 21일 {leader_to_kor(r.get('leader_21'))}")
    if has_rows(sector_df):
        top = sector_df.sort_values(["rank_21", "rank_63"]).head(2)["ticker"].tolist()
        if top:
            lines.append("미국 상위: " + ", ".join(US_SECTOR.get(t, t) for t in top))
    return lines if lines else ["—"]


def strongest_change(style_df):
    if not has_rows(style_df):
        return ("—", "—")
    changed = style_df[style_df["change_state"].isin(["WATCH", "ROTATING", "CONFIRMED"])]
    if len(changed) == 0:
        return ("안정", "뚜렷한 변화 없음")
    priority = {"CONFIRMED": 3, "ROTATING": 2, "WATCH": 1}
    changed = changed.assign(_p=changed["change_state"].map(priority).fillna(0))
    rr = changed.sort_values("_p", ascending=False).iloc[0]
    return state_to_kor(rr["change_state"]), PAIR_INFO.get(rr["pair_id"], {}).get("label", rr["pair_id"])


def style_overall_comment(row):
    state = str(row.get("change_state", ""))
    leader21 = str(row.get("leader_21", "—"))
    leader63 = str(row.get("leader_63", "—"))
    leader126 = str(row.get("leader_126", "—"))

    if leader21 == leader63 == leader126:
        return f"단기·중기·반기 흐름이 모두 {leader_to_kor(leader63)} 쪽으로 정렬돼 있습니다."
    if leader21 != leader63 and leader63 == leader126:
        return f"단기 흐름은 {leader_to_kor(leader21)} 쪽으로 기울었지만, 중심축은 아직 {leader_to_kor(leader63)} 쪽에 있습니다."
    if leader21 == leader63 and leader63 != leader126:
        return f"최근 1~3개월 흐름이 {leader_to_kor(leader21)} 쪽으로 맞춰지며, 이전 추세와 다른 방향으로 이동 중입니다."
    if state == "ROTATING":
        return f"최근 흐름이 {leader_to_kor(leader21)} 쪽으로 이동하고 있어 회전 가능성을 주의해서 볼 구간입니다."
    if state == "CONFIRMED":
        return "기존 중심축과 다른 방향으로 리더십이 넘어가는 신호가 비교적 분명합니다."
    return "단기·중기·장기 신호가 엇갈려 아직 한 방향으로 단정하기 어렵습니다."


def style_selected_comment(row, pair_id):
    info = PAIR_INFO[pair_id]
    return {
        "기준": info["meaning"],
        "21일": f"{leader_to_kor(row.get('leader_21','—'))} 우위",
        "63일": f"{leader_to_kor(row.get('leader_63','—'))} 우위",
        "126일": f"{leader_to_kor(row.get('leader_126','—'))} 우위",
        "상태": state_to_kor(row.get("change_state", "")),
        "종합": style_overall_comment(row),
    }


def prep_style_table(style):
    wanted = [
        "growth_value","large_small","cap_equal","small_value_large_growth",
        "us_developed_ex_us","developed_em","cyclical_defensive"
    ]
    df = style[style["pair_id"].isin(wanted)].copy()
    df["비교축"] = df["pair_id"].map(lambda x: PAIR_INFO.get(x, {}).get("label", x))
    df["21일"] = df["leader_21"].map(leader_to_kor)
    df["63일"] = df["leader_63"].map(leader_to_kor)
    df["126일"] = df["leader_126"].map(leader_to_kor)
    df = df[[
        "비교축","21일","63일","126일",
        "freq_21","freq_63","freq_126","rs_return_21","rs_return_63","rs_return_126","change_state"
    ]].rename(columns={
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
        parts.append("올라오는 쪽은 " + ", ".join(mapping.get(x, x) for x in emerging[:2]) + "입니다.")
    if weakening:
        parts.append("둔화되는 쪽은 " + ", ".join(mapping.get(x, x) for x in weakening[:2]) + "입니다.")
    return " ".join(parts)


def build_market_snapshot(style, sector, global_sector, region, breadth, sentiment, regime, fisher, author_view):
    snapshot = {}
    if has_rows(regime):
        r = regime.iloc[-1]
        snapshot["시장국면"] = {
            "기계적국면": regime_to_kor(str(r.get("mechanical_state", "—"))),
            "전고점대비": num(r.get("spy_drawdown_from_ath"), 4),
            "21일수익률": num(r.get("spy_return_21"), 4),
            "63일수익률": num(r.get("spy_return_63"), 4),
            "126일수익률": num(r.get("spy_return_126"), 4),
        }
    if has_rows(style):
        rows = []
        for pid in ["growth_value", "large_small", "cap_equal", "cyclical_defensive", "us_developed_ex_us", "developed_em"]:
            x = style[style["pair_id"].eq(pid)]
            if len(x) == 0:
                continue
            r = x.iloc[0]
            rows.append({
                "비교축": PAIR_INFO.get(pid, {}).get("label", pid),
                "21일": leader_to_kor(r.get("leader_21")),
                "63일": leader_to_kor(r.get("leader_63")),
                "126일": leader_to_kor(r.get("leader_126")),
                "21일상대강도": num(r.get("rs_return_21"), 4),
                "63일상대강도": num(r.get("rs_return_63"), 4),
                "126일상대강도": num(r.get("rs_return_126"), 4),
                "상태": state_to_kor(r.get("change_state")),
            })
        snapshot["스타일리더십"] = rows
    if has_rows(region):
        r = region.sort_values(["rank_21", "rank_63"]).head(6).copy()
        snapshot["지역리더십"] = [
            {
                "대상": REGION_MAP.get(row.get("ticker"), row.get("ticker")),
                "21일순위": int(row.get("rank_21")),
                "63일순위": int(row.get("rank_63")),
                "21일초과수익": num(row.get("excess_21"), 4),
                "63일초과수익": num(row.get("excess_63"), 4),
                "상태": state_to_kor(row.get("trend_label")),
            }
            for _, row in r.iterrows()
        ]
    if has_rows(global_sector):
        g = global_sector.sort_values(["rank_21", "rank_63"]).head(6).copy()
        snapshot["글로벌섹터"] = [
            {
                "대상": GLOBAL_SECTOR.get(row.get("ticker"), row.get("ticker")),
                "21일순위": int(row.get("rank_21")),
                "63일순위": int(row.get("rank_63")),
                "21일초과수익": num(row.get("excess_21"), 4),
                "63일초과수익": num(row.get("excess_63"), 4),
                "상태": state_to_kor(row.get("trend_label")),
            }
            for _, row in g.iterrows()
        ]
    if has_rows(sector):
        s = sector.sort_values(["rank_21", "rank_63"]).copy()
        snapshot["미국섹터"] = [
            {
                "대상": US_SECTOR.get(row.get("ticker"), row.get("ticker")),
                "21일순위": int(row.get("rank_21")),
                "63일순위": int(row.get("rank_63")),
                "126일순위": int(row.get("rank_126")),
                "21일초과수익": num(row.get("excess_21"), 4),
                "63일초과수익": num(row.get("excess_63"), 4),
                "상태": state_to_kor(row.get("trend_label")),
            }
            for _, row in s.head(8).iterrows()
        ]
    if has_rows(breadth):
        snapshot["시장참여폭"] = [
            {
                "기간": int(row.get("window")),
                "시장상회비율": num(row.get("breadth_pct"), 4),
                "유효종목수": int(row.get("n_valid")),
            }
            for _, row in breadth.sort_values("window").iterrows()
        ]
    if has_rows(sentiment):
        r = sentiment.iloc[-1]
        snapshot["심리지표"] = {
            "점수": num(r.get("proxy_score"), 2),
            "단계": fisher_stage_to_kor(str(r.get("proxy_stage", "—"))),
            "VIX": num(r.get("vix_warmth"), 3),
            "하이일드": num(r.get("hy_oas_warmth"), 3),
            "SPY추세": num(r.get("spy_trend_warmth"), 3),
            "SPY모멘텀": num(r.get("spy_momentum_warmth"), 3),
        }
    if has_rows(fisher):
        r = fisher.iloc[-1]
        snapshot["Fisher공개시각"] = {
            "기준일": r.get("source_date"),
            "단계": fisher_stage_to_kor(str(r.get("stage_label", "—"))),
            "해석": translate_free_text(r.get("dashboard_interpretation", r.get("public_view", ""))),
        }
    if has_rows(author_view):
        r = author_view.iloc[-1]
        snapshot["현재해석"] = {
            "단계": fisher_stage_to_kor(str(r.get("stage_label", "—"))),
            "근거": translate_free_text(r.get("evidence", "")),
            "경계신호": translate_free_text(r.get("warning_trigger", "")),
        }
    return snapshot


def build_style_chart_snapshot(style_df, style_hist_df, pair_id):
    current = style_df[style_df["pair_id"].eq(pair_id)].iloc[0]
    recent = style_hist_df[style_hist_df["pair_id"].eq(pair_id)].sort_values("date").tail(12).copy()
    recent[["rs_return_21", "rs_return_63", "rs_return_126"]] = recent[["rs_return_21", "rs_return_63", "rs_return_126"]].apply(pd.to_numeric, errors="coerce")
    return {
        "비교축": PAIR_INFO[pair_id]["label"],
        "의미": PAIR_INFO[pair_id]["meaning"],
        "현재": {
            "21일리더": leader_to_kor(current.get("leader_21")),
            "63일리더": leader_to_kor(current.get("leader_63")),
            "126일리더": leader_to_kor(current.get("leader_126")),
            "상태": state_to_kor(current.get("change_state")),
            "21일상대강도": num(current.get("rs_return_21"), 4),
            "63일상대강도": num(current.get("rs_return_63"), 4),
            "126일상대강도": num(current.get("rs_return_126"), 4),
        },
        "최근추이": recent[["date", "rs_return_21", "rs_return_63", "rs_return_126"]].where(pd.notna(recent), None).to_dict("records")
    }


def build_cross_section_snapshot(df, mapping, benchmark_label, top_n=6):
    x = df.sort_values(["rank_21", "rank_63"]).copy()
    use = x.head(top_n)
    return {
        "비교기준": benchmark_label,
        "상위": [
            {
                "대상": mapping.get(r.get("ticker"), r.get("ticker")),
                "21일순위": int(r.get("rank_21")),
                "63일순위": int(r.get("rank_63")),
                "126일순위": int(r.get("rank_126")),
                "21일초과수익": num(r.get("excess_21"), 4),
                "63일초과수익": num(r.get("excess_63"), 4),
                "상태": state_to_kor(r.get("trend_label")),
            }
            for _, r in use.iterrows()
        ],
        "부상": [mapping.get(r.get("ticker"), r.get("ticker")) for _, r in x[x["trend_label"].eq("EMERGING")].head(3).iterrows()],
        "약화": [mapping.get(r.get("ticker"), r.get("ticker")) for _, r in x[x["trend_label"].eq("WEAKENING")].head(3).iterrows()],
    }


def build_breadth_snapshot(breadth_df, breadth_hist_df, window):
    latest = breadth_df.sort_values("window").copy()
    hist = breadth_hist_df[breadth_hist_df["window"].eq(window)].sort_values("date").tail(20).copy()
    hist["breadth_pct"] = pd.to_numeric(hist["breadth_pct"], errors="coerce")
    return {
        "선택기간": int(window),
        "현재표": [
            {
                "기간": int(r.get("window")),
                "시장상회비율": num(r.get("breadth_pct"), 4),
                "유효종목수": int(r.get("n_valid")),
            } for _, r in latest.iterrows()
        ],
        "추이": hist[["date", "breadth_pct"]].where(pd.notna(hist), None).to_dict("records")
    }


def build_sentiment_snapshot(sentiment_df):
    r = sentiment_df.iloc[-1]
    return {
        "시장암시점수": num(r.get("proxy_score"), 2),
        "단계": fisher_stage_to_kor(str(r.get("proxy_stage", "—"))),
        "세부": {
            "VIX": num(r.get("vix_warmth"), 3),
            "하이일드스프레드": num(r.get("hy_oas_warmth"), 3),
            "SPY추세": num(r.get("spy_trend_warmth"), 3),
            "SPY모멘텀": num(r.get("spy_momentum_warmth"), 3),
        }
    }


@st.cache_data(show_spinner=False, persist="disk")
def generate_gpt_text(cache_key, model_name, system_prompt, payload_json):
    if OpenAI is None:
        return None, "openai 패키지가 설치되지 않았습니다."
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        return None, "Streamlit Secrets에 OPENAI_API_KEY가 없습니다."
    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model=model_name,
            instructions=system_prompt,
            input=payload_json,
            max_output_tokens=800,
        )
        return response.output_text.strip(), None
    except Exception as exc:
        return None, str(exc)


def render_gpt_box(text, caption=None):
    title_html = f'<div class="gpt-title">{caption}</div>' if caption else ''
    html = f'<div class="gpt-insight">{title_html}{text}</div>'
    st.markdown(html, unsafe_allow_html=True)


def fallback_main_insight(style, sector, region, breadth):
    lines = []
    if has_rows(style):
        gv = style[style["pair_id"].eq("growth_value")].iloc[0]
        ce = style[style["pair_id"].eq("cap_equal")].iloc[0]
        ux = style[style["pair_id"].eq("us_developed_ex_us")].iloc[0]
        lines.append(f"<b>핵심 해석</b>: 성장/가치는 21일 {leader_to_kor(gv.get('leader_21'))}, 63일 {leader_to_kor(gv.get('leader_63'))} 우위입니다. 가중방식은 21일 {leader_to_kor(ce.get('leader_21'))}, 지역은 63일 {leader_to_kor(ux.get('leader_63'))} 쪽이 앞섭니다.")
    if has_rows(sector):
        top = sector.sort_values(["rank_21", "rank_63"]).head(2)["ticker"].tolist()
        if top:
            lines.append("<b>체크포인트</b>: 미국 섹터 상위는 " + ", ".join(US_SECTOR.get(t, t) for t in top) + "입니다.")
    if has_rows(breadth):
        b = breadth[breadth["window"].eq(21)]
        if len(b):
            lines.append(f"<b>제언</b>: 21일 시장 참여 폭은 {pct(b.iloc[0].get('breadth_pct'))}입니다. 리더십이 확산되는지, 일부 종목에 머무는지 먼저 확인하는 것이 좋습니다.")
    return "".join(f"<p>{x}</p>" for x in lines)


def fallback_style_chart_insight(snapshot):
    cur = snapshot["현재"]
    return (
        f"<p><b>판정</b>: 21일 {cur['21일리더']}, 63일 {cur['63일리더']}, 126일 {cur['126일리더']} 우위입니다.</p>"
        f"<p><b>체크</b>: 단기 신호가 중기 중심축으로 이어지는지 확인하면 됩니다.</p>"
    )


def fallback_cross_section(snapshot):
    top = ", ".join([x["대상"] for x in snapshot.get("상위", [])[:3]])
    emerging = ", ".join(snapshot.get("부상", [])[:2])
    weakening = ", ".join(snapshot.get("약화", [])[:2])
    parts = [f"<p><b>주도</b>: {top}</p>"]
    if emerging:
        parts.append(f"<p><b>변화</b>: 부상하는 축은 {emerging}</p>")
    if weakening:
        parts.append(f"<p><b>체크</b>: 약화되는 축은 {weakening}</p>")
    return "".join(parts)


def fallback_breadth(snapshot):
    rows = snapshot.get("현재표", [])
    if not rows:
        return "<p>데이터가 없습니다.</p>"
    chosen = [r for r in rows if r["기간"] == snapshot["선택기간"]]
    if chosen:
        val = chosen[0]["시장상회비율"]
        return f"<p><b>판정</b>: {snapshot['선택기간']}일 참여 폭은 {val*100:.1f}%입니다.</p><p><b>체크</b>: 수치가 낮으면 상승이 일부 종목에 집중됐을 가능성이 큽니다.</p>"
    return "<p>시장 참여 폭을 통해 상승 확산 여부를 확인할 수 있습니다.</p>"


MAIN_PROMPT = """
너는 글로벌 주식시장 리더십을 해석하는 투자 리서치 보조자다.
JSON만 근거로 한국어로 작성한다.
규칙:
1. 정확히 3개 불릿만 작성한다.
2. 제목은 반드시 "핵심 해석", "체크포인트", "제언"만 사용한다.
3. 각 불릿은 1~2문장, 최대 70자 안팎으로 짧게 쓴다.
4. 성장/가치뿐 아니라 시총가중/동일가중, 미국/비미국, 섹터 흐름을 함께 반영한다.
5. 21일과 63·126일이 다르면 단기 변화와 중기 중심축을 구분한다.
6. breadth는 확산 여부, 심리 지표는 보조 신호로만 요약한다.
7. 매수/매도 추천 말고 이번 주 관찰 포인트를 제시한다.
8. 도취라는 단어는 쓰지 말고 필요하면 유포리아를 사용한다.
9. 문장과 표현을 반복하지 말라.
"""

STYLE_CHART_PROMPT = """
너는 특정 리더십 비교축 차트를 해석한다.
규칙:
1. 3개 불릿만 작성한다.
2. 제목은 "판정", "의미", "체크"를 사용한다.
3. 각 불릿은 1문장 위주로 짧게 쓴다.
4. 21일·63일·126일 리더와 상태를 함께 반영한다.
5. 반복 표현을 피하고, 투자 추천은 하지 말라.
"""

CROSS_SECTION_PROMPT = """
너는 섹터·지역 단면 데이터를 해석한다.
규칙:
1. 3개 불릿만 작성한다.
2. 제목은 "주도", "변화", "체크"를 사용한다.
3. 각 불릿은 1문장, 최대 70자 안팎으로 짧게 쓴다.
4. 상위권, 부상, 약화를 구체적 대상명으로 적는다.
5. 비교기준을 앞에 명시한다.
"""

BREADTH_PROMPT = """
너는 시장 breadth 차트를 해석한다.
규칙:
1. 3개 불릿만 작성한다.
2. 제목은 "판정", "의미", "체크"를 사용한다.
3. 각 불릿은 짧게 쓴다.
4. 선택 기간의 최신 수치와 최근 추세를 함께 반영한다.
"""

SENTIMENT_PROMPT = """
너는 심리 지표를 해석한다.
규칙:
1. 3개 불릿만 작성한다.
2. 제목은 "판정", "세부", "체크"를 사용한다.
3. 각 불릿은 짧게 쓴다.
4. 점수·단계와 VIX/하이일드/SPY 추세를 함께 반영한다.
"""

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

try:
    model_name = st.secrets.get("OPENAI_MODEL", "gpt-5.6-terra")
except Exception:
    model_name = "gpt-5.6-terra"

# ---------- Header ----------
st.title("시장 리더십 대시보드")
st.caption("최근 1~6개월 리더십 변화 · Fisher 심리 사이클 기반")

if not (has_rows(style) and has_rows(sector)):
    st.warning("아직 데이터가 충분히 생성되지 않았습니다. GitHub Actions 실행 여부를 먼저 확인해 주세요.")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    if has_rows(regime):
        r = regime.iloc[-1]
        card("시장 국면", regime_to_kor(str(r.get("mechanical_state", "—"))), f"전고점 대비 {pct(r.get('spy_drawdown_from_ath'))}")
    else:
        card("시장 국면", "—", "")
with c2:
    if has_rows(fisher):
        r = fisher.iloc[-1]
        card("Fisher 공개 시각", fisher_stage_to_kor(str(r.get("stage_label", "—"))), f"기준일: {r.get('source_date', '—')}")
    else:
        card("Fisher 공개 시각", "—", "")
with c3:
    if has_rows(author_view):
        r = author_view.iloc[-1]
        card("현재 해석", fisher_stage_to_kor(str(r.get("stage_label", "—"))), f"확신도: {confidence_to_kor(r.get('confidence', '—'))}")
    else:
        card("현재 해석", "—", "")
with c4:
    compact_card("핵심 리더십", current_leadership_summary(style, sector, region), "스타일·가중방식·지역·미국 섹터 요약")
with c5:
    state_k, axis = strongest_change(style)
    card("변화 포착", state_k, axis)

# ---------- Main insight ----------
st.markdown("### 현재 시장 인사이트")
snapshot = build_market_snapshot(style, sector, global_sector, region, breadth, sentiment, regime, fisher, author_view)
snapshot_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
with st.spinner("최신 리더십 데이터를 종합하는 중..."):
    gpt_main, gpt_main_error = generate_gpt_text("main:" + snapshot_json, model_name, MAIN_PROMPT, snapshot_json)
if gpt_main:
    render_gpt_box(gpt_main, f"GPT API 종합 해석 · 모델: {model_name} · 동일 데이터는 캐시")
else:
    render_gpt_box(fallback_main_insight(style, sector, region, breadth))
    if gpt_main_error:
        st.caption(f"GPT API 미연결: {gpt_main_error}")

st.divider()

# ---------- Style ----------
st.subheader("1. 스타일 리더십")
st.markdown('<div class="section-note">성장/가치, 대형/소형, 시총가중/동일가중, 미국/비미국 같은 축에서 누가 시장을 이끄는지 봅니다.</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="explain-box">21일은 단기 변화, 63일은 현재 중심축, 126일은 더 넓은 맥락입니다.</div>', unsafe_allow_html=True)

    if has_rows(style_hist):
        hist = style_hist.copy()
        hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
        options = [x for x in ["growth_value", "large_small", "cap_equal", "small_value_large_growth", "us_developed_ex_us", "developed_em", "cyclical_defensive"] if x in hist["pair_id"].dropna().unique().tolist()]
        default_idx = options.index("growth_value") if "growth_value" in options else 0
        choice = st.selectbox("상세 해석할 비교축", options, index=default_idx, format_func=lambda x: PAIR_INFO.get(x, {}).get("label", x))
        selected_now = style[style["pair_id"].eq(choice)].iloc[0]
        detail = style_selected_comment(selected_now, choice)
        st.markdown("#### 선택 항목 해석")
        st.markdown(f"- 기준: {detail['기준']}\n- 21일: {detail['21일']}\n- 63일: {detail['63일']}\n- 126일: {detail['126일']}\n- 상태: {detail['상태']}\n- 종합: {detail['종합']}")
        chart = hist[hist["pair_id"].eq(choice)].sort_values("date").copy()
        if len(chart):
            chart[["rs_return_21","rs_return_63","rs_return_126"]] = chart[["rs_return_21","rs_return_63","rs_return_126"]] * 100
            chart = chart.set_index("date")
            st.line_chart(chart[["rs_return_21","rs_return_63","rs_return_126"]], use_container_width=True)
            st.caption("선이 올라갈수록 왼쪽 항목이 상대적으로 강해졌다는 뜻입니다.")

            style_payload = build_style_chart_snapshot(style, style_hist, choice)
            style_json = json.dumps(style_payload, ensure_ascii=False, sort_keys=True, default=str)
            gpt_style, gpt_style_error = generate_gpt_text("style:" + style_json, model_name, STYLE_CHART_PROMPT, style_json)
            if gpt_style:
                render_gpt_box(gpt_style, "선택 차트")
            else:
                render_gpt_box(fallback_style_chart_insight(style_payload))
                if gpt_style_error:
                    st.caption(f"GPT API 미연결: {gpt_style_error}")

st.divider()

# ---------- Global ----------
st.subheader("2. 글로벌 리더십")
st.markdown('<div class="section-note">미국만 보지 않고 지역과 글로벌 섹터까지 함께 확인합니다.</div>', unsafe_allow_html=True)
g1, g2 = st.columns(2)
with g1:
    st.markdown("#### 지역 비교")
    if has_rows(region):
        region_table = prep_table(region, REGION_MAP, "VT 대비")
        st.dataframe(
            region_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "대상": st.column_config.TextColumn(width="medium"),
                "비교기준": st.column_config.TextColumn(width="medium"),
                "빈도 21일": st.column_config.NumberColumn(format="%.1f%%"),
                "빈도 63일": st.column_config.NumberColumn(format="%.1f%%"),
                "초과수익 21일": st.column_config.NumberColumn(format="%.2f%%"),
                "초과수익 63일": st.column_config.NumberColumn(format="%.2f%%"),
            }
        )
        st.markdown(concise_sector_comment(region, REGION_MAP))
        region_chart = region.copy().sort_values(["rank_21", "rank_63"])
        region_chart["대상"] = region_chart["ticker"].map(lambda x: REGION_MAP.get(x, x))
        region_chart["excess_21"] = pd.to_numeric(region_chart["excess_21"], errors="coerce") * 100
        region_chart = region_chart.set_index("대상")[["excess_21"]]
        st.bar_chart(region_chart, use_container_width=True)
        st.caption("막대가 높을수록 최근 21일 동안 VT보다 강했습니다.")
        region_payload = build_cross_section_snapshot(region, REGION_MAP, "VT 대비")
        region_json = json.dumps(region_payload, ensure_ascii=False, sort_keys=True, default=str)
        gpt_region, gpt_region_error = generate_gpt_text("region:" + region_json, model_name, CROSS_SECTION_PROMPT, region_json)
        if gpt_region:
            render_gpt_box(gpt_region, "지역 비교")
        else:
            render_gpt_box(fallback_cross_section(region_payload))
            if gpt_region_error:
                st.caption(f"GPT API 미연결: {gpt_region_error}")
with g2:
    st.markdown("#### 글로벌 섹터 비교")
    if has_rows(global_sector):
        gsec_table = prep_table(global_sector, GLOBAL_SECTOR, "VT 대비")
        st.dataframe(
            gsec_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "대상": st.column_config.TextColumn(width="medium"),
                "비교기준": st.column_config.TextColumn(width="medium"),
                "빈도 21일": st.column_config.NumberColumn(format="%.1f%%"),
                "빈도 63일": st.column_config.NumberColumn(format="%.1f%%"),
                "초과수익 21일": st.column_config.NumberColumn(format="%.2f%%"),
                "초과수익 63일": st.column_config.NumberColumn(format="%.2f%%"),
            }
        )
        st.markdown(concise_sector_comment(global_sector, GLOBAL_SECTOR))
        gsec_chart = global_sector.copy().sort_values(["rank_21", "rank_63"])
        gsec_chart["대상"] = gsec_chart["ticker"].map(lambda x: GLOBAL_SECTOR.get(x, x))
        gsec_chart["excess_21"] = pd.to_numeric(gsec_chart["excess_21"], errors="coerce") * 100
        gsec_chart = gsec_chart.set_index("대상")[["excess_21"]]
        st.bar_chart(gsec_chart, use_container_width=True)
        st.caption("막대가 높을수록 최근 21일 동안 VT보다 강했습니다.")
        gsec_payload = build_cross_section_snapshot(global_sector, GLOBAL_SECTOR, "VT 대비")
        gsec_json = json.dumps(gsec_payload, ensure_ascii=False, sort_keys=True, default=str)
        gpt_gsec, gpt_gsec_error = generate_gpt_text("gsec:" + gsec_json, model_name, CROSS_SECTION_PROMPT, gsec_json)
        if gpt_gsec:
            render_gpt_box(gpt_gsec, "글로벌 섹터")
        else:
            render_gpt_box(fallback_cross_section(gsec_payload))
            if gpt_gsec_error:
                st.caption(f"GPT API 미연결: {gpt_gsec_error}")

st.divider()

# ---------- US sectors ----------
st.subheader("3. 미국 섹터")
st.markdown('<div class="section-note">각 섹터가 미국 시장 전체(SPY)보다 강했는지, 그리고 어느 쪽이 부상/약화되는지 봅니다.</div>', unsafe_allow_html=True)
if has_rows(sector):
    us_table = prep_table(sector, US_SECTOR, "SPY 대비")
    st.dataframe(
        us_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "대상": st.column_config.TextColumn(width="medium"),
            "비교기준": st.column_config.TextColumn(width="medium"),
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
    us_payload = build_cross_section_snapshot(sector, US_SECTOR, "SPY 대비")
    us_json = json.dumps(us_payload, ensure_ascii=False, sort_keys=True, default=str)
    gpt_us, gpt_us_error = generate_gpt_text("ussec:" + us_json, model_name, CROSS_SECTION_PROMPT, us_json)
    if gpt_us:
        render_gpt_box(gpt_us, "미국 섹터")
    else:
        render_gpt_box(fallback_cross_section(us_payload))
        if gpt_us_error:
            st.caption(f"GPT API 미연결: {gpt_us_error}")

st.divider()

# ---------- Breadth & Sentiment ----------
left, right = st.columns(2)
with left:
    st.subheader("4. 시장 참여 폭")
    st.caption("S&P 500 구성종목 중 같은 기간 SPY를 이긴 비율")
    if has_rows(breadth):
        b = breadth.copy()
        b["breadth_pct"] = pd.to_numeric(b["breadth_pct"], errors="coerce") * 100
        b = b.sort_values("window")
        st.dataframe(
            b[["window", "breadth_pct", "n_valid"]].rename(columns={"window": "기간", "breadth_pct": "참여 폭", "n_valid": "유효 종목 수"}),
            use_container_width=True,
            hide_index=True,
            column_config={"참여 폭": st.column_config.NumberColumn(format="%.1f%%")}
        )
        st.markdown("숫자가 높을수록 상승이 시장 전반으로 퍼졌다는 뜻입니다.")
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
            st.caption("선이 올라갈수록 상승 참여가 넓어집니다.")
            breadth_payload = build_breadth_snapshot(breadth, breadth_hist, w)
            breadth_json = json.dumps(breadth_payload, ensure_ascii=False, sort_keys=True, default=str)
            gpt_breadth, gpt_breadth_error = generate_gpt_text("breadth:" + breadth_json, model_name, BREADTH_PROMPT, breadth_json)
            if gpt_breadth:
                render_gpt_box(gpt_breadth, "시장 참여 폭")
            else:
                render_gpt_box(fallback_breadth(breadth_payload))
                if gpt_breadth_error:
                    st.caption(f"GPT API 미연결: {gpt_breadth_error}")
with right:
    st.subheader("5. 심리 지표")
    if has_rows(sentiment):
        s = sentiment.iloc[-1]
        score = s.get("proxy_score", None)
        stage = s.get("proxy_stage", "—")
        try:
            st.metric("시장 암시 점수", f"{float(score):.0f} / 100", fisher_stage_to_kor(str(stage)))
            st.progress(min(max(float(score) / 100, 0), 1))
        except Exception:
            st.metric("시장 암시 점수", "—")
        detail = pd.DataFrame({
            "항목": ["VIX", "하이일드 스프레드", "SPY 추세", "SPY 모멘텀"],
            "점수": [s.get("vix_warmth"), s.get("hy_oas_warmth"), s.get("spy_trend_warmth"), s.get("spy_momentum_warmth")]
        })
        st.dataframe(detail, hide_index=True, use_container_width=True)
        senti_payload = build_sentiment_snapshot(sentiment)
        senti_json = json.dumps(senti_payload, ensure_ascii=False, sort_keys=True, default=str)
        gpt_senti, gpt_senti_error = generate_gpt_text("sentiment:" + senti_json, model_name, SENTIMENT_PROMPT, senti_json)
        if gpt_senti:
            render_gpt_box(gpt_senti, "심리 지표")
        else:
            render_gpt_box("심리 지표는 낙관/비관의 온도를 보여주는 보조 신호입니다. 단독 판단보다 리더십 변화와 함께 보는 것이 좋습니다.")
            if gpt_senti_error:
                st.caption(f"GPT API 미연결: {gpt_senti_error}")

st.divider()

# ---------- Qualitative anchors ----------
st.subheader("6. 해석 메모")
q1, q2 = st.columns(2)
with q1:
    st.markdown("#### Fisher 공개 시각")
    if has_rows(fisher):
        r = fisher.iloc[-1]
        st.markdown(f"**{r.get('source_date', '')} · {fisher_stage_to_kor(r.get('stage_label', ''))}**")
        st.write(translate_free_text(r.get("dashboard_interpretation", r.get("public_view", ""))))
with q2:
    st.markdown("#### 현재 해석")
    if has_rows(author_view):
        r = author_view.iloc[-1]
        st.markdown(f"**{fisher_stage_to_kor(r.get('stage_label', '—'))}**")
        st.write(translate_free_text(r.get("evidence", "")))
        st.caption(f"경계 신호: {translate_free_text(r.get('warning_trigger', '—'))}")

if has_rows(bounce):
    with st.expander("7. 반등 효과 점검"):
        cols = [c for c in ["ticker", "group", "subgroup", "max_drawdown_252", "max_drawdown_126", "rebound_from_126d_low", "current_drawdown_from_126d_high"] if c in bounce.columns]
        show = bounce[cols].copy()
        for c in ["max_drawdown_252", "max_drawdown_126", "rebound_from_126d_low", "current_drawdown_from_126d_high"]:
            if c in show.columns:
                show[c] = pd.to_numeric(show[c], errors="coerce") * 100
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.caption("최근 강세가 추세 전환인지, 큰 낙폭 뒤 반등인지 구분할 때 참고합니다.")

st.caption("매주 미국 금요일 장 마감 후 자동 업데이트 · 차트/섹션별 GPT 해석은 동일 데이터 기준 캐시됩니다.")
