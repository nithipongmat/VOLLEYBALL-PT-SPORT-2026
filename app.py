import streamlit as st
import pandas as pd
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

# --- CHECK VIEW MODE ---
query_params = st.query_params
is_scoreboard = query_params.get("view") == "scoreboard"

DEFAULT_COURT_A = ['ผู้เล่น A1', 'ผู้เล่น A2', 'ผู้เล่น A3', 'ผู้เล่น A4', 'ผู้เล่น A5', 'ผู้เล่น A6']
DEFAULT_COURT_B = ['ผู้เล่น B1', 'ผู้เล่น B2', 'ผู้เล่น B3', 'ผู้เล่น B4', 'ผู้เล่น B5', 'ผู้เล่น B6']

# --- INITIALIZE SESSION STATE ---
if 'match_data' not in st.session_state:
    st.session_state.match_data = {
        'gender': 'ผสม',
        'round_name': '',
        'group_name': '',
        'match_no': '',
        'target_score_reg': 25,
        'target_score_tie': 15,
        'team_a': 'บุคลากร',
        'team_b': 'นักศึกษาชั้นปีที่ 2',
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
        'players_a': {'court': list(DEFAULT_COURT_A), 'bench': ['สำรอง A1', 'สำรอง A2', 'สำรอง A3']},
        'players_b': {'court': list(DEFAULT_COURT_B), 'bench': ['สำรอง B1', 'สำรอง B2', 'สำรอง B3']}
    }

if 'history' not in st.session_state:
    st.session_state.history = []

if 'completed_matches' not in st.session_state:
    st.session_state.completed_matches = []

# --- HELPER FUNCTIONS ---
def save_history():
    st.session_state.history.append(copy.deepcopy(st.session_state.match_data))

def undo_last_action():
    if st.session_state.history:
        st.session_state.match_data = st.session_state.history.pop()

def rotate_team_cw(team_key):
    r = st.session_state.match_data[f'players_{team_key}']['court']
    st.session_state.match_data[f'players_{team_key}']['court'] = r[1:] + [r[0]]

def rotate_team_ccw(team_key):
    r = st.session_state.match_data[f'players_{team_key}']['court']
    st.session_state.match_data[f'players_{team_key}']['court'] = [r[-1]] + r[:-1]

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
    save_history()
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

def minus_score(team):
    curr_set = st.session_state.match_data['current_set']
    if st.session_state.match_data['scores'][curr_set][team] > 0:
        save_history()
        st.session_state.match_data['scores'][curr_set][team] -= 1

# =========================================================
# 📺 MODE 1: SCOREBOARD ( auto-refresh ทุก 1 วินาที )
# =========================================================
if is_scoreboard:
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=1000, key="scoreboard_tick")

    m = st.session_state.match_data
    curr_set = m['current_set']

    is_swapped = m['swapped_sides']
    left_team = 'b' if is_swapped else 'a'
    right_team = 'a' if is_swapped else 'b'

    left_name = m[f'team_{left_team}']
    right_name = m[f'team_{right_team}']

    if m.get('timeout_active', False):
        rem_timeout = int(m['timeout_end_time'] - time.time())
        if rem_timeout <= 0:
            st.session_state.match_data['timeout_active'] = False
        else:
            st.markdown(f"""
            <div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                        background-color: rgba(15, 23, 42, 0.96); z-index: 99999;
                        display: flex; flex-direction: column; align-items: center; justify-content: center;
                        color: white; font-family: sans-serif;">
                <div style="font-size: 40px; font-weight: bold; color: #f59e0b; margin-bottom: 10px;">⏱️ ขอเวลานอก (TIME-OUT)</div>
                <div style="font-size: 50px; font-weight: bold; color: #ffffff; background: #1e293b; padding: 15px 40px; border-radius: 15px; border: 3px solid #f59e0b; margin-bottom: 20px;">
                    {m['timeout_team_name']}
                </div>
                <div style="font-size: 150px; font-weight: bold; color: #ef4444; text-shadow: 0 0 25px rgba(239, 68, 68, 0.8); line-height: 1;">
                    {rem_timeout:02d}
                </div>
                <div style="font-size: 24px; color: #94a3b8; margin-top: 20px;">วินาที</div>
            </div>
            """, unsafe_allow_html=True)

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
st.title("🏐 PT SPORT 2026 VOLLEYBALL SCORE")

# SIDEBAR
with st.sidebar:
    st.header("⚙️ ตั้งค่าการแข่งขัน")
    st.session_state.match_data['gender'] = st.radio("ประเภท", ["ชาย", "หญิง", "ผสม"], horizontal=True)
    st.session_state.match_data['round_name'] = st.text_input("รอบ", st.session_state.match_data['round_name'])
    st.session_state.match_data['group_name'] = st.text_input("สาย", st.session_state.match_data['group_name'])
    st.session_state.match_data['match_no'] = st.text_input("คู่ที่", st.session_state.match_data['match_no'])
    
    st.markdown("---")
    st.subheader("🎯 เกณฑ์คะแนน")
    st.session_state.match_data['target_score_reg'] = st.number_input("เซตปกติ", min_value=1, value=st.session_state.match_data['target_score_reg'])
    st.session_state.match_data['target_score_tie'] = st.number_input("เซตตัดสิน", min_value=1, value=st.session_state.match_data['target_score_tie'])
    
    st.markdown("---")
    st.subheader("👥 ชื่อทีม")
    st.session_state.match_data['team_a'] = st.text_input("ทีม A", st.session_state.match_data['team_a'])
    st.session_state.match_data['team_b'] = st.text_input("ทีม B", st.session_state.match_data['team_b'])

