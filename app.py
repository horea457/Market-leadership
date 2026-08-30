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
    padding-top: 1.15rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}
.block-container h1 {
    line-height: 1.30 !important;
    padding-top: 0.06em !important;
    padding-bottom: 0.18em !important;
    margin-bottom: 0.10em !important;
    overflow: visible !important;
}
.block-container h1 span,
.block-container h1 div {
    line-height: 1.30 !important;
    overflow: visible !important;
}
.metric-card {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 14px;
    padding: 16px 18px;
    min-height: 150px;
    height: auto;
    overflow: visible;
    box-sizing: border-box;
    background: white;
}
.metric-label {
    font-size: 0.95rem;
    color: #475569;
    margin-bottom: 0.35rem;
    font-weight: 600;
}
.metric-value {
    font-size: clamp(1.35rem, 1.75vw, 1.9rem);
    line-height: 1.22;
    font-weight: 700;
    color: #0f172a;
    word-break: keep-all;
    overflow-wrap: anywhere;
    white-space: normal;
}
.metric-value-compact {
    font-size: 0.94rem;
    line-height: 1.48;
    font-weight: 600;
    color: #0f172a;
    white-space: normal;
    word-break: keep-all;
    overflow-wrap: anywhere;
}
.metric-sub-compact {
    margin-top: 0.55rem;
    font-size: 0.82rem;
    color: #64748b;
    line-height: 1.35;
    word-break: keep-all;
    overflow-wrap: anywhere;
}
.metric-sub {
    margin-top: 0.7rem;
    font-size: 0.88rem;
    color: #64748b;
    line-height: 1.35;
    word-break: keep-all;
    overflow-wrap: anywhere;
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

.dashboard-title {
    display: block;
    font-size: clamp(2.0rem, 3vw, 3.0rem);
    font-weight: 800;
    line-height: 1.55;
    letter-spacing: -0.035em;
    color: #0f172a;
    margin: 0 0 0.25rem 0;
    padding: 0.16em 0 0.34em 0;
    min-height: 1.8em;
    overflow: visible !important;
    white-space: normal;
}
.dashboard-subtitle {
    color: #64748b;
    font-size: 0.92rem;
    margin-bottom: 1rem;
}


.action-callout {
    border: 1px solid rgba(37, 99, 235, 0.20);
    border-left: 5px solid #2563eb;
    border-radius: 12px;
    padding: 14px 16px;
    margin-top: 10px;
    margin-bottom: 8px;
    background: rgba(37, 99, 235, 0.035);
}
.action-callout-title {
    font-size: 0.92rem;
    font-weight: 800;
    color: #1e3a8a;
    margin-bottom: 5px;
}
.action-callout-text {
    font-size: 1.02rem;
    line-height: 1.52;
    font-weight: 650;
    color: #0f172a;
    word-break: keep-all;
    overflow-wrap: anywhere;
}


.leader-board {
    margin: 0.25rem 0 1rem 0;
}
.leader-board-title {
    font-size: 1.02rem;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 0.55rem;
}
.leader-card {
    border: 1px solid rgba(148, 163, 184, .30);
    border-radius: 13px;
    padding: 13px 15px;
    min-height: 154px;
    background: #fff;
    box-sizing: border-box;
}
.leader-card-label {
    color: #475569;
    font-weight: 800;
    font-size: .88rem;
    margin-bottom: .5rem;
}
.leader-row {
    display: flex;
    align-items: baseline;
    gap: .42rem;
    margin: .27rem 0;
    line-height: 1.35;
    flex-wrap: wrap;
}
.leader-horizon {
    min-width: 74px;
    color: #64748b;
    font-size: .79rem;
    font-weight: 700;
}
.leader-name {
    color: #0f172a;
    font-size: .94rem;
    font-weight: 800;
}
.leader-return {
    color: #64748b;
    font-size: .79rem;
}
.leader-status {
    margin-top: .52rem;
    padding-top: .48rem;
    border-top: 1px solid rgba(148, 163, 184, .18);
    color: #334155;
    font-size: .80rem;
    line-height: 1.4;
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
    "EWY": "EWY (한국)",
    "MCHI": "MCHI (중국)",
}

REGION_SHORT = {
    "VTI": "미국",
    "VEA": "선진국(미국 제외)",
    "VWO": "신흥국",
    "VGK": "유럽",
    "EWJ": "일본",
    "EWY": "한국",
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
                lines.append(
                    f"{label}: "
                    f"{leader_to_kor(r.get('leader_126'))} → "
                    f"{leader_to_kor(r.get('leader_63'))} → "
                    f"{leader_to_kor(r.get('leader_21'))}"
                )

    if has_rows(global_sector_df):
        top126 = global_sector_df.sort_values(["rank_126", "rank_63", "rank_21"]).iloc[0].get("ticker")
        top63 = global_sector_df.sort_values(["rank_63", "rank_21"]).iloc[0].get("ticker")
        top21 = global_sector_df.sort_values(["rank_21", "rank_63"]).iloc[0].get("ticker")
        lines.append(
            f"글로벌 섹터: "
            f"{GLOBAL_SECTOR_SHORT.get(top126, top126)} → "
            f"{GLOBAL_SECTOR_SHORT.get(top63, top63)} → "
            f"{GLOBAL_SECTOR_SHORT.get(top21, top21)}"
        )
    elif has_rows(sector_df):
        top126 = sector_df.sort_values(["rank_126", "rank_63", "rank_21"]).iloc[0].get("ticker")
        top63 = sector_df.sort_values(["rank_63", "rank_21"]).iloc[0].get("ticker")
        top21 = sector_df.sort_values(["rank_21", "rank_63"]).iloc[0].get("ticker")
        lines.append(
            f"미국 섹터: "
            f"{US_SECTOR_SHORT.get(top126, top126)} → "
            f"{US_SECTOR_SHORT.get(top63, top63)} → "
            f"{US_SECTOR_SHORT.get(top21, top21)}"
        )
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
    """
    Return an explicit transition headline and a short explanation.
    Example: ('대형주 → 소형주', '전환 초기 · IWB/IWM')
    """
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
        candidates.append((priority.get(base, 1), label, r.get("pair_id"), r, reason))

    candidates.sort(key=lambda x: x[0], reverse=True)

    if not candidates or candidates[0][0] == 0:
        return ("뚜렷한 전환 없음", "126·63·21일 리더십이 대체로 정렬")

    _, label, pid, row, _ = candidates[0]
    l21 = row.get("leader_21")
    l63 = row.get("leader_63")
    l126 = row.get("leader_126")

    # Direction should describe the actual old center -> new leader.
    if l21 != l63:
        old_leader, new_leader = l63, l21
    elif l63 != l126:
        old_leader, new_leader = l126, l63
    else:
        old_leader, new_leader = l126, l21

    headline = f"{leader_to_kor(old_leader)} → {leader_to_kor(new_leader)}"

    ticker_hint = {
        "growth_value": "IWF/IWD",
        "large_small": "IWB/IWM",
        "cap_equal": "SPY/RSP",
        "small_value_large_growth": "IWN/IWF",
        "us_developed_ex_us": "VTI/VEA",
        "developed_em": "VEA/VWO",
        "cyclical_defensive": "경기민감/방어",
    }.get(pid, "")

    short_label = label.replace(" · 반등효과 주의", "")
    sub = f"{short_label}"
    if ticker_hint:
        sub += f" · {ticker_hint}"
    if "반등효과 주의" in label:
        sub += " · 반등효과 주의"

    return headline, sub


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
    turnover = cross_section_turnover(df, mapping)
    return {
        "비교기준": benchmark_label,
        "구조판정": turnover,
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
            max_output_tokens=1100,
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
    st.markdown(_main_section_html("레짐·시장 구조", sections.get("동향", []), "trend"), unsafe_allow_html=True)
    st.markdown(_main_section_html("리더십 구조 해석", sections.get("인사이트", []), "insight"), unsafe_allow_html=True)

    action = str(sections.get("현재 대응", "") or "").strip()
    if action:
        safe_action = html.escape(action)
        st.markdown(
            f"""
            <div class="action-callout">
                <div class="action-callout-title">현재 대응</div>
                <div class="action-callout-text">{safe_action}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
    for key in ["동향", "인사이트"]:
        val = obj.get(key, [])
        if isinstance(val, str):
            val = [val]
        if not isinstance(val, list):
            val = []
        out[key] = [str(x).strip() for x in val if str(x).strip()][:6]

    action = obj.get("현재 대응", "")
    if isinstance(action, list):
        action = " ".join(str(x).strip() for x in action if str(x).strip())
    out["현재 대응"] = str(action).strip() if action is not None else ""
    return out




def _top_ticker(df, rank_col):
    if not has_rows(df) or rank_col not in df.columns:
        return None
    x = df.copy()
    x[rank_col] = pd.to_numeric(x[rank_col], errors="coerce")
    x = x.dropna(subset=[rank_col]).sort_values(rank_col)
    return x.iloc[0].get("ticker") if len(x) else None


def leadership_coherence(style, sector, global_sector, region):
    """
    Test whether multiple independent leadership axes tell one coherent story.
    This is stronger evidence than a single 21D winner.
    """
    gv = _style_row(style, "growth_value")
    ls = _style_row(style, "large_small")
    ce = _style_row(style, "cap_equal")
    usx = _style_row(style, "us_developed_ex_us")
    de = _style_row(style, "developed_em")

    signals = []
    growth_complex = 0
    broad_value_complex = 0

    def leader(row, w=21):
        return str(row.get(f"leader_{w}")) if row is not None else ""

    if leader(gv) == "Growth":
        growth_complex += 1
        signals.append("성장")
    elif leader(gv) == "Value":
        broad_value_complex += 1
        signals.append("가치")

    if leader(ce) == "Cap-weight":
        growth_complex += 1
        signals.append("시총가중")
    elif leader(ce) == "Equal-weight":
        broad_value_complex += 1
        signals.append("동일가중")

    if leader(ls) == "Large":
        growth_complex += 1
        signals.append("대형")
    elif leader(ls) == "Small":
        broad_value_complex += 1
        signals.append("소형")

    if leader(usx) in ["US", "United States"]:
        growth_complex += 1
        signals.append("미국")
    elif leader(usx):
        broad_value_complex += 1
        signals.append("비미국")

    if leader(de) in ["Emerging", "EM"]:
        broad_value_complex += 1
        signals.append("신흥국")

    us21 = _top_ticker(sector, "rank_21")
    gl21 = _top_ticker(global_sector, "rank_21")
    reg21 = _top_ticker(region, "rank_21")

    growth_sectors = {"XLK", "XLC", "XLY", "IXN", "IXP", "RXI"}
    broad_value_sectors = {"XLF", "XLI", "XLE", "XLB", "XLRE",
                           "IXG", "EXI", "IXC", "MXI", "REET"}

    if us21 in growth_sectors:
        growth_complex += 1
    elif us21 in broad_value_sectors:
        broad_value_complex += 1

    if gl21 in growth_sectors:
        growth_complex += 1
    elif gl21 in broad_value_sectors:
        broad_value_complex += 1

    if growth_complex >= 4 and growth_complex >= broad_value_complex + 2:
        state = "성장·대형주 복합 신호"
        strength = "정렬"
    elif broad_value_complex >= 4 and broad_value_complex >= growth_complex + 2:
        state = "가치·확산 복합 신호"
        strength = "정렬"
    else:
        state = "혼합 회전"
        strength = "비정렬"

    return {
        "state": state,
        "strength": strength,
        "growth_points": growth_complex,
        "broad_value_points": broad_value_complex,
        "us_sector_21": US_SECTOR_SHORT.get(us21, us21),
        "global_sector_21": GLOBAL_SECTOR_SHORT.get(gl21, gl21),
        "region_21": REGION_MAP.get(reg21, reg21),
    }


def leader_supply_response(stock_supply, sector, global_sector):
    """
    Compare price leaders with listed-company share-count supply.
    Rising price leadership + rising supply = capital is responding to prices.
    Contracting supply = no broad equity-supply response yet.
    """
    if not has_rows(stock_supply):
        return {
            "status": "미측정",
            "text": "상장기업 주식공급 데이터 없음",
            "overlap": False,
        }

    leaders = []
    us21 = _top_ticker(sector, "rank_21")
    gl21 = _top_ticker(global_sector, "rank_21")
    if us21:
        leaders.append(("US", US_SECTOR_SHORT.get(us21, us21)))
    if gl21:
        leaders.append(("EX_US", GLOBAL_SECTOR_SHORT.get(gl21, gl21)))

    # sector_ko is the common bridge available in the current supply data.
    observations = []
    overlap = False
    for universe, leader_name in leaders:
        u = stock_supply[stock_supply["universe"].eq(universe)].copy()
        if not len(u):
            continue
        u["weighted_change_12m"] = pd.to_numeric(u["weighted_change_12m"], errors="coerce")
        u = u.dropna(subset=["weighted_change_12m"])
        if not len(u):
            continue

        # Match by Korean sector label with a few normalization rules.
        norm = str(leader_name).replace("커뮤니케이션서비스", "커뮤니케이션")
        def normalize_sector(v):
            return str(v).replace("커뮤니케이션서비스", "커뮤니케이션")
        matched = u[u["sector_ko"].map(normalize_sector).eq(norm)] if "sector_ko" in u.columns else pd.DataFrame()

        if len(matched):
            val = float(matched.iloc[0]["weighted_change_12m"])
            observations.append(f"{leader_name} {val*100:+.1f}%")
            if val >= 0.0075:
                overlap = True

    us_summary = _supply_universe_summary(stock_supply, "US")
    ex_summary = _supply_universe_summary(stock_supply, "EX_US")
    broad_contracting = (
        us_summary and ex_summary
        and us_summary["weighted_change"] <= 0
        and ex_summary["weighted_change"] <= 0
    )

    if overlap:
        status = "리더에 공급 반응 시작"
        text = " · ".join(observations) if observations else "현재 리더 섹터에서 주식공급 증가"
    elif broad_contracting:
        status = "광범위 공급 반응 없음"
        text = (
            f"미국 {us_summary['weighted_change']*100:+.1f}% · "
            f"ex-US {ex_summary['weighted_change']*100:+.1f}%"
        )
    else:
        status = "공급 반응 혼조"
        text = " · ".join(observations) if observations else "리더와 공급 증가의 뚜렷한 중첩 없음"

    return {"status": status, "text": text, "overlap": overlap}


def leadership_rotation_summary(style, sector, global_sector, region, breadth, stock_supply=None):
    """
    Compact interpretation from currently available dashboard data.
    Breadth describes concentration; it is NOT used as a bullish/bearish veto.
    """
    coherence = leadership_coherence(style, sector, global_sector, region)
    supply = leader_supply_response(stock_supply, sector, global_sector)

    b21 = _breadth_value(breadth, 21)
    b63 = _breadth_value(breadth, 63)
    if b21 is None:
        breadth_text = "breadth 미측정"
    elif b63 is not None and b21 + 0.05 < b63:
        breadth_text = f"21일 {b21*100:.1f}% < 63일 {b63*100:.1f}%: 최근 회전은 좁게 진행"
    elif b63 is not None and b21 > b63 + 0.05:
        breadth_text = f"21일 {b21*100:.1f}% > 63일 {b63*100:.1f}%: 최근 회전이 넓어지는 중"
    else:
        breadth_text = f"21일 {b21*100:.1f}%: 확산 정도는 중립"

    return {
        "coherence": coherence,
        "supply": supply,
        "breadth_text": breadth_text,
    }



def bull_cycle_context(style_hist_df, regime_df):
    """
    Reference prior for the current global bull cycle.
    The 2022-10-12 VT low is treated as a cycle anchor, not a trading signal.
    """
    anchor = pd.Timestamp("2022-10-12")
    as_of = None

    if has_rows(style_hist_df) and "date" in style_hist_df.columns:
        dates = pd.to_datetime(style_hist_df["date"], errors="coerce").dropna()
        if len(dates):
            as_of = dates.max().normalize()

    if as_of is None:
        as_of = pd.Timestamp.now().normalize()

    days = max(0, int((as_of - anchor).days))
    years = days // 365
    months = int(round((days - years * 365) / 30.4))
    if months >= 12:
        years += 1
        months -= 12
    year_no = max(1, int(days // 365.25) + 1)

    drawdown = None
    regime_state = ""
    if has_rows(regime_df):
        r = regime_df.iloc[-1]
        regime_state = str(r.get("mechanical_state", "")).upper()
        try:
            drawdown = float(r.get("spy_drawdown_from_ath"))
        except Exception:
            pass

    bull = any(k in regime_state for k in ["BULL", "ADVANCE", "NEAR-BULL"])
    near_ath = drawdown is not None and drawdown >= -0.03

    if bull and year_no >= 4:
        phase = f"강세장 {year_no}년차"
        prior = "초기 강세장보다 성숙한 국면이라는 시간축 prior"
    elif bull:
        phase = f"강세장 {year_no}년차"
        prior = "강세장 진행 구간"
    else:
        phase = "강세장 연령 적용 제외"
        prior = "현재 기계적 레짐이 Bull이 아님"

    return {
        "anchor": anchor.strftime("%Y-%m-%d"),
        "as_of": as_of.strftime("%Y-%m-%d"),
        "age_text": f"{years}년 {months}개월",
        "year_no": year_no,
        "phase": phase,
        "prior": prior,
        "near_ath": near_ath,
        "drawdown": drawdown,
        "bull": bull,
    }


def cross_section_turnover(df, mapping):
    """
    Extract four structurally different states from 126D -> 63D -> 21D ranks.
    """
    if not has_rows(df):
        return {
            "지속리더": [],
            "신규리더후보": [],
            "단기급부상": [],
            "구리더이탈후보": [],
        }

    out = {
        "지속리더": [],
        "신규리더후보": [],
        "단기급부상": [],
        "구리더이탈후보": [],
    }

    for _, r in df.iterrows():
        try:
            r126 = float(r.get("rank_126"))
            r63 = float(r.get("rank_63"))
            r21 = float(r.get("rank_21"))
            ex63 = float(r.get("excess_63"))
            ex21 = float(r.get("excess_21"))
        except Exception:
            continue

        name = mapping.get(r.get("ticker"), r.get("ticker"))

        if r126 <= 3 and r63 <= 3 and r21 <= 3 and ex63 > 0 and ex21 > 0:
            out["지속리더"].append(name)

        # Not merely a bounce: medium-term leadership has already improved.
        if r126 >= 5 and r63 <= 4 and r21 <= 3 and ex63 > 0 and ex21 > 0:
            out["신규리더후보"].append(name)

        # 21D only: interesting, but not enough to call a new leader.
        if r21 <= 3 and r63 >= 6 and ex21 > 0:
            out["단기급부상"].append(name)

        # Former long-horizon leader that is now weak on both 63D and 21D.
        if r126 <= 3 and r63 >= 6 and r21 >= 6 and ex63 < 0 and ex21 < 0:
            out["구리더이탈후보"].append(name)

    return {k: v[:4] for k, v in out.items()}


def structural_leadership_snapshot(style, sector, global_sector, region, breadth, stock_supply=None):
    """
    Main structural read:
    1) cross-axis coherence,
    2) new-leader formation,
    3) former-leader failure,
    4) breadth concentration,
    5) supply response to price leadership.
    """
    coherence = leadership_coherence(style, sector, global_sector, region)
    us_turn = cross_section_turnover(sector, US_SECTOR_SHORT)
    gl_turn = cross_section_turnover(global_sector, GLOBAL_SECTOR_SHORT)
    reg_turn = cross_section_turnover(region, REGION_MAP)
    supply = leader_supply_response(stock_supply, sector, global_sector)

    b21 = _breadth_value(breadth, 21)
    b63 = _breadth_value(breadth, 63)
    b126 = _breadth_value(breadth, 126)

    if b21 is None:
        breadth_state = "미측정"
    elif b63 is not None and b21 < b63 - 0.05:
        breadth_state = "최근 리더십 집중"
    elif b63 is not None and b21 > b63 + 0.05:
        breadth_state = "최근 리더십 확산"
    else:
        breadth_state = "폭 변화 제한적"

    return {
        "교차축정렬": coherence,
        "지역": reg_turn,
        "글로벌섹터": gl_turn,
        "미국섹터": us_turn,
        "breadth": {
            "판정": breadth_state,
            "21일": b21,
            "63일": b63,
            "126일": b126,
            "주의": "낮은 breadth 자체를 약세 신호로 보지 않음",
        },
        "주식공급반응": supply,
    }



def _period_leader(df, mapping, period):
    """Return the #1 leader for a period with explicit label and excess return."""
    rank_col = f"rank_{period}"
    excess_col = f"excess_{period}"
    if not has_rows(df) or rank_col not in df.columns:
        return None

    x = df.copy()
    x[rank_col] = pd.to_numeric(x[rank_col], errors="coerce")
    if excess_col in x.columns:
        x[excess_col] = pd.to_numeric(x[excess_col], errors="coerce")
    x = x.dropna(subset=[rank_col]).sort_values([rank_col, excess_col] if excess_col in x.columns else [rank_col])
    if not len(x):
        return None

    r = x.iloc[0]
    ticker = r.get("ticker")
    excess = r.get(excess_col) if excess_col in x.columns else None
    return {
        "ticker": ticker,
        "name": mapping.get(ticker, ticker),
        "rank": int(r.get(rank_col)) if pd.notna(r.get(rank_col)) else None,
        "excess": float(excess) if excess is not None and pd.notna(excess) else None,
    }


