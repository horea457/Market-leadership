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
.gpt-insight {
    background: #f8fafc;
    border: 1px solid rgba(37,99,235,.20);
    border-left: 5px solid #2563eb;
    padding: 16px 18px;
    border-radius: 12px;
    margin-top: 12px;
    margin-bottom: 18px;
    line-height: 1.65;
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
        return f"63일: {leader_to_kor(r.get('leader_63','—'))} · 21일: {leader_to_kor(r.get('leader_21','—'))}"
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
        "Budding euphoria": "도취 초기 조짐",
        "Late Optimism": "후기 낙관",
        "Optimism → Early Euphoria": "낙관 → 초기 도취",
        "Euphoria signs, not late euphoria": "도취 조짐, 그러나 후기 도취는 아님",
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
        "Supports early-euphoria monitoring rather than an imminent bear-market call.": "당장 약세장을 경고하기보다, 초기 도취 진입 여부를 점검해야 한다는 뜻입니다.",
        "Use as a qualitative anchor, not a mechanical score.": "기계적 점수보다 정성적 참고 신호로 보는 것이 적절합니다.",
        "Overall regime: late optimism / early euphoria with uneven sentiment.": "전체적으로는 후기 낙관~초기 도취 구간이지만, 시장 내부 심리는 아직 고르지 않다는 뜻입니다.",
        "Do not label the whole market 'late euphoria'.": "시장 전체를 후기 도취로 단정하긴 이르다는 의미입니다.",
        "More visible capitulation by established pessimists / disappearance of the wall of worry.": "기존 비관론자들의 뚜렷한 항복, 그리고 '걱정의 벽' 약화가 주요 경계 신호입니다.",
        "2026-07-31 post explicitly calls the phase late optimism; 2026-08-23 post says rate/valuation fear and uncertainty remain important and historically constructive.": "7월 31일 글에서는 현재 국면을 '후기 낙관'으로 명시했고, 8월 23일 글에서는 금리·밸류에이션 우려와 불확실성이 여전히 남아 있으며 이것이 역사적으로는 오히려 건설적일 수 있다고 봤습니다.",
    }
    if x in exact:
        return exact[x]
    # partial replacements
    repl = [
        ("Supports early-euphoria monitoring rather than an imminent bear-market call.", "당장 약세장을 경고하기보다, 초기 도취 진입 여부를 점검해야 한다는 뜻입니다."),
        ("More visible capitulation by established pessimists / disappearance of the wall of worry.", "기존 비관론자들의 뚜렷한 항복, 그리고 '걱정의 벽' 약화가 주요 경계 신호입니다."),
        ("late optimism", "후기 낙관"),
        ("Late Optimism", "후기 낙관"),
        ("budding euphoria", "도취 초기 조짐"),
        ("Budding euphoria", "도취 초기 조짐"),
        ("early euphoria", "초기 도취"),
        ("Early Euphoria", "초기 도취"),
        ("valuation", "밸류에이션"),
        ("fear", "우려"),
        ("uncertainty", "불확실성"),
    ]
    for a,b in repl:
        x = x.replace(a,b)
    return x

def style_overall_comment(row):
    state = str(row.get("change_state", ""))
    leader21 = str(row.get("leader_21", "—"))
    leader63 = str(row.get("leader_63", "—"))
    leader126 = str(row.get("leader_126", "—"))

    if leader21 == leader63 == leader126:
        return f"단기·중기·반기 흐름이 모두 {leader_to_kor(leader63)} 쪽으로 정렬돼 있습니다."
    if leader21 != leader63 and leader63 == leader126:
        return f"단기 흐름은 {leader_to_kor(leader21)} 쪽으로 흔들리지만, 아직 중심축은 {leader_to_kor(leader63)} 쪽에 있습니다."
    if leader21 == leader63 and leader63 != leader126:
        return f"최근 1~3개월 흐름이 {leader_to_kor(leader21)} 쪽으로 맞춰지며, 이전 추세와 다른 방향으로 전환이 진행 중입니다."
    if state == "ROTATING":
        return f"최근 흐름이 {leader_to_kor(leader21)} 쪽으로 빠르게 이동하고 있어 회전 가능성을 주의해서 볼 구간입니다."
    if state == "CONFIRMED":
        return f"최근 흐름이 이전과 다른 축으로 넘어가는 신호가 비교적 분명합니다."
    return f"단기·중기·장기 신호가 엇갈려 있어 아직 방향을 단정하기 이릅니다."

def style_selected_comment(row, pair_id):
    info = PAIR_INFO[pair_id]
    t21 = f"21일: {leader_to_kor(row.get('leader_21','—'))} 우위"
    t63 = f"63일: {leader_to_kor(row.get('leader_63','—'))} 우위"
    t126 = f"126일: {leader_to_kor(row.get('leader_126','—'))} 우위"
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


def _safe_records(df, cols=None, n=None):
    if not has_rows(df):
        return []
    x = df.copy()
    if cols:
        cols = [c for c in cols if c in x.columns]
        x = x[cols]
    if n:
        x = x.head(n)
    x = x.where(pd.notna(x), None)
    return x.to_dict(orient="records")


