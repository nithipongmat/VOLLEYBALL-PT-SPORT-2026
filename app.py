import streamlit as st
import json
import os
import time
import copy

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
    'server': 'a',
    'match_started': False,
    'match_paused': False,
    'start_time': None,
    'accumulated_time': 0,
    'timeout_active': False,
    'timeout_team_name': '',
    'timeout_end_time': 0,
    'players_a': {
        'court': {'1': 'ผู้เล่น A1', '2': 'ผู้เล่น A2', '3': 'ผู้เล่น A3', '4': 'ผู้เล่น A4', '5': 'ผู้เล่น A5', '6': 'ผู้เล่น A6'},
        'bench': ['สำรอง A1', 'สำรอง A2', 'สำรอง A3']
    },
    'players_b': {
        'court': {'1': 'ผู้เล่น B1', '2': 'ผู้เล่น B2', '3': 'ผู้เล่น B3', '4': 'ผู้เล่น B4', '5': 'ผู้เล่น B5', '6': 'ผู้เล่น B6'},
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

query_params = st.query_params
is_scoreboard = query_params.get("view") == "scoreboard"

def update_and_sync():
    save_shared_state(st.session_state.match_data)

# ROTATION AUTOMATICALLY: 1 -> 6 -> 5 -> 4 -> 3 -> 2 -> 1
def rotate_team_cw(team_key):
    c = st.session_state.match_data[f'players_{team_key}']['court']
    new_c = {
        '6': c['1'],
        '5': c['6'],
        '4': c['5'],
        '3': c['4'],
        '2': c['3'],
        '1': c['2']
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
    
    # เปลี่ยนฝั่งเสิร์ฟ -> หมุนตำแหน่งอัตโนมัติ (สลับผู้เล่นตามตำแหน่งจริง)
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
# 📺 MODE 1: SCOREBOARD DISPLAY
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

    # TIMER CALCULATION
    if m['match_started'] and not m.get('match_paused', False):
        elapsed_sec = int(m.get('accumulated_time', 0) + (time.time() - m['start_time']))
        status_badge = "🔴 LIVE"
        status_color = "#ef4444"
    elif m.get('match_paused', False):
        elapsed_sec = int(m.get('accumulated_time', 0))
        status_badge = "⏸️ พักเวลา"
        status_color = "#f59e0b"
    else:
        elapsed_sec = 0
        status_badge = "⏹️ รอเริ่มแข่ง"
        status_color = "#64748b"

    time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_sec))

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

st.title("🏐 PT SPORT 2026 CONTROLLER")

# --- SIDEBAR: MATCH SETTINGS & PLAYER NAMES ---
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
    
    st.markdown("---")
    st.subheader(f"🏃‍♂️ รายชื่อผู้เล่น {m['team_a']}")
    for pos in ['1', '2', '3', '4', '5', '6']:
        m['players_a']['court'][pos] = st.text_input(f"ตัวจริง ตำแหน่ง {pos}", m['players_a']['court'][pos], key=f"sb_ta_{pos}")
    for idx_b in range(len(m['players_a']['bench'])):
        m['players_a']['bench'][idx_b] = st.text_input(f"สำรอง A{idx_b+1}", m['players_a']['bench'][idx_b], key=f"sb_bench_a_{idx_b}")

    st.markdown("---")
    st.subheader(f"🏃‍♂️ รายชื่อผู้เล่น {m['team_b']}")
    for pos in ['1', '2', '3', '4', '5', '6']:
        m['players_b']['court'][pos] = st.text_input(f"ตัวจริง ตำแหน่ง {pos}", m['players_b']['court'][pos], key=f"sb_tb_{pos}")
    for idx_b in range(len(m['players_b']['bench'])):
        m['players_b']['bench'][idx_b] = st.text_input(f"สำรอง B{idx_b+1}", m['players_b']['bench'][idx_b], key=f"sb_bench_b_{idx_b}")

    if st.button("💾 บันทึกตั้งค่า/รายชื่อทั้งหมด", type="primary", use_container_width=True):
        update_and_sync()
        st.success("บันทึกข้อมูลเรียบร้อย!")

# MATCH TIME CONTROLS (WITH PAUSE BUTTON)
start_col1, start_col2, start_col3, start_col4 = st.columns([2, 1.5, 1, 1])

with start_col1:
    if not m['match_started']:
        if st.button("▶️ เริ่มเวลาแข่ง (Start)", type="primary", use_container_width=True):
            m['match_started'] = True
            m['match_paused'] = False
            m['start_time'] = time.time()
            m['accumulated_time'] = 0
            update_and_sync()
            st.rerun()
    elif m.get('match_paused', False):
        if st.button("▶️ เดินเวลาต่อ (Resume)", type="primary", use_container_width=True):
            m['match_paused'] = False
            m['start_time'] = time.time()
            update_and_sync()
            st.rerun()
    else:
        elapsed = int(m.get('accumulated_time', 0) + (time.time() - m['start_time']))
        t_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        st.success(f"🔴 LIVE: ⏱️ {t_str}")

with start_col2:
    if m['match_started'] and not m.get('match_paused', False):
        if st.button("⏸️ พัก/หยุดเวลา", use_container_width=True):
            m['match_paused'] = True
            m['accumulated_time'] += (time.time() - m['start_time'])
            update_and_sync()
            st.rerun()

with start_col3:
    if st.button("🔄 รีเซ็ตเวลา", use_container_width=True):
        m['match_started'] = False
        m['match_paused'] = False
        m['accumulated_time'] = 0
        m['start_time'] = None
        update_and_sync()
        st.rerun()