def _top_n_period(df, mapping, period, n=3):
    rank_col = f"rank_{period}"
    excess_col = f"excess_{period}"
    if not has_rows(df) or rank_col not in df.columns:
        return []
    x = df.copy()
    x[rank_col] = pd.to_numeric(x[rank_col], errors="coerce")
    if excess_col in x.columns:
        x[excess_col] = pd.to_numeric(x[excess_col], errors="coerce")
    x = x.dropna(subset=[rank_col]).sort_values(rank_col).head(n)
    out = []
    for _, r in x.iterrows():
        ticker = r.get("ticker")
        out.append({
            "ticker": ticker,
            "name": mapping.get(ticker, ticker),
            "rank": int(r.get(rank_col)) if pd.notna(r.get(rank_col)) else None,
            "excess": float(r.get(excess_col)) if excess_col in x.columns and pd.notna(r.get(excess_col)) else None,
        })
    return out


def current_leader_board(region, global_sector, sector):
    """
    63D is the current center.
    21D is the short-term challenger.
    126D is the prior / established trend.
    """
    boards = []
    for key, label, df, mapping, benchmark in [
        ("region", "지역", region, REGION_MAP, "VT"),
        ("global_sector", "글로벌 섹터", global_sector, GLOBAL_SECTOR, "VT"),
        ("us_sector", "미국 섹터", sector, US_SECTOR, "SPY"),
    ]:
        p126 = _period_leader(df, mapping, 126)
        p63 = _period_leader(df, mapping, 63)
        p21 = _period_leader(df, mapping, 21)

        if p126 and p63 and p21:
            if p126["ticker"] == p63["ticker"] == p21["ticker"]:
                status = "126·63·21일 모두 1위 → 지속 리더"
            elif p63["ticker"] == p21["ticker"]:
                status = "63·21일 1위 일치 → 현재 리더십 강화"
            elif p126["ticker"] == p63["ticker"] and p21["ticker"] != p63["ticker"]:
                status = "기존 리더 유지 중, 21일 단기 도전자 출현"
            else:
                status = "리더 교체 진행/혼조"
        else:
            status = "데이터 확인 필요"

        boards.append({
            "key": key,
            "label": label,
            "benchmark": benchmark,
            "126": p126,
            "63": p63,
            "21": p21,
            "top3_63": _top_n_period(df, mapping, 63, 3),
            "top3_21": _top_n_period(df, mapping, 21, 3),
            "status": status,
        })
    return boards


