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
        'court': {'1': 'A1', '2': 'A2', '3': 'A3', '4': 'A4', '5': 'A5', '6': 'A6'},
        'bench': ['สำรอง A1', 'สำรอง A2', 'สำรอง A3', 'สำรอง A4', 'สำรอง A5'],
        'libero': ['ลิบเบโร่ A1', 'ลิบเบโร่ A2'],
        'initial_court': {'1': 'A1', '2': 'A2', '3': 'A3', '4': 'A4', '5': 'A5', '6': 'A6'}
    },
    'players_b': {
        'court': {'1': 'B1', '2': 'B2', '3': 'B3', '4': 'B4', '5': 'B5', '6': 'B6'},
        'bench': ['สำรอง B1', 'สำรอง B2', 'สำรอง B3', 'สำรอง B4', 'สำรอง B5'],
        'libero': ['ลิบเบโร่ B1', 'ลิบเบโร่ B2'],
        'initial_court': {'1': 'B1', '2': 'B2', '3': 'B3', '4': 'B4', '5': 'B5', '6': 'B6'}
    }
}

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

# ฟังก์ชันหมุนตำแหน่งตามเข็มนาฬิกา (ปรับให้บังคับอัปเดต Dictionary โดยตรง)
def rotate_team_cw(team_key):
    c = st.session_state.match_data[f'players_{team_key}']['court']
    # ตำแหน่ง 2 ไป 1, ตำแหน่ง 1 ไป 6, ตำแหน่ง 6 ไป 5, ตำแหน่ง 5 ไป 4, ตำแหน่ง 4 ไป 3, ตำแหน่ง 3 ไป 2
    new_court = {
        '1': str(c['2']),
        '6': str(c['1']),
        '5': str(c['6']),
        '4': str(c['5']),
        '3': str(c['4']),
        '2': str(c['3'])
    }
    st.session_state.match_data[f'players_{team_key}']['court'] = new_court

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
    
    # ถ้าทีมที่ได้แต้มไม่ได้เป็นฝ่ายเสิร์ฟมาก่อน = แย่งเสิร์ฟคืนได้ (Side-out) -> หมุนตำแหน่งตามเข็มนาฬิกา
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
            
    update_and_sync()