def build_market_snapshot(style, sector, global_sector, region, breadth, sentiment, regime, fisher, author_view):
    snapshot = {}

    if has_rows(regime):
        r = regime.iloc[-1]
        snapshot["시장국면"] = {
            "기계적_국면": regime_to_kor(str(r.get("mechanical_state", "—"))),
            "전고점대비": r.get("spy_drawdown_from_ath"),
            "21일수익률": r.get("spy_return_21"),
            "63일수익률": r.get("spy_return_63"),
            "126일수익률": r.get("spy_return_126"),
        }

    if has_rows(style):
        wanted = [
            "growth_value", "large_small", "cap_equal", "small_value_large_growth",
            "cyclical_defensive", "us_developed_ex_us", "developed_em"
        ]
        rows = []
        for pid in wanted:
            x = style[style["pair_id"].eq(pid)]
            if len(x) == 0:
                continue
            r = x.iloc[0]
            rows.append({
                "비교축": PAIR_INFO.get(pid, {}).get("label", pid),
                "21일": leader_to_kor(r.get("leader_21")),
                "63일": leader_to_kor(r.get("leader_63")),
                "126일": leader_to_kor(r.get("leader_126")),
                "21일_빈도": r.get("freq_21"),
                "63일_빈도": r.get("freq_63"),
                "126일_빈도": r.get("freq_126"),
                "21일_상대강도": r.get("rs_return_21"),
                "63일_상대강도": r.get("rs_return_63"),
                "126일_상대강도": r.get("rs_return_126"),
                "상태": state_to_kor(r.get("change_state")),
            })
        snapshot["스타일리더십"] = rows

    if has_rows(region):
        r = region.sort_values(["rank_21", "rank_63"]).head(6).copy()
        snapshot["지역리더십"] = [
            {
                "대상": REGION_MAP.get(row.get("ticker"), row.get("ticker")),
                "21일순위": row.get("rank_21"),
                "63일순위": row.get("rank_63"),
                "21일초과수익": row.get("excess_21"),
                "63일초과수익": row.get("excess_63"),
                "상태": state_to_kor(row.get("trend_label")),
            }
            for _, row in r.iterrows()
        ]

    if has_rows(global_sector):
        g = global_sector.sort_values(["rank_21", "rank_63"]).head(6).copy()
        snapshot["글로벌섹터"] = [
            {
                "대상": GLOBAL_SECTOR.get(row.get("ticker"), row.get("ticker")),
                "21일순위": row.get("rank_21"),
                "63일순위": row.get("rank_63"),
                "21일초과수익": row.get("excess_21"),
                "63일초과수익": row.get("excess_63"),
                "상태": state_to_kor(row.get("trend_label")),
            }
            for _, row in g.iterrows()
        ]

    if has_rows(sector):
        s = sector.sort_values(["rank_21", "rank_63"]).copy()
        top = s.head(5)
        changing = s[s["trend_label"].isin(["EMERGING", "WEAKENING"])]
        use = pd.concat([top, changing]).drop_duplicates(subset=["ticker"]).head(9)
        snapshot["미국섹터"] = [
            {
                "대상": US_SECTOR.get(row.get("ticker"), row.get("ticker")),
                "21일순위": row.get("rank_21"),
                "63일순위": row.get("rank_63"),
                "126일순위": row.get("rank_126"),
                "21일초과수익": row.get("excess_21"),
                "63일초과수익": row.get("excess_63"),
                "상태": state_to_kor(row.get("trend_label")),
            }
            for _, row in use.iterrows()
        ]

    if has_rows(breadth):
        snapshot["시장참여폭"] = [
            {
                "기간": row.get("window"),
                "시장상회종목비율": row.get("breadth_pct"),
                "유효종목수": row.get("n_valid"),
            }
            for _, row in breadth.sort_values("window").iterrows()
        ]

    if has_rows(sentiment):
        r = sentiment.iloc[-1]
        snapshot["시장심리프록시"] = {
            "점수": r.get("proxy_score"),
            "단계": fisher_stage_to_kor(str(r.get("proxy_stage", "—"))),
            "VIX": r.get("vix_warmth"),
            "하이일드스프레드": r.get("hy_oas_warmth"),
            "SPY추세": r.get("spy_trend_warmth"),
            "SPY모멘텀": r.get("spy_momentum_warmth"),
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


@st.cache_data(show_spinner=False, persist="disk")
def generate_gpt_market_insight(snapshot_json, model_name):
    if OpenAI is None:
        return None, "openai 패키지가 설치되지 않았습니다."

    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        return None, "Streamlit Secrets에 OPENAI_API_KEY가 없습니다."

    client = OpenAI(api_key=api_key)

    instructions = """
너는 글로벌 주식시장 리더십을 해석하는 투자 리서치 보조자다.
사용자가 제공한 JSON 데이터만 근거로 현재 시장의 리더십과 심리 국면을 한국어로 해석한다.

규칙:
1. 4~6문장, 한 문단으로 작성한다.
2. 첫 문장에서 현재 시장 국면과 가장 중요한 리더십 특징을 말한다.
3. 21일·63일·126일이 엇갈리면 '단기 변화'와 '기존 중심축'을 구분한다.
4. 미국만 보지 말고 지역/글로벌 섹터 확인 신호를 함께 반영한다.
5. 시장 참여 폭(breadth)이 리더십 확산인지 집중인지 판단하는 보조 근거라는 점을 반영한다.
6. Fisher 공개 시각과 현재 방법론 해석은 정성적 앵커로만 사용하고, 서로 다르면 그 차이를 짧게 설명한다.
7. 데이터에 없는 원인, 뉴스, 거시경제 사실을 지어내지 않는다.
8. '매수', '매도', '추천' 같은 투자행동 지시는 하지 않는다.
9. 특정 필명이나 'Kasugano/카스가노소라'라는 단어는 절대 쓰지 않는다.
10. 같은 표현을 반복하지 말고, '현재 ~한 상황이라 ~로 해석된다' 식으로 인사이트 중심으로 쓴다.
11. 단순 수치 나열보다 '무엇이 바뀌고 있고 무엇은 아직 유지되는지'를 우선한다.
"""

    response = client.responses.create(
        model=model_name,
        instructions=instructions,
        input=snapshot_json,
        max_output_tokens=700,
    )
    return response.output_text.strip(), None

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
st.title("시장 리더십 대시보드")
st.caption("최근 1~6개월 리더십 변화 · Fisher 심리 사이클 기반")

if not (has_rows(style) and has_rows(sector)):
    st.warning("아직 데이터가 충분히 생성되지 않았습니다. GitHub Actions 실행 여부를 먼저 확인해 주세요.")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if has_rows(regime):
        r = regime.iloc[-1]
        card("시장 국면", regime_to_kor(str(r.get("mechanical_state","—")).replace(" / ", " / ")), f"전고점 대비 {pct(r.get('spy_drawdown_from_ath'))}")
    else:
        card("시장 국면", "—", "")

with c2:
    if has_rows(fisher):
        r = fisher.iloc[-1]
        card("Fisher 공개 시각", fisher_stage_to_kor(str(r.get("stage_label","—"))), f"기준일: {r.get('source_date','—')}")
    else:
        card("Fisher 공개 시각", "—", "")

with c3:
    if has_rows(author_view):
        r = author_view.iloc[-1]
        card("현재 해석", fisher_stage_to_kor(str(r.get("stage_label","—"))), f"확신도: {confidence_to_kor(r.get('confidence','—'))}")
    else:
        card("현재 해석", "—", "")

with c4:
    card("핵심 스타일", current_style_leader(style), "성장주 vs 가치주 기준")

with c5:
    state, axis = strongest_change(style)
    card("변화 포착", state_to_kor(state), axis)

# ---------- GPT summary ----------
st.markdown("### 현재 시장 인사이트")
snapshot = build_market_snapshot(
    style, sector, global_sector, region, breadth, sentiment, regime, fisher, author_view
)
snapshot_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)

