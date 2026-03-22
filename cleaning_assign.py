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
    """리스트에서 무작위로 1개 꺼내기"""
    if not pool:
        return None
    return pool.pop(rnd.randrange(len(pool)))


def shuffled(items, rnd):
    """리스트를 복사해서 무작위 순서로 섞기"""
    items = items[:]
    rnd.shuffle(items)
    return items


def assign_core_to_groups(groups, core_pool, assignments, rnd):
    """주어진 그룹 순서대로 핵심 구역을 1개씩 배정"""
    for c in groups:
        if not core_pool:
            break
        assignments[c].append(pop_random(core_pool, rnd))


def distribute_one_week(capacities, exempt_superhard_set, rnd):
    """
    한 주 배정.

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

    # 전원 0명인 경우
    if all_zero_case:
        leftover = super_pool + hard_pool + general_pool
        week_superhard = set()
        return assignments, week_superhard, leftover, False, True

    # 생활반 구간 나누기
    b_groups = [c for c in class_names if 1 <= capacities[c] <= 3]
    c_groups = [c for c in class_names if 4 <= capacities[c] <= 6]
    d_groups = [c for c in class_names if 7 <= capacities[c] <= 11]

    # 핵심 구역 부족 여부
    severe_shortage = len(nonzero) < 9

    # -------------------------
    # 핵심 구역 배정
    # -------------------------
    if severe_shortage:
        # 인원이 너무 부족한 경우
        # 초고난도 면제는 폐지하고, 핵심 구역을 단순하게 배정한다.
        core_pool = super_pool + hard_pool

        # 4~11명 생활반을 먼저 처리하고, 부족하면 1~3명 생활반으로 내려간다.
        core_order = shuffled(c_groups + d_groups, rnd) + shuffled(b_groups, rnd)
        assign_core_to_groups(core_order, core_pool, assignments, rnd)

        leftover_core = core_pool[:]  # 아직 남은 핵심 구역은 따로 둔다

    else:
        # 일반적인 경우
        # 4~11명 생활반이 먼저 핵심 구역을 받는다.
        cd_groups = c_groups + d_groups

        # 초고난도 면제 대상은 뒤로 미룬다.
        non_exempt_cd = [c for c in cd_groups if c not in exempt_superhard_set]
        exempt_cd = [c for c in cd_groups if c in exempt_superhard_set]

        core_order = shuffled(non_exempt_cd, rnd) + shuffled(exempt_cd, rnd)

        # 초고난도부터 먼저 배정
        for c in core_order:
            if super_pool:
                assignments[c].append(pop_random(super_pool, rnd))
            else:
                break

        # 초고난도가 남아 있으면 고난도는 아직 핵심을 못 받은 4~11명에게 배정
        remaining_cd = [c for c in cd_groups if len(assignments[c]) == 0]
        remaining_cd = shuffled(remaining_cd, rnd)

        for c in remaining_cd:
            if hard_pool:
                assignments[c].append(pop_random(hard_pool, rnd))
            else:
                break

        # 핵심 구역이 남으면 1~3명 생활반이 대신 받는다
        core_pool = super_pool + hard_pool
        b_order = shuffled(b_groups, rnd)
        assign_core_to_groups(b_order, core_pool, assignments, rnd)

        leftover_core = core_pool[:]

    # -------------------------
    # 일반 구역 배정
    # -------------------------
    # 1) 아직 아무 구역도 없는 생활반에 일반 구역 1개
    first_general_targets = shuffled(
        [c for c in class_names if capacities[c] > 0 and len(assignments[c]) == 0],
        rnd
    )
    for c in first_general_targets:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # 2) 4~6명 / 7~11명 생활반 중 1개 받은 곳에 일반 구역 추가
    second_general_targets = shuffled(
        [c for c in class_names if 4 <= capacities[c] <= 11 and len(assignments[c]) == 1],
        rnd
    )
    for c in second_general_targets:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # 3) 7~11명 생활반 중 2개 받은 곳에 일반 구역 추가
    third_general_targets = shuffled(
        [c for c in class_names if 7 <= capacities[c] <= 11 and len(assignments[c]) == 2],
        rnd
    )
    for c in third_general_targets:
        if general_pool:
            assignments[c].append(pop_random(general_pool, rnd))

    # 남은 구역
    leftover = leftover_core + general_pool

    # 이번 주 초고난도 담당 생활반 기록
    week_superhard = {
        c for c in class_names
        if any(a in super_hard_areas for a in assignments[c])
    }

    return assignments, week_superhard, leftover, severe_shortage, False


def distribute_5_weeks(capacities, initial_exempt_set=None, seed=None):
    """5주 배정"""
    rnd_master = random.Random(seed)
    weeks = []
    leftovers = []
    warnings = []

    prev = set(initial_exempt_set or set())
    all_zero_case = all(v == 0 for v in capacities.values())

    for i in range(5):
        rnd = random.Random(rnd_master.randint(0, 2**31 - 1))

        assgn, super_set, leftover, severe, _ = distribute_one_week(
            capacities,
            prev,
            rnd
        )

        weeks.append(assgn)
        leftovers.append(leftover)
        prev = super_set

        if severe and not all_zero_case:
            warnings.append("인원 부족으로 화장실/목욕탕을 2주 연속 청소하는 생활반이 등장할 수 있습니다.")

    # 표 만들기
    rows = []
    for c in class_names:
        row = {"생활반": c, "청소가능인원": capacities[c]}
        for i, w in enumerate(weeks, 1):
            row[f"{i}주차"] = ", ".join(w[c]) if w[c] else ""
        rows.append(row)

    # 마지막 줄: 아직 배정되지 못한 구역
    leftover_row = {"생활반": "인원 부족으로 배정되지 못한 청소구역", "청소가능인원": ""}
    for i, lst in enumerate(leftovers, 1):
        leftover_row[f"{i}주차"] = ", ".join(lst) if lst else ""
    rows.append(leftover_row)

    df = pd.DataFrame(rows)
    return df, warnings, all_zero_case


# -------------------------
# 화면
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
    cols = st.columns(3)
    for col, cname in zip(cols, class_names[i:i + 3]):
        cap_inputs[cname] = col.number_input(
            cname,
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

seed = st.text_input(
    "난수 시드(정수, 빈칸이면 무작위)",
    value="",
    help="같은 시드를 입력하면 같은 결과를 다시 얻을 수 있습니다."
)
seed_val = int(seed) if seed.isdigit() else None

if st.button("▶ 결과 생성"):
    capacities = {c: int(cap_inputs[c]) for c in class_names}
    df, warnings, all_zero_case = distribute_5_weeks(
        capacities,
        initial_exempt_set=set(initial_exempt),
        seed=seed_val
    )

    st.success("배정 완료. 결과를 확인하세요.")

    if all_zero_case:
        st.markdown("## 🐱 고양이 모드")
        st.markdown("모든 생활반이 0명입니다. 오늘은 고양이가 근무합니다. 🐾")

    for w in warnings:
        st.warning(w)

    st.header("배정 결과")
    st.dataframe(df, use_container_width=True, height=650)

    if st.checkbox("원시 배정 데이터 보기 (디버그)"):
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
