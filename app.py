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
    'round_name': 'รอบแบ่งกลุ่ม',
    'group_name': 'สาย A',
    'match_no': '1',
    'target_score_reg': 25,
    'target_score_tie': 15,
    'team_a': 'ทีม A',
    'team_b': 'ทีม B',
    'scores': [{'a': 0, 'b': 0}, {'a': 0, 'b': 0}, {'a': 0, 'b': 0}],
    'timeouts_a': [0, 0, 0],
    'timeouts_b': [0, 0, 0],
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
    'logs': [],
    'players_a_list': ['ตัวจริง A1', 'ตัวจริง A2', 'ตัวจริง A3', 'ตัวจริง A4', 'ตัวจริง A5', 'ตัวจริง A6'],
    'players_b_list': ['ตัวจริง B1', 'ตัวจริง B2', 'ตัวจริง B3', 'ตัวจริง B4', 'ตัวจริง B5', 'ตัวจริง B6'],
    'bench_a': ['สำรอง A1', 'สำรอง A2', 'สำรอง A3', 'สำรอง A4', 'สำรอง A5'],
    'bench_b': ['สำรอง B1', 'สำรอง B2', 'สำรอง B3', 'สำรอง B4', 'สำรอง B5'],
    'match_archives': [],
    'ui_key': 0
}

def load_shared_state():
    data = copy.deepcopy(DEFAULT_MATCH_DATA)
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                data.update(loaded)
                if 'match_archives' not in data: data['match_archives'] = []
                if 'timeouts_a' not in data: data['timeouts_a'] = [0, 0, 0]
                if 'timeouts_b' not in data: data['timeouts_b'] = [0, 0, 0]
        except Exception:
            pass
    return data

def save_shared_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if 'match_data' not in st.session_state:
    st.session_state.match_data = load_shared_state()

m = st.session_state.match_data
query_params = st.query_params
is_scoreboard = query_params.get("view") == "scoreboard"

def update_and_sync():
    save_shared_state(st.session_state.match_data)

def save_snapshot(action_text=""):
    m = st.session_state.match_data
    snapshot = {
        'scores': copy.deepcopy(m['scores']),
        'current_set': m['current_set'],
        'server': m['server'],
        'swapped_sides': m['swapped_sides'],
        'players_a_list': copy.deepcopy(m['players_a_list']),
        'players_b_list': copy.deepcopy(m['players_b_list']),
        'bench_a': copy.deepcopy(m['bench_a']),
        'bench_b': copy.deepcopy(m['bench_b']),
        'timeouts_a': copy.deepcopy(m['timeouts_a']),
        'timeouts_b': copy.deepcopy(m['timeouts_b'])
    }
    m['history'].append(snapshot)
    if len(m['history']) > 30: m['history'].pop(0)
    
    if action_text:
        now_str = time.strftime("%H:%M:%S")
        m['logs'].insert(0, f"[{now_str}] {action_text}")
        if len(m['logs']) > 50: m['logs'].pop()

def undo_last_action():
    m = st.session_state.match_data
    if m['history']:
        last_state = m['history'].pop()
        m['scores'] = last_state['scores']
        m['current_set'] = last_state['current_set']
        m['server'] = last_state['server']
        m['swapped_sides'] = last_state['swapped_sides']
        m['players_a_list'] = last_state.get('players_a_list', m['players_a_list'])
        m['players_b_list'] = last_state.get('players_b_list', m['players_b_list'])
        m['bench_a'] = last_state.get('bench_a', m['bench_a'])
        m['bench_b'] = last_state.get('bench_b', m['bench_b'])
        m['timeouts_a'] = last_state.get('timeouts_a', m['timeouts_a'])
        m['timeouts_b'] = last_state.get('timeouts_b', m['timeouts_b'])
        if m['logs']: m['logs'].pop(0)
        m['ui_key'] = m.get('ui_key', 0) + 1
        update_and_sync()

def check_set_winner(sa, sb, target):
    if (sa >= target or sb >= target) and abs(sa - sb) >= 2:
        return 'a' if sa > sb else 'b'
    return None

