import streamlit as st
import json
import os
import time
import copy
from io import BytesIO
import xlsxwriter

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

st.set_page_config(page_title="PT SPORT 2026 VOLLEYBALL SCORE", layout="wide", initial_sidebar_state="expanded")

STATE_FILE = "match_state.json"

DEFAULT_MATCH_DATA = {
    'gender': 'ผสม',
    'round_name': '',
    'group_name': '',
    'match_no': '',
    'target_score_reg': 25,
    'target_score_tie': 15,
    'team_a': 'ทีม A',
    'team_b': 'ทีม B',
    'scores': [{'a': 0, 'b': 0}, {'a': 0, 'b': 0}, {'a': 0, 'b': 0}],
    'current_set': 0,
    'swapped_sides': False,
    'timeouts': {'a': [[False, False], [False, False], [False, False]], 
                 'b': [[False, False], [False, False], [False, False]]},
    'server': 'a',
    'match_started': False,
    'start_time': None,
    'timeout_active': False,
    'timeout_team_name': '',
    'timeout_end_time': 0,
    'players_a': {
        'court': {'1': 'A1', '2': 'A2', '3': 'A3', '4': 'A4', '5': 'A5', '6': 'A6'},
        'bench': ['สำรอง A1', 'สำรอง A2', 'สำรอง A3']
    },
    'players_b': {
        'court': {'1': 'B1', '2': 'B2', '3': 'B3', '4': 'B4', '5': 'B5', '6': 'B6'},
        'bench': ['สำรอง B1', 'สำรอง B2', 'สำรอง B3']
    }
}

# --- SHARED STATE FUNCTIONS ---
def load_shared_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return copy.deepcopy(DEFAULT_MATCH_DATA)

def save_shared_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if 'match_data' not in st.session_state:
    st.session_state.match_data = load_shared_state()

# --- CHECK VIEW MODE ---
query_params = st.query_params
is_scoreboard = query_params.get("view") == "scoreboard"

def update_and_sync():
    save_shared_state(st.session_state.match_data)

def rotate_team_cw(team_key):
    # Rotation 1 -> 6 -> 5 -> 4 -> 3 -> 2 -> 1
    c = st.session_state.match_data[f'players_{team_key}']['court']
    new_c = {
        '1': c['2'],
        '6': c['1'],
        '5': c['6'],
        '4': c['5'],
        '3': c['4'],
        '2': c['3']
    }
    st.session_state.match_data[f'players_{team_key}']['court'] = new_c

def toggle_sides():
    st.session_state.match_data['swapped_sides'] = not st.session_state.match_data['swapped_sides']

def check_set_winner(sa, sb, target):
    if (sa >= target or sb >= target) and abs(sa - sb) >= 2:
        return 'a' if sa > sb else 'b'
    return None

def calculate_sets_won():
    m = st.session_state.match_data
    sets_a, sets_b = 0, 0
    for i in range(3):
        target = m['target_score_reg'] if i < 2 else m['target_score_tie']
        winner = check_set_winner(m['scores'][i]['a'], m['scores'][i]['b'], target)
        if winner == 'a': sets_a += 1
        elif winner == 'b': sets_b += 1
    return sets_a, sets_b

sets_won_a, sets_won_b = calculate_sets_won()
match_winner = None
if sets_won_a >= 2: match_winner = st.session_state.match_data['team_a']
elif sets_won_b >= 2: match_winner = st.session_state.match_data['team_b']

def add_score(team):
    if match_winner: return
    curr_set = st.session_state.match_data['current_set']
    st.session_state.match_data['scores'][curr_set][team] += 1
    
    if st.session_state.match_data['server'] != team:
        st.session_state.match_data['server'] = team
        rotate_team_cw(team)

    curr_target = st.session_state.match_data['target_score_reg'] if curr_set < 2 else st.session_state.match_data['target_score_tie']
    sa = st.session_state.match_data['scores'][curr_set]['a']
    sb = st.session_state.match_data['scores'][curr_set]['b']
    
    if check_set_winner(sa, sb, curr_target):
        new_sets_a, new_sets_b = calculate_sets_won()
        if new_sets_a < 2 and new_sets_b < 2 and curr_set < 2:
            st.session_state.match_data['current_set'] += 1
            toggle_sides()
    update_and_sync()

def minus_score(team):
    curr_set = st.session_state.match_data['current_set']
    if st.session_state.match_data['scores'][curr_set][team] > 0:
        st.session_state.match_data['scores'][curr_set][team] -= 1
        update_and_sync()

