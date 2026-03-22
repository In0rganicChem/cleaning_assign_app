# cleaning_assign.py
# 설치:
# python -m pip install streamlit pandas

import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="청소구역 배정 프로그램", layout="wide")

# -------------------------
# 모바일 UI 조정
st.markdown("""
<style>
@media (max-width: 768px) {
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
}
</style>
""", unsafe_allow_html=True)
# -------------------------

# 생활반
class_names = [
    "2생활반","3생활반","5생활반","6생활반","7생활반","8생활반",
    "10생활반","11생활반","12생활반","13생활반","14생활반"
]

# 구역
super_hard = ["1층 화장실", "2층 화장실", "3층 화장실", "1층 목욕탕"]
hard = ["2층 샤워장", "3층 샤워장", "1층 세면장", "2층 세면장", "3층 세면장"]
general_base = [
    "1층 세탁실", "1층 복도", "2층 복도", "3층 복도", "동편 계단", "중앙 계단",
    "2층 휴게실", "3층 휴게실", "체단실", "군척장", "공용세탁방", "당구장",
    "사지방", "노래방", "2층 세탁실", "3층 세탁실"
]


def pop(pool, rnd):
    return pool.pop(rnd.randrange(len(pool))) if pool else None


def order_by_capacity(names, cap, rnd):
    grouped = {}
    for c in names:
        grouped.setdefault(cap[c], []).append(c)

    result = []
    for k in sorted(grouped.keys(), reverse=True):
        tmp = grouped[k]
        rnd.shuffle(tmp)
        result.extend(tmp)
    return result


def assign_one_week(cap, exempt_set, rnd):
    assignments = {c: [] for c in class_names}

    super_pool = super_hard.copy()
    hard_pool = hard.copy()
    general_pool = general_base.copy()

    nonzero = [c for c in class_names if cap[c] > 0]

    # -------------------------
    # 0명만 있는 경우
    if not nonzero:
        return assignments, [], False, True

    severe_shortage = len(nonzero) < 9

    # -------------------------
    # 핵심 구역 배정
    # -------------------------

    if severe_shortage:
        # 초고난도 면제 무시
        core_pool = super_pool + hard_pool
        ordered = order_by_capacity(nonzero, cap, rnd)

        for c in ordered:
            if core_pool:
                assignments[c].append(pop(core_pool, rnd))

        leftover_core = core_pool

        warning = True

    else:
        warning = False

        # 4명 이상
        four_plus = [c for c in class_names if cap[c] >= 4]

        # 초고난도 (면제 제외 우선)
        first = [c for c in four_plus if c not in exempt_set]
        second = [c for c in four_plus if c in exempt_set]

        for c in order_by_capacity(first, cap, rnd):
            if super_pool:
                assignments[c].append(pop(super_pool, rnd))

        for c in order_by_capacity(second, cap, rnd):
            if super_pool:
                assignments[c].append(pop(super_pool, rnd))

        # 고난도
        remaining = [c for c in four_plus if len(assignments[c]) == 0]
        for c in order_by_capacity(remaining, cap, rnd):
            if hard_pool:
                assignments[c].append(pop(hard_pool, rnd))

        # 1~3명에게 핵심 배정
        rest_core_super = super_pool[:]
        rest_core_hard = hard_pool[:]

        small = [c for c in class_names if 1 <= cap[c] <= 3 and len(assignments[c]) == 0]

        # 초고난도 (면제 고려)
        first = [c for c in small if c not in exempt_set]
        second = [c for c in small if c in exempt_set]

        for c in order_by_capacity(first, cap, rnd):
            if rest_core_super:
                assignments[c].append(pop(rest_core_super, rnd))

        for c in order_by_capacity(second, cap, rnd):
            if rest_core_super:
                assignments[c].append(pop(rest_core_super, rnd))

        # 고난도
        for c in order_by_capacity(small, cap, rnd):
            if len(assignments[c]) == 0 and rest_core_hard:
                assignments[c].append(pop(rest_core_hard, rnd))

        leftover_core = rest_core_super + rest_core_hard

    # -------------------------
    # 일반 구역 배정
    # -------------------------

    # 1개도 없는 애들
    targets = [c for c in class_names if cap[c] > 0 and len(assignments[c]) == 0]
    for c in order_by_capacity(targets, cap, rnd):
        if general_pool:
            assignments[c].append(pop(general_pool, rnd))

    # 4~6 → 2개
    targets = [c for c in class_names if 4 <= cap[c] <= 6 and len(assignments[c]) == 1]
    for c in order_by_capacity(targets, cap, rnd):
        if general_pool:
            assignments[c].append(pop(general_pool, rnd))

    # 7~11 → 3개
    targets = [c for c in class_names if cap[c] >= 7 and len(assignments[c]) == 2]
    for c in order_by_capacity(targets, cap, rnd):
        if general_pool:
            assignments[c].append(pop(general_pool, rnd))

    leftover = leftover_core + general_pool

    return assignments, leftover, warning, False


def assign_5_weeks(cap, initial_exempt, seed):
    rnd_master = random.Random(seed)

    weeks = []
    leftovers = []
    warnings = []

    prev = set(initial_exempt)

    for i in range(5):
        rnd = random.Random(rnd_master.randint(0, 999999999))

        assgn, left, warn, all_zero = assign_one_week(cap, prev, rnd)

        weeks.append(assgn)
        leftovers.append(left)

        prev = {c for c in class_names if any(a in super_hard for a in assgn[c])}

        if warn:
            warnings.append(f"{i+1}주차: 인원 부족으로 초고난도 연속 배정 가능")

    rows = []
    for c in class_names:
        row = {"생활반": c, "청소가능인원": cap[c]}
        for i in range(5):
            row[f"{i+1}주차"] = ", ".join(weeks[i][c])
        rows.append(row)

    # leftover row
    row = {"생활반": "인원 부족으로 배정되지 못한 청소구역", "청소가능인원": ""}
    for i in range(5):
        row[f"{i+1}주차"] = ", ".join(leftovers[i])
    rows.append(row)

    df = pd.DataFrame(rows)

    return df, warnings, all_zero


# -------------------------
# UI
st.title("생활반 청소 배정")

cap_inputs = {}
for i in range(0, len(class_names), 3):
    cols = st.columns(3)
    for j, c in enumerate(class_names[i:i+3]):
        cap_inputs[c] = cols[j].number_input(c, 0, 11, 3)

initial_exempt = st.multiselect("1주차 초고난도 면제", class_names)

seed = st.text_input("시드")
seed = int(seed) if seed.isdigit() else None

if st.button("실행"):
    cap = {c: int(cap_inputs[c]) for c in class_names}
    df, warnings, all_zero = assign_5_weeks(cap, initial_exempt, seed)

    if all_zero:
        st.info("🐱 모든 생활반이 0명입니다.")

    for w in warnings:
        st.warning(w)

    st.dataframe(df, use_container_width=True)