try:
    model_name = st.secrets.get("OPENAI_MODEL", "gpt-5.6-terra")
except Exception:
    model_name = "gpt-5.6-terra"

with st.spinner("최신 리더십 데이터를 종합하는 중..."):
    try:
        gpt_insight, gpt_error = generate_gpt_market_insight(snapshot_json, model_name)
    except Exception as exc:
        gpt_insight, gpt_error = None, str(exc)

if gpt_insight:
    st.markdown(f'<div class="gpt-insight">{gpt_insight}</div>', unsafe_allow_html=True)
    st.caption(f"GPT API 종합 해석 · 모델: {model_name} · 동일 데이터는 캐시, 데이터 갱신 시 재생성")
else:
    # GPT 미설정 시 앱이 깨지지 않도록 짧은 규칙 기반 대체 문구 제공
    fallback = "API 키를 연결하면 이 영역에 최신 리더십·글로벌 흐름·시장 참여 폭·심리 지표를 종합한 인사이트가 자동 생성됩니다."
    st.markdown(f'<div class="gpt-insight">{fallback}</div>', unsafe_allow_html=True)
    if gpt_error:
        st.caption(f"GPT API 미연결: {gpt_error}")

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
            st.metric("시장 암시 점수", f"{float(score):.0f} / 100", fisher_stage_to_kor(str(stage)))
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
        st.markdown(f"**{r.get('source_date','')} · {fisher_stage_to_kor(r.get('stage_label',''))}**")
        st.write(translate_free_text(r.get("dashboard_interpretation", r.get("public_view",""))))

with q2:
    st.markdown("#### 현재 해석")
    if has_rows(author_view):
        r = author_view.iloc[-1]
        st.markdown(f"**{fisher_stage_to_kor(r.get('stage_label','—'))}**")
        st.write(translate_free_text(r.get("evidence","")))
        st.caption(f"경계 신호: {translate_free_text(r.get('warning_trigger','—'))}")

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