# =========================================================
# 📺 MODE 1: SCOREBOARD ( auto-refresh 1 sec )
# =========================================================
if is_scoreboard:
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=1000, key="scoreboard_tick")

    m = load_shared_state()
    curr_set = m['current_set']

    is_swapped = m['swapped_sides']
    left_team = 'b' if is_swapped else 'a'
    right_team = 'a' if is_swapped else 'b'

    left_name = m[f'team_{left_team}']
    right_name = m[f'team_{right_team}']

    # TIMEOUT OVERLAY POPUP
    if m.get('timeout_active', False):
        rem_timeout = int(m['timeout_end_time'] - time.time())
        if rem_timeout <= 0:
            m['timeout_active'] = False
            save_shared_state(m)
        else:
            st.markdown(f"""
            <div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                        background-color: rgba(15, 23, 42, 0.98); z-index: 99999;
                        display: flex; flex-direction: column; align-items: center; justify-content: center;
                        color: white; font-family: sans-serif;">
                <div style="font-size: 40px; font-weight: bold; color: #f59e0b; margin-bottom: 10px;">⏱️ ขอเวลานอก (TIME-OUT)</div>
                <div style="font-size: 50px; font-weight: bold; color: #ffffff; background: #1e293b; padding: 15px 40px; border-radius: 15px; border: 3px solid #f59e0b; margin-bottom: 20px;">
                    {m['timeout_team_name']}
                </div>
                <div style="font-size: 160px; font-weight: bold; color: #ef4444; text-shadow: 0 0 25px rgba(239, 68, 68, 0.8); line-height: 1;">
                    {rem_timeout:02d}
                </div>
                <div style="font-size: 24px; color: #94a3b8; margin-top: 20px;">วินาที</div>
            </div>
            """, unsafe_allow_html=True)

    # MATCH TIMER
    if m['match_started'] and m['start_time']:
        elapsed_sec = int(time.time() - m['start_time'])
        time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_sec))
        status_badge = "🔴 LIVE"
        status_color = "#ef4444"
    else:
        time_str = "00:00:00"
        status_badge = "⏸️ รอเริ่มแข่ง"
        status_color = "#f59e0b"

    st.markdown("<h1 style='text-align: center; font-size: 50px; margin-bottom: 0px;'>PT SPORT 2026</h1>", unsafe_allow_html=True)
    
    serve_left_icon = " 🏐" if m['server'] == left_team else ""
    serve_right_icon = " 🏐" if m['server'] == right_team else ""

    team_head_col1, vs_col, team_head_col2 = st.columns([5, 2, 5])
    with team_head_col1:
        st.markdown(f"<div style='border: 3px solid white; border-radius: 12px; padding: 12px; text-align: center; font-size: 32px; font-weight: bold;'>{left_name}{serve_left_icon}</div>", unsafe_allow_html=True)
    with vs_col:
        st.markdown("<h1 style='text-align: center; margin: 0; font-size: 40px;'>VS</h1>", unsafe_allow_html=True)
    with team_head_col2:
        st.markdown(f"<div style='border: 3px solid white; border-radius: 12px; padding: 12px; text-align: center; font-size: 32px; font-weight: bold;'>{right_name}{serve_right_icon}</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    sc_left, sc_center, sc_right = st.columns([4, 3, 4])

    with sc_left:
        score_left = m['scores'][curr_set][left_team]
        st.markdown(f"""
        <div style='border: 4px solid white; border-radius: 20px; padding: 20px; text-align: center; background-color: #0f172a;'>
            <h1 style='font-size: 160px; margin: 0; color: #2563eb; font-weight: bold;'>{score_left:02d}</h1>
        </div>
        """, unsafe_allow_html=True)

    with sc_center:
        st.markdown(f"""
        <div style='border: 2px solid white; border-radius: 10px; padding: 8px; text-align: center; font-size: 26px; font-weight: bold; background-color: #1e293b; margin-bottom: 15px;'>
            <span style='color: {status_color}; font-size: 16px; margin-right: 8px;'>{status_badge}</span> ⏱️ {time_str}
        </div>
        """, unsafe_allow_html=True)

        for s_idx in range(3):
            set_sa = m['scores'][s_idx][left_team]
            set_sb = m['scores'][s_idx][right_team]
            is_active = (s_idx == curr_set)
            bg_color = "#2563eb" if is_active else "#334155"
            border_style = "3px solid #f59e0b" if is_active else "1px solid #64748b"

            st.markdown(f"""
            <div style='border: {border_style}; border-radius: 8px; padding: 6px; text-align: center; background-color: {bg_color}; margin-bottom: 8px;'>
                <div style='font-size: 14px; color: #cbd5e1;'>SET {s_idx + 1}</div>
                <div style='font-size: 22px; font-weight: bold;'>{set_sa} - {set_sb}</div>
            </div>
            """, unsafe_allow_html=True)

    with sc_right:
        score_right = m['scores'][curr_set][right_team]
        st.markdown(f"""
        <div style='border: 4px solid white; border-radius: 20px; padding: 20px; text-align: center; background-color: #0f172a;'>
            <h1 style='font-size: 160px; margin: 0; color: #ea580c; font-weight: bold;'>{score_right:02d}</h1>
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# =========================================================
# 🎛️ MODE 2: CONTROLLER PANEL
# =========================================================
if HAS_AUTOREFRESH:
    st_autorefresh(interval=1000, key="controller_tick")

m = st.session_state.match_data

st.title("🏐 PT SPORT 2026 VOLLEYBALL SCORE CONTROLLER")

# SIDEBAR
with st.sidebar:
    st.header("⚙️ ตั้งค่าการแข่งขัน")
    m['gender'] = st.radio("ประเภท", ["ชาย", "หญิง", "ผสม"], horizontal=True, index=["ชาย", "หญิง", "ผสม"].index(m['gender']))
    m['round_name'] = st.text_input("รอบ", m['round_name'])
    m['group_name'] = st.text_input("สาย", m['group_name'])
    m['match_no'] = st.text_input("คู่ที่", m['match_no'])
    
    st.markdown("---")
    st.subheader("🎯 เกณฑ์คะแนน")
    m['target_score_reg'] = st.number_input("เซตปกติ", min_value=1, value=m['target_score_reg'])
    m['target_score_tie'] = st.number_input("เซตตัดสิน", min_value=1, value=m['target_score_tie'])
    
    st.markdown("---")
    st.subheader("👥 ชื่อทีม")
    m['team_a'] = st.text_input("ทีม A", m['team_a'])
    m['team_b'] = st.text_input("ทีม B", m['team_b'])
    
    if st.button("💾 บันทึกการตั้งค่า", type="primary"):
        update_and_sync()
        st.success("บันทึกข้อมูลเรียบร้อย!")

# MATCH TIME CONTROLS
start_col1, start_col2, start_col3 = st.columns([2, 1, 1])
with start_col1:
    if not m['match_started']:
        if st.button("▶️ เริ่มการแข่งขัน (Start Match)", type="primary", use_container_width=True):
            m['match_started'] = True
            m['start_time'] = time.time()
            update_and_sync()
            st.rerun()
    else:
        elapsed_sec = int(time.time() - m['start_time']) if m['start_time'] else 0
        time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_sec))
        st.success(f"🟢 **กำลังแข่งขัน:** ⏱️ {time_str}")

with start_col2:
    if st.button("⏸️ รีเซ็ตเวลาแข่ง", use_container_width=True):
        m['start_time'] = time.time()
        update_and_sync()
        st.rerun()

with start_col3:
    if st.button("🔄 สลับฝั่ง (Swap)", use_container_width=True):
        toggle_sides()
        update_and_sync()
        st.rerun()

st.markdown("---")

# SCORE CONTROL
curr_set = m['current_set']
is_swapped = m['swapped_sides']
left_team = 'b' if is_swapped else 'a'
right_team = 'a' if is_swapped else 'b'

col1, col2 = st.columns(2)

with col1:
    t_key = left_team
    t_name = m[f'team_{t_key}']
    with st.container(border=True):
        st.markdown(f"### {t_name} {'🏐' if m['server'] == t_key else ''}")
        st.markdown(f"<h1 style='text-align: center; font-size: 80px; margin: 0;'>{m['scores'][curr_set][t_key]}</h1>", unsafe_allow_html=True)
        if st.button(f"➕ ได้คะแนน ({t_name})", use_container_width=True, type="primary", key="add_left"):
            add_score(t_key)
            st.rerun()
        if st.button("➖ 1 คะแนน", use_container_width=True, key="minus_left"):
            minus_score(t_key)
            st.rerun()

with col2:
    t_key = right_team
    t_name = m[f'team_{t_key}']
    with st.container(border=True):
        st.markdown(f"### {t_name} {'🏐' if m['server'] == t_key else ''}")
        st.markdown(f"<h1 style='text-align: center; font-size: 80px; margin: 0;'>{m['scores'][curr_set][t_key]}</h1>", unsafe_allow_html=True)
        if st.button(f"➕ ได้คะแนน ({t_name})", use_container_width=True, type="primary", key="add_right"):
            add_score(t_key)
            st.rerun()
        if st.button("➖ 1 คะแนน", use_container_width=True, key="minus_right"):
            minus_score(t_key)
            st.rerun()

# TIMEOUT SECTION WITH COUNTDOWN
st.markdown("---")
st.write("### ⏱️ ขอเวลานอก (Time-out)")

# Show countdown if active
if m.get('timeout_active', False):
    rem_timeout = int(m['timeout_end_time'] - time.time())
    if rem_timeout <= 0:
        m['timeout_active'] = False
        update_and_sync()
    else:
        st.warning(f"⏳ **กำลังขอเวลานอก:** {m['timeout_team_name']} — **เหลือเวลา {rem_timeout} วินาที**")

to_col1, to_col2 = st.columns(2)

with to_col1:
    left_name = m[f'team_{left_team}']
    if st.button(f"⏱️ ขอเวลานอก {left_name} (30 วินาที)", use_container_width=True):
        m['timeout_active'] = True
        m['timeout_team_name'] = left_name
        m['timeout_end_time'] = time.time() + 30
        update_and_sync()
        st.rerun()

with to_col2:
    right_name = m[f'team_{right_team}']
    if st.button(f"⏱️ ขอเวลานอก {right_name} (30 วินาที)", use_container_width=True):
        m['timeout_active'] = True
        m['timeout_team_name'] = right_name
        m['timeout_end_time'] = time.time() + 30
        update_and_sync()
        st.rerun()

# PLAYER ROTATION ACCORDING TO YOUR DRAWING
st.markdown("---")
st.subheader("🏐 ผังตำแหน่งนักกีฬาในสนาม (ตรงตามแผนผัง)")

court_a = m['players_a']['court']
court_b = m['players_b']['court']

field_col1, field_col2 = st.columns(2)

with field_col1:
    st.markdown(f"#### TEAM A ({m['team_a']})")
    # Row 1: Front [4, 3, 2]
    f_r1_1, f_r1_2, f_r1_3 = st.columns(3)
    court_a['4'] = f_r1_1.text_input("ตำแหน่ง 4", court_a['4'], key="ta_4")
    court_a['3'] = f_r1_2.text_input("ตำแหน่ง 3", court_a['3'], key="ta_3")
    court_a['2'] = f_r1_3.text_input("ตำแหน่ง 2", court_a['2'], key="ta_2")
    
    # Row 2: Back [5, 6, 1]
    f_r2_1, f_r2_2, f_r2_3 = st.columns(3)
    court_a['5'] = f_r2_1.text_input("ตำแหน่ง 5", court_a['5'], key="ta_5")
    court_a['6'] = f_r2_2.text_input("ตำแหน่ง 6", court_a['6'], key="ta_6")
    court_a['1'] = f_r2_3.text_input("ตำแหน่ง 1 (เสิร์ฟ)", court_a['1'], key="ta_1")

    if st.button("🔄 หมุนตำแหน่ง Team A (CW)", use_container_width=True):
        rotate_team_cw('a')
        update_and_sync()
        st.rerun()

with field_col2:
    st.markdown(f"#### TEAM B ({m['team_b']})")
    # Row 1: Front [2, 3, 4]
    f_rb1_1, f_rb1_2, f_rb1_3 = st.columns(3)
    court_b['2'] = f_rb1_1.text_input("ตำแหน่ง 2", court_b['2'], key="tb_2")
    court_b['3'] = f_rb1_2.text_input("ตำแหน่ง 3", court_b['3'], key="tb_3")
    court_b['4'] = f_rb1_3.text_input("ตำแหน่ง 4", court_b['4'], key="tb_4")
    
    # Row 2: Back [1, 6, 5]
    f_rb2_1, f_rb2_2, f_rb2_3 = st.columns(3)
    court_b['1'] = f_rb2_1.text_input("ตำแหน่ง 1 (เสิร์ฟ)", court_b['1'], key="tb_1")
    court_b['6'] = f_rb2_2.text_input("ตำแหน่ง 6", court_b['6'], key="tb_6")
    court_b['5'] = f_rb2_3.text_input("ตำแหน่ง 5", court_b['5'], key="tb_5")

    if st.button("🔄 หมุนตำแหน่ง Team B (CW)", use_container_width=True):
        rotate_team_cw('b')
        update_and_sync()
        st.rerun()

if st.button("💾 บันทึกตำแหน่งผู้เล่น", type="primary"):
    update_and_sync()
    st.success("บันทึกตำแหน่งผู้เล่นเรียบร้อย!")
