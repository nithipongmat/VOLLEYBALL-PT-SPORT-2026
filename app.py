import streamlit as st
import json
import os
import time
import copy

# =========================================================
# AUTO REFRESH
# =========================================================

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="PT SPORT 2026 VOLLEYBALL SCORE",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# STATE FILE
# =========================================================

STATE_FILE = "match_state.json"


# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_MATCH_DATA = {

    # Competition
    "gender": "ผสม",
    "round_name": "รอบแบ่งกลุ่ม",
    "group_name": "สาย A",
    "match_no": "1",

    # Score
    "target_score_reg": 25,
    "target_score_tie": 15,

    # Teams
    "team_a": "ทีม A",
    "team_b": "ทีม B",

    # Scores
    "scores": [
        {"a": 0, "b": 0},
        {"a": 0, "b": 0},
        {"a": 0, "b": 0}
    ],

    # Current set
    "current_set": 0,

    # Serve
    "server": "a",

    # Scoreboard
    "swapped_sides": False,

    # Match timer
    "match_started": False,
    "match_paused": False,
    "start_time": None,
    "accumulated_time": 0,

    # Time-out
    "timeout_active": False,
    "timeout_team_name": "",
    "timeout_end_time": 0,

    # Undo
    "history": [],

    # Logs
    "logs": [],

    # Players
    #
    # IMPORTANT:
    #
    # index 0 = position 1
    # index 1 = position 2
    # index 2 = position 3
    # index 3 = position 4
    # index 4 = position 5
    # index 5 = position 6
    #
    "players_a_list": [
        "ตัวจริง A1",
        "ตัวจริง A2",
        "ตัวจริง A3",
        "ตัวจริง A4",
        "ตัวจริง A5",
        "ตัวจริง A6"
    ],

    "players_b_list": [
        "ตัวจริง B1",
        "ตัวจริง B2",
        "ตัวจริง B3",
        "ตัวจริง B4",
        "ตัวจริง B5",
        "ตัวจริง B6"
    ],

    # Bench
    "bench_a": [
        "สำรอง A1",
        "สำรอง A2",
        "สำรอง A3",
        "สำรอง A4",
        "สำรอง A5"
    ],

    "bench_b": [
        "สำรอง B1",
        "สำรอง B2",
        "สำรอง B3",
        "สำรอง B4",
        "สำรอง B5"
    ],

    # Archives
    "archives": []
}


# =========================================================
# LOAD / SAVE
# =========================================================

