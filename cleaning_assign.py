# cleaning_assign.py
# install:
# python -m pip install streamlit pandas openpyxl
import streamlit as st
import pandas as pd
import random
from io import BytesIO

st.set_page_config(page_title="청소구역 배정 프로그램", layout="wide")

# -------------------------
# 생활반 이름
class_names = [
    "2생활반","3생활반","5생활반","6생활반","7생활반","8생활반",
    "10생활반","11생활반","12생활반","13생활반","14생활반"
]

# 구역 풀 (고정)
super_hard_areas = ["1층 화장실", "2층 화장실", "3층 화장실", "1층 목욕탕"]  # 초고난도 4개
hard_areas = ["2층 샤워장", "3층 샤워장", "1층 세면장", "2층 세면장", "3층 세면장"]  # 고난도 5개
general_areas_base = [
    "1층 세탁실", "1층 복도", "2층 복도", "3층 복도", "동편 계단", "중앙 계단",
    "2층 휴게실", "3층 휴게실", "체단실", "군척장", "공용세탁방", "당구장",
    "사지방", "노래방", "2층 세탁실", "3층 세탁실"
]  # 일반 16개
# -------------------------

def pop_random(pool, rnd):
    if not pool:
        return None
    return pool.pop(rnd.randrange(len(pool)))

def distribute_one_week(capacities, prev_week_superhard_set, rnd: random.Random):
    """
    capacities: dict {class_name: int}
    prev_week_superhard_set: set of class_names who had 초고난도 last week
    rnd: random.Random instance
    returns: assignments dict {class_name: [area,...]}, and week_superhard_set (set)
    """

    # Make fresh pools
    super_pool = super_hard_areas.copy()
    hard_pool = hard_areas.copy()
    general_pool = general_areas_base.copy()

    assignments = {c: [] for c in class_names}

    # Working order: shuffle class order at start of week to avoid index bias
    working_order = class_names.copy()
    rnd.shuffle(working_order)

    # A단계 - 인원이 0명인 생활반은 청소 안함


    # B단계 - 인원이 1~3명인 생활반은 쉬운 청소구역 1개만 배정
    b_candidates = [c for c in working_order if 1 <= capacities[c] <= 3]
    rnd.shuffle(b_candidates)
    for c in b_candidates:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # C단계 - 인원이 4-11명인 생활반에 핵심 청소구역 하나씩 배정. 이때 화장실/1층목욕탕은 2주 연속 하지 않도록 함.
    core_candidates = [c for c in working_order if capacities[c] >= 4 and len(assignments[c]) == 0]
    not_had_last = [c for c in core_candidates if c not in prev_week_superhard_set]
    had_last = [c for c in core_candidates if c in prev_week_superhard_set]

    rnd.shuffle(not_had_last)
    rnd.shuffle(had_last)

    assigned_core = set()

    # Assign super-hard to not_had_last first
    for c in not_had_last:
        if super_pool:
            assignments[c].append(pop_random(super_pool, rnd))
            assigned_core.add(c)
        else:
            break

    # If super_pool still remains, assign to had_last group
    for c in had_last:
        if super_pool:
            assignments[c].append(pop_random(super_pool, rnd))
            assigned_core.add(c)
        else:
            break

    # Assign remaining core hard areas (고난도) to still-unassigned core candidates
    remaining_candidates = [c for c in core_candidates if c not in assigned_core]
    rnd.shuffle(remaining_candidates)
    for c in remaining_candidates:
        if hard_pool:
            assignments[c].append(pop_random(hard_pool, rnd))
            assigned_core.add(c)
        else:
            break

    # Any leftover core areas become part of general pool
    leftover_core = super_pool + hard_pool
    if leftover_core:
        general_pool.extend(leftover_core)
    rnd.shuffle(general_pool)

    # D단계. 핵심 청소구역 아직 못 받은 생활반 있으면 거기에는 일반 청소구역 배정
    no_assignment = [c for c in working_order if capacities[c] > 0 and len(assignments[c]) == 0]
    rnd.shuffle(no_assignment)
    for c in no_assignment:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # E단계 - 인원이 4-11명인 생활반에 일반 청소구역 하나씩 더 배정
    candidates_f = [c for c in working_order if capacities[c] >= 4 and len(assignments[c]) == 1]
    rnd.shuffle(candidates_f)
    for c in candidates_f:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))
        else:
            break

    # F단계 - 4~7명인 생활반은 여기서 끝
    # nothing to do

    # G단계 - 인원이 8~11명인 생활반에 일반 청소구역하나씩 더 배정
    candidates_h = [c for c in working_order if capacities[c] >= 8 and len(assignments[c]) == 2]
    rnd.shuffle(candidates_h)
    for c in candidates_h:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))
        else:
            break

    # H단계 - 남은 청소구역이 있다면 인원이 많은 생활반부터 하나씩 추가로 계속 분배
    # ---------- FINAL STEP : If general_pool still has areas, assign them to ALL non-zero groups
    # in descending order of capacity (tie-break randomized), repeating cycles until pool is empty.
    if general_pool:
        # Candidates: all with capacity > 0 (exclude 0-cap groups)
        candidates_all = [c for c in class_names if capacities[c] > 0]
        # group by capacity and within same cap shuffle so tie-break is random
        grouped = {}
        for c in candidates_all:
            grouped.setdefault(capacities[c], []).append(c)
        ordered = []
        for cap in sorted(grouped.keys(), reverse=True):
            subs = grouped[cap]
            rnd.shuffle(subs)
            ordered.extend(subs)
        # Assign round-robin over ordered list until pool empty
        idx = 0
        while general_pool and ordered:
            c = ordered[idx % len(ordered)]
            assignments[c].append(pop_random(general_pool, rnd))
            idx += 1

    # Determine this week's superhard receivers
    week_superhard = set()
    for c in class_names:
        for a in assignments[c]:
            if a in super_hard_areas:
                week_superhard.add(c)
                break

    return assignments, week_superhard