with start_col4:
    if st.button("🔁 สลับฝั่ง", use_container_width=True):
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
        st.markdown(f"### {t_name} {'🏐 (เสิร์ฟ)' if m['server'] == t_key else ''}")
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
        st.markdown(f"### {t_name} {'🏐 (เสิร์ฟ)' if m['server'] == t_key else ''}")
        st.markdown(f"<h1 style='text-align: center; font-size: 80px; margin: 0;'>{m['scores'][curr_set][t_key]}</h1>", unsafe_allow_html=True)
        if st.button(f"➕ ได้คะแนน ({t_name})", use_container_width=True, type="primary", key="add_right"):
            add_score(t_key)
            st.rerun()
        if st.button("➖ 1 คะแนน", use_container_width=True, key="minus_right"):
            minus_score(t_key)
            st.rerun()

# TIMEOUT SECTION
st.markdown("---")
st.write("### ⏱️ ขอเวลานอก (Time-out)")

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

# FIELD DISPLAY & SUBSTITUTION SYSTEM
st.markdown("---")
st.subheader("🏐 ผังสนามและการเปลี่ยนตัวนักกีฬา")

def render_player_box(pos_num, player_name, is_server=False):
    border_color = "#f59e0b" if is_server else "#475569"
    serve_tag = " 🏐" if is_server else ""
    return f"""
    <div style="border: 2px solid {border_color}; border-radius: 8px; padding: 10px; text-align: center; background-color: #1e293b; margin-bottom: 10px;">
        <div style="font-size: 14px; color: #f59e0b; font-weight: bold;">ตำแหน่ง {pos_num}{serve_tag}</div>
        <div style="font-size: 18px; font-weight: bold; color: white; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{player_name}</div>
    </div>
    """

court_a = m['players_a']['court']
bench_a = m['players_a']['bench']
court_b = m['players_b']['court']
bench_b = m['players_b']['bench']

field_col1, field_col2 = st.columns(2)

# --- TEAM A FIELD & SUB ---
with field_col1:
    st.markdown(f"### {m['team_a']} {'🏐' if m['server'] == 'a' else ''}")
    
    # ROW 1: 5 | 4
    r1_1, r1_2 = st.columns(2)
    with r1_1: st.markdown(render_player_box('5', court_a['5']), unsafe_allow_html=True)
    with r1_2: st.markdown(render_player_box('4', court_a['4']), unsafe_allow_html=True)
    
    # ROW 2: 6 | 3
    r2_1, r2_2 = st.columns(2)
    with r2_1: st.markdown(render_player_box('6', court_a['6']), unsafe_allow_html=True)
    with r2_2: st.markdown(render_player_box('3', court_a['3']), unsafe_allow_html=True)

    # ROW 3: 1 | 2
    r3_1, r3_2 = st.columns(2)
    with r3_1: st.markdown(render_player_box('1', court_a['1'], is_server=(m['server'] == 'a')), unsafe_allow_html=True)
    with r3_2: st.markdown(render_player_box('2', court_a['2']), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"**🔄 ระบบเปลี่ยนตัวผู้เล่น ({m['team_a']}):**")
    
    sub_out_a = st.selectbox("ผู้เล่นในสนามที่จะออก", list(court_a.values()), key="sub_out_a")
    sub_in_a = st.selectbox("ผู้เล่นสำรองที่จะเข้า", bench_a, key="sub_in_a")
    
    if st.button("🔁 ยืนยันเปลี่ยนตัว Team A", type="primary", use_container_width=True):
        pos_key = [k for k, v in court_a.items() if v == sub_out_a][0]
        bench_idx = bench_a.index(sub_in_a)
        court_a[pos_key], bench_a[bench_idx] = bench_a[bench_idx], court_a[pos_key]
        update_and_sync()
        st.success(f"เปลี่ยนตัวสำเร็จ: {sub_out_a} ↔ {sub_in_a}")
        st.rerun()

# --- TEAM B FIELD & SUB ---
with field_col2:
    st.markdown(f"### {m['team_b']} {'🏐' if m['server'] == 'b' else ''}")
    
    # ROW 1: 2 | 1
    r1_1, r1_2 = st.columns(2)
    with r1_1: st.markdown(render_player_box('2', court_b['2']), unsafe_allow_html=True)
    with r1_2: st.markdown(render_player_box('1', court_b['1'], is_server=(m['server'] == 'b')), unsafe_allow_html=True)
    
    # ROW 2: 3 | 6
    r2_1, r2_2 = st.columns(2)
    with r2_1: st.markdown(render_player_box('3', court_b['3']), unsafe_allow_html=True)
    with r2_2: st.markdown(render_player_box('6', court_b['6']), unsafe_allow_html=True)

    # ROW 3: 4 | 5
    r3_1, r3_2 = st.columns(2)
    with r3_1: st.markdown(render_player_box('4', court_b['4']), unsafe_allow_html=True)
    with r3_2: st.markdown(render_player_box('5', court_b['5']), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"**🔄 ระบบเปลี่ยนตัวผู้เล่น ({m['team_b']}):**")
    
    sub_out_b = st.selectbox("ผู้เล่นในสนามที่จะออก", list(court_b.values()), key="sub_out_b")
    sub_in_b = st.selectbox("ผู้เล่นสำรองที่จะเข้า", bench_b, key="sub_in_b")
    
    if st.button("🔁 ยืนยันเปลี่ยนตัว Team B", type="primary", use_container_width=True):
        pos_key = [k for k, v in court_b.items() if v == sub_out_b][0]
        bench_idx = bench_b.index(sub_in_b)
        court_b[pos_key], bench_b[bench_idx] = bench_b[bench_idx], court_b[pos_key]
        update_and_sync()
        st.success(f"เปลี่ยนตัวสำเร็จ: {sub_out_b} ↔ {sub_in_b}")
        st.rerun()
