from pathlib import Path
import json
import html
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

.main-section-card {
    border: 1px solid rgba(148,163,184,.26);
    border-radius: 12px;
    padding: 14px 16px 12px 16px;
    margin: 9px 0;
    background: #ffffff;
}
.main-section-card.trend { border-left: 5px solid #2563eb; }
.main-section-card.insight { border-left: 5px solid #d97706; }
.main-section-card.direction { border-left: 5px solid #059669; }
.main-section-title {
    font-size: 1.02rem;
    font-weight: 750;
    color: #0f172a;
    margin-bottom: 6px;
}
.main-section-card ul {
    margin: 0.2rem 0 0.1rem 1.25rem;
    padding: 0;
}
.main-section-card li {
    margin: 0.25rem 0;
    line-height: 1.55;
}
.change-pill {
    display: inline-block;
    border: 1px solid rgba(100,116,139,.28);
    border-radius: 999px;
    padding: 3px 9px;
    font-size: .80rem;
    color: #475569;
    background: #f8fafc;
}
.supply-note {
    color: #64748b;
    font-size: .87rem;
    line-height: 1.45;
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

US_SECTOR_SHORT = {
    "XLK": "기술",
    "XLF": "금융",
    "XLI": "산업재",
    "XLE": "에너지",
    "XLB": "소재",
    "XLY": "경기소비재",
    "XLP": "필수소비재",
    "XLV": "헬스케어",
    "XLU": "유틸리티",
    "XLRE": "부동산",
    "XLC": "커뮤니케이션서비스",
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

GLOBAL_SECTOR_SHORT = {
    "IXN": "기술",
    "IXG": "금융",
    "EXI": "산업재",
    "IXC": "에너지",
    "MXI": "소재",
    "RXI": "경기소비재",
    "KXI": "필수소비재",
    "IXJ": "헬스케어",
    "JXI": "유틸리티",
    "REET": "부동산",
    "IXP": "커뮤니케이션서비스",
}

REGION_MAP = {
    "VTI": "VTI (미국)",
    "VEA": "VEA (선진국, 미국 제외)",
    "VWO": "VWO (신흥국)",
    "VGK": "VGK (유럽)",
    "EWJ": "EWJ (일본)",
    "MCHI": "MCHI (중국)",
}

REGION_SHORT = {
    "VTI": "미국",
    "VEA": "선진국(미국 제외)",
    "VWO": "신흥국",
    "VGK": "유럽",
    "EWJ": "일본",
    "MCHI": "중국",
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


def current_leadership_summary(style_df, sector_df, region_df, global_sector_df):
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
                lines.append(f"{label}: {leader_to_kor(r.get('leader_21'))} → {leader_to_kor(r.get('leader_63'))}")
    if has_rows(global_sector_df):
        top21 = global_sector_df.sort_values(["rank_21", "rank_63"]).iloc[0].get("ticker")
        top63 = global_sector_df.sort_values(["rank_63", "rank_21"]).iloc[0].get("ticker")
        lines.append(f"글로벌 섹터: {GLOBAL_SECTOR_SHORT.get(top21, top21)} → {GLOBAL_SECTOR_SHORT.get(top63, top63)}")
    elif has_rows(sector_df):
        top21 = sector_df.sort_values(["rank_21", "rank_63"]).iloc[0].get("ticker")
        top63 = sector_df.sort_values(["rank_63", "rank_21"]).iloc[0].get("ticker")
        lines.append(f"미국 섹터: {US_SECTOR_SHORT.get(top21, top21)} → {US_SECTOR_SHORT.get(top63, top63)}")
    return lines if lines else ["—"]


def _style_leader_support(row, window):
    try:
        rr = float(row.get(f"rs_return_{window}"))
        freq = float(row.get(f"freq_{window}"))
        return freq if rr >= 0 else 1 - freq
    except Exception:
        return None


def style_change_judgement(row, bounce_df=None):
    """Classify whether a style move looks temporary, transitional, or persistent."""
    l21 = row.get("leader_21")
    l63 = row.get("leader_63")
    l126 = row.get("leader_126")
    s21 = _style_leader_support(row, 21)
    s63 = _style_leader_support(row, 63)
    rr21 = abs(float(row.get("rs_return_21", 0) or 0))

    if l21 == l63 == l126:
        label = "지속"
        reason = f"21·63·126일이 모두 {leader_to_kor(l21)}로 정렬"
    elif l21 == l63 and l63 != l126:
        if s21 is not None and s63 is not None and s21 >= 0.58 and s63 >= 0.54:
            label = "전환 진행"
            reason = f"21·63일이 {leader_to_kor(l21)}로 정렬되고 빈도도 뒷받침"
        else:
            label = "전환 초기"
            reason = f"21·63일은 {leader_to_kor(l21)}로 같지만 강도 확인이 더 필요"
    elif l21 != l63 and l63 == l126:
        if s21 is not None and s21 >= 0.62 and rr21 >= 0.025:
            label = "전환 초기"
            reason = f"21일 {leader_to_kor(l21)} 반전이 강하지만 63·126일 중심축은 {leader_to_kor(l63)}"
        else:
            label = "일시적 가능성"
            reason = f"21일만 {leader_to_kor(l21)}로 바뀌고 63·126일은 {leader_to_kor(l63)} 유지"
    else:
        label = "혼조/재반전"
        reason = "21·63·126일 신호가 일관되지 않음"

    bounce_risk = False
    if has_rows(bounce_df) and l21 != l63:
        try:
            new_ticker = row.get("numerator") if float(row.get("rs_return_21", 0)) >= 0 else row.get("denominator")
            b = bounce_df[bounce_df["ticker"].eq(new_ticker)]
            if len(b):
                br = b.iloc[0]
                dd = float(br.get("max_drawdown_126"))
                rebound = float(br.get("rebound_from_126d_low"))
                bounce_risk = dd <= -0.15 and rebound >= 0.15
        except Exception:
            bounce_risk = False
    if bounce_risk:
        label += " · 반등효과 주의"
        reason += "; 직전 낙폭 대비 반등 효과도 큼"
    return label, reason


def cross_change_judgement(row):
    """Cross-sectional rank transition label for sectors/regions."""
    try:
        r21 = float(row.get("rank_21"))
        r63 = float(row.get("rank_63"))
        r126 = float(row.get("rank_126"))
        ex21 = float(row.get("excess_21"))
        ex63 = float(row.get("excess_63"))
    except Exception:
        return "데이터 부족"

    if r21 <= 3 and r63 <= 3 and r126 <= 3 and ex21 > 0 and ex63 > 0:
        return "지속 리더"
    if r21 <= 3 and r63 <= 4 and r126 > 4 and ex21 > 0 and ex63 > 0:
        return "전환 진행"
    if r21 <= 3 and r63 >= 7:
        return "단기 급부상"
    if (r63 - r21) >= 3 and ex21 > 0:
        return "부상 초기"
    if (r63 - r21) <= -3:
        return "약화"
    if ex21 > 0 and ex63 > 0:
        return "우위 유지"
    if ex21 > 0 and ex63 <= 0:
        return "단기 반전"
    return "혼조"


def strongest_change(style_df, bounce_df=None):
    if not has_rows(style_df):
        return ("—", "—")
    candidates = []
    priority = {
        "전환 진행": 5,
        "전환 초기": 4,
        "일시적 가능성": 3,
        "혼조/재반전": 2,
        "지속": 0,
    }
    for _, r in style_df.iterrows():
        label, reason = style_change_judgement(r, bounce_df)
        base = label.split(" · ")[0]
        candidates.append((priority.get(base, 1), label, r.get("pair_id"), reason))
    candidates.sort(key=lambda x: x[0], reverse=True)
    if not candidates or candidates[0][0] == 0:
        return ("안정", "뚜렷한 신규 전환 없음")
    _, label, pid, _ = candidates[0]
    return label, PAIR_INFO.get(pid, {}).get("label", pid)


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


def style_selected_comment(row, pair_id, bounce_df=None):
    info = PAIR_INFO[pair_id]
    change_label, change_reason = style_change_judgement(row, bounce_df)
    return {
        "기준": info["meaning"],
        "21일": f"{leader_to_kor(row.get('leader_21','—'))} 우위",
        "63일": f"{leader_to_kor(row.get('leader_63','—'))} 우위",
        "126일": f"{leader_to_kor(row.get('leader_126','—'))} 우위",
        "상태": state_to_kor(row.get("change_state", "")),
        "변화판정": change_label,
        "판정근거": change_reason,
        "종합": style_overall_comment(row),
    }


def prep_style_table(style, bounce_df=None):
    wanted = [
        "growth_value","large_small","cap_equal","small_value_large_growth",
        "us_developed_ex_us","developed_em","cyclical_defensive"
    ]
    df = style[style["pair_id"].isin(wanted)].copy()
    df["비교축"] = df["pair_id"].map(lambda x: PAIR_INFO.get(x, {}).get("label", x))
    df["21일"] = df["leader_21"].map(leader_to_kor)
    df["63일"] = df["leader_63"].map(leader_to_kor)
    df["126일"] = df["leader_126"].map(leader_to_kor)
    df["변화판정"] = df.apply(lambda r: style_change_judgement(r, bounce_df)[0], axis=1)
    df = df[[
        "비교축","21일","63일","126일","변화판정",
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
    x["변화판정"] = x.apply(cross_change_judgement, axis=1)
    x = x[[
        "대상","비교기준","rank_21","rank_63","rank_126","변화판정",
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


def build_market_snapshot(style, sector, global_sector, region, breadth, sentiment, regime, fisher, author_view, bounce=None, stock_supply=None):
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
            change_label, change_reason = style_change_judgement(r, bounce)
            rows.append({
                "비교축": PAIR_INFO.get(pid, {}).get("label", pid),
                "126일": leader_to_kor(r.get("leader_126")),
                "63일": leader_to_kor(r.get("leader_63")),
                "21일": leader_to_kor(r.get("leader_21")),
                "126일상대강도": num(r.get("rs_return_126"), 4),
                "63일상대강도": num(r.get("rs_return_63"), 4),
                "21일상대강도": num(r.get("rs_return_21"), 4),
                "126일빈도": num(r.get("freq_126"), 4),
                "63일빈도": num(r.get("freq_63"), 4),
                "21일빈도": num(r.get("freq_21"), 4),
                "변화판정": change_label,
                "판정근거": change_reason,
            })
        snapshot["스타일변화"] = rows
    if has_rows(region):
        r = region.sort_values(["rank_21", "rank_63"]).head(6).copy()
        snapshot["지역리더십"] = [
            {
                "대상": REGION_MAP.get(row.get("ticker"), row.get("ticker")),
                "126일순위": int(row.get("rank_126")) if pd.notna(row.get("rank_126")) else None,
                "63일순위": int(row.get("rank_63")) if pd.notna(row.get("rank_63")) else None,
                "21일순위": int(row.get("rank_21")) if pd.notna(row.get("rank_21")) else None,
                "63일초과수익": num(row.get("excess_63"), 4),
                "21일초과수익": num(row.get("excess_21"), 4),
                "변화판정": cross_change_judgement(row),
            }
            for _, row in r.iterrows()
        ]
    if has_rows(global_sector):
        g = global_sector.sort_values(["rank_21", "rank_63"]).head(8).copy()
        snapshot["글로벌섹터"] = [
            {
                "대상": GLOBAL_SECTOR.get(row.get("ticker"), row.get("ticker")),
                "126일순위": int(row.get("rank_126")) if pd.notna(row.get("rank_126")) else None,
                "63일순위": int(row.get("rank_63")) if pd.notna(row.get("rank_63")) else None,
                "21일순위": int(row.get("rank_21")) if pd.notna(row.get("rank_21")) else None,
                "63일초과수익": num(row.get("excess_63"), 4),
                "21일초과수익": num(row.get("excess_21"), 4),
                "변화판정": cross_change_judgement(row),
            }
            for _, row in g.iterrows()
        ]
    if has_rows(sector):
        s = sector.sort_values(["rank_21", "rank_63"]).copy()
        snapshot["미국섹터"] = [
            {
                "대상": US_SECTOR.get(row.get("ticker"), row.get("ticker")),
                "126일순위": int(row.get("rank_126")) if pd.notna(row.get("rank_126")) else None,
                "63일순위": int(row.get("rank_63")) if pd.notna(row.get("rank_63")) else None,
                "21일순위": int(row.get("rank_21")) if pd.notna(row.get("rank_21")) else None,
                "63일초과수익": num(row.get("excess_63"), 4),
                "21일초과수익": num(row.get("excess_21"), 4),
                "변화판정": cross_change_judgement(row),
            }
            for _, row in s.head(10).iterrows()
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
    if has_rows(stock_supply):
        supply_block = {}
        for universe, label in [("US", "미국"), ("GLOBAL", "글로벌"), ("EX_US", "글로벌_exUS")]:
            u = stock_supply[stock_supply["universe"].eq(universe)].copy()
            if not len(u):
                continue
            # Show both expansion and contraction ends; these are the most informative changes.
            u["weighted_change_12m"] = pd.to_numeric(u["weighted_change_12m"], errors="coerce")
            u["net_breadth_12m"] = pd.to_numeric(u["net_breadth_12m"], errors="coerce")
            expansion = u.sort_values("weighted_change_12m", ascending=False).head(3)
            contraction = u.sort_values("weighted_change_12m", ascending=True).head(3)
            combined = pd.concat([expansion, contraction]).drop_duplicates(subset=["sector"]).head(6)
            supply_block[label] = [
                {
                    "섹터": row.get("sector_ko", row.get("sector")),
                    "3개월가중주식수증감": num(row.get("weighted_change_3m"), 4),
                    "6개월가중주식수증감": num(row.get("weighted_change_6m"), 4),
                    "12개월가중주식수증감": num(row.get("weighted_change_12m"), 4),
                    "12개월증가기업비중": num(row.get("pct_increasing_12m"), 4),
                    "12개월감소기업비중": num(row.get("pct_decreasing_12m"), 4),
                    "12개월순공급breadth": num(row.get("net_breadth_12m"), 4),
                    "커버리지": num(row.get("coverage_of_sector_weight"), 4),
                    "판정": row.get("signal"),
                }
                for _, row in combined.iterrows()
            ]
        snapshot["주식공급"] = supply_block
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
        snapshot["현재방법론해석"] = {
            "단계": fisher_stage_to_kor(str(r.get("stage_label", "—"))),
            "근거": translate_free_text(r.get("evidence", "")),
            "경계신호": translate_free_text(r.get("warning_trigger", "")),
        }
    return snapshot


def build_style_chart_snapshot(style_df, style_hist_df, pair_id, bounce_df=None):
    current = style_df[style_df["pair_id"].eq(pair_id)].iloc[0]
    recent = style_hist_df[style_hist_df["pair_id"].eq(pair_id)].sort_values("date").tail(12).copy()
    recent[["rs_return_21", "rs_return_63", "rs_return_126"]] = recent[["rs_return_21", "rs_return_63", "rs_return_126"]].apply(pd.to_numeric, errors="coerce")
    change_label, change_reason = style_change_judgement(current, bounce_df)
    return {
        "비교축": PAIR_INFO[pair_id]["label"],
        "의미": PAIR_INFO[pair_id]["meaning"],
        "현재": {
            "126일리더": leader_to_kor(current.get("leader_126")),
            "63일리더": leader_to_kor(current.get("leader_63")),
            "21일리더": leader_to_kor(current.get("leader_21")),
            "변화판정": change_label,
            "판정근거": change_reason,
            "21일상대강도": num(current.get("rs_return_21"), 4),
            "63일상대강도": num(current.get("rs_return_63"), 4),
            "126일상대강도": num(current.get("rs_return_126"), 4),
            "21일빈도": num(current.get("freq_21"), 4),
            "63일빈도": num(current.get("freq_63"), 4),
            "126일빈도": num(current.get("freq_126"), 4),
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
                "126일순위": int(r.get("rank_126")) if pd.notna(r.get("rank_126")) else None,
                "63일순위": int(r.get("rank_63")) if pd.notna(r.get("rank_63")) else None,
                "21일순위": int(r.get("rank_21")) if pd.notna(r.get("rank_21")) else None,
                "21일초과수익": num(r.get("excess_21"), 4),
                "63일초과수익": num(r.get("excess_63"), 4),
                "변화판정": cross_change_judgement(r),
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


def _main_section_html(title, items, css_class):
    safe_items = [html.escape(str(x)) for x in items if x]
    lis = "".join(f"<li>{x}</li>" for x in safe_items)
    return f'<div class="main-section-card {css_class}"><div class="main-section-title">{title}</div><ul>{lis}</ul></div>'


def render_main_sections(sections, caption=None):
    st.markdown(_main_section_html("동향", sections.get("동향", []), "trend"), unsafe_allow_html=True)
    st.markdown(_main_section_html("인사이트", sections.get("인사이트", []), "insight"), unsafe_allow_html=True)
    st.markdown(_main_section_html("다이렉션", sections.get("다이렉션", []), "direction"), unsafe_allow_html=True)
    if caption:
        st.caption(caption)


def parse_main_sections(text):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        obj = json.loads(cleaned)
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    out = {}
    for key in ["동향", "인사이트", "다이렉션"]:
        val = obj.get(key, [])
        if isinstance(val, str):
            val = [val]
        if not isinstance(val, list):
            val = []
        out[key] = [str(x).strip() for x in val if str(x).strip()][:4]
    return out


def fallback_main_sections(style, sector, global_sector, region, breadth, stock_supply=None, bounce_df=None):
    trend, insight, direction = [], [], []
    if has_rows(style):
        gvx = style[style["pair_id"].eq("growth_value")]
        cex = style[style["pair_id"].eq("cap_equal")]
        uxx = style[style["pair_id"].eq("us_developed_ex_us")]
        if len(gvx):
            gv = gvx.iloc[0]
            lab, why = style_change_judgement(gv, bounce_df)
            trend.append(f"성장/가치: 126일 {leader_to_kor(gv.get('leader_126'))} → 63일 {leader_to_kor(gv.get('leader_63'))} → 21일 {leader_to_kor(gv.get('leader_21'))}.")
            insight.append(f"성장/가치 변화는 '{lab}'로 판정: {why}.")
        if len(cex):
            ce = cex.iloc[0]
            lab, why = style_change_judgement(ce, bounce_df)
            trend.append(f"가중방식: 126일 {leader_to_kor(ce.get('leader_126'))} → 63일 {leader_to_kor(ce.get('leader_63'))} → 21일 {leader_to_kor(ce.get('leader_21'))}.")
            insight.append(f"가중방식은 '{lab}': {why}.")
        if len(uxx):
            ux = uxx.iloc[0]
            lab, _ = style_change_judgement(ux, bounce_df)
            trend.append(f"미국/비미국: 126일 {leader_to_kor(ux.get('leader_126'))} → 63일 {leader_to_kor(ux.get('leader_63'))} → 21일 {leader_to_kor(ux.get('leader_21'))}.")
            insight.append(f"지역 리더십 변화는 '{lab}' 단계입니다.")
    if has_rows(global_sector):
        t21 = global_sector.sort_values(["rank_21", "rank_63"]).iloc[0]
        t63 = global_sector.sort_values(["rank_63", "rank_21"]).iloc[0]
        trend.append(f"글로벌 섹터는 63일 {GLOBAL_SECTOR_SHORT.get(t63.get('ticker'), t63.get('ticker'))}에서 21일 {GLOBAL_SECTOR_SHORT.get(t21.get('ticker'), t21.get('ticker'))} 쪽으로 단기 리더가 이동했습니다.")
    if has_rows(breadth):
        b21 = breadth[breadth["window"].eq(21)]
        if len(b21):
            bp = float(b21.iloc[0].get("breadth_pct"))
            insight.append(f"21일 breadth는 {bp*100:.1f}%로, 신규 리더십이 시장 전반으로 확산됐는지 판단할 핵심 확인 신호입니다.")
    if has_rows(stock_supply):
        for universe, label in [("US", "미국"), ("EX_US", "비미국")]:
            u = stock_supply[stock_supply["universe"].eq(universe)].copy()
            if len(u):
                u["weighted_change_12m"] = pd.to_numeric(u["weighted_change_12m"], errors="coerce")
                top = u.sort_values("weighted_change_12m", ascending=False).iloc[0]
                trend.append(f"{label} 주식공급은 {top.get('sector_ko', top.get('sector'))}에서 12개월 주식수 증가가 가장 큽니다.")
    direction.append("21일만 바뀐 축은 추격하지 말고 63일 정렬 여부를 먼저 확인합니다.")
    direction.append("21일과 63일이 같은 방향으로 정렬되고 breadth까지 넓어지면 리더십 전환 신뢰도를 한 단계 높입니다.")
    direction.append("주식공급 증가가 특정 리더 섹터에서 함께 가속되면 후기 낙관/유포리아 위험 신호로 별도 점검합니다.")
    return {"동향": trend[:4], "인사이트": insight[:4], "다이렉션": direction[:4]}


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
너는 글로벌 주식시장 리더십 변화의 지속성을 판별하는 투자 리서치 보조자다.
입력 JSON에 있는 데이터만 사용한다. 외부 뉴스나 원인을 추측하지 않는다.

반드시 아래 JSON 객체 하나만 출력한다. 코드펜스나 markdown은 쓰지 않는다.
{
  "동향": ["문장", "문장", "문장"],
  "인사이트": ["문장", "문장", "문장"],
  "다이렉션": ["문장", "문장", "문장"]
}

작성 규칙:
1. 동향: '무엇이 바뀌고 있는가'만 쓴다. 126일 → 63일 → 21일 순으로 스타일 변화, 미국/비미국, 글로벌/미국 섹터, breadth, 주식공급 변화를 구체적으로 적는다.
2. 인사이트: 변화가 '일시적 가능성 / 전환 초기 / 전환 진행 / 지속' 중 어디에 가까운지 판단하고 근거를 쓴다. 21일 단독 변화는 약하게, 21·63일 정렬은 강하게 본다.
3. 일시적 반등 여부를 판단할 때 빈도, 상대강도, 63/126일 정렬, bounce-effect 정보, breadth, 글로벌 확인 신호를 함께 본다.
4. 주식공급은 미국과 글로벌/ex-US를 구분한다. 주식공급 증가가 강세 리더 섹터와 겹치는지 여부를 late-optimism/euphoria 보조 신호로 해석하되, IPO 전체 공급과 동일시하지 않는다.
5. 다이렉션: 매수/매도 종목 추천이 아니라 '현재 중심축 유지 / 신규 리더 관찰 / 어떤 조건에서 전환 인정 / 어떤 조건에서 신호 폐기'처럼 행동 규칙을 명확히 쓴다.
6. '확인 필요'로 끝내지 말고 무엇이 확인되면 판단이 바뀌는지 명시한다. 예: 21일 리더가 63일에도 우위 + breadth 50% 이상 + 글로벌 동조.
7. 각 배열은 2~4개 문장, 각 문장은 가능한 한 1~2줄로 간결하게 쓴다.
8. '도취'라는 단어는 쓰지 않고 '유포리아'를 사용한다.
9. 특정 필명은 절대 쓰지 않는다.
"""

STYLE_CHART_PROMPT = """
너는 특정 리더십 비교축의 현재 4분면과 21·63·126일 신호를 해석하는 투자 리서치 보조자다.
출력 형식:
1. HTML만 출력한다.
2. <ul> 안에 4개 bullet을 쓴다.
3. bullet 제목은 각각 <b>현재 판정</b>, <b>변화의 지속성</b>, <b>의미</b>, <b>확인 조건</b>으로 시작한다.
4. 126일 → 63일 → 21일 순서로 리더가 어떻게 바뀌었는지 먼저 읽는다.
5. 입력의 변화판정(일시적 가능성/전환 초기/전환 진행/지속)과 빈도·상대강도·반등효과 정보를 반드시 반영한다.
6. '확인 필요'로 끝내지 말고 무엇이 바뀌면 전환을 인정하거나 폐기할지 구체적으로 쓴다.
"""

CROSS_SECTION_PROMPT = """
너는 지역/섹터 리더십 4분면과 순위 변화를 해석하는 투자 리서치 보조자다.
출력 형식:
1. HTML만 출력한다.
2. <ul> 안에 4개 bullet을 쓴다.
3. bullet 제목은 각각 <b>주도 축</b>, <b>변화의 지속성</b>, <b>해석</b>, <b>확인 조건</b>으로 시작한다.
4. 비교기준을 먼저 밝히고, 126일 → 63일 → 21일 순위 변화와 초과수익을 연결한다.
5. 단기 급부상과 지속 리더를 구분하고, 구체적 대상명을 사용한다.
"""

BREADTH_PROMPT = """
너는 시장 breadth 차트를 해석하는 보조자다.
출력 형식:
1. HTML만 출력한다.
2. <ul> 안에 4개 bullet을 쓴다.
3. bullet 제목은 각각 <b>현재 판정</b>, <b>추세</b>, <b>의미</b>, <b>체크포인트</b>로 시작한다.
4. 선택한 기간의 최신 수치와 최근 추세를 함께 설명한다.
"""

SENTIMENT_PROMPT = """
너는 심리 지표를 해석하는 보조자다.
출력 형식:
1. HTML만 출력한다.
2. <ul> 안에 3개 bullet을 쓴다.
3. bullet 제목은 각각 <b>현재 판정</b>, <b>세부 신호</b>, <b>체크포인트</b>로 시작한다.
4. 점수·단계와 VIX/하이일드/SPY 추세/모멘텀을 함께 반영한다.
"""


SUPPLY_PROMPT = """
너는 섹터별 기업 주식공급 데이터를 해석하는 투자 리서치 보조자다.
입력은 기존 상장기업의 발행주식수 증감 프록시다. IPO 전체 공급과 동일시하면 안 된다.
출력은 HTML <ul> 안의 3개 bullet만 작성한다.
각 bullet은 <b>공급 확대</b>, <b>공급 축소</b>, <b>의미</b>로 시작한다.
어느 섹터에서 발행주식수가 늘고 줄었는지 구체적으로 쓰고, 주가 리더십과 결합할 때 late-optimism/euphoria 경계 신호가 될 수 있다는 점을 조건부로 설명한다.
데이터 커버리지가 낮은 섹터는 단정하지 않는다.
"""


def prep_supply_table(stock_supply_df, universe):
    if not has_rows(stock_supply_df):
        return pd.DataFrame()
    x = stock_supply_df[stock_supply_df["universe"].eq(universe)].copy()
    if not len(x):
        return pd.DataFrame()
    x = x.sort_values("weighted_change_12m", ascending=False)
    x = x[[
        "sector_ko", "weighted_change_3m", "weighted_change_6m", "weighted_change_12m",
        "pct_increasing_12m", "pct_decreasing_12m", "coverage_of_sector_weight", "n_valid_12m", "signal"
    ]].rename(columns={
        "sector_ko": "섹터",
        "weighted_change_3m": "주식수 증감 3개월",
        "weighted_change_6m": "주식수 증감 6개월",
        "weighted_change_12m": "주식수 증감 12개월",
        "pct_increasing_12m": "증가기업 비중 12개월",
        "pct_decreasing_12m": "감소기업 비중 12개월",
        "coverage_of_sector_weight": "섹터가중치 커버리지",
        "n_valid_12m": "유효 기업 수",
        "signal": "판정",
    })
    for c in ["주식수 증감 3개월", "주식수 증감 6개월", "주식수 증감 12개월", "증가기업 비중 12개월", "감소기업 비중 12개월", "섹터가중치 커버리지"]:
        x[c] = pd.to_numeric(x[c], errors="coerce") * 100
    return x


def build_supply_snapshot(stock_supply_df, universe, horizon):
    if not has_rows(stock_supply_df):
        return {}
    x = stock_supply_df[stock_supply_df["universe"].eq(universe)].copy()
    if not len(x):
        return {}
    chg = f"weighted_change_{horizon}"
    br = f"net_breadth_{horizon}"
    x[chg] = pd.to_numeric(x[chg], errors="coerce")
    x[br] = pd.to_numeric(x[br], errors="coerce")
    x = x.sort_values(chg, ascending=False)
    return {
        "시장": universe,
        "기간": horizon,
        "공급증가상위": [
            {
                "섹터": r.get("sector_ko", r.get("sector")),
                "가중주식수증감": num(r.get(chg), 4),
                "순공급breadth": num(r.get(br), 4),
                "판정": r.get("signal"),
                "커버리지": num(r.get("coverage_of_sector_weight"), 4),
            } for _, r in x.head(4).iterrows()
        ],
        "공급감소상위": [
            {
                "섹터": r.get("sector_ko", r.get("sector")),
                "가중주식수증감": num(r.get(chg), 4),
                "순공급breadth": num(r.get(br), 4),
                "판정": r.get("signal"),
                "커버리지": num(r.get("coverage_of_sector_weight"), 4),
            } for _, r in x.tail(4).sort_values(chg).iterrows()
        ],
    }



def _base_quadrant_layout(fig, title, x_title, y_title, y_ref=50):
    fig.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=520,
        margin=dict(l=50, r=30, t=65, b=55),
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        template="plotly_white",
        font=dict(family="Arial, Apple SD Gothic Neo, Malgun Gothic, sans-serif", size=12),
    )
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="#94a3b8")
    fig.add_hline(y=y_ref, line_width=1, line_dash="dash", line_color="#94a3b8")
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148,163,184,.16)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,.16)", zeroline=False)
    return fig


def plot_supply_quadrant(stock_supply_df, universe, horizon="12m"):
    x = stock_supply_df[stock_supply_df["universe"].eq(universe)].copy()
    chg = f"weighted_change_{horizon}"
    br = f"net_breadth_{horizon}"
    x[chg] = pd.to_numeric(x[chg], errors="coerce") * 100
    x[br] = pd.to_numeric(x[br], errors="coerce") * 100
    x = x.dropna(subset=[chg, br]).sort_values("sector_ko")

    colors = [
        "#2563eb", "#16a34a", "#dc2626", "#7c3aed", "#ea580c", "#0891b2",
        "#65a30d", "#db2777", "#4f46e5", "#b45309", "#059669", "#475569"
    ]
    fig = go.Figure()
    for i, (_, r) in enumerate(x.iterrows()):
        label = str(r.get("sector_ko", r.get("sector")))
        fig.add_trace(go.Scatter(
            x=[r[chg]], y=[r[br]], mode="markers+text", name=label,
            text=[label], textposition="top center",
            marker=dict(size=12, color=colors[i % len(colors)], line=dict(width=1, color="white")),
            hovertemplate=f"<b>{label}</b><br>가중 주식수 증감: %{{x:.2f}}%<br>순 공급 breadth: %{{y:.1f}}%p<extra></extra>",
        ))
    label = {"US": "미국", "GLOBAL": "글로벌", "EX_US": "글로벌 ex-US"}.get(universe, universe)
    hlabel = {"3m": "3개월", "6m": "6개월", "12m": "12개월"}.get(horizon, horizon)
    _base_quadrant_layout(
        fig,
        f"{label} 섹터별 주식 공급 · {hlabel}",
        "가중 발행주식수 증감 (%)",
        "증가기업 비중 - 감소기업 비중 (%p)",
        y_ref=0,
    )
    fig.add_annotation(xref="paper", yref="paper", x=.99, y=.98, text="우상단: 공급 증가 확산", showarrow=False, font=dict(size=11, color="#64748b"))
    fig.add_annotation(xref="paper", yref="paper", x=.01, y=.03, text="좌하단: 주식수 축소 확산", showarrow=False, font=dict(size=11, color="#64748b"))
    return fig


def plot_style_quadrant(selected_row, pair_id):
    periods = [
        ("126일", "rs_return_126", "freq_126", "circle-open", "#1d4ed8"),
        ("63일", "rs_return_63", "freq_63", "diamond", "#ef4444"),
        ("21일", "rs_return_21", "freq_21", "circle", "#60a5fa"),
    ]
    fig = go.Figure()
    xs, ys = [], []
    for name, xcol, ycol, symbol, color in periods:
        xv = pd.to_numeric(selected_row.get(xcol), errors="coerce")
        yv = pd.to_numeric(selected_row.get(ycol), errors="coerce")
        if pd.notna(xv) and pd.notna(yv):
            x = float(xv) * 100
            y = float(yv) * 100
            xs.append(x)
            ys.append(y)
            fig.add_trace(go.Scatter(
                x=[x], y=[y], mode="markers+text", name=name,
                marker=dict(size=15, color=color, symbol=symbol, line=dict(width=1.5, color="white")),
                text=[name], textposition="top center", cliponaxis=False,
                hovertemplate=f"<b>{name}</b><br>상대강도: %{{x:.2f}}%<br>승리 빈도: %{{y:.1f}}%<extra></extra>",
            ))

    _base_quadrant_layout(
        fig,
        PAIR_INFO.get(pair_id, {}).get("label", pair_id),
        "상대강도 (%)",
        "승리 빈도 (%)",
        y_ref=50,
    )

    if xs:
        xmin, xmax = min(xs + [0]), max(xs + [0])
        xpad = max((xmax - xmin) * 0.15, 1.5)
        ymin, ymax = min(ys + [50]), max(ys + [50])
        ypad = max((ymax - ymin) * 0.18, 2.0)
        fig.update_xaxes(range=[xmin - xpad, xmax + xpad])
        fig.update_yaxes(range=[ymin - ypad, ymax + ypad])

    fig.update_layout(
        height=440,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def plot_cross_quadrant_all_periods(df, mapping, short_mapping, benchmark_label, use_ticker_labels=True):
    colors = [
        "#2563eb", "#16a34a", "#dc2626", "#7c3aed", "#ea580c", "#0891b2",
        "#65a30d", "#db2777", "#4f46e5", "#b45309", "#059669", "#475569"
    ]
    periods = [
        (126, "126일 · 기존 추세"),
        (63, "63일 · 현재 중심"),
        (21, "21일 · 단기 변화"),
    ]
    work = df.copy().reset_index(drop=True)

    all_x, all_y = [], []
    for period, _ in periods:
        xv = pd.to_numeric(work.get(f"excess_{period}"), errors="coerce") * 100
        yv = pd.to_numeric(work.get(f"freq_{period}"), errors="coerce") * 100
        all_x.extend(xv.dropna().tolist())
        all_y.extend(yv.dropna().tolist())

    if all_x:
        xmin, xmax = min(all_x + [0]), max(all_x + [0])
        xpad = max((xmax - xmin) * 0.08, 1.0)
        xrange = [xmin - xpad, xmax + xpad]
    else:
        xrange = [-5, 5]

    if all_y:
        ymin, ymax = min(all_y + [50]), max(all_y + [50])
        ypad = max((ymax - ymin) * 0.10, 1.5)
        yrange = [ymin - ypad, ymax + ypad]
    else:
        yrange = [40, 60]

    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=[x[1] for x in periods],
        horizontal_spacing=0.055,
        shared_yaxes=True,
    )

    missing = []
    for col_idx, (period, _) in enumerate(periods, start=1):
        for i, row in work.iterrows():
            ticker = row.get("ticker")
            full_label = short_mapping.get(ticker, mapping.get(ticker, ticker))
            point_label = str(ticker) if use_ticker_labels else str(full_label)
            xv = pd.to_numeric(row.get(f"excess_{period}"), errors="coerce")
            yv = pd.to_numeric(row.get(f"freq_{period}"), errors="coerce")

            if pd.isna(xv) or pd.isna(yv):
                missing.append(f"{ticker} {period}일")
                continue

            fig.add_trace(
                go.Scatter(
                    x=[float(xv) * 100],
                    y=[float(yv) * 100],
                    mode="markers+text",
                    name=str(full_label),
                    legendgroup=str(ticker),
                    showlegend=(col_idx == 1),
                    marker=dict(
                        size=11,
                        color=colors[i % len(colors)],
                        line=dict(width=1, color="white"),
                    ),
                    text=[point_label],
                    textposition="top center",
                    textfont=dict(size=9),
                    cliponaxis=False,
                    hovertemplate=(
                        f"<b>{full_label}</b><br>{period}일"
                        f"<br>{benchmark_label} 대비 초과수익: %{{x:.2f}}%"
                        f"<br>승리 빈도: %{{y:.1f}}%<extra></extra>"
                    ),
                ),
                row=1,
                col=col_idx,
            )

        fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="#94a3b8", row=1, col=col_idx)
        fig.add_hline(y=50, line_width=1, line_dash="dash", line_color="#94a3b8", row=1, col=col_idx)
        fig.update_xaxes(
            range=xrange,
            title_text=f"{benchmark_label} 대비 (%)",
            row=1,
            col=col_idx,
            showgrid=True,
            gridcolor="rgba(148,163,184,.14)",
            zeroline=False,
        )
        fig.update_yaxes(
            range=yrange,
            row=1,
            col=col_idx,
            showgrid=True,
            gridcolor="rgba(148,163,184,.14)",
            zeroline=False,
        )

    fig.update_yaxes(title_text="승리 빈도 (%)", row=1, col=1)
    fig.update_layout(
        height=455,
        margin=dict(l=45, r=25, t=95, b=55),
        hovermode="closest",
        template="plotly_white",
        font=dict(family="Arial, Apple SD Gothic Neo, Malgun Gothic, sans-serif", size=11),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.13,
            xanchor="left",
            x=0,
            font=dict(size=10),
        ),
        title=dict(
            text="126일 → 63일 → 21일 리더십 비교",
            x=0.01,
            xanchor="left",
            font=dict(size=14),
        ),
    )
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=.995,
        y=.98,
        text="우상단 = 강한 리더십",
        showarrow=False,
        font=dict(size=10, color="#64748b"),
    )
    fig._missing_points = sorted(set(missing))
    return fig

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
stock_supply = read_csv("stock_supply_sector_latest.csv")
stock_supply_hist = read_csv("stock_supply_sector_history.csv")
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
    compact_card("핵심 리더십", current_leadership_summary(style, sector, region, global_sector), "21일 → 63일 기준")
with c5:
    state_k, axis = strongest_change(style, bounce)
    card("변화 포착", state_k, axis)

# ---------- Main insight ----------
st.markdown("### 현재 시장 인사이트")
snapshot = build_market_snapshot(
    style, sector, global_sector, region, breadth, sentiment, regime, fisher, author_view,
    bounce=bounce, stock_supply=stock_supply
)
snapshot_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
with st.spinner("변화의 지속성과 다음 확인 조건을 종합하는 중..."):
    gpt_main, gpt_main_error = generate_gpt_text("main-v6.6:" + snapshot_json, model_name, MAIN_PROMPT, snapshot_json)
sections = parse_main_sections(gpt_main) if gpt_main else None
if not sections:
    sections = fallback_main_sections(style, sector, global_sector, region, breadth, stock_supply, bounce)
render_main_sections(sections, f"GPT 변화 해석 · {model_name}" if gpt_main else None)
if gpt_main_error and not gpt_main:
    st.caption(f"GPT API 미연결: {gpt_main_error}")

st.divider()

# ---------- Style ----------
st.subheader("1. 스타일 리더십")
st.markdown('<div class="section-note">성장/가치, 대형/소형, 시총가중/동일가중, 미국/비미국 같은 축에서 누가 시장을 이끄는지 봅니다.</div>', unsafe_allow_html=True)
if has_rows(style):
    style_table = prep_style_table(style, bounce)
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
        detail = style_selected_comment(selected_now, choice, bounce)
        st.markdown("#### 선택 항목 해석")
        st.markdown(
            f"- 기준: {detail['기준']}\n"
            f"- 126일 → 63일 → 21일: {detail['126일']} → {detail['63일']} → {detail['21일']}\n"
            f"- **변화 판정: {detail['변화판정']}** — {detail['판정근거']}\n"
            f"- 종합: {detail['종합']}"
        )

        chart = hist[hist["pair_id"].eq(choice)].sort_values("date").copy()
        if len(chart):
            fig = plot_style_quadrant(selected_now, choice)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.caption("현재 시점의 126일·63일·21일 세 점만 표시합니다. 연결선 없이 위치 변화만 비교합니다.")

            style_payload = build_style_chart_snapshot(style, style_hist, choice, bounce)
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
        region_fig = plot_cross_quadrant_all_periods(region, REGION_MAP, REGION_SHORT, "VT", use_ticker_labels=False)
        st.plotly_chart(region_fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("126일·63일·21일을 같은 축으로 나란히 비교합니다. 정확한 수치는 점에 마우스를 올리면 보입니다.")
        if getattr(region_fig, "_missing_points", []):
            st.caption("미표시 데이터: " + ", ".join(region_fig._missing_points))
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
        gsec_fig = plot_cross_quadrant_all_periods(global_sector, GLOBAL_SECTOR, GLOBAL_SECTOR_SHORT, "VT", use_ticker_labels=True)
        st.plotly_chart(gsec_fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("세 기간을 같은 축으로 비교합니다. 점에는 ETF 티커만 표시하고 섹터명·수치는 hover에서 확인합니다.")
        if getattr(gsec_fig, "_missing_points", []):
            st.caption("미표시 데이터: " + ", ".join(gsec_fig._missing_points))
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
    us_fig = plot_cross_quadrant_all_periods(sector, US_SECTOR, US_SECTOR_SHORT, "SPY", use_ticker_labels=True)
    st.plotly_chart(us_fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("세 기간을 같은 축으로 비교합니다. 점에는 ETF 티커만 표시하고 섹터명·수치는 hover에서 확인합니다.")
    if getattr(us_fig, "_missing_points", []):
        st.caption("미표시 데이터: " + ", ".join(us_fig._missing_points))
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

# ---------- Stock supply ----------
st.subheader("6. 미국 · 글로벌 주식 공급")
st.markdown(
    '<div class="section-note">기존 상장기업의 발행주식수가 어느 섹터에서 늘고 줄어드는지 봅니다. 주식분할은 조정하고, 미국은 IVV·글로벌은 ACWI 구성종목 표본을 사용합니다.</div>',
    unsafe_allow_html=True,
)
if has_rows(stock_supply):
    supply_tabs = st.tabs(["미국", "글로벌", "글로벌 ex-US"])
    for tab, universe in zip(supply_tabs, ["US", "GLOBAL", "EX_US"]):
        with tab:
            supply_table = prep_supply_table(stock_supply, universe)
            if len(supply_table):
                st.dataframe(
                    supply_table,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "주식수 증감 3개월": st.column_config.NumberColumn(format="%.2f%%"),
                        "주식수 증감 6개월": st.column_config.NumberColumn(format="%.2f%%"),
                        "주식수 증감 12개월": st.column_config.NumberColumn(format="%.2f%%"),
                        "증가기업 비중 12개월": st.column_config.NumberColumn(format="%.1f%%"),
                        "감소기업 비중 12개월": st.column_config.NumberColumn(format="%.1f%%"),
                        "섹터가중치 커버리지": st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )
                h = st.radio(
                    "주식 공급 기간", ["3m", "6m", "12m"], horizontal=True,
                    key=f"supply_period_{universe}",
                    format_func=lambda x: {"3m":"3개월", "6m":"6개월", "12m":"12개월"}[x],
                )
                st.plotly_chart(plot_supply_quadrant(stock_supply, universe, h), use_container_width=True, config={"displayModeBar": False})
                st.caption("오른쪽은 가중 발행주식수 증가, 위쪽은 주식수가 늘어난 기업의 breadth가 더 넓다는 뜻입니다.")
                payload = build_supply_snapshot(stock_supply, universe, h)
                payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
                gpt_supply, gpt_supply_error = generate_gpt_text(
                    f"supply-v1:{universe}:{h}:" + payload_json,
                    model_name,
                    SUPPLY_PROMPT,
                    payload_json,
                )
                if gpt_supply:
                    render_gpt_box(gpt_supply, "주식 공급 해석")
                elif gpt_supply_error:
                    st.caption(f"GPT API 미연결: {gpt_supply_error}")
            else:
                st.info("이 시장의 주식 공급 데이터가 아직 충분하지 않습니다.")
    st.markdown(
        '<div class="supply-note">※ 이 지표는 기존 상장기업의 shares outstanding 변화입니다. IPO·SPAC·신규 상장 전체 공급을 완전히 포함하지 않으므로 Fisher식 equity-supply 판단의 한 구성요소로 사용합니다. 글로벌 데이터는 ACWI 표본이며 섹터별 커버리지를 함께 표시합니다.</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("주식 공급 데이터는 새 파이프라인을 한 번 실행하면 생성됩니다. GitHub Actions의 Run workflow를 실행해 주세요.")

st.divider()

# ---------- Qualitative anchors ----------
st.subheader("7. 해석 메모")
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
    with st.expander("8. 반등 효과 점검"):
        cols = [c for c in ["ticker", "group", "subgroup", "max_drawdown_252", "max_drawdown_126", "rebound_from_126d_low", "current_drawdown_from_126d_high"] if c in bounce.columns]
        show = bounce[cols].copy()
        for c in ["max_drawdown_252", "max_drawdown_126", "rebound_from_126d_low", "current_drawdown_from_126d_high"]:
            if c in show.columns:
                show[c] = pd.to_numeric(show[c], errors="coerce") * 100
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.caption("최근 강세가 추세 전환인지, 큰 낙폭 뒤 반등인지 구분할 때 참고합니다.")

st.caption("매주 미국 금요일 장 마감 후 자동 업데이트 · 차트/섹션별 GPT 해석은 동일 데이터 기준 캐시됩니다.")
