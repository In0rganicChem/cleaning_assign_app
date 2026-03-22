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
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
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

# 청소구역
super_hard_areas = ["1층 화장실", "2층 화장실", "3층 화장실", "1층 목욕탕"]
hard_areas = ["2층 샤워장", "3층 샤워장", "1층 세면장", "2층 세면장", "3층 세면장"]
general_areas_base = [
    "1층 세탁실", "1층 복도", "2층 복도", "3층 복도", "동편 계단", "중앙 계단",
    "2층 휴게실", "3층 휴게실", "체단실", "군척장", "공용세탁방", "당구장",
    "사지방", "노래방", "2층 세탁실", "3층 세탁실"
]


def pop_random(pool, rnd):
    """풀에서 무작위로 1개 꺼낸다."""
    if not pool:
        return None
    return pool.pop(rnd.randrange(len(pool)))


def distribute_one_week(capacities, exempt_superhard_set, rnd):
    """
    한 주차 배정.

    capacities: {생활반명: 청소가능인원}
    exempt_superhard_set: 이번 주 초고난도 면제 대상
    rnd: random.Random 객체
    """
    super_pool = super_hard_areas.copy()
    hard_pool = hard_areas.copy()
    general_pool = general_areas_base.copy()

    assignments = {c: [] for c in class_names}

    # 주차마다 생활반 순서를 섞어서 편향을 줄인다
    working_order = class_names.copy()
    rnd.shuffle(working_order)

    # A. 0명은 배정 없음
    # 아무것도 하지 않음

    # B. 1~3명은 일반 구역 1개만 배정
    b_candidates = [c for c in working_order if 1 <= capacities[c] <= 3]
    rnd.shuffle(b_candidates)
    for c in b_candidates:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # C. 4~11명은 핵심 구역 1개씩 배정
    core_candidates = [c for c in working_order if capacities[c] >= 4 and len(assignments[c]) == 0]

    # 이번 주 초고난도 면제 대상은 먼저 제외한다
    not_had_last = [c for c in core_candidates if c not in exempt_superhard_set]
    had_last = [c for c in core_candidates if c in exempt_superhard_set]

    rnd.shuffle(not_had_last)
    rnd.shuffle(had_last)

    assigned_core = set()

    # 초고난도 먼저 배정
    for c in not_had_last:
        if super_pool:
            assignments[c].append(pop_random(super_pool, rnd))
            assigned_core.add(c)
        else:
            break

    for c in had_last:
        if super_pool:
            assignments[c].append(pop_random(super_pool, rnd))
            assigned_core.add(c)
        else:
            break

    # 남은 핵심 대상에게 고난도 배정
    remaining_candidates = [c for c in core_candidates if c not in assigned_core]
    rnd.shuffle(remaining_candidates)
    for c in remaining_candidates:
        if hard_pool:
            assignments[c].append(pop_random(hard_pool, rnd))
            assigned_core.add(c)
        else:
            break

    # 핵심 구역이 남았다면 일반 구역 풀로 합친다
    leftover_core = super_pool + hard_pool
    if leftover_core:
        general_pool.extend(leftover_core)
    rnd.shuffle(general_pool)

    # D. 아직 아무 배정도 못 받은 생활반은 일반 구역 1개 배정
    no_assignment = [c for c in working_order if capacities[c] > 0 and len(assignments[c]) == 0]
    rnd.shuffle(no_assignment)
    for c in no_assignment:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # E. 4~11명이고 1개 받은 생활반은 일반 구역 1개 추가
    candidates_f = [c for c in working_order if capacities[c] >= 4 and len(assignments[c]) == 1]
    rnd.shuffle(candidates_f)
    for c in candidates_f:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))
        else:
            break

    # F. 4~7명은 여기서 끝
    # 아무것도 하지 않음

    # G. 8~11명이고 2개 받은 생활반은 일반 구역 1개 추가
    candidates_h = [c for c in working_order if capacities[c] >= 8 and len(assignments[c]) == 2]
    rnd.shuffle(candidates_h)
    for c in candidates_h:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))
        else:
            break

    # 남은 청소구역은 따로 반환만 하고, 여기서 더 이상 자동 배정하지 않는다
    leftover_areas = general_pool.copy()

    # 이번 주 초고난도 담당 생활반 기록
    week_superhard = set()
    for c in class_names:
        if any(a in super_hard_areas for a in assignments[c]):
            week_superhard.add(c)

    return assignments, week_superhard, leftover_areas