def load_shared_state():

    data = copy.deepcopy(DEFAULT_MATCH_DATA)

    if os.path.exists(STATE_FILE):

        try:

            with open(
                STATE_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                loaded = json.load(f)

                data.update(loaded)

        except Exception:
            pass

    return data


def save_shared_state(data):

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# SESSION STATE
# =========================================================

if "match_data" not in st.session_state:

    st.session_state.match_data = load_shared_state()


m = st.session_state.match_data


# =========================================================
# VIEW MODE
# =========================================================

query_params = st.query_params

is_scoreboard = (
    query_params.get("view") == "scoreboard"
)


# =========================================================
# SYNC
# =========================================================

def update_and_sync():

    save_shared_state(
        st.session_state.match_data
    )


# =========================================================
# LOG + SNAPSHOT
# =========================================================

def save_snapshot(action_text=""):

    m = st.session_state.match_data

    snapshot = {

        "scores":
            copy.deepcopy(m["scores"]),

        "current_set":
            m["current_set"],

        "server":
            m["server"],

        "swapped_sides":
            m["swapped_sides"],

        "players_a_list":
            copy.deepcopy(m["players_a_list"]),

        "players_b_list":
            copy.deepcopy(m["players_b_list"]),

        "bench_a":
            copy.deepcopy(m["bench_a"]),

        "bench_b":
            copy.deepcopy(m["bench_b"])

    }

    m["history"].append(snapshot)

    if len(m["history"]) > 50:
        m["history"].pop(0)

    if action_text:

        now_str = time.strftime("%H:%M:%S")

        m["logs"].insert(
            0,
            f"[{now_str}] {action_text}"
        )

        if len(m["logs"]) > 100:
            m["logs"].pop()


# =========================================================
# UNDO
# =========================================================

def undo_last_action():

    m = st.session_state.match_data

    if not m["history"]:
        return

    last_state = m["history"].pop()

    m["scores"] = last_state["scores"]

    m["current_set"] = (
        last_state["current_set"]
    )

    m["server"] = (
        last_state["server"]
    )

    m["swapped_sides"] = (
        last_state["swapped_sides"]
    )

    m["players_a_list"] = (
        last_state["players_a_list"]
    )

    m["players_b_list"] = (
        last_state["players_b_list"]
    )

    m["bench_a"] = (
        last_state["bench_a"]
    )

    m["bench_b"] = (
        last_state["bench_b"]
    )

    if m["logs"]:
        m["logs"].pop(0)

    update_and_sync()


# =========================================================
# SET WINNER
# =========================================================

def check_set_winner(
    score_a,
    score_b,
    target
):

    if (
        (score_a >= target or score_b >= target)
        and abs(score_a - score_b) >= 2
    ):

        if score_a > score_b:
            return "a"

        return "b"

    return None


# =========================================================
# SETS WON
# =========================================================

def calculate_sets_won():

    m = st.session_state.match_data

    sets_a = 0
    sets_b = 0

    for i in range(3):

        target = (
            m["target_score_reg"]
            if i < 2
            else m["target_score_tie"]
        )

        winner = check_set_winner(
            m["scores"][i]["a"],
            m["scores"][i]["b"],
            target
        )

        if winner == "a":
            sets_a += 1

        elif winner == "b":
            sets_b += 1

    return sets_a, sets_b


# =========================================================
# ROTATION
# =========================================================
#
# ตำแหน่งจริง:
#
#        NET
#
#   5          4
#
#   6          3
#
#   1          2
#
#
# หมุนตามเข็ม:
#
#   1 → 6
#   6 → 5
#   5 → 4
#   4 → 3
#   3 → 2
#   2 → 1
#
# ดังนั้น:
#
# [1,2,3,4,5,6]
#
# →
#
# [2,3,4,5,6,1]
#
# =========================================================

def rotate_team_cw(team_key):

    m = st.session_state.match_data

    if team_key == "a":

        plist = m["players_a_list"]

    else:

        plist = m["players_b_list"]

    old = plist.copy()

    plist[0] = old[1]   # 2 → 1
    plist[1] = old[2]   # 3 → 2
    plist[2] = old[3]   # 4 → 3
    plist[3] = old[4]   # 5 → 4
    plist[4] = old[5]   # 6 → 5
    plist[5] = old[0]   # 1 → 6


# =========================================================
# RESET POSITIONS
# =========================================================

def reset_positions():

    m = st.session_state.match_data

    save_snapshot(
        "รีเซ็ตตำแหน่งผู้เล่น"
    )

    m["players_a_list"] = [
        f"ตัวจริง A{i+1}"
        for i in range(6)
    ]

    m["players_b_list"] = [
        f"ตัวจริง B{i+1}"
        for i in range(6)
    ]

    update_and_sync()


# =========================================================
# GET COURT
# =========================================================

def get_current_court(team_key):

    m = st.session_state.match_data

    if team_key == "a":

        plist = m["players_a_list"]

    else:

        plist = m["players_b_list"]

    return {

        "1": plist[0],
        "2": plist[1],
        "3": plist[2],
        "4": plist[3],
        "5": plist[4],
        "6": plist[5]

    }


# =========================================================
# SUBSTITUTION
# =========================================================

def substitute_player(
    team_key,
    main_idx,
    bench_idx
):

    m = st.session_state.match_data

    if team_key == "a":

        plist = m["players_a_list"]
        blist = m["bench_a"]
        team_name = m["team_a"]

    else:

        plist = m["players_b_list"]
        blist = m["bench_b"]
        team_name = m["team_b"]

    out_player = plist[main_idx]
    in_player = blist[bench_idx]

    plist[main_idx] = in_player
    blist[bench_idx] = out_player

    save_snapshot(
        f"{team_name} เปลี่ยนตัว: "
        f"{in_player} เข้า / "
        f"{out_player} ออก"
    )

    update_and_sync()


# =========================================================
# ADD SCORE
# =========================================================

def add_score(team):

    m = st.session_state.match_data

    # ตรวจว่าการแข่งขันจบแล้วหรือยัง
    sets_a, sets_b = calculate_sets_won()

    if sets_a >= 2 or sets_b >= 2:
        return

    curr_set = m["current_set"]

    if curr_set >= 3:
        return

    team_name = (
        m["team_a"]
        if team == "a"
        else m["team_b"]
    )

    # Snapshot ก่อนเปลี่ยนข้อมูล
    save_snapshot(
        f"{team_name} ได้คะแนน (+1)"
    )

    # =====================================================
    # SIDE-OUT
    # =====================================================
    #
    # ถ้าทีมที่ได้แต้มไม่ได้เป็นฝ่ายเสิร์ฟ
    #
    # → ได้สิทธิ์เสิร์ฟ
    # → หมุนตามเข็มนาฬิกา 1 ตำแหน่ง
    # → คนใหม่ที่ตำแหน่ง 1 เสิร์ฟ
    #
    # ถ้าเป็นฝ่ายเสิร์ฟอยู่แล้ว
    #
    # → ไม่หมุน
    #
    # =====================================================

    if m["server"] != team:

        m["server"] = team

        rotate_team_cw(team)

        st.toast(
            f"🏐 {team_name} ได้สิทธิ์เสิร์ฟ + หมุนตำแหน่ง",
            icon="🔄"
        )

    # เพิ่มคะแนน
    m["scores"][curr_set][team] += 1

    # =====================================================
    # CHECK SET
    # =====================================================

    target = (
        m["target_score_reg"]
        if curr_set < 2
        else m["target_score_tie"]
    )

    score_a = m["scores"][curr_set]["a"]
    score_b = m["scores"][curr_set]["b"]

    winner = check_set_winner(
        score_a,
        score_b,
        target
    )

    if winner:

        new_sets_a, new_sets_b = calculate_sets_won()

        winner_name = (
            m["team_a"]
            if winner == "a"
            else m["team_b"]
        )

        m["logs"].insert(
            0,
            f"[{time.strftime('%H:%M:%S')}] "
            f"🏆 {winner_name} ชนะ SET {curr_set + 1}"
        )

        # Match ยังไม่จบ → ไปเซตต่อไป
        if (
            new_sets_a < 2
            and new_sets_b < 2
            and curr_set < 2
        ):

            m["current_set"] += 1

            # หมายเหตุ:
            # server ยังคงเป็นทีมเดิม
            # เพราะสิทธิ์เสิร์ฟของจังหวะสุดท้าย
            # เป็นข้อมูลสำคัญสำหรับการเริ่มเซต
            #
            # หากการแข่งขันของงานต้องกำหนดผู้เสิร์ฟ
            # ใหม่ทุกเซต สามารถเพิ่มตัวเลือกได้ภายหลัง

        update_and_sync()

        return

    update_and_sync()


# =========================================================
# SUBTRACT SCORE
# =========================================================

def subtract_score(team):

    m = st.session_state.match_data

    curr_set = m["current_set"]

    if curr_set >= 3:
        return

    if m["scores"][curr_set][team] <= 0:
        return

    team_name = (
        m["team_a"]
        if team == "a"
        else m["team_b"]
    )

    save_snapshot(
        f"{team_name} ลดคะแนน (-1)"
    )

    m["scores"][curr_set][team] -= 1

    update_and_sync()


# =========================================================
# TIMEOUT
# =========================================================

def trigger_timeout(team_key):

    m = st.session_state.match_data

    team_name = (
        m["team_a"]
        if team_key == "a"
        else m["team_b"]
    )

    save_snapshot(
        f"{team_name} ขอเวลานอก"
    )

    m["timeout_active"] = True

    m["timeout_team_name"] = team_name

    m["timeout_end_time"] = (
        time.time() + 30
    )

    update_and_sync()


# =========================================================
# ARCHIVE
# =========================================================

def save_current_match_to_archive():

    m = st.session_state.match_data

    sets_a, sets_b = calculate_sets_won()

    if sets_a > sets_b:

        winner_name = m["team_a"]

    elif sets_b > sets_a:

        winner_name = m["team_b"]

    else:

        winner_name = "เสมอ/ยังไม่จบ"

    record = {

        "timestamp":
            time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "match_no":
            m["match_no"],

        "round_name":
            m["round_name"],

        "group_name":
            m["group_name"],

        "gender":
            m["gender"],

        "team_a":
            m["team_a"],

        "team_b":
            m["team_b"],

        "sets_a":
            sets_a,

        "sets_b":
            sets_b,

        "scores":
            copy.deepcopy(
                m["scores"]
            ),

        "winner":
            winner_name
    }

    m["archives"].insert(
        0,
        record
    )


# =========================================================
# NEW MATCH
# =========================================================

def start_new_match():

    m = st.session_state.match_data

    save_current_match_to_archive()

    try:

        next_no = str(
            int(m["match_no"]) + 1
        )

    except Exception:

        next_no = (
            m["match_no"] + " (ใหม่)"
        )

    m["match_no"] = next_no

    m["team_a"] = (
        f"ทีม A (คู่ที่ {next_no})"
    )

    m["team_b"] = (
        f"ทีม B (คู่ที่ {next_no})"
    )

    m["scores"] = [
        {"a": 0, "b": 0},
        {"a": 0, "b": 0},
        {"a": 0, "b": 0}
    ]

    m["current_set"] = 0

    m["server"] = "a"

    m["swapped_sides"] = False

    m["history"] = []

    m["logs"] = []

    m["match_started"] = False

    m["match_paused"] = False

    m["accumulated_time"] = 0

    m["start_time"] = None

    m["timeout_active"] = False

    m["timeout_team_name"] = ""

    m["timeout_end_time"] = 0

    m["players_a_list"] = [
        f"ตัวจริง A{i+1}"
        for i in range(6)
    ]

    m["players_b_list"] = [
        f"ตัวจริง B{i+1}"
        for i in range(6)
    ]

    update_and_sync()


# =========================================================
# CURRENT MATCH WINNER
# =========================================================

sets_won_a, sets_won_b = calculate_sets_won()

match_winner = None

if sets_won_a >= 2:

    match_winner = m["team_a"]

elif sets_won_b >= 2:

    match_winner = m["team_b"]


# =========================================================
# =========================================================
# SCOREBOARD MODE
# =========================================================
# =========================================================

if is_scoreboard:

    if HAS_AUTOREFRESH:

        st_autorefresh(
            interval=1000,
            key="scoreboard_tick"
        )

    m = load_shared_state()

    curr_set = m["current_set"]

    # ป้องกัน index
    if curr_set > 2:
        curr_set = 2

    # =====================================================
    # SIDE SWAP
    # =====================================================

    if m.get("swapped_sides", False):

        left_team = "b"
        right_team = "a"

        left_name = m["team_b"]
        right_name = m["team_a"]

        left_score = (
            m["scores"][curr_set]["b"]
        )

        right_score = (
            m["scores"][curr_set]["a"]
        )

        left_color = "#ea580c"
        right_color = "#2563eb"

    else:

        left_team = "a"
        right_team = "b"

        left_name = m["team_a"]
        right_name = m["team_b"]

        left_score = (
            m["scores"][curr_set]["a"]
        )

        right_score = (
            m["scores"][curr_set]["b"]
        )

        left_color = "#2563eb"
        right_color = "#ea580c"


    # =====================================================
    # TIMEOUT OVERLAY
    # =====================================================

    if m.get("timeout_active", False):

        rem_timeout = int(
            m["timeout_end_time"]
            - time.time()
        )

        if rem_timeout <= 0:

            m["timeout_active"] = False

            save_shared_state(m)

        else:

            st.markdown(
                f"""
                <div style="
                    position:fixed;
                    top:0;
                    left:0;
                    width:100vw;
                    height:100vh;
                    background:#0f172a;
                    z-index:99999;
                    display:flex;
                    flex-direction:column;
                    align-items:center;
                    justify-content:center;
                    color:white;
                ">

                    <div style="
                        font-size:40px;
                        font-weight:bold;
                        color:#f59e0b;
                    ">
                        ⏱️ TIME-OUT
                    </div>

                    <div style="
                        font-size:50px;
                        font-weight:bold;
                        background:#1e293b;
                        padding:15px 40px;
                        border-radius:15px;
                        border:3px solid #f59e0b;
                        margin:20px 0;
                    ">
                        {m["timeout_team_name"]}
                    </div>

                    <div style="
                        font-size:160px;
                        font-weight:bold;
                        color:#ef4444;
                    ">
                        {rem_timeout:02d}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )


    # =====================================================
    # MATCH TIMER
    # =====================================================

    if (
        m["match_started"]
        and not m.get("match_paused", False)
    ):

        elapsed_sec = int(
            m.get("accumulated_time", 0)
            +
            (
                time.time()
                - m["start_time"]
            )
        )

        status_badge = "🔴 LIVE"
        status_color = "#ef4444"

    elif m.get("match_paused", False):

        elapsed_sec = int(
            m.get("accumulated_time", 0)
        )

        status_badge = "⏸️ พักเวลา"
        status_color = "#f59e0b"

    else:

        elapsed_sec = 0

        status_badge = "⏹️ รอเริ่มแข่ง"
        status_color = "#64748b"


    time_str = time.strftime(
        "%H:%M:%S",
        time.gmtime(elapsed_sec)
    )


    # =====================================================
    # HEADER
    # =====================================================

    st.markdown(
        f"""
        <h1 style="
            text-align:center;
            font-size:40px;
            margin-bottom:0;
        ">
            PT SPORT 2026
            <br>
            <span style="font-size:25px;">
                คู่ที่ {m["match_no"]}
                -
                {m["round_name"]}
                {m["group_name"]}
            </span>
        </h1>
        """,
        unsafe_allow_html=True
    )


    serve_left = (
        " 🏐"
        if m["server"] == left_team
        else ""
    )

    serve_right = (
        " 🏐"
        if m["server"] == right_team
        else ""
    )


    team_head_col1, vs_col, team_head_col2 = st.columns(
        [5, 2, 5]
    )


    with team_head_col1:

        st.markdown(
            f"""
            <div style="
                border:3px solid white;
                border-radius:12px;
                padding:12px;
                text-align:center;
                font-size:32px;
                font-weight:bold;
            ">
                {left_name}
                {serve_left}
            </div>
            """,
            unsafe_allow_html=True
        )


    with vs_col:

        st.markdown(
            """
            <h1 style="
                text-align:center;
                margin:0;
                font-size:40px;
            ">
                VS
            </h1>
            """,
            unsafe_allow_html=True
        )


    with team_head_col2:

        st.markdown(
            f"""
            <div style="
                border:3px solid white;
                border-radius:12px;
                padding:12px;
                text-align:center;
                font-size:32px;
                font-weight:bold;
            ">
                {right_name}
                {serve_right}
            </div>
            """,
            unsafe_allow_html=True
        )


    st.markdown("<br>", unsafe_allow_html=True)


    # =====================================================
    # SCORE
    # =====================================================

    sc_left, sc_center, sc_right = st.columns(
        [4, 3, 4]
    )


    with sc_left:

        st.markdown(
            f"""
            <div style="
                border:4px solid white;
                border-radius:20px;
                padding:20px;
                text-align:center;
                background:#0f172a;
            ">
                <div style="
                    font-size:160px;
                    color:{left_color};
                    font-weight:bold;
                ">
                    {left_score:02d}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


    with sc_center:

        st.markdown(
            f"""
            <div style="
                border:2px solid white;
                border-radius:10px;
                padding:8px;
                text-align:center;
                font-size:26px;
                font-weight:bold;
                background:#1e293b;
                margin-bottom:15px;
            ">
                <span style="
                    color:{status_color};
                    font-size:16px;
                ">
                    {status_badge}
                </span>
                ⏱️ {time_str}
            </div>
            """,
            unsafe_allow_html=True
        )


        for s_idx in range(3):

            s_left = (
                m["scores"][s_idx][left_team]
            )

            s_right = (
                m["scores"][s_idx][right_team]
            )

            is_active = (
                s_idx == curr_set
            )

            border = (
                "3px solid #f59e0b"
                if is_active
                else "1px solid #64748b"
            )

            bg = (
                "#2563eb"
                if is_active
                else "#334155"
            )

            st.markdown(
                f"""
                <div style="
                    border:{border};
                    border-radius:8px;
                    padding:6px;
                    text-align:center;
                    background:{bg};
                    margin-bottom:8px;
                ">
                    <div style="
                        font-size:14px;
                    ">
                        SET {s_idx + 1}
                    </div>

                    <div style="
                        font-size:22px;
                        font-weight:bold;
                    ">
                        {s_left} - {s_right}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


    with sc_right:

        st.markdown(
            f"""
            <div style="
                border:4px solid white;
                border-radius:20px;
                padding:20px;
                text-align:center;
                background:#0f172a;
            ">
                <div style="
                    font-size:160px;
                    color:{right_color};
                    font-weight:bold;
                ">
                    {right_score:02d}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


    st.stop()


# =========================================================
# =========================================================
# CONTROLLER
# =========================================================
# =========================================================

if HAS_AUTOREFRESH:

    st_autorefresh(
        interval=1000,
        key="controller_tick"
    )


st.title(
    f"🏐 PT SPORT 2026 CONTROLLER "
    f"(คู่ที่ {m['match_no']})"
)


st.markdown(
    f"""
    ### 📌 กำลังแข่ง:
    **SET {m["current_set"] + 1}**
    |
    เป้าหมาย
    **{
        m["target_score_reg"]
        if m["current_set"] < 2
        else m["target_score_tie"]
    } คะแนน**
    """
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header(
        "⚙️ ตั้งค่าการแข่งขัน"
    )


    m["gender"] = st.radio(
        "ประเภท",
        ["ชาย", "หญิง", "ผสม"],
        horizontal=True,
        index=[
            "ชาย",
            "หญิง",
            "ผสม"
        ].index(m["gender"])
    )


    m["round_name"] = st.text_input(
        "รอบ",
        m["round_name"]
    )


    m["group_name"] = st.text_input(
        "สาย",
        m["group_name"]
    )


    m["match_no"] = st.text_input(
        "คู่ที่",
        m["match_no"]
    )


    m["target_score_reg"] = st.number_input(
        "คะแนนเซตปกติ",
        min_value=1,
        value=m["target_score_reg"]
    )


    m["target_score_tie"] = st.number_input(
        "คะแนนเซตตัดสิน",
        min_value=1,
        value=m["target_score_tie"]
    )


    m["team_a"] = st.text_input(
        "ชื่อทีม A",
        m["team_a"]
    )


    m["team_b"] = st.text_input(
        "ชื่อทีม B",
        m["team_b"]
    )


    st.markdown("---")


    # =====================================================
    # PLAYERS A
    # =====================================================

    with st.expander(
        f"👕 ผู้เล่น {m['team_a']}"
    ):

        st.markdown(
            "**ตัวจริง — ตำแหน่ง 1-6**"
        )

        for idx in range(6):

            m["players_a_list"][idx] = st.text_input(
                f"ตำแหน่ง {idx + 1}",
                m["players_a_list"][idx],
                key=f"main_a_{idx}"
            )


        st.markdown("**ตัวสำรอง**")

        for idx in range(
            len(m["bench_a"])
        ):

            m["bench_a"][idx] = st.text_input(
                f"สำรอง {idx + 1}",
                m["bench_a"][idx],
                key=f"bench_a_{idx}"
            )


    # =====================================================
    # PLAYERS B
    # =====================================================

    with st.expander(
        f"👕 ผู้เล่น {m['team_b']}"
    ):

        st.markdown(
            "**ตัวจริง — ตำแหน่ง 1-6**"
        )

        for idx in range(6):

            m["players_b_list"][idx] = st.text_input(
                f"ตำแหน่ง {idx + 1}",
                m["players_b_list"][idx],
                key=f"main_b_{idx}"
            )


        st.markdown("**ตัวสำรอง**")

        for idx in range(
            len(m["bench_b"])
        ):

            m["bench_b"][idx] = st.text_input(
                f"สำรอง {idx + 1}",
                m["bench_b"][idx],
                key=f"bench_b_{idx}"
            )


    if st.button(
        "💾 บันทึกข้อมูล",
        type="primary",
        use_container_width=True
    ):

        update_and_sync()

        st.success(
            "บันทึกข้อมูลเรียบร้อย"
        )


# =========================================================
# MATCH CONTROL
# =========================================================

start_col1, start_col2, start_col3, start_col4, start_col5 = st.columns(
    [2, 1.2, 1.2, 1.2, 2.2]
)


# START / RESUME

with start_col1:

    if not m["match_started"]:

        if st.button(
            "▶️ เริ่มเวลาแข่ง",
            type="primary",
            use_container_width=True
        ):

            m["match_started"] = True

            m["match_paused"] = False

            m["start_time"] = time.time()

            m["accumulated_time"] = 0

            save_snapshot(
                "เริ่มเวลาแข่งขัน"
            )

            update_and_sync()

            st.rerun()


    elif m.get("match_paused", False):

        if st.button(
            "▶️ เดินเวลาต่อ",
            type="primary",
            use_container_width=True
        ):

            m["match_paused"] = False

            m["start_time"] = time.time()

            save_snapshot(
                "เดินเวลาต่อ"
            )

            update_and_sync()

            st.rerun()


    else:

        elapsed = int(
            m.get("accumulated_time", 0)
            +
            (
                time.time()
                - m["start_time"]
            )
        )

        st.success(
            "🔴 LIVE "
            +
            time.strftime(
                "%H:%M:%S",
                time.gmtime(elapsed)
            )
        )


# PAUSE

with start_col2:

    if (
        m["match_started"]
        and not m.get("match_paused", False)
    ):

        if st.button(
            "⏸️ พักเวลา",
            use_container_width=True
        ):

            m["match_paused"] = True

            m["accumulated_time"] += (
                time.time()
                - m["start_time"]
            )

            save_snapshot(
                "พักเวลาแข่งขัน"
            )

            update_and_sync()

            st.rerun()


# RESET TIME

with start_col3:

    if st.button(
        "🔄 รีเซ็ตเวลา",
        use_container_width=True
    ):

        m["match_started"] = False

        m["match_paused"] = False

        m["accumulated_time"] = 0

        m["start_time"] = None

        update_and_sync()

        st.rerun()


# UNDO

with start_col4:

    if st.button(
        "↩️ เลิกทำ",
        use_container_width=True
    ):

        undo_last_action()

        st.rerun()


# NEW MATCH

with start_col5:

    if st.button(
        "➕ บันทึกผล + คู่ถัดไป",
        type="primary",
        use_container_width=True
    ):

        start_new_match()

        st.rerun()


# =========================================================
# SCORE
# =========================================================

st.markdown("---")

curr_set = m["current_set"]

col1, col2 = st.columns(2)


# =========================================================
# TEAM A
# =========================================================

with col1:

    t_name = m["team_a"]

    with st.container(border=True):

        st.markdown(
            f"""
            ### {t_name}
            {"🏐 กำลังเสิร์ฟ"
             if m["server"] == "a"
             else ""}
            """
        )


        st.markdown(
            f"""
            <h1 style="
                text-align:center;
                font-size:80px;
                margin:0;
            ">
                {m["scores"][curr_set]["a"]}
            </h1>
            """,
            unsafe_allow_html=True
        )


        b1, b2 = st.columns(2)


        with b1:

            if st.button(
                f"➕ ได้คะแนน ({t_name})",
                use_container_width=True,
                type="primary",
                key="add_a"
            ):

                add_score("a")

                st.rerun()


        with b2:

            if st.button(
                f"➖ ลดคะแนน ({t_name})",
                use_container_width=True,
                key="sub_a"
            ):

                subtract_score("a")

                st.rerun()


        b3, b4 = st.columns(2)


        with b3:

            if st.button(
                f"🔄 หมุนตำแหน่ง ({t_name})",
                use_container_width=True,
                key="rot_a"
            ):

                save_snapshot(
                    f"{t_name} หมุนตำแหน่งด้วยมือ"
                )

                rotate_team_cw("a")

                update_and_sync()

                st.rerun()


        with b4:

            if st.button(
                f"🏐 กำหนดเสิร์ฟ ({t_name})",
                use_container_width=True,
                key="serve_a"
            ):

                save_snapshot(
                    f"กำหนดให้ {t_name} เสิร์ฟ"
                )

                m["server"] = "a"

                update_and_sync()

                st.rerun()


# =========================================================
# TEAM B
# =========================================================

with col2:

    t_name = m["team_b"]

    with st.container(border=True):

        st.markdown(
            f"""
            ### {t_name}
            {"🏐 กำลังเสิร์ฟ"
             if m["server"] == "b"
             else ""}
            """
        )


        st.markdown(
            f"""
            <h1 style="
                text-align:center;
                font-size:80px;
                margin:0;
            ">
                {m["scores"][curr_set]["b"]}
            </h1>
            """,
            unsafe_allow_html=True
        )


        b1, b2 = st.columns(2)


        with b1:

            if st.button(
                f"➕ ได้คะแนน ({t_name})",
                use_container_width=True,
                type="primary",
                key="add_b"
            ):

                add_score("b")

                st.rerun()


        with b2:

            if st.button(
                f"➖ ลดคะแนน ({t_name})",
                use_container_width=True,
                key="sub_b"
            ):

                subtract_score("b")

                st.rerun()


        b3, b4 = st.columns(2)


        with b3:

            if st.button(
                f"🔄 หมุนตำแหน่ง ({t_name})",
                use_container_width=True,
                key="rot_b"
            ):

                save_snapshot(
                    f"{t_name} หมุนตำแหน่งด้วยมือ"
                )

                rotate_team_cw("b")

                update_and_sync()

                st.rerun()


        with b4:

            if st.button(
                f"🏐 กำหนดเสิร์ฟ ({t_name})",
                use_container_width=True,
                key="serve_b"
            ):

                save_snapshot(
                    f"กำหนดให้ {t_name} เสิร์ฟ"
                )

                m["server"] = "b"

                update_and_sync()

                st.rerun()


# =========================================================
# TIMEOUT / COURT
# =========================================================

st.markdown("<br>", unsafe_allow_html=True)

st.subheader(
    "⏱️ เวลานอก & การจัดการสนาม"
)


to_col1, to_col2, to_col3, to_col4 = st.columns(4)


with to_col1:

    if st.button(
        f"⏱️ เวลานอก ({m['team_a']})",
        use_container_width=True,
        key="timeout_a"
    ):

        trigger_timeout("a")

        st.rerun()


with to_col2:

    if st.button(
        f"⏱️ เวลานอก ({m['team_b']})",
        use_container_width=True,
        key="timeout_b"
    ):

        trigger_timeout("b")

        st.rerun()


with to_col3:

    if st.button(
        "🔄 สลับฝั่งบอร์ด",
        use_container_width=True
    ):

        m["swapped_sides"] = (
            not m.get(
                "swapped_sides",
                False
            )
        )

        update_and_sync()

        st.rerun()


with to_col4:

    if st.button(
        "🔄 รีเซ็ตตำแหน่ง",
        use_container_width=True
    ):

        reset_positions()

        st.rerun()


# =========================================================
# TIMEOUT DISPLAY
# =========================================================

if m.get("timeout_active", False):

    rem_timeout = int(
        m["timeout_end_time"]
        - time.time()
    )

    if rem_timeout <= 0:

        m["timeout_active"] = False

        update_and_sync()

    else:

        st.markdown(
            f"""
            <div style="
                background:#7f1d1d;
                border:2px solid #ef4444;
                border-radius:10px;
                padding:15px;
                margin-top:15px;
                text-align:center;
                color:white;
            ">

                <div style="
                    font-size:20px;
                    font-weight:bold;
                    color:#f59e0b;
                ">
                    ⏱️ กำลังขอเวลานอก:
                    {m["timeout_team_name"]}
                </div>

                <div style="
                    font-size:48px;
                    font-weight:bold;
                    color:#ef4444;
                ">
                    {rem_timeout:02d}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# COURT
# =========================================================

st.markdown("---")

st.subheader(
    "🏐 ผังตำแหน่งผู้เล่น"
)


def render_player_box(
    pos_num,
    player_name,
    is_server=False
):

    border_color = (
        "#f59e0b"
        if is_server
        else "#475569"
    )

    serve_tag = (
        " 🏐 เสิร์ฟ"
        if is_server
        else ""
    )

    return f"""
    <div style="
        border:2px solid {border_color};
        border-radius:8px;
        padding:8px;
        text-align:center;
        background:#1e293b;
        margin-bottom:6px;
    ">

        <div style="
            font-size:12px;
            color:#f59e0b;
            font-weight:bold;
        ">
            ตำแหน่ง {pos_num}
            {serve_tag}
        </div>

        <div style="
            font-size:18px;
            font-weight:bold;
            color:white;
        ">
            {player_name}
        </div>

    </div>
    """


field_col1, field_col2 = st.columns(2)


court_a = get_current_court("a")
court_b = get_current_court("b")


# =========================================================
# TEAM A COURT
# =========================================================

with field_col1:

    st.markdown(
        f"""
        ### {m["team_a"]}
        {"🏐" if m["server"] == "a" else ""}
        """
    )


    # 5 | 4
    r1_1, r1_2 = st.columns(2)

    with r1_1:

        st.markdown(
            render_player_box(
                "5",
                court_a["5"]
            ),
            unsafe_allow_html=True
        )

    with r1_2:

        st.markdown(
            render_player_box(
                "4",
                court_a["4"]
            ),
            unsafe_allow_html=True
        )


    # 6 | 3
    r2_1, r2_2 = st.columns(2)

    with r2_1:

        st.markdown(
            render_player_box(
                "6",
                court_a["6"]
            ),
            unsafe_allow_html=True
        )

    with r2_2:

        st.markdown(
            render_player_box(
                "3",
                court_a["3"]
            ),
            unsafe_allow_html=True
        )


    # 1 | 2
    r3_1, r3_2 = st.columns(2)

    with r3_1:

        st.markdown(
            render_player_box(
                "1",
                court_a["1"],
                m["server"] == "a"
            ),
            unsafe_allow_html=True
        )

    with r3_2:

        st.markdown(
            render_player_box(
                "2",
                court_a["2"]
            ),
            unsafe_allow_html=True
        )


    # =====================================================
    # SUB A
    # =====================================================

    with st.expander(
        f"🔄 เปลี่ยนตัว ({m['team_a']})"
    ):

        sub_c1, sub_c2, sub_c3 = st.columns(
            [3, 3, 2]
        )


        with sub_c1:

            sel_main_a = st.selectbox(
                "ตัวจริงที่จะออก",
                [
                    f"ตำแหน่ง {i+1}: {p}"
                    for i, p
                    in enumerate(
                        m["players_a_list"]
                    )
                ],
                key="select_main_a"
            )


        with sub_c2:

            sel_bench_a = st.selectbox(
                "ตัวสำรองที่จะเข้า",
                [
                    f"สำรอง {i+1}: {p}"
                    for i, p
                    in enumerate(
                        m["bench_a"]
                    )
                ],
                key="select_bench_a"
            )


        with sub_c3:

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                "ยืนยัน",
                key="confirm_sub_a",
                type="primary",
                use_container_width=True
            ):

                main_idx = int(
                    sel_main_a
                    .split(":")[0]
                    .replace(
                        "ตำแหน่ง ",
                        ""
                    )
                ) - 1

                bench_idx = int(
                    sel_bench_a
                    .split(":")[0]
                    .replace(
                        "สำรอง ",
                        ""
                    )
                ) - 1

                substitute_player(
                    "a",
                    main_idx,
                    bench_idx
                )

                st.rerun()


# =========================================================
# TEAM B COURT
# =========================================================

with field_col2:

    st.markdown(
        f"""
        ### {m["team_b"]}
        {"🏐" if m["server"] == "b" else ""}
        """
    )


    # 2 | 1
    r1_1, r1_2 = st.columns(2)

    with r1_1:

        st.markdown(
            render_player_box(
                "2",
                court_b["2"]
            ),
            unsafe_allow_html=True
        )

    with r1_2:

        st.markdown(
            render_player_box(
                "1",
                court_b["1"],
                m["server"] == "b"
            ),
            unsafe_allow_html=True
        )


    # 3 | 6
    r2_1, r2_2 = st.columns(2)

    with r2_1:

        st.markdown(
            render_player_box(
                "3",
                court_b["3"]
            ),
            unsafe_allow_html=True
        )

    with r2_2:

        st.markdown(
            render_player_box(
                "6",
                court_b["6"]
            ),
            unsafe_allow_html=True
        )


    # 4 | 5
    r3_1, r3_2 = st.columns(2)

    with r3_1:

        st.markdown(
            render_player_box(
                "4",
                court_b["4"]
            ),
            unsafe_allow_html=True
        )

    with r3_2:

        st.markdown(
            render_player_box(
                "5",
                court_b["5"]
            ),
            unsafe_allow_html=True
        )


    # =====================================================
    # SUB B
    # =====================================================

    with st.expander(
        f"🔄 เปลี่ยนตัว ({m['team_b']})"
    ):

        sub_c1, sub_c2, sub_c3 = st.columns(
            [3, 3, 2]
        )


        with sub_c1:

            sel_main_b = st.selectbox(
                "ตัวจริงที่จะออก",
                [
                    f"ตำแหน่ง {i+1}: {p}"
                    for i, p
                    in enumerate(
                        m["players_b_list"]
                    )
                ],
                key="select_main_b"
            )


        with sub_c2:

            sel_bench_b = st.selectbox(
                "ตัวสำรองที่จะเข้า",
                [
                    f"สำรอง {i+1}: {p}"
                    for i, p
                    in enumerate(
                        m["bench_b"]
                    )
                ],
                key="select_bench_b"
            )


        with sub_c3:

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                "ยืนยัน",
                key="confirm_sub_b",
                type="primary",
                use_container_width=True
            ):

                main_idx = int(
                    sel_main_b
                    .split(":")[0]
                    .replace(
                        "ตำแหน่ง ",
                        ""
                    )
                ) - 1

                bench_idx = int(
                    sel_bench_b
                    .split(":")[0]
                    .replace(
                        "สำรอง ",
                        ""
                    )
                ) - 1

                substitute_player(
                    "b",
                    main_idx,
                    bench_idx
                )

                st.rerun()


# =========================================================
# MATCH SUMMARY
# =========================================================

st.markdown("---")

hist_col1, hist_col2 = st.columns(2)


# =========================================================
# SET SUMMARY
# =========================================================

with hist_col1:

    st.subheader(
        f"📊 ผลคู่ปัจจุบัน "
        f"(คู่ที่ {m['match_no']})"
    )


    sets_won_a, sets_won_b = calculate_sets_won()


    for idx in range(3):

        sa = m["scores"][idx]["a"]

        sb = m["scores"][idx]["b"]

        target = (
            m["target_score_reg"]
            if idx < 2
            else m["target_score_tie"]
        )

        winner = check_set_winner(
            sa,
            sb,
            target
        )


        if idx == curr_set:

            status = "กำลังแข่ง"

        elif winner:

            status = "จบแล้ว"

        else:

            status = "ยังไม่เริ่ม"


        winner_text = ""

        if winner:

            winner_text = (
                "🏆 "
                +
                (
                    m["team_a"]
                    if winner == "a"
                    else m["team_b"]
                )
            )


        st.info(
            f"**SET {idx + 1}** "
            f"({status}) : "
            f"**{m['team_a']}** "
            f"{sa} - {sb} "
            f"**{m['team_b']}** "
            f"{winner_text}"
        )


    st.markdown(
        f"""
        ### 🏆 ผลรวม
        **{m["team_a"]}**
        {sets_won_a}
        -
        {sets_won_b}
        **{m["team_b"]}**
        """
    )


# =========================================================
# LOG
# =========================================================

with hist_col2:

    st.subheader(
        "📜 ประวัติเหตุการณ์"
    )


    if m.get("logs"):

        st.text_area(
            "เหตุการณ์ล่าสุด",
            value="\n".join(
                m["logs"]
            ),
            height=220,
            disabled=True
        )

    else:

        st.info(
            "ยังไม่มีประวัติ"
        )


# =========================================================
# ARCHIVE
# =========================================================

st.markdown("---")

st.subheader(
    "📚 ประวัติการแข่งขัน"
)


if m.get("archives"):

    for idx, rec in enumerate(
        m["archives"]
    ):

        title = (
            f"📁 คู่ที่ {rec['match_no']}: "
            f"{rec['team_a']} vs "
            f"{rec['team_b']} "
            f"({rec['sets_a']} - "
            f"{rec['sets_b']} เซต) "
            f"🏆 {rec['winner']}"
        )


        with st.expander(title):

            st.write(
                f"บันทึก: {rec['timestamp']}"
            )

            st.write(
                f"ประเภท: {rec['gender']}"
            )

            st.write(
                f"รอบ: {rec['round_name']} "
                f"{rec['group_name']}"
            )


            st.markdown(
                "### คะแนนแต่ละเซต"
            )


            for s in range(3):

                st.write(
                    f"SET {s+1}: "
                    f"{rec['team_a']} "
                    f"{rec['scores'][s]['a']} - "
                    f"{rec['scores'][s]['b']} "
                    f"{rec['team_b']}"
                )


            e1, e2 = st.columns(2)


            with e1:

                edit_a = st.text_input(
                    "ชื่อทีม A",
                    rec["team_a"],
                    key=f"arc_a_{idx}"
                )


                edit_sa = st.number_input(
                    "เซต A",
                    0,
                    3,
                    rec["sets_a"],
                    key=f"arc_sa_{idx}"
                )


            with e2:

                edit_b = st.text_input(
                    "ชื่อทีม B",
                    rec["team_b"],
                    key=f"arc_b_{idx}"
                )


                edit_sb = st.number_input(
                    "เซต B",
                    0,
                    3,
                    rec["sets_b"],
                    key=f"arc_sb_{idx}"
                )


            edit_winner = st.text_input(
                "ผู้ชนะ",
                rec["winner"],
                key=f"arc_winner_{idx}"
            )


            c1, c2 = st.columns(2)


            with c1:

                if st.button(
                    "💾 บันทึก",
                    key=f"save_arc_{idx}",
                    type="primary",
                    use_container_width=True
                ):

                    rec["team_a"] = edit_a

                    rec["team_b"] = edit_b

                    rec["sets_a"] = edit_sa

                    rec["sets_b"] = edit_sb

                    rec["winner"] = edit_winner

                    update_and_sync()

                    st.success(
                        "บันทึกแล้ว"
                    )

                    st.rerun()


            with c2:

                if st.button(
                    "🗑️ ลบ",
                    key=f"delete_arc_{idx}",
                    use_container_width=True
                ):

                    m["archives"].pop(idx)

                    update_and_sync()

                    st.rerun()


    # =====================================================
    # DOWNLOAD JSON
    # =====================================================

    json_data = json.dumps(
        m["archives"],
        ensure_ascii=False,
        indent=2
    )


    st.download_button(
        "📥 ดาวน์โหลดประวัติการแข่งขัน JSON",
        data=json_data,
        file_name="all_matches_archive.json",
        mime="application/json"
    )


else:

    st.info(
        "ยังไม่มีประวัติการแข่งขัน"
    )
