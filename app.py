# app.py
import streamlit as st
import pandas as pd
import random
from io import BytesIO

st.set_page_config(page_title="청소구역 배정 프로그램", layout="wide")

# -------------------------
# 생활반 이름 (user-provided list)
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
]  # 16개
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

    # ---------- A. cap == 0 -> skip ----------
    # no assignment for those; assignments remain empty

    # ---------- B. cap 1~3 -> general 1개, end ----------
    # choose from working_order but shuffle candidates for extra randomness
    b_candidates = [c for c in working_order if 1 <= capacities[c] <= 3]
    rnd.shuffle(b_candidates)
    for c in b_candidates:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # ---------- C. cap >=4 -> 핵심구역 배정 (초고난도 우선: 지난주 초고난도 안 받은 반 먼저) ----------
    core_candidates = [c for c in working_order if capacities[c] >= 4 and len(assignments[c]) == 0]
    # Prefer those who did NOT have super-hard last week
    not_had_last = [c for c in core_candidates if c not in prev_week_superhard_set]
    had_last = [c for c in core_candidates if c in prev_week_superhard_set]

    # Shuffle candidate lists so within groups assignment is random
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

    # Any leftover core areas (super_pool + hard_pool) become part of general pool
    leftover_core = super_pool + hard_pool
    if leftover_core:
        general_pool.extend(leftover_core)
    # Shuffle general pool now
    rnd.shuffle(general_pool)

    # ---------- D. 핵심 못 받은 (len(assignments[c])==0 and cap>0) -> general 1 ----------
    no_assignment = [c for c in working_order if capacities[c] > 0 and len(assignments[c]) == 0]
    rnd.shuffle(no_assignment)
    for c in no_assignment:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # ---------- E. (removed specific cap==3 stop because B handles 1-3 already) ----------
    # (All 1~3 already finished in B)

    # ---------- F. cap 4~11 & currently 1 assignment -> + general 1 ----------
    candidates_f = [c for c in working_order if capacities[c] >= 4 and len(assignments[c]) == 1]
    rnd.shuffle(candidates_f)
    for c in candidates_f:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))
        else:
            break

    # ---------- G. cap 4~7 stop ----------
    # Those with cap 4~7 stop here (we will not assign further)

    # ---------- H. cap 8~11 & currently 2 assignments -> + general 1 ----------
    candidates_h = [c for c in working_order if capacities[c] >= 8 and len(assignments[c]) == 2]
    rnd.shuffle(candidates_h)
    for c in candidates_h:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))
        else:
            break

    # ---------- I (implicit from H): If general_pool remains, distribute to groups with exactly 2 assigned by capacity desc ----------
    if general_pool:
        two_assigned = [c for c in class_names if capacities[c] > 0 and len(assignments[c]) == 2]
        # Group by capacity and shuffle within same-capacity
        grouped = {}
        for c in two_assigned:
            grouped.setdefault(capacities[c], []).append(c)
        ordered = []
        for cap in sorted(grouped.keys(), reverse=True):
            subs = grouped[cap]
            rnd.shuffle(subs)
            ordered.extend(subs)
        # round-robin assign while pool exists
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

""")

# 입력란
st.header("1) 청소가능인원 입력 (0~11)")
cols = st.columns(3)
cap_inputs = {}
for i, cname in enumerate(class_names):
    col = cols[i % 3]
    cap_inputs[cname] = col.number_input(f"{cname}", min_value=0, max_value=11, value=3, step=1, key=f"cap_{cname}")

seed_input = st.text_input("난수 시드를 원하면 입력(정수, 빈칸이면 무작위)", value="", help="same seed => same outcome")
seed_val = int(seed_input) if seed_input.strip().isdigit() else None

st.write(" ")
st.markdown("**2) 실행**")
if st.button("▶ 5주차 배정 실행 (결과 생성)"):
    capacities = {c: int(cap_inputs[c]) for c in class_names}
    weeks_assignments, df = distribute_5_weeks(capacities, seed=seed_val)
    st.success("배정 완료. 결과를 확인하세요.")
    st.header("배정 결과")
    st.dataframe(df.style.set_properties(**{'white-space': 'pre'}), height=600)


    if st.checkbox("원시 배정 데이터 보기 (디버그)"):
        st.write(weeks_assignments)

st.markdown("---")
