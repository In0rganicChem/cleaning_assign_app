# cleaning_assign.py
# 설치:
# python -m pip install streamlit pandas openpyxl

import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="청소구역 배정 프로그램", layout="wide")

st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.15rem !important; }

        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 0.7rem !important;
            padding-right: 0.7rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 생활반 이름
class_names = [
    "2생활반", "3생활반", "5생활반", "6생활반", "7생활반", "8생활반",
    "10생활반", "11생활반", "12생활반", "13생활반", "14생활반"
]

# 청소구역 그룹
AREA_GROUPS = {
    "A": ["1층 화장실", "2층 화장실", "3층 화장실", "1층 목욕탕"],
    "B": ["2층 샤워장", "3층 샤워장"],
    "C": ["1층 세면장", "2층 세면장", "3층 세면장", "2층 휴게실", "3층 휴게실"],
    "D": [
        "1층 복도", "2층 복도", "3층 복도",
        "1층 세탁실", "2층 세탁실", "3층 세탁실",
        "공용 세탁방", "군척장", "체단실", "당구장",
        "사지방", "노래방", "동편 계단", "중앙 계단"
    ],
}


def make_pools():
    """그룹별 청소구역 풀을 새로 만든다."""
    return {k: v[:] for k, v in AREA_GROUPS.items()}


def shuffled(items, rnd):
    """리스트를 복사해서 무작위 순서로 섞는다."""
    items = items[:]
    rnd.shuffle(items)
    return items


def draw_from_allowed_groups(pools, allowed_groups, rnd):
    """
    허용된 그룹들 중 남아 있는 구역 하나를 무작위로 뽑는다.
    뽑힌 구역은 해당 풀에서 제거한다.
    """
    candidates = []
    for group in allowed_groups:
        for area in pools[group]:
            candidates.append((group, area))

    if not candidates:
        return None

    group, area = candidates[rnd.randrange(len(candidates))]
    pools[group].remove(area)
    return area


def draw_one_from_group(pools, group_name, rnd):
    """특정 그룹에서 구역 하나를 무작위로 뽑는다."""
    return draw_from_allowed_groups(pools, [group_name], rnd)


def most_populous_targets(capacities, count, rnd):
    """
    인원이 많은 생활반부터 고른다.
    인원이 같으면 랜덤으로 섞는다.
    """
    eligible = [c for c in class_names if capacities[c] > 0]
    grouped = {}
    for c in eligible:
        grouped.setdefault(capacities[c], []).append(c)

    ordered = []
    for cap in sorted(grouped.keys(), reverse=True):
        chunk = shuffled(grouped[cap], rnd)
        ordered.extend(chunk)

    return ordered[:min(count, len(ordered))]


