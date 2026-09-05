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
    'history': [],
    'has_libero_a': True,
    'has_libero_b': True,
    'players_a': {
        'court': {'1': 'ผู้เล่น A1', '2': 'ผู้เล่น A2', '3': 'ผู้เล่น A3', '4': 'ผู้เล่น A4', '5': 'ผู้เล่น A5', '6': 'ผู้เล่น A6'},
        'bench': ['สำรอง A1', 'สำรอง A2', 'สำรอง A3', 'สำรอง A4', 'สำรอง A5'],
        'libero': ['ลิบเบโร่ A1', 'ลิบเบโร่ A2'],
        'initial_court': {'1': 'ผู้เล่น A1', '2': 'ผู้เล่น A2', '3': 'ผู้เล่น A3', '4': 'ผู้เล่น A4', '5': 'ผู้เล่น A5', '6': 'ผู้เล่น A6'}
    },
    'players_b': {
        'court': {'1': 'ผู้เล่น B1', '2': 'ผู้เล่น B2', '3': 'ผู้เล่น B3', '4': 'ผู้เล่น B4', '5': 'ผู้เล่น B5', '6': 'ผู้เล่น B6'},
        'bench': ['สำรอง B1', 'สำรอง B2', 'สำรอง B3', 'สำรอง B4', 'สำรอง B5'],
        'libero': ['ลิบเบโร่ B1', 'ลิบเบโร่ B2'],
        'initial_court': {'1': 'ผู้เล่น B1', '2': 'ผู้เล่น B2', '3': 'ผู้เล่น B3', '4': 'ผู้เล่น B4', '5': 'ผู้เล่น B5', '6': 'ผู้เล่น B6'}
    }
}

# --- SHARED STATE FUNCTIONS ---
def load_shared_state():
    data = copy.deepcopy(DEFAULT_MATCH_DATA)
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                data.update(loaded)
        except Exception:
            pass
            
    for team_key in ['players_a', 'players_b']:
        if team_key not in data:
            data[team_key] = copy.deepcopy(DEFAULT_MATCH_DATA[team_key])
        if 'initial_court' not in data[team_key]:
            data[team_key]['initial_court'] = copy.deepcopy(data[team_key]['court'])
        if 'bench' not in data[team_key] or len(data[team_key]['bench']) < 5:
            data[team_key]['bench'] = copy.deepcopy(DEFAULT_MATCH_DATA[team_key]['bench'])
        if 'libero' not in data[team_key]:
            data[team_key]['libero'] = copy.deepcopy(DEFAULT_MATCH_DATA[team_key]['libero'])
            
    if 'has_libero_a' not in data: data['has_libero_a'] = True
    if 'has_libero_b' not in data: data['has_libero_b'] = True
    if 'history' not in data: data['history'] = []
            
    return data

def save_shared_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if 'match_data' not in st.session_state:
    st.session_state.match_data = load_shared_state()

query_params = st.query_params
is_scoreboard = query_params.get("view") == "scoreboard"

def update_and_sync():
    save_shared_state(st.session_state.match_data)

def save_snapshot():
    m = st.session_state.match_data
    snapshot = {
        'scores': copy.deepcopy(m['scores']),
        'current_set': m['current_set'],
        'server': m['server'],
        'swapped_sides': m['swapped_sides'],
        'players_a_court': copy.deepcopy(m['players_a']['court']),
        'players_b_court': copy.deepcopy(m['players_b']['court'])
    }
    m['history'].append(snapshot)
    if len(m['history']) > 30:
        m['history'].pop(0)

def undo_last_action():
    m = st.session_state.match_data
    if m['history']:
        last_state = m['history'].pop()
        m['scores'] = last_state['scores']
        m['current_set'] = last_state['current_set']
        m['server'] = last_state['server']
        m['swapped_sides'] = last_state['swapped_sides']
        m['players_a']['court'] = last_state['players_a_court']
        m['players_b']['court'] = last_state['players_b_court']
        update_and_sync()