def calculate_sets_won(scores=None):
    if scores is None: scores = m['scores']
    sets_a, sets_b = 0, 0
    for i in range(3):
        target = m['target_score_reg'] if i < 2 else m['target_score_tie']
        winner = check_set_winner(scores[i]['a'], scores[i]['b'], target)
        if winner == 'a': sets_a += 1
        elif winner == 'b': sets_b += 1
    return sets_a, sets_b

def rotate_team_cw(team_key):
    m = st.session_state.match_data
    target_list = m['players_a_list'] if team_key == 'a' else m['players_b_list']
    first_player = target_list.pop(0)
    target_list.append(first_player)
    m['ui_key'] = m.get('ui_key', 0) + 1

def reset_positions():
    m = st.session_state.match_data
    save_snapshot("รีเซ็ตตำแหน่งสนามเป็นค่าเริ่มต้น")
    m['players_a_list'] = [f"ตัวจริง A{i+1}" for i in range(6)]
    m['players_b_list'] = [f"ตัวจริง B{i+1}" for i in range(6)]
    m['ui_key'] = m.get('ui_key', 0) + 1
    update_and_sync()

def get_current_court(team_key):
    m = st.session_state.match_data
    plist = m['players_a_list'] if team_key == 'a' else m['players_b_list']
    return {'1': plist[0], '2': plist[1], '3': plist[2], '4': plist[3], '5': plist[4], '6': plist[5]}

def substitute_player(team_key, pos_idx, bench_idx):
    m = st.session_state.match_data
    plist = m['players_a_list'] if team_key == 'a' else m['players_b_list']
    blist = m['bench_a'] if team_key == 'a' else m['bench_b']
    team_name = m['team_a'] if team_key == 'a' else m['team_b']
    out_player = plist[pos_idx]
    in_player = blist[bench_idx]
    plist[pos_idx] = in_player
    blist[bench_idx] = out_player
    m['ui_key'] = m.get('ui_key', 0) + 1
    save_snapshot(f"{team_name} เปลี่ยนตัว: {in_player} (เข้า) แทน {out_player} (ออก)")
    update_and_sync()

sets_won_a, sets_won_b = calculate_sets_won()
match_winner = None
if sets_won_a >= 2: match_winner = m['team_a']
elif sets_won_b >= 2: match_winner = m['team_b']

def add_score(team):
    if match_winner: return
    curr_set = m['current_set']
    team_name = m['team_a'] if team == 'a' else m['team_b']
    
    if m['server'] != team:
        m['server'] = team
        rotate_team_cw(team)
        server_name = get_current_court(team)['1']
        save_snapshot(f"{team_name} ได้แต้ม (เปลี่ยนเสิร์ฟ & หมุนตำแหน่ง -> {server_name} เสิร์ฟ)")
    else:
        save_snapshot(f"{team_name} ได้คะแนน (+1)")

    m['scores'][curr_set][team] += 1
    curr_target = m['target_score_reg'] if curr_set < 2 else m['target_score_tie']
    sa = m['scores'][curr_set]['a']
    sb = m['scores'][curr_set]['b']
    
    if check_set_winner(sa, sb, curr_target):
        new_sets_a, new_sets_b = calculate_sets_won()
        if new_sets_a < 2 and new_sets_b < 2 and curr_set < 2:
            m['current_set'] += 1
            m['swapped_sides'] = not m.get('swapped_sides', False)
            save_snapshot(f"จบเซตที่ {curr_set+1} สลับฝั่งอัตโนมัติ")
            
    update_and_sync()

def subtract_score(team):
    curr_set = m['current_set']
    if m['scores'][curr_set][team] > 0:
        team_name = m['team_a'] if team == 'a' else m['team_b']
        save_snapshot(f"{team_name} ลดคะแนน (-1)")
        m['scores'][curr_set][team] -= 1
        update_and_sync()

def trigger_timeout(team_key):
    curr_set = m['current_set']
    timeout_key = f'timeouts_{team_key}'
    
    if m[timeout_key][curr_set] < 2:
        m[timeout_key][curr_set] += 1
        team_name = m['team_a'] if team_key == 'a' else m['team_b']
        save_snapshot(f"{team_name} ขอเวลานอก (ครั้งที่ {m[timeout_key][curr_set]}/2)")
        m['timeout_active'] = True
        m['timeout_team_name'] = team_name
        m['timeout_end_time'] = time.time() + 30
        update_and_sync()