def distribute_5_weeks(capacities, initial_exempt_set=None, seed=None):
    """5주 배정."""
    rnd_master = random.Random(seed)
    weeks = []
    leftovers = []

    # 1주차 초고난도 면제 대상
    prev_superhard = set(initial_exempt_set or set())

    for _ in range(5):
        week_seed = rnd_master.randint(0, 2**31 - 1)
        rnd = random.Random(week_seed)

        assgn, week_superhard, leftover_areas = distribute_one_week(
            capacities,
            prev_superhard,
            rnd
        )

        weeks.append(assgn)
        leftovers.append(leftover_areas)
        prev_superhard = week_superhard.copy()

    # 표 만들기
    rows = []
    for c in class_names:
        row = {"생활반": c, "청소가능인원": capacities[c]}
        for i, assgn in enumerate(weeks, start=1):
            row[f"{i}주차"] = ", ".join(assgn[c]) if assgn[c] else ""
        rows.append(row)

    # 마지막 줄: 남은 청소구역
    leftover_row = {"생활반": "인원 부족으로 아직 배정되지 않은 청소구역", "청소가능인원": ""}
    for i, lst in enumerate(leftovers, start=1):
        leftover_row[f"{i}주차"] = ", ".join(lst) if lst else ""
    rows.append(leftover_row)

    df = pd.DataFrame(rows)
    return weeks, leftovers, df


# -------------------------
# 화면
st.title("생활반 별 청소 구역")

st.markdown(
    """
생활반 청소 가능 인원에 따라 배정되는 청소구역 수가 달라집니다.

1~3명: 일반 구역 1개  
4~7명: 핵심 구역 1개 + 일반 구역 1개  
8~11명: 핵심 구역 1개 + 일반 구역 2개  
"""
)

st.header("생활반 별 청소가능인원을 입력하십시오 (0~11)")

cap_inputs = {}
chunk_size = 3
for start in range(0, len(class_names), chunk_size):
    row = class_names[start:start + chunk_size]
    cols = st.columns(len(row))
    for col, cname in zip(cols, row):
        cap_inputs[cname] = col.number_input(
            f"{cname}",
            min_value=0,
            max_value=11,
            value=11,
            step=1,
            key=f"cap_{cname}"
        )

st.subheader("1주차 초고난도 면제 대상")
st.caption("지난 회차 5주차에서 초고난도(화장실/목욕탕)를 맡았던 생활반을 선택하면, 새 회차 1주차에서 우선 제외됩니다.")
initial_exempt = st.multiselect(
    "면제할 생활반 선택",
    class_names,
    default=[]
)

seed_input = st.text_input(
    "난수 시드(정수, 빈칸이면 무작위)",
    value="",
    help="같은 시드를 입력하면 같은 결과를 다시 얻을 수 있습니다."
)
seed_val = int(seed_input) if seed_input.strip().isdigit() else None

if st.button("▶ 결과 생성"):
    capacities = {c: int(cap_inputs[c]) for c in class_names}
    weeks_assignments, leftovers, df = distribute_5_weeks(
        capacities,
        initial_exempt_set=set(initial_exempt),
        seed=seed_val
    )

    st.success("배정 완료. 결과를 확인하세요.")
    st.header("배정 결과")
    st.dataframe(df, use_container_width=True, height=650)

    if any(leftovers):
        st.warning("아래 행에 남은 청소구역이 표시되어 있습니다. 필요하면 수동으로 추가 분배하세요.")

    if st.checkbox("원시 배정 데이터 보기 (디버그)"):
        st.write(weeks_assignments)
        st.write(leftovers)

st.markdown("---")
st.markdown("Python 코드로 만든 Streamlit 앱입니다.")

with st.expander("📄 현재 실행 중인 코드 보기"):
    try:
        with open(__file__, "r", encoding="utf-8") as f:
            st.code(f.read(), language="python", height=500)
    except Exception as e:
        st.error(str(e))

# 로컬 실행:
# python -m streamlit run cleaning_assign.py