def reset_all_match_scores():
    m = st.session_state.match_data
    m['scores'] = [{'a': 0, 'b': 0}, {'a': 0, 'b': 0}, {'a': 0, 'b': 0}]
    m['current_set'] = 0
    m['history'] = []
    m['players_a']['court'] = copy.deepcopy(m['players_a']['initial_court'])
    m['players_b']['court'] = copy.deepcopy(m['players_b']['initial_court'])
    m['match_started'] = False
    m['match_paused'] = False
    m['accumulated_time'] = 0
    m['start_time'] = None
    update_and_sync()

# หมุนตำแหน่งตามเข็มนาฬิกา (กติกาจริง: 1->6, 6->5, 5->4, 4->3, 3->2, 2->1)
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

def reset_team_rotation(team_key):
    st.session_state.match_data[f'players_{team_key}']['court'] = copy.deepcopy(
        st.session_state.match_data[f'players_{team_key}'].get('initial_court', st.session_state.match_data[f'players_{team_key}']['court'])
    )

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
    save_snapshot()
    curr_set = st.session_state.match_data['current_set']
    
    # Side-out: ถ้าเดิมไม่ได้เป็นฝ่ายเสิร์ฟ แล้วแย่งแต้มกลับมาได้ -> หมุนตำแหน่งตามเข็มนาฬิกา
    if st.session_state.match_data['server'] != team:
        st.session_state.match_data['server'] = team
        rotate_team_cw(team)

    st.session_state.match_data['scores'][curr_set][team] += 1

    curr_target = st.session_state.match_data['target_score_reg'] if curr_set < 2 else st.session_state.match_data['target_score_tie']
    sa = st.session_state.match_data['scores'][curr_set]['a']
    sb = st.session_state.match_data['scores'][curr_set]['b']
    
    if check_set_winner(sa, sb, curr_target):
        new_sets_a, new_sets_b = calculate_sets_won()
        if new_sets_a < 2 and new_sets_b < 2 and curr_set < 2:
            st.session_state.match_data['current_set'] += 1
            toggle_sides()
    update_and_sync()