def _leader_line_html(horizon_label, obj):
    if not obj:
        return (
            f'<div class="leader-row"><span class="leader-horizon">{horizon_label}</span>'
            f'<span class="leader-name">—</span></div>'
        )
    ex = ""
    if obj.get("excess") is not None:
        ex = f'<span class="leader-return">({obj["excess"]*100:+.1f}%p)</span>'
    return (
        f'<div class="leader-row"><span class="leader-horizon">{horizon_label}</span>'
        f'<span class="leader-name">{html.escape(str(obj["name"]))}</span>{ex}</div>'
    )


def render_current_leader_board(region, global_sector, sector):
    boards = current_leader_board(region, global_sector, sector)
    st.markdown(
        '<div class="leader-board-title">현재 리더 · 63일을 현재 중심으로 봅니다</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3, gap="small")
    for col, b in zip(cols, boards):
        with col:
            html_block = (
                '<div class="leader-card">'
                f'<div class="leader-card-label">{b["label"]} · {b["benchmark"]} 대비</div>'
                + _leader_line_html("126일 기존", b["126"])
                + _leader_line_html("63일 현재", b["63"])
                + _leader_line_html("21일 단기", b["21"])
                + f'<div class="leader-status">{html.escape(b["status"])}</div>'
                + '</div>'
            )
            st.markdown(html_block, unsafe_allow_html=True)
    st.caption(
        "63일 = 현재 중심축, 21일 = 최근 변화/도전자, 126일 = 기존 추세. "
        "괄호는 각 비교기준 대비 초과수익입니다."
    )
    return boards


def leader_board_snapshot(region, global_sector, sector):
    """Compact JSON payload for GPT so it cannot miss who the current leaders are."""
    boards = current_leader_board(region, global_sector, sector)
    out = {}
    for b in boards:
        def clean(obj):
            if not obj:
                return None
            return {
                "ticker": obj.get("ticker"),
                "이름": obj.get("name"),
                "초과수익": round(obj.get("excess"), 4) if obj.get("excess") is not None else None,
            }
        out[b["label"]] = {
            "비교기준": b["benchmark"],
            "126일_기존리더": clean(b["126"]),
            "63일_현재리더": clean(b["63"]),
            "21일_단기리더": clean(b["21"]),
            "63일_top3": [clean(x) for x in b["top3_63"]],
            "21일_top3": [clean(x) for x in b["top3_21"]],
            "상태": b["status"],
        }
    return out


def build_current_action(style, sector, global_sector, region, breadth, cycle=None,
                         stock_supply=None, regime=None, style_hist=None):
    """
    Portfolio direction:
    - Do not exit a bull merely because it is near ATH.
    - Do not chase a 21D winner.
    - Prefer 63D persistence + cross-axis alignment + former-leader failure.
    """
    structural = structural_leadership_snapshot(
        style, sector, global_sector, region, breadth, stock_supply
    )
    age = bull_cycle_context(style_hist, regime)

    # Best current targets.
    focus = []
    for block_key in ["지역", "글로벌섹터", "미국섹터"]:
        block = structural.get(block_key, {})
        for k in ["신규리더후보", "단기급부상", "지속리더"]:
            vals = block.get(k, [])
            if vals:
                focus.extend(vals[:1])
                break
    focus = [x for i, x in enumerate(focus) if x and x not in focus[:i]]
    focus_text = "·".join(focus[:3]) if focus else "현재 상위 리더"

    old_fail = (
        structural["지역"].get("구리더이탈후보", [])
        + structural["글로벌섹터"].get("구리더이탈후보", [])
        + structural["미국섹터"].get("구리더이탈후보", [])
    )

    coherence = structural["교차축정렬"]
    new_confirmed = (
        len(structural["지역"].get("신규리더후보", []))
        + len(structural["글로벌섹터"].get("신규리더후보", []))
        + len(structural["미국섹터"].get("신규리더후보", []))
    )

    # Regime action first.
    if age["bull"] and age["near_ath"] and age["year_no"] >= 4:
        regime_action = (
            "시장 이탈보다 핵심 롱은 유지"
            "; 시간제약 레버리지가 있다면 점진 축소"
        )
    elif age["bull"]:
        regime_action = "핵심 롱 유지"
    else:
        regime_action = "시장 레짐 재확인을 우선"

    # Leadership action second.
    if new_confirmed > 0 and coherence.get("strength") == "정렬":
        leadership_action = (
            f"{focus_text}는 63일에서도 리더 후보가 확인되므로 신규 리서치·비중 확대를 단계적으로 검토"
        )
    else:
        leadership_action = (
            f"{focus_text}는 관찰하되 21일 승자 추격은 보류; "
            "63일 우위와 다른 스타일·지역·섹터의 동조가 생길 때 비중 이동을 검토"
        )

    if old_fail:
        old_text = " / ".join(old_fail[:3])
        tail = f" 기존 리더 중 {old_text}의 복귀 실패가 이어지면 과거 리더 복귀보다 신규 리더 탐색을 우선"
    else:
        tail = " 기존 리더의 63·21일 약화가 동시에 확인되는지도 함께 봅니다"

    return f"{regime_action}. {leadership_action}. {tail}."


def fallback_main_sections(style, sector, global_sector, region, breadth, stock_supply=None,
                           bounce_df=None, regime=None, style_hist=None):
    regime_lines, leadership_lines = [], []

    age = bull_cycle_context(style_hist, regime)
    structural = structural_leadership_snapshot(
        style, sector, global_sector, region, breadth, stock_supply
    )
    leaders = current_leader_board(region, global_sector, sector)

    if age["bull"]:
        dd = age.get("drawdown")
        dd_txt = f", 전고점 대비 {dd*100:.1f}%" if dd is not None else ""
        regime_lines.append(
            f"{age['phase']}({age['age_text']}){dd_txt}. 시장 전체 레짐은 Bull이며 고점권 자체를 약세 전환 신호로 보지 않습니다."
        )
    elif has_rows(regime):
        r = regime.iloc[-1]
        regime_lines.append(
            f"현재 시장 전체 레짐은 {regime_to_kor(str(r.get('mechanical_state', '—')))}입니다."
        )

    # Explicit current leaders.
    current_parts = []
    short_parts = []
    for b in leaders:
        if b["63"]:
            current_parts.append(f"{b['label']} {b['63']['name']}")
        if b["21"] and b["63"] and b["21"]["ticker"] != b["63"]["ticker"]:
            short_parts.append(f"{b['label']} {b['21']['name']}")
    if current_parts:
        leadership_lines.append("현재 63일 리더: " + " / ".join(current_parts) + ".")
    if short_parts:
        leadership_lines.append("21일 단기 도전자: " + " / ".join(short_parts) + ".")

    # New leaders / old leader failure.
    new_parts, old_parts, persistent_parts = [], [], []
    for label, block in [
        ("지역", structural["지역"]),
        ("글로벌", structural["글로벌섹터"]),
        ("미국", structural["미국섹터"]),
    ]:
        if block.get("신규리더후보"):
            new_parts.append(f"{label} " + "·".join(block["신규리더후보"][:2]))
        if block.get("구리더이탈후보"):
            old_parts.append(f"{label} " + "·".join(block["구리더이탈후보"][:2]))
        if block.get("지속리더"):
            persistent_parts.append(f"{label} " + "·".join(block["지속리더"][:2]))

    if persistent_parts:
        leadership_lines.append("지속 리더: " + " / ".join(persistent_parts) + ".")
    if new_parts:
        leadership_lines.append("신규 리더 후보: " + " / ".join(new_parts) + ".")
    if old_parts:
        leadership_lines.append("기존 리더 이탈 후보: " + " / ".join(old_parts) + ".")
    elif not new_parts:
        leadership_lines.append("구 리더의 구조적 이탈과 신규 리더의 63일 정착은 아직 뚜렷하지 않습니다.")

    b = structural["breadth"]
    if b.get("21일") is not None:
        btxt = f"21일 {b['21일']*100:.1f}%"
        if b.get("63일") is not None:
            btxt += f" vs 63일 {b['63일']*100:.1f}%"
        leadership_lines.append(
            f"리더십 폭: {btxt} — {b['판정']}. 이는 약세 신호가 아니라 리더십이 얼마나 집중됐는지 보여줍니다."
        )

    supply = structural["주식공급반응"]
    if supply.get("status") != "미측정":
        leadership_lines.append(
            f"공급 반응: {supply['status']} — {supply['text']}. 현재 가격 리더에 자본공급이 따라붙는지 확인합니다."
        )

    return {
        "동향": regime_lines[:2],
        "인사이트": leadership_lines[:6],
        "현재 대응": build_current_action(
            style, sector, global_sector, region, breadth,
            stock_supply=stock_supply, regime=regime, style_hist=style_hist
        ),
    }


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
        return f"<p><b>판정</b>: {snapshot['선택기간']}일 참여 폭은 {val*100:.1f}%입니다.</p><p><b>의미</b>: 수치가 낮으면 리더십이 일부 종목에 집중된 것이며, 그 자체를 약세 신호로 보지는 않습니다.</p>"
    return "<p>시장 참여 폭을 통해 상승 확산 여부를 확인할 수 있습니다.</p>"


MAIN_PROMPT = """
너는 글로벌 주식시장 레짐과 리더십 변화를 해석하는 투자 리서치 보조자다.
입력 JSON의 수치만 사용한다. 외부 뉴스나 원인을 만들지 않는다.

반드시 아래 JSON 객체 하나만 출력한다.
{
  "동향": ["문장", "문장"],
  "인사이트": ["문장", "문장", "문장", "문장", "문장"],
  "현재 대응": "한 문장"
}

가장 중요한 정의:
- 63일 = 현재 시장의 중심 리더십.
- 21일 = 단기 변화/도전자. 21일만 강하면 현재 리더라고 부르지 않는다.
- 126일 = 기존 추세/과거 리더.
- 지역, 글로벌 섹터, 미국 섹터를 반드시 각각 따로 말한다.
- ticker와 한글 이름을 같이 쓴다. 예: EWY(한국), XLE(에너지), MXI(글로벌 소재).

핵심 방법론:
- 시장 전체 Bull/Bear 레짐과 스타일·지역·섹터 상대성과를 분리한다.
- 126일 → 63일 → 21일 순서로 구조 변화를 읽되, '현재 리더'라는 표현은 63일 1위에 사용한다.
- 21일 단독 1위는 '단기 도전자/급부상'으로 부른다.
- 63일·21일이 함께 강하고 126일보다 순위가 개선된 대상은 '신규 리더 후보'다.
- 126일 과거 리더가 63일·21일 모두 밀리면 '기존 리더 이탈 후보'다.
- breadth는 좋고 나쁨이 아니라 리더십 집중/확산만 설명한다.
- 주식공급은 현재 가격 리더에 자본·경쟁·신규공급이 반응하는지 본다.
- 공급 감소를 곧바로 bullish, 공급 증가를 곧바로 bearish라고 하지 않는다.
- 섹터 ETF가 비리딩이어도 내부 신규 대표 기업은 별도 스크리닝 대상이다.

작성 규칙:
1. "동향"은 2개 문장.
2. 첫 문장: 시장 레짐, 강세장 연령, 전고점 위치.
3. 두 번째 문장: 스타일 리더십에서 126→63→21의 가장 중요한 변화.
4. "인사이트"는 5~6개 문장.
5. 첫 문장은 반드시 "현재 리더:"로 시작하고 63일 기준 지역·글로벌 섹터·미국 섹터 3개를 모두 명시한다.
6. 두 번째 문장은 "단기 변화:"로 시작하고 21일 리더가 63일 리더와 다른 축을 구체적으로 쓴다.
7. 세 번째 문장은 "구조 변화:"로 시작하고 신규 리더 후보와 지속 리더를 구분한다.
8. 네 번째 문장은 "구 리더:"로 시작하고 이탈 후보가 있는지 명시한다.
9. 다섯 번째 문장은 "리더십 폭:"으로 시작하고 21일과 63일 breadth를 집중/확산으로 해석한다.
10. 여섯 번째 문장이 필요하면 "공급:"으로 시작하고 현재 리더와 주식공급의 중첩을 설명한다.
11. 일반론을 반복하지 말고 실제 ticker·지역·섹터·수치 중심으로 쓴다.
12. "현재 대응"은 지금 유지할 것, 추격하지 않을 것, 무엇이 확인되면 비중 이동을 검토할지를 한 문장에 쓴다.
13. 행동 조건은 breadth 50%/60% 같은 고정 임계값이 아니라 63일 지속성 + 교차축 동조 + 구 리더 약화를 사용한다.
14. 시간제약 레버리지가 있다는 경우에만 점진 축소를 조건부로 언급한다.
15. 특정 ETF 직접 매수/매도 명령은 하지 않는다.
16. 특정 필명은 절대 쓰지 않는다.
"""

STYLE_CHART_PROMPT = """
너는 특정 스타일 리더십 축을 해석하는 투자 리서치 보조자다.
출력은 HTML <ul> 안 4개 bullet만 쓴다.
제목은 <b>현재 구조</b>, <b>지속성</b>, <b>반등효과</b>, <b>다음 판정</b>.

규칙:
- 반드시 126일 → 63일 → 21일 순서로 읽는다.
- 21일 단독 반전은 중기 리더십 전환으로 과대평가하지 않는다.
- 21·63일 정렬 + 빈도와 상대강도 동조는 전환 신뢰도를 높인다.
- frequency는 얼마나 자주 이겼는지, magnitude/상대수익은 얼마나 크게 이겼는지를 구분해 설명한다.
- 큰 과거 낙폭 뒤의 21일 강세는 반등효과 가능성을 먼저 점검한다.
- 성장/가치·대형/소형 상대성과를 '성장주 베어마켓/가치주 베어마켓'이라고 부르지 않는다.
- 무엇이 63일 또는 126일까지 이어지면 구조적 전환으로 승격할지 한 문장으로 명시한다.
"""

CROSS_SECTION_PROMPT = """
너는 지역/섹터 리더십의 교체 과정을 해석하는 투자 리서치 보조자다.
출력은 HTML <ul> 안 4개 bullet만 쓴다.
제목은 <b>기존 리더</b>, <b>신규 리더 후보</b>, <b>이탈 후보</b>, <b>다음 판정</b>.

규칙:
- 비교기준(SPY 또는 VT)을 먼저 밝힌다.
- 126일→63일→21일 순위를 본다.
- 21일만 상위권이면 '단기 급부상', 63일·21일이 함께 상위권이고 초과수익이 양수면 '신규 리더 후보'로 표현한다.
- 126일 상위권이던 대상이 63일·21일 모두 하위권이고 초과수익도 음수면 '기존 리더 이탈 후보'로 표현한다.
- 시장 전체가 회복하는데도 과거 리더가 복귀하지 못하는 현상을 새 레짐의 단서로 본다.
- 다만 현재 데이터는 최대 126일이므로 장기간 구조적 탈락을 확정하지 말고 '후보'로 표현한다.
- 섹터 ETF가 비리딩이어도 섹터 내부의 신규 대표 기업은 존재할 수 있음을 한 줄에서 주의한다.
"""

BREADTH_PROMPT = """
너는 시장 breadth를 '리더십의 폭'으로 해석하는 보조자다.
출력은 HTML <ul> 안 4개 bullet만 쓴다.
제목은 <b>현재 폭</b>, <b>21일 vs 63일</b>, <b>레짐 의미</b>, <b>다음 관찰</b>.

규칙:
- breadth가 낮으면 '나쁜 시장', 높으면 '좋은 시장'이라고 말하지 않는다.
- 회의주의에서는 리딩 후보가 많아 폭이 넓고 상대수익 차이가 작을 수 있다.
- 낙관주의로 넘어갈수록 진짜 리딩 섹터가 형성되며 breadth가 좁아질 수 있다.
- 따라서 21일 breadth가 63일보다 낮으면 '최근 리더십 집중', 높으면 '최근 리더십 확산'이라고 표현한다.
- breadth는 리더십 교체의 승인 임계값이 아니다. 50%/60% 같은 고정 임계값으로 매매 조건을 만들지 않는다.
- 스타일·지역·섹터의 63일 지속성과 함께 읽는다.
"""

SENTIMENT_PROMPT = """
너는 VIX·하이일드·시장추세 proxy를 해석하는 보조자다.
출력은 HTML <ul> 안 3개 bullet만 쓴다.
제목은 <b>현재 위험 스트레스</b>, <b>무엇을 말해주나</b>, <b>무엇을 말해주지 못하나</b>.

규칙:
- VIX·HY는 현재 위험 스트레스의 동행 지표로 설명한다.
- VIX가 낮다는 이유만으로 유포리아, 높다는 이유만으로 비관주의를 판정하지 않는다.
- 심리 사이클에는 expectations gap, 전문가/대중의 기대, IPO·신규공급이 추가로 필요하다고 명시한다.
"""

SUPPLY_PROMPT = """
너는 섹터별 주식공급을 자본사이클 관점에서 해석하는 투자 리서치 보조자다.
입력은 기존 상장기업의 발행주식수 증감 proxy이며 IPO 전체 공급과 동일하지 않다.
출력은 HTML <ul> 안 4개 bullet만 쓴다.
제목은 <b>공급 상태</b>, <b>가격 리더와 중첩</b>, <b>시차</b>, <b>의미</b>.

규칙:
- 주가 상승은 미래 공급·창업·모방·경쟁을 유도하는 인센티브가 될 수 있다.
- 공급 반응에는 시차가 있으므로 현재 공급 축소를 곧바로 bullish, 공급 증가를 곧바로 bearish로 해석하지 않는다.
- 현재 가격 리더 섹터에서 공급이 늘기 시작하는지를 가장 중요하게 본다.
- 가격 리더십은 강한데 공급이 아직 제한적이면 자본 부족/희소성 구간일 수 있다.
- 가격 리더십과 광범위 공급 확대가 겹치기 시작하면 사이클 성숙·경쟁 증가의 단서로 본다.
- 커버리지가 낮으면 단정하지 않는다.
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
        title={"text": title, "x": 0.02, "xanchor": "left", "y": 0.98, "yanchor": "top"},
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=560,
        margin=dict(l=85, r=85, t=105, b=85),
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0,
            font=dict(size=10),
        ),
        template="plotly_white",
        font=dict(family="Arial, Apple SD Gothic Neo, Malgun Gothic, sans-serif", size=12),
    )
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="#94a3b8")
    fig.add_hline(y=y_ref, line_width=1, line_dash="dash", line_color="#94a3b8")
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,.16)",
        zeroline=False,
        automargin=True,
        title_standoff=14,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,.16)",
        zeroline=False,
        automargin=True,
        title_standoff=14,
    )
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
    short_sector = {
        "커뮤니케이션서비스": "커뮤니케이션",
        "경기소비재": "경기소비재",
        "필수소비재": "필수소비재",
        "헬스케어": "헬스케어",
        "부동산": "부동산",
        "유틸리티": "유틸리티",
        "산업재": "산업재",
        "에너지": "에너지",
        "금융": "금융",
        "기술": "기술",
        "소재": "소재",
    }

    fig = go.Figure()
    xs, ys = [], []
    positions = ["top center", "bottom center", "middle right", "middle left"]

    for i, (_, r) in enumerate(x.iterrows()):
        full_label = str(r.get("sector_ko", r.get("sector")))
        point_label = short_sector.get(full_label, full_label)
        xv, yv = float(r[chg]), float(r[br])
        xs.append(xv)
        ys.append(yv)

        fig.add_trace(go.Scatter(
            x=[xv],
            y=[yv],
            mode="markers+text",
            name=full_label,
            showlegend=False,
            text=[point_label],
            textposition=positions[i % len(positions)],
            textfont=dict(size=10),
            cliponaxis=False,
            marker=dict(
                size=12,
                color=colors[i % len(colors)],
                line=dict(width=1, color="white"),
            ),
            hovertemplate=(
                f"<b>{full_label}</b>"
                f"<br>가중 주식수 증감: %{{x:.2f}}%"
                f"<br>순 공급 breadth: %{{y:.1f}}%p"
                "<extra></extra>"
            ),
        ))

    market_label = {"US": "미국", "GLOBAL": "글로벌", "EX_US": "글로벌 ex-US"}.get(universe, universe)
    hlabel = {"3m": "3개월", "6m": "6개월", "12m": "12개월"}.get(horizon, horizon)

    _base_quadrant_layout(
        fig,
        f"{market_label} 섹터별 주식 공급 · {hlabel}",
        "가중 발행주식수 증감 (%)",
        "증가기업 비중 - 감소기업 비중 (%p)",
        y_ref=0,
    )

    if xs:
        xmin, xmax = min(xs + [0]), max(xs + [0])
        xpad = max((xmax - xmin) * 0.16, 0.08)
        fig.update_xaxes(range=[xmin - xpad, xmax + xpad])
    if ys:
        ymin, ymax = min(ys + [0]), max(ys + [0])
        ypad = max((ymax - ymin) * 0.16, 4)
        fig.update_yaxes(range=[ymin - ypad, ymax + ypad])

    return fig


def resolve_style_plot_row(style_df, style_hist_df, pair_id):
    """Use latest snapshot first, then backfill missing plot metrics from latest history row."""
    latest = style_df[style_df["pair_id"].eq(pair_id)]
    if latest.empty:
        return None, ["latest row"]
    row = latest.iloc[0].copy()
    hist_row = None
    if has_rows(style_hist_df) and "pair_id" in style_hist_df.columns:
        h = style_hist_df[style_hist_df["pair_id"].eq(pair_id)].copy()
        if len(h):
            if "date" in h.columns:
                h["date"] = pd.to_datetime(h["date"], errors="coerce")
                h = h.sort_values("date")
            hist_row = h.iloc[-1]
    needed = []
    for n in [21, 63, 126]:
        for col in [f"rs_return_{n}", f"freq_{n}"]:
            val = pd.to_numeric(row.get(col), errors="coerce")
            if pd.isna(val) and hist_row is not None:
                hval = pd.to_numeric(hist_row.get(col), errors="coerce")
                if pd.notna(hval):
                    row[col] = hval
                    val = hval
            if pd.isna(val):
                needed.append(col)
    return row, needed


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
        fig.update_yaxes(range=[max(0, ymin - ypad), min(100, ymax + ypad)])
    else:
        fig.update_xaxes(range=[-5, 5])
        fig.update_yaxes(range=[35, 65])

    fig.update_layout(
        height=500,
        margin=dict(l=80, r=70, t=105, b=80),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="left",
            x=0,
            font=dict(size=10),
        ),
    )
    fig.update_xaxes(automargin=True, title_standoff=14)
    fig.update_yaxes(automargin=True, title_standoff=14)
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
        xpad = max((xmax - xmin) * 0.13, 1.5)
        xrange = [xmin - xpad, xmax + xpad]
    else:
        xrange = [-5, 5]

    if all_y:
        ymin, ymax = min(all_y + [50]), max(all_y + [50])
        ypad = max((ymax - ymin) * 0.16, 2.5)
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
                    showlegend=False,
                    marker=dict(
                        size=11,
                        color=colors[i % len(colors)],
                        line=dict(width=1, color="white"),
                    ),
                    text=[point_label],
                    textposition=["top center", "bottom center", "middle right", "middle left"][i % 4],
                    textfont=dict(size=8),
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
            automargin=True,
            title_standoff=12,
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
        height=540,
        margin=dict(l=75, r=65, t=115, b=85),
        hovermode="closest",
        template="plotly_white",
        font=dict(family="Arial, Apple SD Gothic Neo, Malgun Gothic, sans-serif", size=11),
        title=dict(
            text="126일 → 63일 → 21일 리더십 비교",
            x=0.01,
            xanchor="left",
            font=dict(size=14),
        ),
    )
    fig.update_annotations(font=dict(size=11))
    fig._missing_points = sorted(set(missing))
    return fig


# ---------- Rule-based sentiment cycle ----------
def _norm100(value):
    """Normalize a 0~1 or 0~100 proxy into 0~100."""
    try:
        v = float(value)
    except Exception:
        return None
    if pd.isna(v):
        return None
    if abs(v) <= 1.5:
        v *= 100
    return max(0.0, min(100.0, v))


def _breadth_value(breadth_df, window):
    if not has_rows(breadth_df):
        return None
    x = breadth_df[breadth_df["window"].eq(window)]
    if not len(x):
        return None
    try:
        return float(x.iloc[-1].get("breadth_pct"))
    except Exception:
        return None


def _style_row(style_df, pair_id):
    if not has_rows(style_df):
        return None
    x = style_df[style_df["pair_id"].eq(pair_id)]
    return x.iloc[0] if len(x) else None


def _supply_universe_summary(stock_supply_df, universe):
    if not has_rows(stock_supply_df):
        return None
    x = stock_supply_df[stock_supply_df["universe"].eq(universe)].copy()
    if not len(x):
        return None

    for c in ["sector_weight_pct", "weighted_change_12m", "net_breadth_12m", "coverage_of_sector_weight"]:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors="coerce")

    valid = x.dropna(subset=["weighted_change_12m"]).copy()
    if not len(valid):
        return None

    weights = valid["sector_weight_pct"].fillna(0) if "sector_weight_pct" in valid.columns else pd.Series(1.0, index=valid.index)
    if float(weights.sum()) <= 0:
        weights = pd.Series(1.0, index=valid.index)

    weighted_change = float((valid["weighted_change_12m"] * weights).sum() / weights.sum())

    if "net_breadth_12m" in valid.columns:
        bmask = valid["net_breadth_12m"].notna()
        if bmask.any():
            bw = weights[bmask]
            net_breadth = float((valid.loc[bmask, "net_breadth_12m"] * bw).sum() / bw.sum())
        else:
            net_breadth = None
    else:
        net_breadth = None

    if "coverage_of_sector_weight" in valid.columns:
        coverage = float(valid["coverage_of_sector_weight"].dropna().median()) if valid["coverage_of_sector_weight"].notna().any() else None
    else:
        coverage = None

    if weighted_change >= 0.02 and (net_breadth is not None and net_breadth >= 0.15):
        status = "공급 증가 확산"
    elif weighted_change >= 0.0075 or (net_breadth is not None and net_breadth >= 0.10):
        status = "공급 증가 초기"
    elif weighted_change <= -0.01 and (net_breadth is None or net_breadth <= -0.05):
        status = "공급 위축"
    else:
        status = "중립"

    return {
        "status": status,
        "weighted_change": weighted_change,
        "net_breadth": net_breadth,
        "coverage": coverage,
    }


def classify_sentiment_cycle(style_df, sector_df, global_sector_df, breadth_df, sentiment_df, regime_df, stock_supply_df):
    """
    Reproducible state-machine inspired by the Fisher/Kasugano framework.

    Important:
    - No manual 'current view' CSV is used.
    - Late euphoria is intentionally NOT confirmed until IPO/SPAC/low-quality issuance
      and expectations-gap data are connected.
    """
    modules = []

    # 1) Market regime
    mechanical = ""
    drawdown = None
    if has_rows(regime_df):
        rr = regime_df.iloc[-1]
        mechanical = str(rr.get("mechanical_state", "")).upper()
        try:
            drawdown = float(rr.get("spy_drawdown_from_ath"))
        except Exception:
            drawdown = None

    if "BEAR" in mechanical:
        regime_status = "Bear"
        regime_score = -1
    elif "CORRECTION" in mechanical:
        regime_status = "조정"
        regime_score = 0
    elif any(k in mechanical for k in ["BULL", "ADVANCE", "NEAR-BULL"]):
        regime_status = "Bull"
        regime_score = 1
    else:
        regime_status = "불명확"
        regime_score = 0

    regime_evidence = regime_status
    if drawdown is not None:
        regime_evidence += f" · 전고점 대비 {drawdown*100:.1f}%"
    modules.append({
        "모듈": "Market Regime",
        "판정": regime_status,
        "근거": regime_evidence,
        "측정": "완료" if has_rows(regime_df) else "미연결",
    })

    # 2) Risk stress — descriptive only.
    # VIX is contemporaneous/lagging and must NOT determine the sentiment stage.
    risk_status = "미측정"
    sentiment_warmth = None
    risk_score = None
    if has_rows(sentiment_df):
        sr = sentiment_df.iloc[-1]
        vix_w = _norm100(sr.get("vix_warmth"))
        hy_w = _norm100(sr.get("hy_oas_warmth"))
        sentiment_warmth = _norm100(sr.get("proxy_score"))
        vals = [x for x in [vix_w, hy_w] if x is not None]
        if vals:
            risk_score = sum(vals) / len(vals)
            if risk_score >= 70:
                risk_status = "스트레스 낮음"
            elif risk_score >= 40:
                risk_status = "중립"
            else:
                risk_status = "스트레스 높음"

    risk_evidence = "VIX·하이일드 proxy · 사이클 단계 판정에는 미사용"
    if risk_score is not None:
        risk_evidence += f" · 안정도 {risk_score:.0f}/100"
    modules.append({
        "모듈": "Risk Stress",
        "판정": risk_status,
        "근거": risk_evidence,
        "측정": "보조",
    })

    # 3) Expectations gap — deliberately not invented.
    modules.append({
        "모듈": "Expectations Gap",
        "판정": "미측정",
        "근거": "실적 surprise·경제 surprise 데이터 필요",
        "측정": "미연결",
    })

    # 4) Equity supply — listed-company share count only, so explicitly partial.
    supply_us = _supply_universe_summary(stock_supply_df, "US")
    supply_ex = _supply_universe_summary(stock_supply_df, "EX_US")
    supply_parts = []
    supply_rank = 0  # -1 contraction, 0 neutral, 1 rising, 2 broad rising
    supply_coverage = []
    for obj, label in [(supply_us, "미국"), (supply_ex, "ex-US")]:
        if not obj:
            continue
        supply_parts.append(
            f"{label} {obj['status']} ({obj['weighted_change']*100:+.1f}%)"
        )
        if obj["coverage"] is not None:
            supply_coverage.append(obj["coverage"])
        if obj["status"] == "공급 증가 확산":
            supply_rank = max(supply_rank, 2)
        elif obj["status"] == "공급 증가 초기":
            supply_rank = max(supply_rank, 1)
        elif obj["status"] == "공급 위축" and supply_rank == 0:
            supply_rank = -1

    if supply_parts:
        if supply_rank >= 2:
            supply_status = "공급 증가 확산"
        elif supply_rank == 1:
            supply_status = "공급 증가 초기"
        elif supply_rank < 0:
            supply_status = "공급 위축"
        else:
            supply_status = "중립"
        supply_evidence = " · ".join(supply_parts)
        supply_measure = "부분 측정"
    else:
        supply_status = "미측정"
        supply_evidence = "기존 상장기업 발행주식수 데이터 필요"
        supply_measure = "미연결"

    modules.append({
        "모듈": "Equity Supply",
        "판정": supply_status,
        "근거": supply_evidence,
        "측정": supply_measure,
    })

    # 5) Speculation — only a hot-pocket proxy. Never call broad speculation confirmed.
    gv = _style_row(style_df, "growth_value")
    ce = _style_row(style_df, "cap_equal")
    ls = _style_row(style_df, "large_small")

    growth_hot = bool(gv is not None and str(gv.get("leader_21")) == "Growth")
    cap_hot = bool(ce is not None and str(ce.get("leader_21")) == "Cap-weight")
    small_hot = bool(ls is not None and str(ls.get("leader_21")) == "Small")

    tech_hot = False
    tech_evidence = []
    if has_rows(sector_df):
        us_tech = sector_df[sector_df["ticker"].eq("XLK")]
        if len(us_tech):
            r = us_tech.iloc[0]
            try:
                rank21 = int(r.get("rank_21"))
                if rank21 <= 2:
                    tech_hot = True
                    tech_evidence.append(f"미국 기술 21일 {rank21}위")
            except Exception:
                pass
    if has_rows(global_sector_df):
        gl_tech = global_sector_df[global_sector_df["ticker"].eq("IXN")]
        if len(gl_tech):
            r = gl_tech.iloc[0]
            try:
                rank21 = int(r.get("rank_21"))
                if rank21 <= 2:
                    tech_hot = True
                    tech_evidence.append(f"글로벌 기술 21일 {rank21}위")
            except Exception:
                pass

    hot_points = int(growth_hot) + int(cap_hot) + int(tech_hot)
    if sentiment_warmth is not None and sentiment_warmth >= 65:
        hot_points += 1

    if hot_points >= 3:
        speculation_status = "일부 포켓 과열 후보"
    elif hot_points >= 2:
        speculation_status = "낙관적 리더십"
    else:
        speculation_status = "과열 신호 제한적"

    spec_bits = []
    if growth_hot:
        spec_bits.append("성장주 단기 우위")
    if cap_hot:
        spec_bits.append("시총가중 우위")
    if small_hot:
        spec_bits.append("소형주 우위")
    spec_bits.extend(tech_evidence)
    if sentiment_warmth is not None:
        spec_bits.append(f"심리 proxy {sentiment_warmth:.0f}/100")
    if not spec_bits:
        spec_bits = ["저품질 IPO·SPAC 데이터 미연결"]

    modules.append({
        "모듈": "Speculation",
        "판정": speculation_status,
        "근거": " · ".join(spec_bits),
        "측정": "부분 측정",
    })

    # 6) Leadership / breadth
    b21 = _breadth_value(breadth_df, 21)
    b63 = _breadth_value(breadth_df, 63)
    equal21 = bool(ce is not None and str(ce.get("leader_21")) == "Equal-weight")

    if b21 is None:
        leadership_status = "미측정"
        lead_evidence = "breadth 데이터 필요"
    else:
        if b21 < 0.45 and not equal21:
            leadership_status = "리더십 집중"
        elif b21 >= 0.60 and (equal21 or (b63 is not None and b21 >= b63)):
            leadership_status = "광범위 확산"
        else:
            leadership_status = "확산 초기/혼조"

        lead_evidence = f"21일 breadth {b21*100:.1f}%"
        if b63 is not None:
            lead_evidence += f" · 63일 {b63*100:.1f}%"
        if ce is not None:
            lead_evidence += f" · 21일 {leader_to_kor(ce.get('leader_21'))}"

    modules.append({
        "모듈": "Leadership / Breadth",
        "판정": leadership_status,
        "근거": lead_evidence,
        "측정": "완료" if b21 is not None else "미연결",
    })

    # ---------- Provisional cycle interpretation ----------
    # The broad sentiment stage is not allowed to be "confirmed" without
    # expectations-gap + primary-market supply data. Current data only narrows the range.
    if regime_score < 0:
        stage = "비관~회의"
    elif regime_score == 0:
        stage = "회의 가능성"
    else:
        # Bull market. Use supply response and speculative pockets only to narrow
        # the optimism-side range; do not infer Wall of Worry from VIX.
        if speculation_status == "일부 포켓 과열 후보":
            if supply_rank >= 1:
                stage = "후기 낙관~초기 유포리아 가능성"
            else:
                stage = "낙관~후기 낙관 가능성"
        elif supply_rank >= 1 or speculation_status == "낙관적 리더십":
            stage = "낙관~후기 낙관 가능성"
        else:
            stage = "낙관 가능성"

    # Confidence from measured coverage — transparent, not fake precision.
    measured_weight = 0.0
    measured_weight += 1.0 if has_rows(regime_df) else 0.0
    measured_weight += 0.25 if risk_score is not None else 0.0  # descriptive only
    measured_weight += 0.75 if supply_parts else 0.0
    measured_weight += 0.5 if has_rows(style_df) else 0.0  # speculation is only partial
    measured_weight += 0.5 if b21 is not None else 0.0  # distribution, not stage
    # Expectations gap + IPO/SPAC/primary supply intentionally get 0 until connected.
    coverage_ratio = measured_weight / 4.0

    if supply_coverage and min(supply_coverage) < 0.25:
        coverage_ratio *= 0.9

    if coverage_ratio >= 0.72:
        confidence = "중상"
    elif coverage_ratio >= 0.52:
        confidence = "중간"
    else:
        confidence = "낮음"

    # Critical late-cycle modules are not yet connected.
    # Until Expectations Gap and IPO/SPAC/low-quality issuance are available,
    # do not display a confidence higher than medium.
    confidence = "중간" if confidence == "중상" else confidence

    missing = []
    if not supply_parts:
        missing.append("주식공급")
    missing.append("IPO/SPAC·저품질 신규공급")
    missing.append("실적·경제 expectations gap")
    missing.append("뉴스·전문가 기대/회의론의 정량화")

    if "초기 유포리아" in stage:
        headline_reason = "Bull + 일부 과열 포켓 + 공급 반응이 나타나지만 핵심 1차시장·기대 데이터가 부족"
    elif "후기 낙관" in stage:
        headline_reason = "Bull 진행과 일부 뜨거운 리더십은 보이지만 광범위 신규공급·기대과열은 확인되지 않음"
    elif "낙관" in stage:
        headline_reason = "Bull은 진행 중이나 현재 데이터만으로 후기 단계나 유포리아를 확정할 근거는 부족"
    elif "회의" in stage:
        headline_reason = "시장 국면과 리더십만으로는 낙관 단계 진입을 확정하기 어려움"
    else:
        headline_reason = "약세 국면에서 비관·회의 구간 가능성이 높음"

    return {
        "stage": stage,
        "confidence": confidence,
        "coverage_ratio": coverage_ratio,
        "reason": headline_reason,
        "modules": modules,
        "missing": missing,
        "late_euphoria_locked": True,
    }


def cycle_rule_table():
    return pd.DataFrame([
        {
            "단계": "비관",
            "핵심 조건": "Bear/대폭 하락 + 걱정의 벽 강함 + 주식공급 위축",
        },
        {
            "단계": "회의",
            "핵심 조건": "가격은 회복/상승하지만 기대가 낮고 신규공급·낙관 확산이 제한",
        },
        {
            "단계": "낙관",
            "핵심 조건": "Bull 진행 + 현실이 낮은 기대를 상회 + 공급 과열 없음",
        },
        {
            "단계": "후기 낙관",
            "핵심 조건": "Bull 고도화 + 공급 증가/뜨거운 리더십 + 기대치 상승, 아직 광범위 과열은 아님",
        },
        {
            "단계": "초기 유포리아 후보",
            "핵심 조건": "일부 과열 포켓 + 신규공급 반응 + 기대치 상승이 동시에 나타남",
        },
        {
            "단계": "후기 유포리아",
            "핵심 조건": "현재 자동 확정 금지 — IPO/SPAC·저품질 신규공급·expectations gap 연결 필요",
        },
    ])


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

cycle = classify_sentiment_cycle(
    style, sector, global_sector, breadth, sentiment, regime, stock_supply
)

try:
    model_name = st.secrets.get("OPENAI_MODEL", "gpt-5.6-terra")
except Exception:
    model_name = "gpt-5.6-terra"

# ---------- Header ----------
st.markdown('<div class="dashboard-title">시장 리더십 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">최근 1~6개월 리더십 변화 · 지역·섹터·시장 참여 폭·주식공급</div>', unsafe_allow_html=True)

if not (has_rows(style) and has_rows(sector)):
    st.warning("아직 데이터가 충분히 생성되지 않았습니다. GitHub Actions 실행 여부를 먼저 확인해 주세요.")

c1, c2, c3, c4 = st.columns([0.95, 1.30, 1.85, 1.05], gap="small")

with c1:
    if has_rows(regime):
        r = regime.iloc[-1]
        age_ctx = bull_cycle_context(style_hist, regime)
        sub = f"전고점 대비 {pct(r.get('spy_drawdown_from_ath'))}"
        if age_ctx["bull"]:
            sub = f"{age_ctx['phase']} · " + sub
        card(
            "시장 국면",
            regime_to_kor(str(r.get("mechanical_state", "—"))),
            sub
        )
    else:
        card("시장 국면", "—", "")

with c2:
    compact_card(
        "시장 심리 사이클",
        [cycle["stage"]],
        f"범위 추정 · 신뢰도 {cycle['confidence']}"
    )

with c3:
    compact_card(
        "핵심 리더십",
        current_leadership_summary(style, sector, region, global_sector),
        "기존 추세(126일) → 중심(63일) → 단기(21일)"
    )

with c4:
    change_headline, change_sub = strongest_change(style, bounce)
    card("가장 큰 스타일 변화", change_headline, change_sub)

st.caption(
    "스타일 변화는 시장 전체 방향이 아니라 성장/가치·대형/소형·시총/동일가중 등 "
    "비교축 중 현재 변화 강도가 가장 큰 한 축을 보여줍니다."
)

# ---------- Main insight ----------
st.markdown("### 현재 시장 인사이트")
leader_board = render_current_leader_board(region, global_sector, sector)

snapshot = build_market_snapshot(
    style, sector, global_sector, region, breadth, sentiment, regime,
    pd.DataFrame(), pd.DataFrame(),
    bounce=bounce, stock_supply=stock_supply
)
snapshot["규칙기반_시장심리사이클"] = {
    "현재단계": cycle["stage"],
    "신뢰도": cycle["confidence"],
    "핵심근거": cycle["reason"],
    "모듈": cycle["modules"],
    "미연결": cycle["missing"],
}
rotation_snapshot = leadership_rotation_summary(
    style, sector, global_sector, region, breadth, stock_supply
)
snapshot["리더십_구조"] = rotation_snapshot
snapshot["강세장_시간축"] = bull_cycle_context(style_hist, regime)
snapshot["구조적_리더십교체"] = structural_leadership_snapshot(
    style, sector, global_sector, region, breadth, stock_supply
)
snapshot["현재리더보드"] = leader_board_snapshot(region, global_sector, sector)
snapshot_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
with st.spinner("지역·섹터·주식공급의 리더십 변화를 종합하는 중..."):
    gpt_main, gpt_main_error = generate_gpt_text("main-v6.22-explicit-leaders:" + snapshot_json, model_name, MAIN_PROMPT, snapshot_json)
sections = parse_main_sections(gpt_main) if gpt_main else None
if not sections:
    sections = fallback_main_sections(
        style, sector, global_sector, region, breadth, stock_supply, bounce,
        regime=regime, style_hist=style_hist
    )

if not sections.get("현재 대응"):
    sections["현재 대응"] = build_current_action(
        style, sector, global_sector, region, breadth, cycle, stock_supply,
        regime=regime, style_hist=style_hist
    )

render_main_sections(sections, f"GPT 리더십 변화 해석 · {model_name}" if gpt_main else None)
if gpt_main_error and not gpt_main:
    st.caption(f"GPT API 미연결: {gpt_main_error}")

st.markdown("### 보조: 시장 심리 사이클 범위")
st.markdown(
    f'<div class="explain-box"><b>{cycle["stage"]}</b> · 보조 추정 · 신뢰도 {cycle["confidence"]}<br>'
    f'{cycle["reason"]}</div>',
    unsafe_allow_html=True,
)

cycle_modules_df = pd.DataFrame(cycle["modules"])
connected_modules_df = cycle_modules_df[cycle_modules_df["측정"] != "미연결"].copy()

st.dataframe(
    connected_modules_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "모듈": st.column_config.TextColumn(width="medium"),
        "판정": st.column_config.TextColumn(width="medium"),
        "근거": st.column_config.TextColumn(width="large"),
        "측정": st.column_config.TextColumn(width="small"),
    },
)

st.caption(
    "사이클은 현재 '범위 추정'입니다. VIX·HY는 위험 스트레스 설명에만 쓰고 단계 판정에는 사용하지 않습니다. "
    "Expectations Gap과 IPO/SPAC·저품질 신규공급이 연결되기 전에는 신뢰도를 최대 '중간'으로 제한합니다."
)

with st.expander("사이클 판정 로직 보기"):
    st.dataframe(cycle_rule_table(), use_container_width=True, hide_index=True)
    st.markdown(
        """
- **전환 초기**: 21일 또는 21·63일 리더가 기존 126일/63일 중심축과 달라지기 시작했지만, 아직 장기축까지 정렬되지 않은 상태입니다.
- **Risk Stress**: VIX·하이일드 스프레드는 현재 위험 스트레스의 동행 지표로만 봅니다. 심리 단계의 선행 판정에는 사용하지 않습니다.
- **Equity Supply**: 현재는 기존 상장기업의 발행주식수 변화만 반영하므로 `부분 측정`입니다.
- **Speculation**: 성장/시총가중/기술주 리더십과 심리 proxy로 `일부 포켓`만 탐지합니다.
- **Expectations Gap**: 실적 surprise·경제 surprise 데이터가 아직 없어 판정에 넣지 않습니다.
- 따라서 이 모델은 **극단을 억지로 점수화하지 않고 조건을 만족할 때만 단계가 이동**합니다.
        """
    )

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

    options = [x for x in ["growth_value", "large_small", "cap_equal", "small_value_large_growth", "us_developed_ex_us", "developed_em", "cyclical_defensive"] if x in style["pair_id"].dropna().unique().tolist()]
    if options:
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

        plot_row, missing_style_metrics = resolve_style_plot_row(style, style_hist, choice)
        if plot_row is not None and len(missing_style_metrics) < 6:
            fig = plot_style_quadrant(plot_row, choice)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.caption("현재 시점의 126일·63일·21일 세 점입니다. X축은 상대강도, Y축은 승리 빈도이며 50%가 빈도 기준선입니다.")
            if missing_style_metrics:
                st.warning("일부 기간의 빈도/상대강도 데이터가 비어 있습니다: " + ", ".join(missing_style_metrics) + ". 아래 calc_leadership.py 업데이트 후 Actions를 한 번 실행하면 보완됩니다.")
        else:
            st.warning("4분면에 필요한 빈도 데이터가 없습니다. calc_leadership.py를 최신 버전으로 교체한 뒤 GitHub Actions를 실행해 주세요.")

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
st.markdown('<div class="section-note">지역과 글로벌 섹터를 각각 한 줄 전체 폭으로 봅니다. 126일 → 63일 → 21일의 분포 이동을 비교합니다.</div>', unsafe_allow_html=True)

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
    region_fig = plot_cross_quadrant_all_periods(region, REGION_MAP, REGION_SHORT, "VT", use_ticker_labels=True)
    st.plotly_chart(region_fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("126일·63일·21일을 같은 축으로 비교합니다. 점에는 지역 ETF 티커만 표시하고, 상세 수치는 hover에서 확인합니다.")
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
    st.caption("126일·63일·21일을 같은 축으로 비교합니다. ETF 티커만 표시해 겹침을 줄였고, 섹터명·수치는 hover에서 확인합니다.")
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
    st.caption("126일·63일·21일을 같은 축으로 비교합니다. ETF 티커만 표시해 겹침을 줄였고, 섹터명·수치는 hover에서 확인합니다.")
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
    supply_path = PROCESSED / "stock_supply_sector_latest.csv"
    if not supply_path.exists():
        st.error("주식 공급 파일 자체가 없습니다. scripts/fetch_stock_supply.py와 최신 run_pipeline.py가 GitHub에 반영되지 않은 상태일 가능성이 큽니다.")
    else:
        st.warning("stock_supply_sector_latest.csv는 있지만 내용이 비어 있습니다. 최신 fetch_stock_supply.py로 교체한 뒤 GitHub Actions를 다시 실행해 주세요.")
    st.code("scripts/fetch_stock_supply.py\nrun_pipeline.py\nrequirements.txt", language="text")
    st.caption("Actions 로그에서 'Fetching US and global equity-supply proxy...'와 마지막 'Stock-supply proxy updated:' 문구가 보여야 정상입니다.")

st.divider()

if has_rows(bounce):
    with st.expander("7. 반등 효과 점검"):
        cols = [c for c in ["ticker", "group", "subgroup", "max_drawdown_252", "max_drawdown_126", "rebound_from_126d_low", "current_drawdown_from_126d_high"] if c in bounce.columns]
        show = bounce[cols].copy()
        for c in ["max_drawdown_252", "max_drawdown_126", "rebound_from_126d_low", "current_drawdown_from_126d_high"]:
            if c in show.columns:
                show[c] = pd.to_numeric(show[c], errors="coerce") * 100
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.caption("최근 강세가 추세 전환인지, 큰 낙폭 뒤 반등인지 구분할 때 참고합니다.")

st.caption("매주 미국 금요일 장 마감 후 자동 업데이트 · 시장 레짐 → 구 리더 이탈 → 신규 리더 형성 → 공급 반응 순서")
