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
    if not pool:
        return None
    return pool.pop(rnd.randrange(len(pool)))


def shuffled(items, rnd):
    items = items[:]
    rnd.shuffle(items)
    return items


def assign_next_from_pool(targets, pool, assignments, rnd):
    for c in targets:
        if not pool:
            break
        assignments[c].append(pop_random(pool, rnd))


def distribute_one_week(capacities, exempt_superhard_set, rnd):
    assignments = {c: [] for c in class_names}

    super_pool = super_hard_areas.copy()
    hard_pool = hard_areas.copy()
    general_pool = general_areas_base.copy()

    nonzero = [c for c in class_names if capacities[c] > 0]

    if not nonzero:
        leftover = super_pool + hard_pool + general_pool
        return assignments, set(), leftover, False, True

    b_groups = [c for c in class_names if 1 <= capacities[c] <= 3]
    c_groups = [c for c in class_names if 4 <= capacities[c] <= 6]
    d_groups = [c for c in class_names if 7 <= capacities[c] <= 11]
    core_4_11 = c_groups + d_groups

    severe_shortage = len(nonzero) <= 8

    if severe_shortage:
        core_recipients = shuffled(nonzero, rnd)

        assign_next_from_pool(core_recipients, super_pool, assignments, rnd)
        assign_next_from_pool(
            [c for c in core_recipients if len(assignments[c]) == 0],
            hard_pool,
            assignments,
            rnd
        )

        leftover_core = super_pool + hard_pool

    else:
        if len(core_4_11) >= 9:
            core_recipients = rnd.sample(core_4_11, 9)
        else:
            need = 9 - len(core_4_11)
            core_recipients = core_4_11[:] + rnd.sample(b_groups, need)

        non_exempt = [c for c in core_recipients if c not in exempt_superhard_set]
        exempt = [c for c in core_recipients if c in exempt_superhard_set]

        assign_next_from_pool(shuffled(non_exempt, rnd), super_pool, assignments, rnd)
        assign_next_from_pool(shuffled(exempt, rnd), super_pool, assignments, rnd)

        remaining_core_targets = [c for c in core_recipients if len(assignments[c]) == 0]
        assign_next_from_pool(shuffled(remaining_core_targets, rnd), hard_pool, assignments, rnd)

        leftover_core = super_pool + hard_pool

    first_general_targets = [
        c for c in class_names
        if capacities[c] > 0 and len(assignments[c]) == 0
    ]
    assign_next_from_pool(shuffled(first_general_targets, rnd), general_pool, assignments, rnd)

    second_general_targets = [
        c for c in class_names
        if 4 <= capacities[c] <= 11 and len(assignments[c]) == 1
    ]
    assign_next_from_pool(shuffled(second_general_targets, rnd), general_pool, assignments, rnd)

    third_general_targets = [
        c for c in class_names
        if 7 <= capacities[c] <= 11 and len(assignments[c]) == 2
    ]
    assign_next_from_pool(shuffled(third_general_targets, rnd), general_pool, assignments, rnd)

    leftover = leftover_core + general_pool

    week_superhard = {
        c for c in class_names
        if any(a in super_hard_areas for a in assignments[c])
    }

    return assignments, week_superhard, leftover, severe_shortage, False


def distribute_5_weeks(capacities, first_week_exempt_set=None, seed=None):
    rnd_master = random.Random(seed)
    weeks = []
    leftovers = []

    warning_flag = False

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
            warning_flag = True

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

    return pd.DataFrame(rows), warning_flag, all_zero_case


# -------------------------
# 화면
# -------------------------
st.title("청소구역 배정 프로그램")

st.header("생활반 별 청소가능인원을 입력하십시오 (0~11)")
st.markdown(
    """
생활반 청소 가능 인원에 따라 배정되는 청소구역 수가 달라집니다.
 
1-3명: 쉬운 구역 1개  
4-6명: 구역 2개  
7-11명: 구역 3개  
화장실 및 목욕탕은 2주 연속 청소하지 않습니다.
"""
)


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
first_week_exempt = st.multiselect(
    "면제할 생활반 선택",
    class_names,
    default=[]
)

seed_input = st.text_input("난수 시드", value="")
seed_val = int(seed_input) if seed_input.isdigit() else None

if st.button("▶ 결과 생성"):
    capacities = {c: int(cap_inputs[c]) for c in class_names}
    df, warning_flag, all_zero_case = distribute_5_weeks(
        capacities,
        first_week_exempt_set=set(first_week_exempt),
        seed=seed_val
    )

    st.success("배정 완료. 결과를 확인하세요.")

    if all_zero_case:
        st.markdown("## 🐱")
        st.markdown("청소 인원이 부족하여 짬타이거가 청소합니다.")

    if warning_flag:
        st.warning("청소 인원이 매우 부족하여 2주 연속 화장실/목욕탕을 청소하는 생활반이 나올 수 있습니다.")

    st.header("배정 결과")

    # 초고난도 bold 처리
    html = df.to_html(escape=False, index=False)
    for area in super_hard_areas:
        html = html.replace(area, f"<b>{area}</b>")
    html = html.replace("<th>", '<th style="text-align:center;">')
    st.markdown(html, unsafe_allow_html=True)

st.markdown("---")
st.markdown("Python 코드로 만든 Streamlit 앱입니다.")

with st.expander("📄 현재 실행 중인 코드 보기"):
    try:
        with open(__file__, "r", encoding="utf-8") as f:
            st.code(f.read(), language="python", height=500)
    except Exception as e:
        st.error(str(e))