# =========================================================
# 📺 MODE 1: SCOREBOARD DISPLAY
# =========================================================
if is_scoreboard:
    if HAS_AUTOREFRESH: st_autorefresh(interval=1000, key="scoreboard_tick")
    m = load_shared_state()
    curr_set = m['current_set']
    is_swapped = m['swapped_sides']
    left_team, right_team = ('b', 'a') if is_swapped else ('a', 'b')
    left_name, right_name = m[f'team_{left_team}'], m[f'team_{right_team}']

    if m.get('timeout_active', False):
        rem_timeout = int(m['timeout_end_time'] - time.time())
        if rem_timeout <= 0:
            m['timeout_active'] = False
            save_shared_state(m)
        else:
            st.markdown(f"""
            <div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(15, 23, 42, 0.98); z-index: 99999; display: flex; flex-direction: column; align-items: center; justify-content: center; color: white;">
                <div style="font-size: 40px; font-weight: bold; color: #f59e0b;">⏱️ ขอเวลานอก (TIME-OUT)</div>
                <div style="font-size: 50px; font-weight: bold; background: #1e293b; padding: 15px 40px; border-radius: 15px; border: 3px solid #f59e0b; margin: 20px 0;">{m['timeout_team_name']}</div>
                <div style="font-size: 160px; font-weight: bold; color: #ef4444; line-height: 1;">{rem_timeout:02d}</div>
            </div>""", unsafe_allow_html=True)

    if m['match_started'] and not m.get('match_paused', False):
        elapsed_sec = int(m.get('accumulated_time', 0) + (time.time() - m['start_time']))
        status_badge, status_color = "🔴 LIVE", "#ef4444"
    elif m.get('match_paused', False):
        elapsed_sec = int(m.get('accumulated_time', 0))
        status_badge, status_color = "⏸️ พักเวลา", "#f59e0b"
    else:
        elapsed_sec = 0
        status_badge, status_color = "⏹️ รอเริ่มแข่ง", "#64748b"

    time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_sec))
    st.markdown("<h1 style='text-align: center; font-size: 50px; margin-bottom: 0px;'>PT SPORT 2026</h1>", unsafe_allow_html=True)
    
    serve_left = " 🏐" if m['server'] == left_team else ""
    serve_right = " 🏐" if m['server'] == right_team else ""

    team_head_col1, vs_col, team_head_col2 = st.columns([5, 2, 5])
    with team_head_col1: st.markdown(f"<div style='border: 3px solid white; border-radius: 12px; padding: 12px; text-align: center; font-size: 32px; font-weight: bold;'>{left_name}{serve_left}</div>", unsafe_allow_html=True)
    with vs_col: st.markdown("<h1 style='text-align: center; margin: 0; font-size: 40px;'>VS</h1>", unsafe_allow_html=True)
    with team_head_col2: st.markdown(f"<div style='border: 3px solid white; border-radius: 12px; padding: 12px; text-align: center; font-size: 32px; font-weight: bold;'>{right_name}{serve_right}</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    sc_left, sc_center, sc_right = st.columns([4, 3, 4])

    with sc_left:
        st.markdown(f"<div style='border: 4px solid white; border-radius: 20px; padding: 20px; text-align: center; background-color: #0f172a;'><h1 style='font-size: 160px; margin: 0; color: #2563eb; font-weight: bold;'>{m['scores'][curr_set][left_team]:02d}</h1></div>", unsafe_allow_html=True)

    with sc_center:
        st.markdown(f"<div style='border: 2px solid white; border-radius: 10px; padding: 8px; text-align: center; font-size: 26px; font-weight: bold; background-color: #1e293b; margin-bottom: 15px;'><span style='color: {status_color}; font-size: 16px; margin-right: 8px;'>{status_badge}</span> ⏱️ {time_str}</div>", unsafe_allow_html=True)
        for s_idx in range(3):
            set_sa, set_sb = m['scores'][s_idx][left_team], m['scores'][s_idx][right_team]
            is_active = (s_idx == curr_set)
            st.markdown(f"<div style='border: {'3px solid #f59e0b' if is_active else '1px solid #64748b'}; border-radius: 8px; padding: 6px; text-align: center; background-color: {'#2563eb' if is_active else '#334155'}; margin-bottom: 8px;'><div style='font-size: 14px;'>SET {s_idx + 1}</div><div style='font-size: 22px; font-weight: bold;'>{set_sa} - {set_sb}</div></div>", unsafe_allow_html=True)

    with sc_right:
        st.markdown(f"<div style='border: 4px solid white; border-radius: 20px; padding: 20px; text-align: center; background-color: #0f172a;'><h1 style='font-size: 160px; margin: 0; color: #ea580c; font-weight: bold;'>{m['scores'][curr_set][right_team]:02d}</h1></div>", unsafe_allow_html=True)

    st.stop()

# =========================================================
# 🎛️ MODE 2: CONTROLLER PANEL
# =========================================================
if HAS_AUTOREFRESH: st_autorefresh(interval=1000, key="controller_tick")
m = st.session_state.match_data
st.title("🏐 PT SPORT 2026 CONTROLLER")

# SIDEBAR: ตั้งค่าและรายชื่อ
with st.sidebar:
    st.header("⚙️ ตั้งค่าการแข่งขัน")
    m['gender'] = st.radio("ประเภท", ["ชาย", "หญิง", "ผสม"], horizontal=True, index=["ชาย", "หญิง", "ผสม"].index(m['gender']))
    m['round_name'] = st.text_input("รอบ", m['round_name'])
    m['group_name'] = st.text_input("สาย", m['group_name'])
    m['match_no'] = st.text_input("คู่ที่", m['match_no'])
    m['target_score_reg'] = st.number_input("เซตปกติ", min_value=1, value=m['target_score_reg'])
    m['target_score_tie'] = st.number_input("เซตตัดสิน", min_value=1, value=m['target_score_tie'])
    m['team_a'] = st.text_input("ทีม A", m['team_a'])
    m['team_b'] = st.text_input("ทีม B", m['team_b'])
    
    st.markdown("---")
    st.subheader(f"🏃‍♂️ ตัวจริง {m['team_a']}")
    for pos in ['1', '2', '3', '4', '5', '6']:
        m['players_a']['court'][pos] = st.text_input(f"ตำแหน่ง {pos}", m['players_a']['court'][pos], key=f"sb_ta_{pos}")
        m['players_a']['initial_court'][pos] = m['players_a']['court'][pos]
    
    st.subheader(f"🪑 ตัวสำรอง (5 คน) {m['team_a']}")
    for idx in range(5):
        m['players_a']['bench'][idx] = st.text_input(f"สำรอง {idx+1}", m['players_a']['bench'][idx], key=f"sb_ta_bench_{idx}")

    m['has_libero_a'] = st.checkbox(f"ใช้ลิบเบโร่ ({m['team_a']})", value=m['has_libero_a'])
    if m['has_libero_a']:
        st.subheader(f"🛡️ ลิบเบโร่ {m['team_a']}")
        for idx in range(2):
            m['players_a']['libero'][idx] = st.text_input(f"ลิบเบโร่ {idx+1}", m['players_a']['libero'][idx], key=f"sb_ta_lib_{idx}")

    st.markdown("---")
    st.subheader(f"🏃‍♂️ ตัวจริง {m['team_b']}")
    for pos in ['1', '2', '3', '4', '5', '6']:
        m['players_b']['court'][pos] = st.text_input(f"ตำแหน่ง {pos}", m['players_b']['court'][pos], key=f"sb_tb_{pos}")
        m['players_b']['initial_court'][pos] = m['players_b']['court'][pos]
    
    st.subheader(f"🪑 ตัวสำรอง (5 คน) {m['team_b']}")
    for idx in range(5):
        m['players_b']['bench'][idx] = st.text_input(f"สำรอง {idx+1}", m['players_b']['bench'][idx], key=f"sb_tb_bench_{idx}")

    m['has_libero_b'] = st.checkbox(f"ใช้ลิบเบโร่ ({m['team_b']})", value=m['has_libero_b'])
    if m['has_libero_b']:
        st.subheader(f"🛡️ ลิบเบโร่ {m['team_b']}")
        for idx in range(2):
            m['players_b']['libero'][idx] = st.text_input(f"ลิบเบโร่ {idx+1}", m['players_b']['libero'][idx], key=f"sb_tb_lib_{idx}")

    if st.button("💾 บันทึกตั้งค่า/รายชื่อ", type="primary", use_container_width=True):
        update_and_sync()
        st.success("บันทึกข้อมูลเรียบร้อย!")

# MATCH SUMMARY
if match_winner:
    st.balloons()
    st.success(f"🎉 **การแข่งขันจบสิ้น! ทีมชนะเลิศคือ: {match_winner}** 🎉")
    st.markdown("### 📋 สรุปผลการแข่งขัน (Match Summary)")
    sum_col1, sum_col2 = st.columns(2)
    with sum_col1:
        st.info(f"🏆 **ผู้ชนะ:** {match_winner}\n\n📊 **คะแนนรวมเซต:** {m['team_a']} ({sets_won_a}) - ({sets_won_b}) {m['team_b']}")
    with sum_col2:
        tot_sec = int(m.get('accumulated_time', 0))
        st.info(f"⏱️ **เวลาที่ใช้ทั้งหมด:** {time.strftime('%H:%M:%S', time.gmtime(tot_sec))}\n\n🏆 **ผลแต่ละเซต:** " + 
                ", ".join([f"SET {i+1}: {m['scores'][i]['a']}-{m['scores'][i]['b']}" for i in range(3) if m['scores'][i]['a'] > 0 or m['scores'][i]['b'] > 0]))
    st.markdown("---")

# PAST SETS
with st.expander("📊 ดูผลการแข่งขันเซตที่ผ่านมา (Past Sets)", expanded=False):
    s_col1, s_col2, s_col3 = st.columns(3)
    for i, col in enumerate([s_col1, s_col2, s_col3]):
        with col:
            st.markdown(f"**SET {i+1}** {'(กำลังแข่ง)' if i == m['current_set'] else ''}")
            st.write(f"{m['team_a']}: **{m['scores'][i]['a']}** คะแนน")
            st.write(f"{m['team_b']}: **{m['scores'][i]['b']}** คะแนน")

# CONTROLS
start_col1, start_col2, start_col3, start_col4, start_col5, start_col6 = st.columns([1.8, 1.2, 1, 1, 1.2, 1.5])
with start_col1:
    if not m['match_started']:
        if st.button("▶️ เริ่มเวลาแข่ง", type="primary", use_container_width=True):
            m['match_started'] = True
            m['match_paused'] = False
            m['start_time'] = time.time()
            m['accumulated_time'] = 0
            update_and_sync()
            st.rerun()
    elif m.get('match_paused', False):
        if st.button("▶️ เดินเวลาต่อ", type="primary", use_container_width=True):
            m['match_paused'] = False
            m['start_time'] = time.time()
            update_and_sync()
            st.rerun()
    else:
        elapsed = int(m.get('accumulated_time', 0) + (time.time() - m['start_time']))
        st.success(f"🔴 LIVE: ⏱️ {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")

with start_col2:
    if m['match_started'] and not m.get('match_paused', False):
        if st.button("⏸️ พัก/หยุดเวลา", use_container_width=True):
            m['match_paused'] = True
            m['accumulated_time'] += (time.time() - m['start_time'])
            update_and_sync()
            st.rerun()

with start_col3:
    if st.button("🔄 เวลา", use_container_width=True, help="รีเซ็ตเฉพาะเวลา"):
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

with start_col5:
    if st.button("↩️ ย้อนกลับ", type="secondary", use_container_width=True, help="Undo ลบคะแนนล่าสุด"):
        undo_last_action()
        st.rerun()

with start_col6:
    if st.button("🧹 รีเซ็ตคะแนนทั้งหมด", type="primary", use_container_width=True, help="รีเซ็ตคะแนนทุกเซตและตำแหน่งสนาม"):
        reset_all_match_scores()
        st.rerun()

st.markdown("---")

# SCORE CONTROLS
curr_set = m['current_set']
is_swapped = m['swapped_sides']
left_team, right_team = ('b', 'a') if is_swapped else ('a', 'b')

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

with col2:
    t_key = right_team
    t_name = m[f'team_{t_key}']
    with st.container(border=True):
        st.markdown(f"### {t_name} {'🏐 (เสิร์ฟ)' if m['server'] == t_key else ''}")
        st.markdown(f"<h1 style='text-align: center; font-size: 80px; margin: 0;'>{m['scores'][curr_set][t_key]}</h1>", unsafe_allow_html=True)
        if st.button(f"➕ ได้คะแนน ({t_name})", use_container_width=True, type="primary", key="add_right"):
            add_score(t_key)
            st.rerun()

# TIME-OUT SECTION
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
    if st.button(f"⏱️ ขอเวลานอก {m[f'team_{left_team}']} (30 วินาที)", use_container_width=True):
        m['timeout_active'] = True
        m['timeout_team_name'] = m[f'team_{left_team}']
        m['timeout_end_time'] = time.time() + 30
        update_and_sync()
        st.rerun()

with to_col2:
    if st.button(f"⏱️ ขอเวลานอก {m[f'team_{right_team}']} (30 วินาที)", use_container_width=True):
        m['timeout_active'] = True
        m['timeout_team_name'] = m[f'team_{right_team}']
        m['timeout_end_time'] = time.time() + 30
        update_and_sync()
        st.rerun()

# FIELD DISPLAY & SUBSTITUTION
st.markdown("---")
st.subheader("🏐 ผังสนามและการเปลี่ยนตัวนักกีฬา")

def render_player_box(pos_num, player_name, is_server=False, is_libero=False):
    border_color = "#f59e0b" if is_server else ("#10b981" if is_libero else "#475569")
    serve_tag = " 🏐" if is_server else ""
    lib_tag = " 🛡️(L)" if is_libero else ""
    return f"""<div style="border: 2px solid {border_color}; border-radius: 8px; padding: 10px; text-align: center; background-color: #1e293b; margin-bottom: 10px;">
        <div style="font-size: 14px; color: #f59e0b; font-weight: bold;">ตำแหน่ง {pos_num}{serve_tag}{lib_tag}</div>
        <div style="font-size: 18px; font-weight: bold; color: white;">{player_name}</div>
    </div>"""

field_col1, field_col2 = st.columns(2)

# TEAM A FIELD
with field_col1:
    st.markdown(f"### {m['team_a']} {'🏐' if m['server'] == 'a' else ''}")
    court_a, bench_a, lib_a = m['players_a']['court'], m['players_a']['bench'], m['players_a']['libero']
    has_lib_a = m.get('has_libero_a', False)
    
    r1_1, r1_2 = st.columns(2)
    with r1_1: st.markdown(render_player_box('5', court_a['5'], is_libero=(has_lib_a and court_a['5'] in lib_a)), unsafe_allow_html=True)
    with r1_2: st.markdown(render_player_box('4', court_a['4'], is_libero=(has_lib_a and court_a['4'] in lib_a)), unsafe_allow_html=True)
    r2_1, r2_2 = st.columns(2)
    with r2_1: st.markdown(render_player_box('6', court_a['6'], is_libero=(has_lib_a and court_a['6'] in lib_a)), unsafe_allow_html=True)
    with r2_2: st.markdown(render_player_box('3', court_a['3'], is_libero=(has_lib_a and court_a['3'] in lib_a)), unsafe_allow_html=True)
    r3_1, r3_2 = st.columns(2)
    with r3_1: st.markdown(render_player_box('1', court_a['1'], is_server=(m['server'] == 'a'), is_libero=(has_lib_a and court_a['1'] in lib_a)), unsafe_allow_html=True)
    with r3_2: st.markdown(render_player_box('2', court_a['2'], is_libero=(has_lib_a and court_a['2'] in lib_a)), unsafe_allow_html=True)

    if st.button("🔄 รีเซ็ตตำแหน่ง Team A", use_container_width=True):
        reset_team_rotation('a')
        update_and_sync()
        st.rerun()

    # Regular Substitution
    st.markdown(f"**🔄 เปลี่ยนตัวปกติ ({m['team_a']}):**")
    sub_out_a = st.selectbox("ออก (ตัวจริง)", list(court_a.values()), key="sub_out_a")
    sub_in_a = st.selectbox("เข้า (ตัวสำรอง)", bench_a, key="sub_in_a")
    if st.button("🔁 ยืนยันเปลี่ยนตัว Team A", use_container_width=True):
        pos_key = [k for k, v in court_a.items() if v == sub_out_a][0]
        bench_idx = bench_a.index(sub_in_a)
        court_a[pos_key], bench_a[bench_idx] = bench_a[bench_idx], court_a[pos_key]
        update_and_sync()
        st.rerun()

    # Libero Replacement
    if has_lib_a:
        st.markdown(f"**🛡️ เปลี่ยนตัวลิบเบโร่ (แดนหลังเท่านั้น):**")
        backrow_a = {k: court_a[k] for k in ['1', '6', '5']}
        lib_pos_a = st.selectbox("ตำแหน่งแดนหลัง (1, 6, 5)", list(backrow_a.keys()), format_func=lambda x: f"ตำแหน่ง {x} ({backrow_a[x]})", key="lib_pos_a")
        lib_in_a = st.selectbox("เลือกเปลี่ยนเป็น", lib_a + [m['players_a']['initial_court'].get(lib_pos_a, 'ผู้เล่นเดิม')], key="lib_in_a")
        if st.button("🛡️ เปลี่ยนตัวลิบเบโร่ Team A", use_container_width=True):
            court_a[lib_pos_a] = lib_in_a
            update_and_sync()
            st.rerun()

# TEAM B FIELD
with field_col2:
    st.markdown(f"### {m['team_b']} {'🏐' if m['server'] == 'b' else ''}")
    court_b, bench_b, lib_b = m['players_b']['court'], m['players_b']['bench'], m['players_b']['libero']
    has_lib_b = m.get('has_libero_b', False)

    r1_1, r1_2 = st.columns(2)
    with r1_1: st.markdown(render_player_box('2', court_b['2'], is_libero=(has_lib_b and court_b['2'] in lib_b)), unsafe_allow_html=True)
    with r1_2: st.markdown(render_player_box('1', court_b['1'], is_server=(m['server'] == 'b'), is_libero=(has_lib_b and court_b['1'] in lib_b)), unsafe_allow_html=True)
    r2_1, r2_2 = st.columns(2)
    with r2_1: st.markdown(render_player_box('3', court_b['3'], is_libero=(has_lib_b and court_b['3'] in lib_b)), unsafe_allow_html=True)
    with r2_2: st.markdown(render_player_box('6', court_b['6'], is_libero=(has_lib_b and court_b['6'] in lib_b)), unsafe_allow_html=True)
    r3_1, r3_2 = st.columns(2)
    with r3_1: st.markdown(render_player_box('4', court_b['4'], is_libero=(has_lib_b and court_b['4'] in lib_b)), unsafe_allow_html=True)
    with r3_2: st.markdown(render_player_box('5', court_b['5'], is_libero=(has_lib_b and court_b['5'] in lib_b)), unsafe_allow_html=True)

    if st.button("🔄 รีเซ็ตตำแหน่ง Team B", use_container_width=True):
        reset_team_rotation('b')
        update_and_sync()
        st.rerun()

    # Regular Substitution
    st.markdown(f"**🔄 เปลี่ยนตัวปกติ ({m['team_b']}):**")
    sub_out_b = st.selectbox("ออก (ตัวจริง)", list(court_b.values()), key="sub_out_b")
    sub_in_b = st.selectbox("เข้า (ตัวสำรอง)", bench_b, key="sub_in_b")
    if st.button("🔁 ยืนยันเปลี่ยนตัว Team B", use_container_width=True):
        pos_key = [k for k, v in court_b.items() if v == sub_out_b][0]
        bench_idx = bench_b.index(sub_in_b)
        court_b[pos_key], bench_b[bench_idx] = bench_b[bench_idx], court_b[pos_key]
        update_and_sync()
        st.rerun()

    # Libero Replacement
    if has_lib_b:
        st.markdown(f"**🛡️ เปลี่ยนตัวลิบเบโร่ (แดนหลังเท่านั้น):**")
        backrow_b = {k: court_b[k] for k in ['1', '6', '5']}
        lib_pos_b = st.selectbox("ตำแหน่งแดนหลัง (1, 6, 5)", list(backrow_b.keys()), format_func=lambda x: f"ตำแหน่ง {x} ({backrow_b[x]})", key="lib_pos_b")
        lib_in_b = st.selectbox("เลือกเปลี่ยนเป็น", lib_b + [m['players_b']['initial_court'].get(lib_pos_b, 'ผู้เล่นเดิม')], key="lib_in_b")
        if st.button("🛡️ เปลี่ยนตัวลิบเบโร่ Team B", use_container_width=True):
            court_b[lib_pos_b] = lib_in_b
            update_and_sync()
            st.rerun()