def distribute_one_week(capacities, prev_week_a_set, rnd):
    """
    한 주 배정.

    capacities: {생활반명: 청소가능인원}
    prev_week_a_set: 지난 주에 그룹 A를 배정받은 생활반
    rnd: random.Random 객체
    """
    assignments = {c: [] for c in class_names}
    pools = make_pools()

    nonzero = [c for c in class_names if capacities[c] > 0]

    # 0명만 있는 경우
    if not nonzero:
        leftover = pools["A"] + pools["B"] + pools["C"] + pools["D"]
        return assignments, set(), leftover, False, True

    # 인원 구간
    b_groups = [c for c in class_names if 1 <= capacities[c] <= 3]
    c_groups = [c for c in class_names if 4 <= capacities[c] <= 6]
    d_groups = [c for c in class_names if 7 <= capacities[c] <= 11]

    # 1-3명 생활반이 7개 이상이면, A 2주 연속 방지 규칙을 무시한다
    ignore_a_repeat = len(b_groups) >= 7
    warning_flag = ignore_a_repeat

    # -------------------------
    # 2. 1~3명 생활반에 25개 중 1개씩 랜덤 배정
    # -------------------------
    for c in shuffled(b_groups, rnd):
        if ignore_a_repeat or c not in prev_week_a_set:
            allowed = ["A", "B", "C", "D"]
        else:
            # 지난 주 A를 받은 생활반은 A를 못 받게 한다
            allowed = ["B", "C", "D"]

        area = draw_from_allowed_groups(pools, allowed, rnd)
        if area is not None:
            assignments[c].append(area)

    # -------------------------
    # 3. 그룹 A를 아직 배정받지 못한 4~11명 생활반에 배정
    #    (A 반복 금지는 여기서도 동일하게 적용)
    # -------------------------
    step3_targets = [c for c in c_groups + d_groups if len(assignments[c]) == 0]

    if not ignore_a_repeat:
        step3_targets = [c for c in step3_targets if c not in prev_week_a_set]

    for c in shuffled(step3_targets, rnd):
        area = draw_one_from_group(pools, "A", rnd)
        if area is not None:
            assignments[c].append(area)

    # A가 남았다면 여기서 leftover로 남는다
    # -------------------------
    # 4. 그룹 B를 아직 배정받지 못한 4~11명 생활반에 배정
    # -------------------------
    step4_targets = [c for c in c_groups + d_groups if len(assignments[c]) == 0]
    for c in shuffled(step4_targets, rnd):
        area = draw_one_from_group(pools, "B", rnd)
        if area is not None:
            assignments[c].append(area)

    # -------------------------
    # 5. 그룹 C를 아직 배정받지 못한 4~11명 생활반에 배정
    # -------------------------
    step5_targets = [c for c in c_groups + d_groups if len(assignments[c]) == 0]
    for c in shuffled(step5_targets, rnd):
        area = draw_one_from_group(pools, "C", rnd)
        if area is not None:
            assignments[c].append(area)

    # -------------------------
    # 6. 남은 그룹 C를 인원이 많은 생활반부터 배정
    # -------------------------
    remaining_c = len(pools["C"])
    if remaining_c > 0:
        targets = most_populous_targets(capacities, remaining_c, rnd)
        for c in targets:
            area = draw_one_from_group(pools, "C", rnd)
            if area is not None:
                assignments[c].append(area)

    # -------------------------
    # 7. 인원이 4~11명인 생활반 중, 아직 1개만 배정받은 곳에 D 배정
    # -------------------------
    step7_targets = [c for c in c_groups + d_groups if len(assignments[c]) == 1]
    for c in shuffled(step7_targets, rnd):
        area = draw_one_from_group(pools, "D", rnd)
        if area is not None:
            assignments[c].append(area)

    # -------------------------
    # 8. 인원이 7~11명인 생활반 중, 아직 2개만 배정받은 곳에 D 배정
    # -------------------------
    step8_targets = [c for c in d_groups if len(assignments[c]) == 2]
    for c in shuffled(step8_targets, rnd):
        area = draw_one_from_group(pools, "D", rnd)
        if area is not None:
            assignments[c].append(area)

    # 남은 구역
    leftover = pools["A"] + pools["B"] + pools["C"] + pools["D"]

    # 이번 주 그룹 A 담당 생활반
    week_a = {
        c for c in class_names
        if any(a in AREA_GROUPS["A"] for a in assignments[c])
    }

    return assignments, week_a, leftover, warning_flag, False


def distribute_5_weeks(capacities, first_week_a_set=None, seed=None):
    """5주 배정"""
    rnd_master = random.Random(seed)
    weeks = []
    leftovers = []
    warning_flag = False

    prev_a_set = set(first_week_a_set or set())
    all_zero_case = all(v == 0 for v in capacities.values())

    for _ in range(5):
        rnd = random.Random(rnd_master.randint(0, 2**31 - 1))

        assgn, week_a, leftover, week_warning, _ = distribute_one_week(
            capacities,
            prev_a_set,
            rnd
        )

        weeks.append(assgn)
        leftovers.append(leftover)
        prev_a_set = week_a

        if week_warning and not all_zero_case:
            warning_flag = True

    # 결과 표
    rows = []
    for c in class_names:
        row = {"생활반": c, "청소가능인원": capacities[c]}
        for i, week in enumerate(weeks, 1):
            row[f"{i}주차"] = ", ".join(week[c]) if week[c] else ""
        rows.append(row)

    leftover_row = {"생활반": "인원 부족으로 배정되지 못한 청소구역", "청소가능인원": ""}
    for i, lst in enumerate(leftovers, 1):
        leftover_row[f"{i}주차"] = ", ".join(lst) if lst else ""
    rows.append(leftover_row)

    return pd.DataFrame(rows), warning_flag, all_zero_case


