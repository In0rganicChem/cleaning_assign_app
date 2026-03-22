# cleaning_assign.py
import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="청소구역 배정 프로그램", layout="wide")

# -------------------------
# 데이터 정의
# -------------------------
class_names = [
    "2생활반","3생활반","5생활반","6생활반","7생활반","8생활반",
    "10생활반","11생활반","12생활반","13생활반","14생활반"
]

super_hard_areas = ["1층 화장실","2층 화장실","3층 화장실","1층 목욕탕"]
hard_areas = ["2층 샤워장","3층 샤워장","1층 세면장","2층 세면장","3층 세면장"]

general_areas = [
    "1층 세탁실","1층 복도","2층 복도","3층 복도","동편 계단","중앙 계단",
    "2층 휴게실","3층 휴게실","체단실","군척장","공용세탁방","당구장",
    "사지방","노래방","2층 세탁실","3층 세탁실"
]

# -------------------------
# 유틸
# -------------------------
def pop_random(pool, rnd):
    return pool.pop(rnd.randrange(len(pool))) if pool else None

def shuffle(lst, rnd):
    lst = lst[:]
    rnd.shuffle(lst)
    return lst

# -------------------------
# 핵심 로직
# -------------------------
def assign_one_week(cap, prev_super, rnd):

    assignments = {c: [] for c in class_names}

    super_pool = super_hard_areas.copy()
    hard_pool = hard_areas.copy()
    general_pool = general_areas.copy()

    nonzero = [c for c in class_names if cap[c] > 0]

    # -------------------------
    # 🐱 전원 0명
    # -------------------------
    if not nonzero:
        leftover = super_pool + hard_pool + general_pool
        return assignments, set(), leftover, False, True

    # -------------------------
    # 그룹 분리
    # -------------------------
    B = [c for c in class_names if 1 <= cap[c] <= 3]
    C = [c for c in class_names if 4 <= cap[c] <= 6]
    D = [c for c in class_names if 7 <= cap[c] <= 11]

    CD = C + D

    severe = len(nonzero) < 9  # 핵심 부족 여부

    # -------------------------
    # 1️⃣ 초고난도 배정
    # -------------------------
    def assign_super(targets):
        for c in targets:
            if not super_pool:
                break
            assignments[c].append(pop_random(super_pool, rnd))

    # 면제 제외 → 면제 포함
    non_exempt = [c for c in CD if c not in prev_super]
    exempt = [c for c in CD if c in prev_super]

    assign_super(shuffle(non_exempt, rnd))
    assign_super(shuffle(exempt, rnd))

    # 부족하면 B까지 내려감
    if super_pool:
        non_exempt_B = [c for c in B if c not in prev_super]
        exempt_B = [c for c in B if c in prev_super]

        assign_super(shuffle(non_exempt_B, rnd))
        assign_super(shuffle(exempt_B, rnd))

    # -------------------------
    # 2️⃣ 고난도 배정
    # -------------------------
    remaining = [c for c in class_names if cap[c] > 0 and len(assignments[c]) == 0]

    for c in shuffle(remaining, rnd):
        if not hard_pool:
            break
        assignments[c].append(pop_random(hard_pool, rnd))

    # -------------------------
    # 핵심 남은 것 처리
    # -------------------------
    leftover_core = super_pool + hard_pool

    # -------------------------
    # 3️⃣ 일반 구역
    # -------------------------

    # (1) 아직 0개인 곳
    for c in shuffle([c for c in class_names if cap[c]>0 and len(assignments[c])==0], rnd):
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # (2) 4~6, 7~11 → 2개 맞추기
    for c in shuffle([c for c in C+D if len(assignments[c])==1], rnd):
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # (3) 7~11 → 3개 맞추기
    for c in shuffle([c for c in D if len(assignments[c])==2], rnd):
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    leftover = leftover_core + general_pool

    # -------------------------
    # 초고난도 기록
    # -------------------------
    week_super = {
        c for c in class_names
        if any(a in super_hard_areas for a in assignments[c])
    }

    return assignments, week_super, leftover, severe, False


# -------------------------
# 5주 실행
# -------------------------
def run_5weeks(cap, first_exempt, seed):

    rnd_master = random.Random(seed)

    weeks = []
    leftovers = []
    warnings = []

    prev = set(first_exempt)

    all_zero = all(v == 0 for v in cap.values())

    for i in range(5):
        rnd = random.Random(rnd_master.randint(0, 10**9))

        ass, sup, left, severe, zero_case = assign_one_week(cap, prev, rnd)

        weeks.append(ass)
        leftovers.append(left)

        # 초고난도 반복 불가 상황 감지
        if severe and not zero_case:
            warnings.append("⚠ 인원 부족으로 초고난도 연속 배정 가능")

        prev = sup

    # 표 생성
    rows = []
    for c in class_names:
        row = {"생활반": c, "청소가능인원": cap[c]}
        for i in range(5):
            row[f"{i+1}주차"] = ", ".join(weeks[i][c])
        rows.append(row)

    # 남은 구역 표시
    last = {"생활반":"인원 부족으로 배정되지 못한 청소구역","청소가능인원":""}
    for i in range(5):
        last[f"{i+1}주차"] = ", ".join(leftovers[i])
    rows.append(last)

    return pd.DataFrame(rows), warnings, all_zero


# -------------------------
# UI
# -------------------------
st.title("생활반 청소 배정")

cap_inputs = {}
for i in range(0, len(class_names), 3):
    cols = st.columns(3)
    for col, c in zip(cols, class_names[i:i+3]):
        cap_inputs[c] = col.number_input(c, 0, 11, 11)

exempt = st.multiselect("1주차 초고난도 면제", class_names)

seed = st.text_input("시드")
seed = int(seed) if seed.isdigit() else None

if st.button("▶ 실행"):

    cap = {c:int(cap_inputs[c]) for c in class_names}

    df, warnings, all_zero = run_5weeks(cap, exempt, seed)

    if all_zero:
        st.markdown("## 🐱 고양이가 대신 청소합니다")
        st.markdown("오늘은 전원 휴무입니다.")

    for w in warnings:
        st.warning(w)

    st.dataframe(df, use_container_width=True)