# =========================================================
# 📺 MODE 1: SCOREBOARD DISPLAY
# =========================================================
if is_scoreboard:
    if HAS_AUTOREFRESH: st_autorefresh(interval=1000, key="scoreboard_tick")
    m = load_shared_state()
    curr_set = m['current_set']
    
    if m.get('swapped_sides', False):
        left_team, right_team = 'b', 'a'
        left_name, right_name = m['team_b'], m['team_a']
        left_score, right_score = m['scores'][curr_set]['b'], m['scores'][curr_set]['a']
        left_color, right_color = "#ea580c", "#2563eb"
    else:
        left_team, right_team = 'a', 'b'
        left_name, right_name = m['team_a'], m['team_b']
        left_score, right_score = m['scores'][curr_set]['a'], m['scores'][curr_set]['b']
        left_color, right_color = "#2563eb", "#ea580c"

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
    st.markdown(f"<h1 style='text-align: center; font-size: 40px; margin-bottom: 0px;'>PT SPORT 2026 (คู่ที่ {m['match_no']} - {m['round_name']} {m['group_name']})</h1>", unsafe_allow_html=True)
    
    serve_left = " 🏐" if m['server'] == left_team else ""
    serve_right = " 🏐" if m['server'] == right_team else ""

    team_head_col1, vs_col, team_head_col2 = st.columns([5, 2, 5])
    with team_head_col1: st.markdown(f"<div style='border: 3px solid white; border-radius: 12px; padding: 12px; text-align: center; font-size: 32px; font-weight: bold;'>{left_name}{serve_left}</div>", unsafe_allow_html=True)
    with vs_col: st.markdown("<h1 style='text-align: center; margin: 0; font-size: 40px;'>VS</h1>", unsafe_allow_html=True)
    with team_head_col2: st.markdown(f"<div style='border: 3px solid white; border-radius: 12px; padding: 12px; text-align: center; font-size: 32px; font-weight: bold;'>{right_name}{serve_right}</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    sc_left, sc_center, sc_right = st.columns([4, 3, 4])

    with sc_left:
        st.markdown(f"<div style='border: 4px solid white; border-radius: 20px; padding: 20px; text-align: center; background-color: #0f172a;'><h1 style='font-size: 160px; margin: 0; color: {left_color}; font-weight: bold;'>{left_score:02d}</h1></div>", unsafe_allow_html=True)

    with sc_center:
        st.markdown(f"<div style='border: 2px solid white; border-radius: 10px; padding: 8px; text-align: center; font-size: 26px; font-weight: bold; background-color: #1e293b; margin-bottom: 15px;'><span style='color: {status_color}; font-size: 16px; margin-right: 8px;'>{status_badge}</span> ⏱️ {time_str}</div>", unsafe_allow_html=True)
        for s_idx in range(3):
            s_left = m['scores'][s_idx][left_team]
            s_right = m['scores'][s_idx][right_team]
            is_active = (s_idx == curr_set)
            st.markdown(f"<div style='border: {'3px solid #f59e0b' if is_active else '1px solid #64748b'}; border-radius: 8px; padding: 6px; text-align: center; background-color: {'#2563eb' if is_active else '#334155'}; margin-bottom: 8px;'><div style='font-size: 14px;'>SET {s_idx + 1}</div><div style='font-size: 22px; font-weight: bold;'>{s_left} - {s_right}</div></div>", unsafe_allow_html=True)

    with sc_right:
        st.markdown(f"<div style='border: 4px solid white; border-radius: 20px; padding: 20px; text-align: center; background-color: #0f172a;'><h1 style='font-size: 160px; margin: 0; color: {right_color}; font-weight: bold;'>{right_score:02d}</h1></div>", unsafe_allow_html=True)

    st.stop()

# =========================================================
# 🎛️ MODE 2: CONTROLLER PANEL
# =========================================================
if HAS_AUTOREFRESH: st_autorefresh(interval=1000, key="controller_tick")

st.title(f"🏐 PT SPORT 2026 CONTROLLER")

current_ui_key = m.get('ui_key', 0)

with st.sidebar:
    st.header("⚙️ ตั้งค่าข้อมูลการแข่งขัน")
    m['gender'] = st.radio("ประเภท", ["ชาย", "หญิง", "ผสม"], horizontal=True, index=["ชาย", "หญิง", "ผสม"].index(m['gender']))
    m['round_name'] = st.text_input("รอบ", m['round_name'])
    m['group_name'] = st.text_input("สาย", m['group_name'])
    m['match_no'] = st.text_input("คู่ที่", m['match_no'])
    m['target_score_reg'] = st.number_input("คะแนนเซตปกติ", min_value=1, value=m['target_score_reg'])
    m['target_score_tie'] = st.number_input("คะแนนเซตตัดสิน", min_value=1, value=m['target_score_tie'])
    m['team_a'] = st.text_input("ชื่อทีม A", m['team_a'])
    m['team_b'] = st.text_input("ชื่อทีม B", m['team_b'])
    
    st.markdown("---")
    
    with st.expander(f"🏃‍♂️ ผู้เล่น {m['team_a']}", expanded=False):
        for idx in range(6):
            m['players_a_list'][idx] = st.text_input(f"ตำแหน่ง {idx+1}", value=m['players_a_list'][idx], key=f"ma_{idx}_{current_ui_key}")
        for idx in range(len(m['bench_a'])):
            m['bench_a'][idx] = st.text_input(f"สำรอง {idx+1}", value=m['bench_a'][idx], key=f"ba_{idx}_{current_ui_key}")

    with st.expander(f"🏃‍♂️ ผู้เล่น {m['team_b']}", expanded=False):
        for idx in range(6):
            m['players_b_list'][idx] = st.text_input(f"ตำแหน่ง {idx+1}", value=m['players_b_list'][idx], key=f"mb_{idx}_{current_ui_key}")
        for idx in range(len(m['bench_b'])):
            m['bench_b'][idx] = st.text_input(f"สำรอง {idx+1}", value=m['bench_b'][idx], key=f"bb_{idx}_{current_ui_key}")

    if st.button("💾 บันทึกการแก้ไข", type="primary", use_container_width=True):
        update_and_sync()
        st.success("บันทึกสำเร็จ!")

tab_ctrl, tab_history, tab_archive = st.tabs(["🎮 ควบคุมการแข่ง", "📝 แก้ไขประวัติเซต", "🗄️ คลังประวัติการแข่งขัน"])

# 🟢 TAB 1: ควบคุมการแข่ง
with tab_ctrl:
    st.markdown(f"### 📌 คู่ที่ {m['match_no']} | **กำลังแข่ง: เซตที่ {m['current_set'] + 1}** (เป้าหมาย {m['target_score_reg'] if m['current_set'] < 2 else m['target_score_tie']} แต้ม)")

    # CONTROLS TIME
    start_col1, start_col2, start_col3, start_col4 = st.columns([2, 1.5, 1.5, 2])
    with start_col1:
        if not m['match_started']:
            if st.button("▶️ เริ่มเวลาแข่ง", type="primary", use_container_width=True):
                m['match_started'] = True
                m['match_paused'] = False
                m['start_time'] = time.time()
                m['accumulated_time'] = 0
                save_snapshot("เริ่มเวลา")
                st.rerun()
        elif m.get('match_paused', False):
            if st.button("▶️ เดินเวลาต่อ", type="primary", use_container_width=True):
                m['match_paused'] = False
                m['start_time'] = time.time()
                save_snapshot("เดินเวลาต่อ")
                st.rerun()
        else:
            elapsed = int(m.get('accumulated_time', 0) + (time.time() - m['start_time']))
            st.success(f"🔴 LIVE: ⏱️ {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")

    with start_col2:
        if m['match_started'] and not m.get('match_paused', False):
            if st.button("⏸️ พักเวลา", use_container_width=True):
                m['match_paused'] = True
                m['accumulated_time'] += (time.time() - m['start_time'])
                save_snapshot("หยุดเวลา")
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
        if st.button("↩️ เลิกทำ (Undo)", type="secondary", use_container_width=True):
            undo_last_action()
            st.rerun()

    st.markdown("---")

    # SCORE CONTROLS
    curr_set = m['current_set']
    col1, col2 = st.columns(2)

    with col1:
        t_name = m['team_a']
        with st.container(border=True):
            st.markdown(f"### {t_name} {'🏐 (เสิร์ฟ)' if m['server'] == 'a' else ''}")
            st.markdown(f"<h1 style='text-align: center; font-size: 80px; margin: 0; color: #2563eb;'>{m['scores'][curr_set]['a']}</h1>", unsafe_allow_html=True)
            
            if st.button(f"➕ ได้คะแนน ({t_name})", use_container_width=True, type="primary", key="add_a"):
                add_score('a')
                st.rerun()
            if st.button(f"➖ ลดคะแนน ({t_name})", use_container_width=True, key="sub_a"):
                subtract_score('a')
                st.rerun()
                    
            b3, b4 = st.columns(2)
            with b3:
                if st.button("🔄 หมุนตำแหน่งเอง", use_container_width=True, key="rot_a_btn"):
                    save_snapshot(f"{t_name} หมุนตำแหน่งเอง")
                    rotate_team_cw('a')
                    update_and_sync()
                    st.rerun()
            with b4:
                if st.button("🏐 ให้สิทธิ์เสิร์ฟ", use_container_width=True, key="srv_a"):
                    save_snapshot(f"เปลี่ยนสิทธิ์เสิร์ฟให้ {t_name}")
                    m['server'] = 'a'
                    update_and_sync()
                    st.rerun()

    with col2:
        t_name = m['team_b']
        with st.container(border=True):
            st.markdown(f"### {t_name} {'🏐 (เสิร์ฟ)' if m['server'] == 'b' else ''}")
            st.markdown(f"<h1 style='text-align: center; font-size: 80px; margin: 0; color: #ea580c;'>{m['scores'][curr_set]['b']}</h1>", unsafe_allow_html=True)
            
            if st.button(f"➕ ได้คะแนน ({t_name})", use_container_width=True, type="primary", key="add_b"):
                add_score('b')
                st.rerun()
            if st.button(f"➖ ลดคะแนน ({t_name})", use_container_width=True, key="sub_b"):
                subtract_score('b')
                st.rerun()
                    
            b3, b4 = st.columns(2)
            with b3:
                if st.button("🔄 หมุนตำแหน่งเอง", use_container_width=True, key="rot_b_btn"):
                    save_snapshot(f"{t_name} หมุนตำแหน่งเอง")
                    rotate_team_cw('b')
                    update_and_sync()
                    st.rerun()
            with b4:
                if st.button("🏐 ให้สิทธิ์เสิร์ฟ", use_container_width=True, key="srv_b"):
                    save_snapshot(f"เปลี่ยนสิทธิ์เสิร์ฟให้ {t_name}")
                    m['server'] = 'b'
                    update_and_sync()
                    st.rerun()

    # ⏱️ ปุ่มขอเวลานอก & จัดการสนาม
    st.markdown("<br>", unsafe_allow_html=True)
    to_col1, to_col2, to_col3 = st.columns([2, 2, 2])
    with to_col1:
        to_a_used = m['timeouts_a'][curr_set]
        if st.button(f"⏱️ ขอเวลานอก {m['team_a']} ({to_a_used}/2)", use_container_width=True, disabled=(to_a_used >= 2)):
            trigger_timeout('a')
            st.rerun()
    with to_col2:
        to_b_used = m['timeouts_b'][curr_set]
        if st.button(f"⏱️ ขอเวลานอก {m['team_b']} ({to_b_used}/2)", use_container_width=True, disabled=(to_b_used >= 2)):
            trigger_timeout('b')
            st.rerun()
    with to_col3:
        if st.button("🔄 สลับฝั่งสนาม (บอร์ดใหญ่)", use_container_width=True):
            m['swapped_sides'] = not m.get('swapped_sides', False)
            update_and_sync()
            st.rerun()

    if m.get('timeout_active', False):
        rem_timeout = int(m['timeout_end_time'] - time.time())
        if rem_timeout <= 0:
            m['timeout_active'] = False
            update_and_sync()
        else:
            st.warning(f"⏱️ **{m['timeout_team_name']}** กำลังขอเวลานอก | เหลือเวลา: {rem_timeout:02d} วินาที")

    st.markdown("---")
    
    # วาดสนามขนาดย่อ
    def render_player_box(pos_num, player_name, is_server=False):
        border_color = "#f59e0b" if is_server else "#475569"
        bg_color = "#1e293b" if not is_server else "#312e81"
        return f"""<div style="border: 2px solid {border_color}; border-radius: 8px; padding: 4px; text-align: center; background-color: {bg_color}; margin-bottom: 6px;"><div style="font-size: 10px; color: #f59e0b;">Pos {pos_num}</div><div style="font-size: 14px; font-weight: bold; color: white;">{player_name}</div></div>"""

    field_col1, field_col2 = st.columns(2)
    court_a = get_current_court('a')
    court_b = get_current_court('b')

    with field_col1:
        st.markdown(f"**{m['team_a']}** (ซ้าย: ท้ายสนาม | ขวา: ติดเน็ต)")
        r1_1, r1_2 = st.columns(2)
        with r1_1: st.markdown(render_player_box('5', court_a['5']), unsafe_allow_html=True)
        with r1_2: st.markdown(render_player_box('4', court_a['4']), unsafe_allow_html=True)
        r2_1, r2_2 = st.columns(2)
        with r2_1: st.markdown(render_player_box('6', court_a['6']), unsafe_allow_html=True)
        with r2_2: st.markdown(render_player_box('3', court_a['3']), unsafe_allow_html=True)
        r3_1, r3_2 = st.columns(2)
        with r3_1: st.markdown(render_player_box('1', court_a['1'], (m['server'] == 'a')), unsafe_allow_html=True)
        with r3_2: st.markdown(render_player_box('2', court_a['2']), unsafe_allow_html=True)

        with st.expander("🔄 เปลี่ยนตัว"):
            s1, s2, s3 = st.columns(3)
            with s1: sel_a_out = st.selectbox("ออก", options=[f"{i+1}:{p}" for i,p in enumerate(m['players_a_list'])], key="sa_o")
            with s2: sel_a_in = st.selectbox("เข้า", options=[f"{i+1}:{p}" for i,p in enumerate(m['bench_a'])], key="sa_i")
            with s3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("เปลี่ยน", key="b_sub_a"):
                    substitute_player('a', int(sel_a_out.split(":")[0])-1, int(sel_a_in.split(":")[0])-1)
                    st.rerun()

    with field_col2:
        st.markdown(f"**{m['team_b']}** (ซ้าย: ติดเน็ต | ขวา: ท้ายสนาม)")
        r1_1, r1_2 = st.columns(2)
        with r1_1: st.markdown(render_player_box('2', court_b['2']), unsafe_allow_html=True)
        with r1_2: st.markdown(render_player_box('1', court_b['1'], (m['server'] == 'b')), unsafe_allow_html=True)
        r2_1, r2_2 = st.columns(2)
        with r2_1: st.markdown(render_player_box('3', court_b['3']), unsafe_allow_html=True)
        with r2_2: st.markdown(render_player_box('6', court_b['6']), unsafe_allow_html=True)
        r3_1, r3_2 = st.columns(2)
        with r3_1: st.markdown(render_player_box('4', court_b['4']), unsafe_allow_html=True)
        with r3_2: st.markdown(render_player_box('5', court_b['5']), unsafe_allow_html=True)

        with st.expander("🔄 เปลี่ยนตัว"):
            s1, s2, s3 = st.columns(3)
            with s1: sel_b_out = st.selectbox("ออก", options=[f"{i+1}:{p}" for i,p in enumerate(m['players_b_list'])], key="sb_o")
            with s2: sel_b_in = st.selectbox("เข้า", options=[f"{i+1}:{p}" for i,p in enumerate(m['bench_b'])], key="sb_i")
            with s3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("เปลี่ยน", key="b_sub_b"):
                    substitute_player('b', int(sel_b_out.split(":")[0])-1, int(sel_b_in.split(":")[0])-1)
                    st.rerun()

    # 🟢 ย้ายปุ่มจบการแข่งขันมาไว้ล่างสุดของหน้าควบคุม
    st.markdown("---")
    st.subheader("🏁 จัดการหลังจบการแข่งขัน")
    
    sets_a, sets_b = calculate_sets_won()
    if sets_a >= 2 or sets_b >= 2:
        winner_name = m['team_a'] if sets_a >= 2 else m['team_b']
        st.success(f"🎉 แมตช์นี้จบแล้ว! ผู้ชนะคือ **{winner_name}** ({sets_a} - {sets_b} เซต)")
        button_type = "primary"
    else:
        st.info("แมตช์ยังไม่จบ (ต้องชนะ 2 ใน 3 เซต)")
        button_type = "secondary"

    if st.button("🏁 จบการแข่งขันคู่นี้และบันทึกลงคลัง", type=button_type, use_container_width=True):
        match_record = {
            'id': time.time(),
            'match_no': m['match_no'],
            'round_name': m['round_name'],
            'group_name': m['group_name'],
            'team_a': m['team_a'],
            'team_b': m['team_b'],
            'scores': copy.deepcopy(m['scores'])
        }
        m['match_archives'].insert(0, match_record)
        
        # Reset data สำหรับคู่ถัดไป
        m['scores'] = [{'a': 0, 'b': 0}, {'a': 0, 'b': 0}, {'a': 0, 'b': 0}]
        m['current_set'] = 0
        m['timeouts_a'] = [0, 0, 0]
        m['timeouts_b'] = [0, 0, 0]
        m['match_started'] = False
        m['match_paused'] = False
        m['accumulated_time'] = 0
        update_and_sync()
        st.success("บันทึกแมตช์ลงคลังและรีเซ็ตบอร์ดเรียบร้อย!")
        st.rerun()

# 🟢 TAB 2: แก้ไขประวัติเซต
with tab_history:
    st.markdown("### 📝 แก้ไขคะแนนแต่ละเซต (Manual Override)")
    st.info("คุณสามารถแก้ไขตัวเลขคะแนนของเซตที่กำลังแข่ง หรือเซตที่จบไปแล้วได้ที่นี่")
    
    for i in range(3):
        st.markdown(f"**เซตที่ {i+1}**")
        c1, c2 = st.columns(2)
        with c1:
            new_a = st.number_input(f"คะแนน {m['team_a']}", min_value=0, value=m['scores'][i]['a'], key=f"edit_a_{i}")
        with c2:
            new_b = st.number_input(f"คะแนน {m['team_b']}", min_value=0, value=m['scores'][i]['b'], key=f"edit_b_{i}")
        
        if new_a != m['scores'][i]['a'] or new_b != m['scores'][i]['b']:
            m['scores'][i]['a'] = new_a
            m['scores'][i]['b'] = new_b
            update_and_sync()
            st.success(f"บันทึกเซตที่ {i+1} เรียบร้อย!")
    
    st.markdown("---")
    st.selectbox("กำหนดเซตปัจจุบันเอง", [1, 2, 3], index=m['current_set'], key="edit_curr_set", on_change=lambda: m.update({'current_set': st.session_state.edit_curr_set - 1}) or update_and_sync())

# 🟢 TAB 3: ประวัติการแข่งขัน (Archive)
with tab_archive:
    st.markdown("### 🗄️ คลังประวัติการแข่งขันที่จบแล้ว")
    
    if m['match_archives']:
        for idx, arc in enumerate(m['match_archives']):
            with st.expander(f"คู่ที่ {arc['match_no']}: {arc['team_a']} VS {arc['team_b']} ({arc['round_name']})"):
                ac1, ac2 = st.columns(2)
                for s_idx in range(3):
                    with ac1:
                        new_sa = st.number_input(f"เซต {s_idx+1} ({arc['team_a']})", value=arc['scores'][s_idx]['a'], key=f"arc_{idx}_a_{s_idx}")
                    with ac2:
                        new_sb = st.number_input(f"เซต {s_idx+1} ({arc['team_b']})", value=arc['scores'][s_idx]['b'], key=f"arc_{idx}_b_{s_idx}")
                    
                    if new_sa != arc['scores'][s_idx]['a'] or new_sb != arc['scores'][s_idx]['b']:
                        m['match_archives'][idx]['scores'][s_idx]['a'] = new_sa
                        m['match_archives'][idx]['scores'][s_idx]['b'] = new_sb
                        update_and_sync()
                        st.success("บันทึกการแก้ไขประวัติเรียบร้อย")
    else:
        st.info("ยังไม่มีประวัติการแข่งขันที่จบแล้ว")