# -------------------------
# 화면
# -------------------------
st.markdown("---")
st.title("청소구역 배정 프로그램")

st.header("생활반 별 청소가능인원을 입력하십시오 (0~11)")
with st.expander("청소구역 배정 규칙 보기"):
    try:
        st.markdown(
            """
생활반 청소 가능 인원에 따라 배정되는 청소구역 수가 달라집니다.

1~3명: 25개 중 1개를 랜덤 배정  
4~6명: 그룹 A → 그룹 B → 그룹 C → 그룹 D 순으로 배정  
7~11명: 그룹 A → 그룹 B → 그룹 C → 그룹 D 순으로 배정  
지난 주 그룹 A를 받은 생활반은, 가능한 경우 이번 주 그룹 A를 다시 받지 않습니다.
"""
        )
    except Exception as e:
        st.error(str(e))

cap_inputs = {}
for i in range(0, len(class_names), 3):
    row = class_names[i:i+3]
    cols = st.columns(len(row))
    for col, cname in zip(cols, row):
        cap_inputs[cname] = col.number_input(
            cname,
            min_value=0,
            max_value=11,
            value=11,
            step=1,
            key=f"cap_{cname}"
        )

st.markdown("---")
first_week_a = st.multiselect(
    "지난 주에 화장실/목욕탕을 배정받은 생활반을 선택하세요.",
    class_names,
    default=[]
)

seed_input = st.text_input(
    "난수 시드를 정수로 입력하세요. 같은 난수 시드는 같은 결과를 보장합니다. 입력하지 않으면 랜덤으로 처리됩니다.",
    value=""
)
seed_val = int(seed_input) if seed_input.isdigit() else None

if st.button("▶ 결과 생성"):
    capacities = {c: int(cap_inputs[c]) for c in class_names}
    df, warning_flag, all_zero_case = distribute_5_weeks(
        capacities,
        first_week_a_set=set(first_week_a),
        seed=seed_val
    )

    st.success("배정 완료. 결과를 확인하세요.")

    if all_zero_case:
        st.markdown("## 🐱")
        st.markdown("청소 인원이 부족하여 짬타이거가 청소합니다.")
        st.image("https://cataas.com/cat", use_container_width=True)
    if warning_flag:
        st.warning("청소가능인원이 매우 부족하여 2주 연속 화장실/목욕탕을 청소하는 생활반이 나올 수 있습니다.")

    st.header("배정 결과")

    html = df.to_html(escape=False, index=False)
    for area in AREA_GROUPS["A"]:
        html = html.replace(area, f"<b>{area}</b>")
    html = html.replace("<th>", '<th style="text-align:center;">')

    st.markdown(
        """
        <style>
        .result-wrap {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
        .result-wrap table {
            min-width: 100%;
            border-collapse: collapse;
        }
        .result-wrap th,
        .result-wrap td {
            white-space: nowrap;
            text-align: center;
            padding: 6px 8px;
            font-size: 12px;
        }
        @media (max-width: 768px) {
            .result-wrap th,
            .result-wrap td {
                font-size: 11px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(f'<div class="result-wrap">{html}</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("Python 코드로 만든 Streamlit 앱입니다.")

with st.expander("📄 현재 실행 중인 코드 보기"):
    try:
        with open(__file__, "r", encoding="utf-8") as f:
            st.code(f.read(), language="python", height=500)
    except Exception as e:
        st.error(str(e))
