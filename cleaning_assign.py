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


def build_priority_order(names, capacities, rnd):
    """인원이 많은 순서대로 정렬하되, 같은 인원끼리는 랜덤으로 섞는다."""
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

    nonzero = [c for c in class_names if capacities[c] > 0]
    all_zero_case = len(nonzero) == 0
    severe_shortage = len(nonzero) < 9

    # 모든 생활반이 0명인 경우
    if all_zero_case:
        leftover_areas = super_pool + hard_pool + general_pool
        week_superhard = set()
        return assignments, week_superhard, leftover_areas, severe_shortage, all_zero_case

    # 주차마다 생활반 순서를 섞어서 편향을 줄인다
    working_order = class_names.copy()
    rnd.shuffle(working_order)

    # -------------------------
    # 핵심 구역 배정
    # -------------------------

    if severe_shortage:
        # 핵심 구역을 모두 배정하기 어려운 경우
        # 초고난도 면제를 무시하고 모든 핵심 구역을 동등하게 처리한다.
        core_pool = super_pool + hard_pool
        core_order = build_priority_order(nonzero, capacities, rnd)

        for c in core_order:
            if core_pool:
                assignments[c].append(pop_random(core_pool, rnd))
            else:
                break

        leftover_core = core_pool[:]

    else:
        # 핵심 구역이 충분한 경우
        # 1) 4명 이상 생활반 중 면제 대상이 아닌 생활반에 초고난도 우선 배정
        four_plus = [c for c in class_names if capacities[c] >= 4]
        super_candidates = build_priority_order(
            [c for c in four_plus if c not in exempt_superhard_set],
            capacities,
            rnd
        )

        for c in super_candidates:
            if super_pool:
                assignments[c].append(pop_random(super_pool, rnd))
            else:
                break

        # 2) 남은 4명 이상 생활반에 고난도 배정
        remaining_four_plus = build_priority_order(
            [c for c in four_plus if len(assignments[c]) == 0],
            capacities,
            rnd
        )

        for c in remaining_four_plus:
            if hard_pool:
                assignments[c].append(pop_random(hard_pool, rnd))
            else:
                break

        # 3) 핵심 구역이 남았다면 1~3명 생활반에 인원 많은 순으로 배정
       # 핵심을 super / hard로 분리
remaining_super = super_pool[:]
remaining_hard = hard_pool[:]

one_to_three = build_priority_order(
    [c for c in class_names if 1 <= capacities[c] <= 3 and len(assignments[c]) == 0],
    capacities,
    rnd
)

# 1) 초고난도: 면제 대상 제외하고 먼저 배정
non_exempt = [c for c in one_to_three if c not in exempt_superhard_set]
exempt = [c for c in one_to_three if c in exempt_superhard_set]

for c in non_exempt:
    if remaining_super:
        assignments[c].append(pop_random(remaining_super, rnd))
    else:
        break

# 2) 초고난도 남으면 면제 대상에도 배정 (불가피한 경우)
for c in exempt:
    if remaining_super:
        assignments[c].append(pop_random(remaining_super, rnd))
    else:
        break

# 3) 나머지는 고난도 배정
remaining_core = remaining_hard

for c in one_to_three:
    if len(assignments[c]) == 0 and remaining_core:
        assignments[c].append(pop_random(remaining_core, rnd))

        leftover_core = remaining_core[:]

    # -------------------------
    # 일반 구역 배정
    # -------------------------

    # 4명 이상이면 일반 구역 1개를 추가한다
    first_general_targets = build_priority_order(
        [c for c in class_names if capacities[c] > 0 and len(assignments[c]) == 0],
        capacities,
        rnd
    )

    for c in first_general_targets:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))
        else:
            break

    # 4~6명은 여기서 끝
    # 7~11명은 일반 구역 1개를 더 받는다
    second_general_targets = build_priority_order(
        [c for c in class_names if capacities[c] >= 4 and len(assignments[c]) == 1],
        capacities,
        rnd
    )

    for c in second_general_targets:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))
        else:
            break

    third_general_targets = build_priority_order(
        [c for c in class_names if capacities[c] >= 7 and len(assignments[c]) == 2],
        capacities,
        rnd
    )

    for c in third_general_targets:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))
        else:
            break

    # 남은 구역은 마지막 줄에 따로 표시
    leftover_areas = leftover_core + general_pool

    # 이번 주 초고난도 담당 생활반 기록
    week_superhard = set()
    for c in class_names:
        if any(a in super_hard_areas for a in assignments[c]):
            week_superhard.add(c)

    return assignments, week_superhard, leftover_areas, severe_shortage, all_zero_case


def distribute_5_weeks(capacities, initial_exempt_set=None, seed=None):
    """5주 배정."""
    rnd_master = random.Random(seed)
    weeks = []
    leftovers = []
    warnings = []

    prev_superhard = set(initial_exempt_set or set())

    all_zero_case = all(v == 0 for v in capacities.values())

    for week_idx in range(1, 6):
        week_seed = rnd_master.randint(0, 2**31 - 1)
        rnd = random.Random(week_seed)

        assgn, week_superhard, leftover_areas, severe_shortage, _ = distribute_one_week(
            capacities,
            prev_superhard,
            rnd
        )

        weeks.append(assgn)
        leftovers.append(leftover_areas)
        prev_superhard = week_superhard.copy()

        if severe_shortage and not all_zero_case:
            warnings.append(
                f"{week_idx}주차: 청소 인원 매우 부족으로, 화장실/목욕탕을 2주 연속 배정받는 생활반이 등장할 수 있습니다."
            )

    # 표 만들기
    rows = []
    for c in class_names:
        row = {"생활반": c, "청소가능인원": capacities[c]}
        for i, assgn in enumerate(weeks, start=1):
            row[f"{i}주차"] = ", ".join(assgn[c]) if assgn[c] else ""
        rows.append(row)

    # 마지막 줄: 아직 배정되지 못한 구역
    leftover_row = {"생활반": "인원 부족으로 배정되지 못한 청소구역", "청소가능인원": ""}
    for i, lst in enumerate(leftovers, start=1):
        leftover_row[f"{i}주차"] = ", ".join(lst) if lst else ""
    rows.append(leftover_row)

    df = pd.DataFrame(rows)
    return weeks, leftovers, df, warnings, all_zero_case


# -------------------------
# 화면
st.title("생활반 별 청소 구역")

st.markdown(
    """
생활반 청소 가능 인원에 따라 배정되는 청소구역 수가 달라집니다.

1~3명: 기본적으로 1개  
4~6명: 기본적으로 2개  
7~11명: 기본적으로 3개  

핵심 구역이 부족하거나 생활반 수가 아주 적으면, 일부 구역은 마지막 줄에 따로 표시됩니다.
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
    weeks_assignments, leftovers, df, warnings, all_zero_case = distribute_5_weeks(
        capacities,
        initial_exempt_set=set(initial_exempt),
        seed=seed_val
    )

    st.success("배정 완료. 결과를 확인하세요.")

    if all_zero_case:
        st.info("청소 인원이 부족하여 짬타이거가 청소합니다. 🐱")

    for msg in warnings:
        st.warning(msg)

    st.header("배정 결과")
    st.dataframe(df, use_container_width=True, height=650)

    if any(leftovers):
        st.warning("아래 행에 아직 배정되지 못한 청소구역이 표시되어 있습니다.")

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
