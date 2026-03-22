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


def shuffled(items, rnd):
    """리스트를 복사해서 무작위 순서로 섞는다."""
    items = items[:]
    rnd.shuffle(items)
    return items


def assign_next_from_pool(targets, pool, assignments, rnd):
    """대상 목록에 풀에서 하나씩 배정한다."""
    for c in targets:
        if not pool:
            break
        assignments[c].append(pop_random(pool, rnd))


def distribute_one_week(capacities, exempt_superhard_set, rnd):
    """
    한 주 배정.

    capacities: {생활반명: 청소가능인원}
    exempt_superhard_set: 이번 주 초고난도 면제 대상
    rnd: random.Random 객체
    """
    assignments = {c: [] for c in class_names}

    super_pool = super_hard_areas.copy()
    hard_pool = hard_areas.copy()
    general_pool = general_areas_base.copy()

    nonzero = [c for c in class_names if capacities[c] > 0]

    # 0명만 있는 경우
    if not nonzero:
        leftover = super_pool + hard_pool + general_pool
        return assignments, set(), leftover, False, True

    # 인원 구간
    b_groups = [c for c in class_names if 1 <= capacities[c] <= 3]
    c_groups = [c for c in class_names if 4 <= capacities[c] <= 6]
    d_groups = [c for c in class_names if 7 <= capacities[c] <= 11]
    core_4_11 = c_groups + d_groups

    # 핵심 구역 부족 여부
    severe_shortage = len(nonzero) <= 8

    # -------------------------
    # 1. 핵심 청소구역 배정
    # -------------------------
    if severe_shortage:
        # 핵심 구역이 부족한 경우
        # 초고난도 면제는 폐지하고, 비는 핵심 구역은 마지막에 따로 남긴다.
        core_recipients = shuffled(nonzero, rnd)

        # 핵심 구역은 있는 사람에게 하나씩만 배정
        assign_next_from_pool(core_recipients, super_pool, assignments, rnd)
        assign_next_from_pool(
            [c for c in core_recipients if len(assignments[c]) == 0],
            hard_pool,
            assignments,
            rnd
        )

        leftover_core = super_pool + hard_pool

    else:
        # 정상 경우
        # 4~11명 생활반이 9개 이상이면 그 중 9개를 고른다.
        # 4~11명 생활반이 8개 이하이면, 그 전부와 1~3명 생활반 일부를 더해 9개를 만든다.
        if len(core_4_11) >= 9:
            core_recipients = rnd.sample(core_4_11, 9)
        else:
            need = 9 - len(core_4_11)
            core_recipients = core_4_11[:] + rnd.sample(b_groups, need)

        # 초고난도는 면제 대상이 아닌 생활반에 먼저 배정
        non_exempt = [c for c in core_recipients if c not in exempt_superhard_set]
        exempt = [c for c in core_recipients if c in exempt_superhard_set]

        assign_next_from_pool(shuffled(non_exempt, rnd), super_pool, assignments, rnd)

        # 초고난도가 남아 있으면 면제 대상에도 배정
        assign_next_from_pool(shuffled(exempt, rnd), super_pool, assignments, rnd)

        # 남은 핵심 구역은 고난도에서 배정
        remaining_core_targets = [c for c in core_recipients if len(assignments[c]) == 0]
        assign_next_from_pool(shuffled(remaining_core_targets, rnd), hard_pool, assignments, rnd)

        leftover_core = super_pool + hard_pool

    # -------------------------
    # 2. 아직 배정받지 못한 생활반에 일반 구역 1개
    # -------------------------
    first_general_targets = [
        c for c in class_names
        if capacities[c] > 0 and len(assignments[c]) == 0
    ]
    assign_next_from_pool(shuffled(first_general_targets, rnd), general_pool, assignments, rnd)

    # -------------------------
    # 3. 4~6명 생활반에 일반 구역 1개 추가
    # -------------------------
    second_general_targets = [
        c for c in class_names
        if 4 <= capacities[c] <= 11 and len(assignments[c]) == 1
    ]
    assign_next_from_pool(shuffled(second_general_targets, rnd), general_pool, assignments, rnd)

    # -------------------------
    # 4. 7~11명 생활반에 일반 구역 1개 추가
    # -------------------------
    third_general_targets = [
        c for c in class_names
        if 7 <= capacities[c] <= 11 and len(assignments[c]) == 2
    ]
    assign_next_from_pool(shuffled(third_general_targets, rnd), general_pool, assignments, rnd)

    # 남은 구역
    leftover = leftover_core + general_pool

    # 이번 주 초고난도 담당 생활반
    week_superhard = {
        c for c in class_names
        if any(a in super_hard_areas for a in assignments[c])
    }

    return assignments, week_superhard, leftover, severe_shortage, False


def distribute_5_weeks(capacities, first_week_exempt_set=None, seed=None):
    """5주 배정"""
    rnd_master = random.Random(seed)
    weeks = []
    leftovers = []
    warnings = []

    prev_superhard = set(first_week_exempt_set or set())
    all_zero_case = all(v == 0 for v in capacities.values())

    for _ in range(5):
        rnd = random.Random(rnd_master.randint(0, 2**31 - 1))

        assgn, week_superhard, leftover, severe_shortage, _ = distribute_one_week(
            capacities,
            prev_superhard,
            rnd
        )

        weeks.append(assgn)
        leftovers.append(leftover)
        prev_superhard = week_superhard

        if severe_shortage and not all_zero_case:
            warnings.append("청소 인원이 매우 부족하여 2주 연속 화장실/목욕탕을 청소하는 생활반이 나올 수 있습니다.")

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

    return pd.DataFrame(rows), warnings, all_zero_case


# -------------------------
# 화면
# -------------------------
st.title("생활반 별 청소 구역")

st.markdown(
    """
생활반 청소 가능 인원에 따라 배정되는 청소구역 수가 달라집니다.

0명: 배정 없음  
1~3명: 일반 구역 1개  
4~6명: 핵심 구역 1개 + 일반 구역 1개  
7~11명: 핵심 구역 1개 + 일반 구역 2개
"""
)

st.header("생활반 별 청소가능인원을 입력하십시오 (0~11)")

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

st.subheader("1주차 초고난도 면제")
st.caption("지난 회차 5주차에서 초고난도(화장실/목욕탕)를 맡았던 생활반을 선택하면, 새 회차 1주차에서 우선 제외됩니다.")
first_week_exempt = st.multiselect(
    "면제할 생활반 선택",
    class_names,
    default=[]
)

seed_input = st.text_input(
    "난수 시드(정수, 빈칸이면 무작위)",
    value="",
    help="같은 시드를 입력하면 같은 결과를 다시 얻을 수 있습니다."
)
seed_val = int(seed_input) if seed_input.isdigit() else None

if st.button("▶ 결과 생성"):
    capacities = {c: int(cap_inputs[c]) for c in class_names}
    df, warnings, all_zero_case = distribute_5_weeks(
        capacities,
        first_week_exempt_set=set(first_week_exempt),
        seed=seed_val
    )

    st.success("배정 완료. 결과를 확인하세요.")

    if all_zero_case:
        st.markdown("## 🐱 고양이 모드")
        st.markdown("모든 생활반이 0명입니다. 오늘은 고양이가 근무합니다. 🐾")

    for msg in warnings:
        st.warning(msg)

    st.header("배정 결과")
    st.dataframe(df, use_container_width=True, height=650)

    if st.checkbox("원시 결과 보기"):
        st.write(df)

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