# ---- distribute for 5 weeks sequentially ----
def distribute_5_weeks(capacities, seed=None):
    rnd_master = random.Random(seed)
    weeks = []
    prev_superhard = set()
    for week_idx in range(1, 6):  # 1..5
        week_seed = rnd_master.randint(0, 2**31 - 1)
        rnd = random.Random(week_seed)
        assgn, week_superhard = distribute_one_week(capacities, prev_superhard, rnd)
        weeks.append(assgn)
        prev_superhard = week_superhard.copy()
    # Build DataFrame
    rows = []
    for c in class_names:
        row = {"생활반": c, "청소가능인원": capacities[c]}
        for i, assgn in enumerate(weeks, start=1):
            areas = assgn[c]
            row[f"{i}주차"] = ", ".join(areas) if areas else ""
        rows.append(row)
    df = pd.DataFrame(rows)
    return weeks, df

# -------------------------
# Streamlit UI
st.title("생활반 별 청소 구역")
st.markdown("""
생활반 청소 가능 인원에 따라 배정되는 청소구역 수가 달라집니다.  
1-3명일 시: 1개 구역  
4-7명일 시 : 2개 구역  
8-11명일 시 : 3개 구역  
""")

# 입력란
st.header("생활반 별 청소가능인원을 입력하십시오 (0~11)")

cap_inputs = {}
chunk_size = 3
for start in range(0, len(class_names), chunk_size):
    row = class_names[start:start+chunk_size]
    cols = st.columns(len(row))
    for col, cname in zip(cols, row):
        cap_inputs[cname] = col.number_input(f"{cname}", min_value=0, max_value=11, value=11, step=1, key=f"cap_{cname}")

seed_input = st.text_input("난수 시드를 원하면 입력(정수, 빈칸이면 무작위)", value="", help="same seed => same outcome")
seed_val = int(seed_input) if seed_input.strip().isdigit() else None

st.write(" ")
if st.button("▶ 결과 생성"):
    capacities = {c: int(cap_inputs[c]) for c in class_names}
    weeks_assignments, df = distribute_5_weeks(capacities, seed=seed_val)
    st.success("배정 완료. 결과를 확인하세요.")
    st.header("배정 결과")
    st.dataframe(df.style.set_properties(**{'white-space': 'pre'}), height=600)

    if st.checkbox("원시 배정 데이터 보기 (디버그)"):
        st.write(weeks_assignments)

st.markdown("---")
# run locally:
# python -m streamlit run cleaning_assign.py