# =========================================================
# 📺 MODE 1: SCOREBOARD DISPLAY (จอบอร์ด)
# =========================================================
if is_scoreboard:
    if HAS_AUTOREFRESH: st_autorefresh(interval=1000, key="scoreboard_tick")
    m = load_shared_state()
    curr_set = m['current_set']
    
    left_name, right_name = m['team_a'], m['team_b']

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
    
    serve_left = " 🏐" if m['server'] == 'a' else ""
    serve_right = " 🏐" if m['server'] == 'b' else ""

    team_head_col1, vs_col, team_head_col2 = st.columns([5, 2, 5])
    with team_head_col1: st.markdown(f"<div style='border: 3px solid white; border-radius: 12px; padding: 12px; text-align: center; font-size: 32px; font-weight: bold;'>{left_name}{serve_left}</div>", unsafe_allow_html=True)
    with vs_col: st.markdown("<h1 style='text-align: center; margin: 0; font-size: 40px;'>VS</h1>", unsafe_allow_html=True)
    with team_head_col2: st.markdown(f"<div style='border: 3px solid white; border-radius: 12px; padding: 12px; text-align: center; font-size: 32px; font-weight: bold;'>{right_name}{serve_right}</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    sc_left, sc_center, sc_right = st.columns([4, 3, 4])

    with sc_left:
        st.markdown(f"<div style='border: 4px solid white; border-radius: 20px; padding: 20px; text-align: center; background-color: #0f172a;'><h1 style='font-size: 160px; margin: 0; color: #2563eb; font-weight: bold;'>{m['scores'][curr_set]['a']:02d}</h1></div>", unsafe_allow_html=True)

    with sc_center:
        st.markdown(f"<div style='border: 2px solid white; border-radius: 10px; padding: 8px; text-align: center; font-size: 26px; font-weight: bold; background-color: #1e293b; margin-bottom: 15px;'><span style='color: {status_color}; font-size: 16px; margin-right: 8px;'>{status_badge}</span> ⏱️ {time_str}</div>", unsafe_allow_html=True)
        for s_idx in range(3):
            set_sa, set_sb = m['scores'][s_idx]['a'], m['scores'][s_idx]['b']
            is_active = (s_idx == curr_set)
            st.markdown(f"<div style='border: {'3px solid #f59e0b' if is_active else '1px solid #64748b'}; border-radius: 8px; padding: 6px; text-align: center; background-color: {'#2563eb' if is_active else '#334155'}; margin-bottom: 8px;'><div style='font-size: 14px;'>SET {s_idx + 1}</div><div style='font-size: 22px; font-weight: bold;'>{set_sa} - {set_sb}</div></div>", unsafe_allow_html=True)

    with sc_right:
        st.markdown(f"<div style='border: 4px solid white; border-radius: 20px; padding: 20px; text-align: center; background-color: #0f172a;'><h1 style='font-size: 160px; margin: 0; color: #ea580c; font-weight: bold;'>{m['scores'][curr_set]['b']:02d}</h1></div>", unsafe_allow_html=True)

    st.stop()

# =========================================================
# 🎛️ MODE 2: CONTROLLER PANEL (หน้าผู้ควบคุม)
# =========================================================
if HAS_AUTOREFRESH: st_autorefresh(interval=1000, key="controller_tick")
m = st.session_state.match_data
st.title("🏐 PT SPORT 2026 CONTROLLER")

# SIDEBAR
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
    st.subheader(f"🏃‍♂️ รายชื่อตัวจริง {m['team_a']}")
    for pos in ['1', '2', '3', '4', '5', '6']:
        m['players_a']['court'][pos] = st.text_input(f"ตำแหน่ง {pos}", m['players_a']['court'][pos], key=f"sb_ta_{pos}")
        m['players_a']['initial_court'][pos] = m['players_a']['court'][pos]
    
    st.subheader(f"🪑 ตัวสำรอง {m['team_a']}")
    for idx in range(5):
        m['players_a']['bench'][idx] = st.text_input(f"สำรอง {idx+1}", m['players_a']['bench'][idx], key=f"sb_ta_bench_{idx}")

    m['has_libero_a'] = st.checkbox(f"ใช้ลิบเบโร่ ({m['team_a']})", value=m['has_libero_a'])
    if m['has_libero_a']:
        st.subheader(f"🛡️ ลิบเบโร่ {m['team_a']}")
        for idx in range(2):
            m['players_a']['libero'][idx] = st.text_input(f"ลิบเบโร่ {idx+1}", m['players_a']['libero'][idx], key=f"sb_ta_lib_{idx}")

    st.markdown("---")
    st.subheader(f"🏃‍♂️ รายชื่อตัวจริง {m['team_b']}")
    for pos in ['1', '2', '3', '4', '5', '6']:
        m['players_b']['court'][pos] = st.text_input(f"ตำแหน่ง {pos}", m['players_b']['court'][pos], key=f"sb_tb_{pos}")
        m['players_b']['initial_court'][pos] = m['players_b']['court'][pos]
    
    st.subheader(f"🪑 ตัวสำรอง {m['team_b']}")
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

# CONTROLS
start_col1, start_col2, start_col3, start_col4, start_col5 = st.columns([2, 1.5, 1.2, 1.5, 2])
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
    if st.button("🔄 เวลา", use_container_width=True):
        m['match_started'] = False
        m['match_paused'] = False
        m['accumulated_time'] = 0
        m['start_time'] = None
        update_and_sync()
        st.rerun()

with start_col4:
    if st.button("↩️ ย้อนกลับ/ลบคะแนน", type="secondary", use_container_width=True):
        undo_last_action()
        st.rerun()

with start_col5:
    if st.button("🧹 รีเซ็ตคะแนนทั้งหมด", type="primary", use_container_width=True):
        reset_all_match_scores()
        st.rerun()

st.markdown("---")

# SCORE CONTROLS (ซ้าย = ทีม A / ขวา = ทีม B ล็อกถาวร)
curr_set = m['current_set']

col1, col2 = st.columns(2)

# ฝั่งซ้าย: ทีม A
with col1:
    t_name = m['team_a']
    with st.container(border=True):
        st.markdown(f"### {t_name} {'🏐 (เสิร์ฟ)' if m['server'] == 'a' else ''}")
        st.markdown(f"<h1 style='text-align: center; font-size: 80px; margin: 0; color: #2563eb;'>{m['scores'][curr_set]['a']}</h1>", unsafe_allow_html=True)
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button(f"➕ ได้คะแนน ({t_name})", use_container_width=True, type="primary", key="add_a_btn"):
                add_score('a')
                st.rerun()
        with btn_c2:
            if st.button(f"🔄 หมุนตำแหน่ง ({t_name})", use_container_width=True, key="rotate_a_btn"):
                rotate_team_cw('a')
                update_and_sync()
                st.rerun()

# ฝั่งขวา: ทีม B
with col2:
    t_name = m['team_b']
    with st.container(border=True):
        st.markdown(f"### {t_name} {'🏐 (เสิร์ฟ)' if m['server'] == 'b' else ''}")
        st.markdown(f"<h1 style='text-align: center; font-size: 80px; margin: 0; color: #ea580c;'>{m['scores'][curr_set]['b']}</h1>", unsafe_allow_html=True)
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button(f"➕ ได้คะแนน ({t_name})", use_container_width=True, type="primary", key="add_b_btn"):
                add_score('b')
                st.rerun()
        with btn_c2:
            if st.button(f"🔄 หมุนตำแหน่ง ({t_name})", use_container_width=True, key="rotate_b_btn"):
                rotate_team_cw('b')
                update_and_sync()
                st.rerun()

# FIELD DISPLAY (ดึงข้อมูลผู้เล่นมาวาดใหม่ตรงๆ ทุกครั้งที่ Render)
st.markdown("---")
st.subheader("🏐 ผังตำแหน่งผู้เล่นบนสนาม (ตำแหน่ง 1 คือจุดเสิร์ฟ)")

def render_player_box(pos_num, player_name, is_server=False):
    border_color = "#f59e0b" if is_server else "#475569"
    serve_tag = " 🏐 (เสิร์ฟ)" if is_server else ""
    return f"""<div style="border: 2px solid {border_color}; border-radius: 8px; padding: 10px; text-align: center; background-color: #1e293b; margin-bottom: 8px;">
        <div style="font-size: 13px; color: #f59e0b; font-weight: bold;">ตำแหน่ง {pos_num}{serve_tag}</div>
        <div style="font-size: 20px; font-weight: bold; color: white;">{player_name}</div>
    </div>"""

field_col1, field_col2 = st.columns(2)

# TEAM A FIELD (ฝั่งซ้าย: ตำแหน่ง 1 อยู่ซ้ายล่าง)
with field_col1:
    st.markdown(f"### {m['team_a']} {'🏐' if m['server'] == 'a' else ''}")
    ca = st.session_state.match_data['players_a']['court']
    
    r1_1, r1_2 = st.columns(2)
    with r1_1: st.markdown(render_player_box('5', ca['5']), unsafe_allow_html=True)
    with r1_2: st.markdown(render_player_box('4', ca['4']), unsafe_allow_html=True)
    
    r2_1, r2_2 = st.columns(2)
    with r2_1: st.markdown(render_player_box('6', ca['6']), unsafe_allow_html=True)
    with r2_2: st.markdown(render_player_box('3', ca['3']), unsafe_allow_html=True)
    
    r3_1, r3_2 = st.columns(2)
    with r3_1: st.markdown(render_player_box('1', ca['1'], is_server=(m['server'] == 'a')), unsafe_allow_html=True)
    with r3_2: st.markdown(render_player_box('2', ca['2']), unsafe_allow_html=True)

# TEAM B FIELD (ฝั่งขวา: ตำแหน่ง 1 อยู่ขวาบน)
with field_col2:
    st.markdown(f"### {m['team_b']} {'🏐' if m['server'] == 'b' else ''}")
    cb = st.session_state.match_data['players_b']['court']

    r1_1, r1_2 = st.columns(2)
    with r1_1: st.markdown(render_player_box('5', cb['5']), unsafe_allow_html=True)
    with r1_2: st.markdown(render_player_box('1', cb['1'], is_server=(m['server'] == 'b')), unsafe_allow_html=True)
    
    r2_1, r2_2 = st.columns(2)
    with r2_1: st.markdown(render_player_box('4', cb['4']), unsafe_allow_html=True)
    with r2_2: st.markdown(render_player_box('2', cb['2']), unsafe_allow_html=True)
    
    r3_1, r3_2 = st.columns(2)
    with r3_1: st.markdown(render_player_box('3', cb['3']), unsafe_allow_html=True)
    with r3_2: st.markdown(render_player_box('6', cb['6']), unsafe_allow_html=True)