# CONTROL BAR
m = st.session_state.match_data
start_col1, start_col2, start_col3 = st.columns([2, 1, 1])
with start_col1:
    if not m['match_started']:
        if st.button("▶️ เริ่มการแข่งขัน (Start Match)", type="primary", use_container_width=True):
            save_history()
            st.session_state.match_data['match_started'] = True
            st.session_state.match_data['start_time'] = time.time()
            st.rerun()
    else:
        st.success("🟢 **สถานะ:** กำลังแข่งขัน")

with start_col2:
    if st.button("↩️ ย้อนกลับ (Undo)", use_container_width=True):
        undo_last_action()
        st.rerun()

with start_col3:
    if st.button("🔄 สลับฝั่ง (Swap)", use_container_width=True):
        save_history()
        toggle_sides()
        st.rerun()

st.markdown("---")

# MAIN SCORE DISPLAY & CONTROLS
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
to_col1, to_col2 = st.columns(2)

with to_col1:
    left_name = m[f'team_{left_team}']
    if st.button(f"⏱️ ขอเวลานอก {left_name} (30 วินาที)", use_container_width=True):
        save_history()
        st.session_state.match_data['timeout_active'] = True
        st.session_state.match_data['timeout_team_name'] = left_name
        st.session_state.match_data['timeout_end_time'] = time.time() + 30
        st.success(f"เริ่มขอเวลานอก: {left_name}")

with to_col2:
    right_name = m[f'team_{right_team}']
    if st.button(f"⏱️ ขอเวลานอก {right_name} (30 วินาที)", use_container_width=True):
        save_history()
        st.session_state.match_data['timeout_active'] = True
        st.session_state.match_data['timeout_team_name'] = right_name
        st.session_state.match_data['timeout_end_time'] = time.time() + 30
        st.success(f"เริ่มขอเวลานอก: {right_name}")

# PLAYER ROTATION MANAGEMENT
st.markdown("---")
st.subheader("🏃 จัดการผู้เล่นและตำแหน่ง (Rotation)")

rot_col1, rot_col2 = st.columns(2)

def render_player_management(team_key):
    t_name = m[f'team_{team_key}']
    st.markdown(f"#### ทีม {t_name}")
    court = m[f'players_{team_key}']['court']
    bench = m[f'players_{team_key}']['bench']

    st.write("**ผู้เล่นในสนาม (6 คน):**")
    pos_labels = ["4 (หน้าซ้าย)", "3 (หน้ากลาง)", "2 (หน้าขวา)", "5 (หลังซ้าย)", "6 (หลังกลาง)", "1 (หลังขวา - เสิร์ฟ)"]
    for i in range(6):
        court[i] = st.text_input(f"ตำแหน่ง {pos_labels[i]}", value=court[i], key=f"p_{team_key}_{i}")

    r_col1, r_col2 = st.columns(2)
    with r_col1:
        if st.button(f"🔄 หมุนตามเข็ม (CW)", key=f"cw_{team_key}", use_container_width=True):
            save_history()
            rotate_team_cw(team_key)
            st.rerun()
    with r_col2:
        if st.button(f"↩️ หมุนทวนเข็ม (CCW)", key=f"ccw_{team_key}", use_container_width=True):
            save_history()
            rotate_team_ccw(team_key)
            st.rerun()

    st.write("**ผู้เล่นสำรอง:**")
    sub_out = st.selectbox("เลือกคนในสนามที่จะออก", court, key=f"out_{team_key}")
    sub_in = st.selectbox("เลือกคนสำรองที่จะเข้า", bench, key=f"in_{team_key}")
    if st.button(f"🔄 เปลี่ยนตัวผู้เล่น ({t_name})", key=f"sub_btn_{team_key}"):
        save_history()
        idx = court.index(sub_out)
        bench_idx = bench.index(sub_in)
        court[idx], bench[bench_idx] = bench[bench_idx], court[idx]
        st.success("เปลี่ยนตัวสำเร็จ!")
        st.rerun()

with rot_col1:
    render_player_management(left_team)

with rot_col2:
    render_player_management(right_team)

# EXPORT DATA
st.markdown("---")
st.subheader("📊 ส่งออกข้อมูลการแข่งขัน (Excel)")
if st.button("📥 ดาวน์โหลดรายงานสรุป (Excel)", type="secondary"):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Match Report')
    
    worksheet.write('A1', 'รายงานผลการแข่งขันวอลเลย์บอล PT SPORT 2026')
    worksheet.write('A3', f"ทีม A: {m['team_a']}")
    worksheet.write('B3', f"ทีม B: {m['team_b']}")
    worksheet.write('A4', f"ผลการแข่ง: เซต {sets_won_a} - {sets_won_b}")
    
    workbook.close()
    output.seek(0)
    
    st.download_button(
        label="💾 คลิกเพื่อดาวน์โหลดไฟล์ Excel",
        data=output,
        file_name="volleyball_match_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
