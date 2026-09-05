import streamlit as st
import copy
import time
from io import BytesIO
import pandas as pd
import xlsxwriter

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="PT SPORT 2026",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# CSS / UI
# =========================================================

st.markdown("""
<style>

.main {
    padding-top: 1rem;
}

.block-container {
    max-width: 1400px;
    padding-top: 1rem;
}

/* Header */
.app-header {
    text-align: center;
    padding: 12px 10px 20px 10px;
}

.app-title {
    font-size: 2.2rem;
    font-weight: 800;
    margin-bottom: 0;
}

.app-subtitle {
    opacity: .65;
    font-size: .95rem;
}

/* Score */
.score-card {
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 20px;
    padding: 22px;
    text-align: center;
    background: rgba(128,128,128,.06);
}

.team-name {
    font-size: 1.35rem;
    font-weight: 700;
}

.score-number {
    font-size: 6rem;
    line-height: 1;
    font-weight: 800;
    margin: 10px 0 20px 0;
}

.serving {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 20px;
    background: #16a34a;
    color: white;
    font-size: .85rem;
    font-weight: 700;
}

/* Set tabs */
.set-box {
    text-align: center;
    padding: 10px;
    border-radius: 12px;
    border: 1px solid rgba(128,128,128,.2);
}

.set-active {
    border: 2px solid #2563eb;
}

/* Court */
.court-container {
    background: #1e293b;
    border: 2px solid #334155;
    border-radius: 15px;
    padding: 15px;
}

.player-box {
    background: white;
    color: #111827;
    border-radius: 10px;
    min-height: 65px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    margin-bottom: 10px;
    border: 2px solid #cbd5e1;
}

.player-box.server {
    border: 3px solid #ef4444;
    background: #fef2f2;
}

.position-tag {
    font-size: .75rem;
    color: #0284c7;
    font-weight: 800;
}

/* Mobile */
@media (max-width: 768px) {
    .app-title { font-size: 1.6rem; }
    .score-number { font-size: 4rem; }
    .team-name { font-size: 1rem; }
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# DEFAULT DATA (Index 0=Pos1, 1=Pos2, ..., 5=Pos6)
# =========================================================

DEFAULT_A = [
    "ผู้เล่น A1 (Pos1)",
    "ผู้เล่น A2 (Pos2)",
    "ผู้เล่น A3 (Pos3)",
    "ผู้เล่น A4 (Pos4)",
    "ผู้เล่น A5 (Pos5)",
    "ผู้เล่น A6 (Pos6)"
]

DEFAULT_B = [
    "ผู้เล่น B1 (Pos1)",
    "ผู้เล่น B2 (Pos2)",
    "ผู้เล่น B3 (Pos3)",
    "ผู้เล่น B4 (Pos4)",
    "ผู้เล่น B5 (Pos5)",
    "ผู้เล่น B6 (Pos6)"
]


def new_match():
    return {
        "gender": "ผสม",
        "round_name": "",
        "group_name": "",
        "match_no": "",

        "team_a": "ทีม A",
        "team_b": "ทีม B",

        "target_reg": 25,
        "target_tie": 15,

        "scores": [
            {"a": 0, "b": 0},
            {"a": 0, "b": 0},
            {"a": 0, "b": 0}
        ],

        "current_set": 0,
        "server": "a",
        "swapped": False,

        "timeouts": {
            "a": [[False, False] for _ in range(3)],
            "b": [[False, False] for _ in range(3)]
        },

        "players_a": {
            "court": DEFAULT_A.copy(),
            "bench": ["สำรอง A1", "สำรอง A2", "สำรอง A3"]
        },

        "players_b": {
            "court": DEFAULT_B.copy(),
            "bench": ["สำรอง B1", "สำรอง B2", "สำรอง B3"]
        }
    }


# =========================================================
# SESSION STATE
# =========================================================

if "match" not in st.session_state:
    st.session_state.match = new_match()

if "undo" not in st.session_state:
    st.session_state.undo = []

if "history" not in st.session_state:
    st.session_state.history = []


# =========================================================
# HELPER
# =========================================================

def save_undo():
    st.session_state.undo.append(copy.deepcopy(st.session_state.match))


def undo():
    if st.session_state.undo:
        st.session_state.match = st.session_state.undo.pop()
        st.toast("↩️ ย้อนกลับเรียบร้อย")
        st.rerun()
    else:
        st.warning("ยังไม่มีรายการให้ Undo")


def set_target(set_no):
    if set_no < 2:
        return st.session_state.match["target_reg"]
    return st.session_state.match["target_tie"]


def set_winner(score_a, score_b, target):
    if max(score_a, score_b) >= target:
        if abs(score_a - score_b) >= 2:
            return "a" if score_a > score_b else "b"
    return None


def sets_won():
    a, b = 0, 0
    for i in range(3):
        winner = set_winner(
            st.session_state.match["scores"][i]["a"],
            st.session_state.match["scores"][i]["b"],
            set_target(i)
        )
        if winner == "a": a += 1
        elif winner == "b": b += 1
    return a, b


def match_winner():
    a, b = sets_won()
    if a >= 2: return "a"
    if b >= 2: return "b"
    return None


# 🔄 หมุนตำแหน่งตามเข็มนาฬิกา (Pos 1 -> 6 -> 5 -> 4 -> 3 -> 2 -> 1)
def rotate_cw(team, save_state=True):
    if save_state:
        save_undo()
    players = st.session_state.match[f"players_{team}"]["court"]
    # ย้ายผู้เล่นตำแหน่ง Pos 6 (Index 5) มาไว้ที่ Pos 1 (Index 0)
    st.session_state.match[f"players_{team}"]["court"] = [players[-1]] + players[:-1]


def rotate(team):
    rotate_cw(team, save_state=True)
    st.rerun()


def substitute(team, out_player, in_player):
    save_undo()
    data = st.session_state.match[f"players_{team}"]
    out_index = data["court"].index(out_player)
    in_index = data["bench"].index(in_player)

    data["court"][out_index], data["bench"][in_index] = (
        data["bench"][in_index],
        data["court"][out_index]
    )
    st.rerun()


def add_score(team):
    if match_winner():
        return

    save_undo()
    m = st.session_state.match
    current = m["current_set"]

    # Side-out: ถ้าฝั่งที่ได้คะแนนไม่ได้เป็นฝ่ายเสิร์ฟ -> ได้สิทธิ์เสิร์ฟ + หมุนตำแหน่ง
    if m["server"] != team:
        m["server"] = team
        rotate_cw(team, save_state=False)

    m["scores"][current][team] += 1

    winner = set_winner(
        m["scores"][current]["a"],
        m["scores"][current]["b"],
        set_target(current)
    )

    if winner:
        a, b = sets_won()
        if a < 2 and b < 2 and current < 2:
            m["current_set"] += 1
            m["swapped"] = not m["swapped"]

    st.rerun()


def minus_score(team):
    m = st.session_state.match
    current = m["current_set"]
    if m["scores"][current][team] > 0:
        save_undo()
        m["scores"][current][team] -= 1
        st.rerun()


def reset_match():
    st.session_state.match = new_match()
    st.session_state.undo = []
    st.rerun()


# =========================================================
# HEADER
# =========================================================

st.markdown("""
<div class="app-header">
    <div class="app-title">🏐 PT SPORT 2026</div>
    <div class="app-subtitle">VOLLEYBALL SCORE SYSTEM</div>
</div>
""", unsafe_allow_html=True)


# =========================================================
# TOP INFO
# =========================================================

m = st.session_state.match

with st.expander("⚙️ ตั้งค่าการแข่งขัน", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        m["gender"] = st.selectbox("ประเภทการแข่งขัน", ["ชาย", "หญิง", "ผสม"])
        m["round_name"] = st.text_input("รอบการแข่งขัน", m["round_name"])
    with c2:
        m["group_name"] = st.text_input("สาย", m["group_name"])
        m["match_no"] = st.text_input("คู่ที่", m["match_no"])
    with c3:
        m["team_a"] = st.text_input("ทีม A", m["team_a"])
        m["team_b"] = st.text_input("ทีม B", m["team_b"])

    c1, c2 = st.columns(2)
    with c1:
        m["target_reg"] = st.number_input("คะแนนเซต 1–2", min_value=1, value=m["target_reg"])
    with c2:
        m["target_tie"] = st.number_input("คะแนนเซต 3", min_value=1, value=m["target_tie"])


# =========================================================
# MATCH STATUS
# =========================================================

a_sets, b_sets = sets_won()
winner = match_winner()
current = m["current_set"]
target = set_target(current)

st.markdown(
    f"""
    ### 🏆 เซตที่ {current + 1}
    **เป้าหมาย {target} คะแนน** | เซตรวม: **{a_sets} - {b_sets}**
    """
)


# =========================================================
# SET SELECTOR
# =========================================================

cols = st.columns(3)
for i in range(3):
    with cols[i]:
        sa = m["scores"][i]["a"]
        sb = m["scores"][i]["b"]
        if st.button(
            f"SET {i+1}\n{sa} - {sb}",
            use_container_width=True,
            type="primary" if i == current else "secondary"
        ):
            m["current_set"] = i
            st.rerun()


# =========================================================
# SCOREBOARD
# =========================================================

st.markdown("---")

left = "b" if m["swapped"] else "a"
right = "a" if m["swapped"] else "b"


def score_card(team):
    name = m[f"team_{team}"]
    score = m["scores"][current][team]
    serving = m["server"] == team

    st.markdown(
        f"""
        <div class="score-card">
            <div class="team-name">{name}</div>
            {"<span class='serving'>🟢 SERVE</span>" if serving else ""}
            <div class="score-number">{score}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(
        f"🏐 +1 {name}",
        key=f"plus_{team}",
        use_container_width=True,
        disabled=bool(winner)
    ):
        add_score(team)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("− 1", key=f"minus_{team}", use_container_width=True):
            minus_score(team)
    with c2:
        if st.button("🏐 Serve", key=f"serve_{team}", use_container_width=True):
            save_undo()
            m["server"] = team
            st.rerun()


c1, c2 = st.columns(2)
with c1: score_card(left)
with c2: score_card(right)


# =========================================================
# WINNER
# =========================================================

if winner:
    winner_name = m[f"team_{winner}"]
    st.success(f"🏆 การแข่งขันจบแล้ว — {winner_name} ชนะ {a_sets} - {b_sets} เซต")
    st.balloons()


# =========================================================
# UNDO / ACTION BUTTONS
# =========================================================

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("↩️ Undo", use_container_width=True):
        undo()
with c2:
    if st.button("🔄 สลับฝั่ง", use_container_width=True):
        save_undo()
        m["swapped"] = not m["swapped"]
        st.rerun()
with c3:
    if st.button("🆕 แมตช์ใหม่", use_container_width=True):
        reset_match()


# =========================================================
# COURT (ผังตำแหน่งเรียงแบบ 5-4 / 6-3 / 1-2)
# =========================================================

st.markdown("---")
st.subheader("🏟️ Rotation / ผังตำแหน่งผู้เล่นในสนาม")


def court(team):
    players = m[f"players_{team}"]["court"]
    name = m[f"team_{team}"]
    is_server_team = (m["server"] == team)

    st.markdown(f"### **{name}**")

    # Map ตำแหน่งตามลูปวอลเลย์บอล: Index 0=P1, 1=P2, 2=P3, 3=P4, 4=P5, 5=P6
    # จัดเรียงตามผัง:
    # 5  4  (แถวหน้า/แดนหน้า)
    # 6  3  (แถวกลาง)
    # 1  2  (แถวหลัง/แดนหลัง)
    layout = [
        [(5, players[4]), (4, players[3])],
        [(6, players[5]), (3, players[2])],
        [(1, players[0]), (2, players[1])]
    ]

    with st.container():
        st.markdown('<div class="court-container">', unsafe_allow_html=True)
        for row in layout:
            col1, col2 = st.columns(2)
            for idx, (pos, player_name) in enumerate(row):
                target_col = col1 if idx == 0 else col2
                is_server = is_server_team and (pos == 1)
                server_class = "server" if is_server else ""
                server_badge = " 🏐 (เสิร์ฟ)" if is_server else ""

                with target_col:
                    st.markdown(
                        f"""
                        <div class="player-box {server_class}">
                            <div class="position-tag">POS {pos}{server_badge}</div>
                            <div>{player_name}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button(f"↻ หมุนตำแหน่ง {name}", key=f"rotate_{team}", use_container_width=True):
        rotate(team)


c1, c2 = st.columns(2)
with c1: court("a")
with c2: court("b")


# =========================================================
# SUBSTITUTION
# =========================================================

st.markdown("---")
st.subheader("🔄 เปลี่ยนตัวผู้เล่น")

c1, c2 = st.columns(2)
for col, team in zip([c1, c2], ["a", "b"]):
    with col:
        name = m[f"team_{team}"]
        data = m[f"players_{team}"]

        out_player = st.selectbox(
            f"ตัวจริงออก — {name}",
            data["court"],
            key=f"out_{team}_{m['scores'][current][team]}"
        )

        in_player = st.selectbox(
            f"ตัวสำรองเข้า — {name}",
            data["bench"],
            key=f"in_{team}_{m['scores'][current][team]}"
        )

        if st.button(f"ยืนยันเปลี่ยนตัว {name}", key=f"sub_btn_{team}", use_container_width=True):
            substitute(team, out_player, in_player)


# =========================================================
# TIMEOUT
# =========================================================

st.markdown("---")
st.subheader("⏱️ Timeout")

c1, c2 = st.columns(2)
for col, team in zip([c1, c2], ["a", "b"]):
    with col:
        used = sum(m["timeouts"][team][current])
        name = m[f"team_{team}"]

        st.write(f"**{name} — ใช้ไป {used}/2 ครั้ง**")

        if st.button(
            f"⏱️ ขอเวลานอก {name}",
            key=f"timeout_{team}",
            use_container_width=True,
            disabled=used >= 2
        ):
            save_undo()
            m["timeouts"][team][current][used] = True
            st.rerun()


# =========================================================
# NEXT SET
# =========================================================

if current < 2 and not winner:
    st.markdown("---")
    if st.button("➡️ ไปเซตถัดไป", type="primary", use_container_width=True):
        save_undo()
        m["current_set"] += 1
        m["swapped"] = not m["swapped"]
        st.rerun()


# =========================================================
# SAVE MATCH
# =========================================================

st.markdown("---")
st.subheader("💾 บันทึกการแข่งขัน")

if st.button("💾 บันทึกผลการแข่งขัน", type="primary", use_container_width=True):
    saved = copy.deepcopy(m)
    saved["winner"] = m[f"team_{winner}"] if winner else "ยังไม่จบ"
    saved["sets"] = f"{a_sets} - {b_sets}"
    st.session_state.history.append(saved)
    st.success("บันทึกการแข่งขันแล้ว")


# =========================================================
# EXCEL EXPORT
# =========================================================

def export_excel(data):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    ws = workbook.add_worksheet("Score Sheet")

    ws.set_landscape()
    ws.set_paper(9)
    ws.fit_to_pages(1, 1)

    title = workbook.add_format({"bold": True, "font_size": 16, "align": "center", "valign": "vcenter"})
    header = workbook.add_format({"bold": True, "border": 1, "align": "center", "valign": "vcenter"})
    cell = workbook.add_format({"border": 1, "align": "center", "valign": "vcenter"})

    ws.merge_range("A1:H1", "PT SPORT 2026 VOLLEYBALL SCORE", title)
    ws.merge_range("A2:H2", f"{data['team_a']} VS {data['team_b']}", header)

    row = 3
    for i in range(3):
        ws.write(row, 0, f"SET {i+1}", header)
        ws.write(row, 1, data["scores"][i]["a"], cell)
        ws.write(row, 2, data["scores"][i]["b"], cell)
        row += 1

    row += 1
    ws.write(row, 0, "Timeout", header)
    row += 1

    for team in ["a", "b"]:
        ws.write(row, 0, data[f"team_{team}"], cell)
        for s in range(3):
            for t in range(2):
                value = "✓" if data["timeouts"][team][s][t] else ""
                ws.write(row, 1 + s * 2 + t, value, cell)
        row += 1

    workbook.close()
    return output.getvalue()


st.download_button(
    "📊 ดาวน์โหลด Score Sheet A4 Excel",
    data=export_excel(m),
    file_name="PTSPORT2026_Volleyball_Score.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)


# =========================================================
# HISTORY
# =========================================================

st.markdown("---")
st.subheader("📜 ประวัติการแข่งขัน")

if not st.session_state.history:
    st.info("ยังไม่มีการแข่งขันที่บันทึก")
else:
    for i, item in enumerate(reversed(st.session_state.history)):
        with st.expander(f"🏐 {item['team_a']} vs {item['team_b']} — {item['sets']}"):
            st.write(f"🏆 ผู้ชนะ: **{item['winner']}**")
            st.table(
                pd.DataFrame({
                    "Set": ["Set 1", "Set 2", "Set 3"],
                    item["team_a"]: [item["scores"][0]["a"], item["scores"][1]["a"], item["scores"][2]["a"]],
                    item["team_b"]: [item["scores"][0]["b"], item["scores"][1]["b"], item["scores"][2]["b"]]
                })
            )
