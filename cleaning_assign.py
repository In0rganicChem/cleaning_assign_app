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
            padding: 1rem !important;
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

# 청소구역
super_hard_areas = ["1층 화장실", "2층 화장실", "3층 화장실", "1층 목욕탕"]
hard_areas = ["2층 샤워장", "3층 샤워장", "1층 세면장", "2층 세면장", "3층 세면장"]
general_areas_base = [
    "1층 세탁실", "1층 복도", "2층 복도", "3층 복도", "동편 계단", "중앙 계단",
    "2층 휴게실", "3층 휴게실", "체단실", "군척장", "공용세탁방", "당구장",
    "사지방", "노래방", "2층 세탁실", "3층 세탁실"
]


def pop_random(pool, rnd):
    """리스트에서 무작위로 하나 꺼내기"""
    if not pool:
        return None
    return pool.pop(rnd.randrange(len(pool)))


def build_priority_order(names, capacities, rnd):
    """인원 많은 순 + 같은 인원은 랜덤"""
    grouped = {}
    for c in names:
        grouped.setdefault(capacities[c], []).append(c)

    ordered = []
    for cap in sorted(grouped.keys(), reverse=True):
        chunk = grouped[cap][:]
        rnd.shuffle(chunk)
        ordered.extend(chunk)

    return ordered


def distribute_one_week(capacities, exempt_superhard_set, rnd):
    """한 주 배정"""

    super_pool = super_hard_areas.copy()
    hard_pool = hard_areas.copy()
    general_pool = general_areas_base.copy()

    assignments = {c: [] for c in class_names}

    nonzero = [c for c in class_names if capacities[c] > 0]
    severe_shortage = len(nonzero) < 9

    # 모든 인원이 0명
    if not nonzero:
        leftover = super_pool + hard_pool + general_pool
        return assignments, set(), leftover, True, True

    working_order = class_names.copy()
    rnd.shuffle(working_order)

    # -------------------------
    # 핵심 구역 배정
    # -------------------------

    if severe_shortage:
        # 핵심 부족 → 면제 무시
        core_pool = super_pool + hard_pool
        order = build_priority_order(nonzero, capacities, rnd)

        for c in order:
            if core_pool:
                assignments[c].append(pop_random(core_pool, rnd))
            else:
                break

        leftover_core = core_pool[:]

    else:
        # 정상 케이스

        four_plus = [c for c in class_names if capacities[c] >= 4]

        # 초고난도 (면제 제외 우선)
        first = build_priority_order(
            [c for c in four_plus if c not in exempt_superhard_set],
            capacities,
            rnd
        )
        for c in first:
            if super_pool:
                assignments[c].append(pop_random(super_pool, rnd))

        # 남은 초고난도 (면제 포함)
        second = build_priority_order(
            [c for c in four_plus if len(assignments[c]) == 0],
            capacities,
            rnd
        )
        for c in second:
            if super_pool:
                assignments[c].append(pop_random(super_pool, rnd))

        # 고난도
        remaining = build_priority_order(
            [c for c in four_plus if len(assignments[c]) == 0],
            capacities,
            rnd
        )
        for c in remaining:
            if hard_pool:
                assignments[c].append(pop_random(hard_pool, rnd))

        # 🔴 여기 수정된 핵심 부분
        remaining_super = super_pool[:]
        remaining_hard = hard_pool[:]

        one_to_three = build_priority_order(
            [c for c in class_names if 1 <= capacities[c] <= 3 and len(assignments[c]) == 0],
            capacities,
            rnd
        )

        non_exempt = [c for c in one_to_three if c not in exempt_superhard_set]
        exempt = [c for c in one_to_three if c in exempt_superhard_set]

        # 초고난도 (면제 제외 우선)
        for c in non_exempt:
            if remaining_super:
                assignments[c].append(pop_random(remaining_super, rnd))

        # 초고난도 남으면 면제에게도
        for c in exempt:
            if remaining_super:
                assignments[c].append(pop_random(remaining_super, rnd))

        # 고난도
        for c in one_to_three:
            if len(assignments[c]) == 0 and remaining_hard:
                assignments[c].append(pop_random(remaining_hard, rnd))

        leftover_core = remaining_super + remaining_hard

    # -------------------------
    # 일반 구역 배정
    # -------------------------

    first_general = build_priority_order(
        [c for c in class_names if capacities[c] > 0 and len(assignments[c]) == 0],
        capacities,
        rnd
    )
    for c in first_general:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    second_general = build_priority_order(
        [c for c in class_names if capacities[c] >= 4 and len(assignments[c]) == 1],
        capacities,
        rnd
    )
    for c in second_general:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    third_general = build_priority_order(
        [c for c in class_names if capacities[c] >= 7 and len(assignments[c]) == 2],
        capacities,
        rnd
    )
    for c in third_general:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    leftover = leftover_core + general_pool

    week_superhard = {
        c for c in class_names
        if any(a in super_hard_areas for a in assignments[c])
    }

    return assignments, week_superhard, leftover, severe_shortage, False


def distribute_5_weeks(capacities, initial_exempt_set=None, seed=None):
    rnd_master = random.Random(seed)
    weeks = []
    leftovers = []
    warnings = []

    prev = set(initial_exempt_set or set())

    for i in range(5):
        rnd = random.Random(rnd_master.randint(0, 2**31 - 1))

        assgn, super_set, leftover, severe, all_zero = distribute_one_week(
            capacities, prev, rnd
        )

        weeks.append(assgn)
        leftovers.append(leftover)
        prev = super_set

        if severe and not all_zero:
            warnings.append(f"{i+1}주차: 인원 부족으로 초고난도 연속 배정 가능")

    rows = []
    for c in class_names:
        row = {"생활반": c, "청소가능인원": capacities[c]}
        for i, w in enumerate(weeks, 1):
            row[f"{i}주차"] = ", ".join(w[c])
        rows.append(row)

    leftover_row = {"생활반": "인원 부족으로 배정되지 못한 청소구역", "청소가능인원": ""}
    for i, lst in enumerate(leftovers, 1):
        leftover_row[f"{i}주차"] = ", ".join(lst)
    rows.append(leftover_row)

    return pd.DataFrame(rows), warnings


# -------------------------
# UI
st.title("생활반 별 청소 구역")

cap_inputs = {}
for i in range(0, len(class_names), 3):
    cols = st.columns(3)
    for col, cname in zip(cols, class_names[i:i+3]):
        cap_inputs[cname] = col.number_input(cname, 0, 11, 3)

initial_exempt = st.multiselect("1주차 초고난도 면제", class_names)

seed = st.text_input("시드")
seed_val = int(seed) if seed.isdigit() else None

if st.button("▶ 실행"):
    capacities = {c: int(cap_inputs[c]) for c in class_names}
    df, warnings = distribute_5_weeks(capacities, set(initial_exempt), seed_val)

    for w in warnings:
        st.warning(w)

    st.dataframe(df, use_container_width=True)
