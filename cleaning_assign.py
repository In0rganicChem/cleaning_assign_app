# cleaning_assign.py
# 설치:
# python -m pip install streamlit pandas

import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="청소구역 배정", layout="wide")

# -------------------------
# 기본 데이터
# -------------------------

class_names = [
    "2생활반", "3생활반", "5생활반", "6생활반", "7생활반", "8생활반",
    "10생활반", "11생활반", "12생활반", "13생활반", "14생활반"
]

super_hard = ["1층 화장실", "2층 화장실", "3층 화장실", "1층 목욕탕"]
hard = ["2층 샤워장", "3층 샤워장", "1층 세면장", "2층 세면장", "3층 세면장"]
general = [
    "1층 세탁실", "1층 복도", "2층 복도", "3층 복도", "동편 계단", "중앙 계단",
    "2층 휴게실", "3층 휴게실", "체단실", "군척장", "공용세탁방", "당구장",
    "사지방", "노래방", "2층 세탁실", "3층 세탁실"
]

# -------------------------
# 유틸
# -------------------------

def pop(pool, rnd):
    return pool.pop(rnd.randrange(len(pool))) if pool else None

def shuffle(lst, rnd):
    lst = lst[:]
    rnd.shuffle(lst)
    return lst

# -------------------------
# 핵심 배정 로직
# -------------------------

def assign_core(assignments, capacities, exempt, rnd):
    super_pool = super_hard.copy()
    hard_pool = hard.copy()

    # 그룹 정의
    b = [c for c in class_names if 1 <= capacities[c] <= 3]
    cd = [c for c in class_names if capacities[c] >= 4]

    # 배정 순서 (중요)
    order = (
        shuffle([c for c in cd if c not in exempt], rnd) +
        shuffle([c for c in cd if c in exempt], rnd) +
        shuffle([c for c in b if c not in exempt], rnd) +
        shuffle([c for c in b if c in exempt], rnd)
    )

    # -------- 초고난도 먼저 --------
    for c in order:
        if not super_pool:
            break
        if len(assignments[c]) == 0:
            assignments[c].append(pop(super_pool, rnd))

    # -------- 고난도 --------
    for c in order:
        if not hard_pool:
            break
        if len(assignments[c]) == 0:
            assignments[c].append(pop(hard_pool, rnd))

    leftover = super_pool + hard_pool

    return assignments, leftover

# -------------------------
# 일반 구역 배정
# -------------------------

def assign_general(assignments, capacities, rnd):
    pool = general.copy()

    # 1개도 없는 곳
    for c in shuffle(class_names, rnd):
        if capacities[c] > 0 and len(assignments[c]) == 0:
            if pool:
                assignments[c].append(pop(pool, rnd))

    # 4~11명 → 2개까지
    for c in shuffle(class_names, rnd):
        if 4 <= capacities[c] <= 11 and len(assignments[c]) == 1:
            if pool:
                assignments[c].append(pop(pool, rnd))

    # 7~11명 → 3개까지
    for c in shuffle(class_names, rnd):
        if 7 <= capacities[c] <= 11 and len(assignments[c]) == 2:
            if pool:
                assignments[c].append(pop(pool, rnd))

    return assignments, pool

# -------------------------
# 1주 배정
# -------------------------

def one_week(capacities, exempt, rnd):
    assignments = {c: [] for c in class_names}

    # 핵심
    assignments, leftover_core = assign_core(assignments, capacities, exempt, rnd)

    # 일반
    assignments, leftover_general = assign_general(assignments, capacities, rnd)

    # 초고난도 담당 기록
    super_set = {
        c for c in class_names
        if any(a in super_hard for a in assignments[c])
    }

    # 경고 조건
    warning = len(super_set) < len(super_hard)

    leftover = leftover_core + leftover_general

    return assignments, super_set, leftover, warning

# -------------------------
# 5주 실행
# -------------------------

def run_5weeks(capacities, initial_exempt, seed):
    rnd_master = random.Random(seed)

    weeks = []
    leftovers = []
    warnings = []

    prev = set(initial_exempt)

    for i in range(5):
        rnd = random.Random(rnd_master.randint(0, 10**9))

        a, s, l, w = one_week(capacities, prev, rnd)

        weeks.append(a)
        leftovers.append(l)
        prev = s

        if w:
            warnings.append("초고난도 2주 연속 발생 가능")

    # 표 생성
    rows = []
    for c in class_names:
        row = {"생활반": c, "청소가능인원": capacities[c]}
        for i in range(5):
            row[f"{i+1}주차"] = ", ".join(weeks[i][c])
        rows.append(row)

    leftover_row = {"생활반": "배정되지 않은 청소구역", "청소가능인원": ""}
    for i in range(5):
        leftover_row[f"{i+1}주차"] = ", ".join(leftovers[i])
    rows.append(leftover_row)

    return pd.DataFrame(rows), warnings

# -------------------------
# UI
# -------------------------

st.title("청소 구역 배정")

cap_inputs = {}
for i in range(0, len(class_names), 3):
    cols = st.columns(3)
    for col, cname in zip(cols, class_names[i:i+3]):
        cap_inputs[cname] = col.number_input(cname, 0, 11, 11)

initial_exempt = st.multiselect("1주차 초고난도 면제", class_names)

seed = st.text_input("시드")
seed_val = int(seed) if seed.isdigit() else None

if st.button("실행"):
    capacities = {c: int(cap_inputs[c]) for c in class_names}

    # 전원 0명 → 이스터에그
    if all(v == 0 for v in capacities.values()):
        st.markdown("## 🐱 고양이가 대신 청소합니다")
        st.image("https://cataas.com/cat")
    else:
        df, warnings = run_5weeks(capacities, initial_exempt, seed_val)

        for w in warnings:
            st.warning(w)

        st.dataframe(df, use_container_width=True)
