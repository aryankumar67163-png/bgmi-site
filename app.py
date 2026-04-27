from flask import Flask, render_template, request, redirect, session
import psycopg
import os

app = Flask(__name__)
app.secret_key = "secret123"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")
    
def get_db():
    return psycopg.connect(DATABASE_URL)

# 🔥 TABLE CREATE
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id SERIAL PRIMARY KEY,
        name TEXT,
        uid TEXT,
        phone TEXT,
        mode TEXT,
        payment_ref TEXT,
        paid TEXT,
        played TEXT,
        kills TEXT,
        rank TEXT,
        win_ratio TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

MATCH_CONFIG = {
    "TDM": {"limit": 8},
    "Erangel": {"limit": 100},
    "Solo": {"limit": 100},
    "Squad": {"limit": 100},
    "Mega TDM": {"limit": 8},
    "Mega Erangel": {"limit": 100}
}

def get_players():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    players = []
    for r in rows:
        players.append({
            "id": r[0],
            "name": r[1],
            "uid": r[2],
            "phone": r[3],
            "mode": r[4],
            "payment_ref": r[5],
            "paid": r[6],
            "played": r[7],
            "kills": r[8],
            "rank": r[9],
            "win_ratio": r[10]
        })
    return players

def mode_count(players, mode):
    return len([p for p in players if p["mode"] == mode])

def get_mode_slots(players):
    mode_slots = {}
    full_modes = []

    for mode, cfg in MATCH_CONFIG.items():
        limit = cfg["limit"]
        used = mode_count(players, mode)

        mode_slots[mode] = {
            "used": used,
            "limit": limit
        }

        if used >= limit:
            full_modes.append(mode)

    return mode_slots, full_modes

@app.route("/")
def home():
    players = get_players()
    mode_slots, full_modes = get_mode_slots(players)

    return render_template("index.html",
        players=players,
        mode_slots=mode_slots,
        full_modes=full_modes
    )

@app.route("/register", methods=["POST"])
def register():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO players (name, uid, phone, mode, payment_ref, paid, played, kills, rank, win_ratio)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        request.form.get("name"),
        request.form.get("uid"),
        request.form.get("phone"),
        request.form.get("mode"),
        request.form.get("payment_ref"),
        "Pending",
        "No",
        "0",
        "",
        ""
    ))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    players = get_players()
    mode_slots, full_modes = get_mode_slots(players)

    total_players = len(players)

    paid_players = len([p for p in players if p.get("paid") == "Paid"])
    pending_players = total_players - paid_players

    total_collection = 0
    mode_earning = {}

for p in players:
    if p.get("paid") == "Paid":
        mode = p.get("mode")
        fee = MATCH_CONFIG.get(mode, {}).get("fee", 0)
        total_collection += fee
        if mode not in mode_earning:
            mode_earning[mode] = 0

        mode_earning[mode] += fee
   
    return render_template(
        "admin.html",
        players=players,
        mode_slots=mode_slots,
        full_modes=full_modes,
        total_players=total_players,
        paid_players=paid_players,
        pending_players=pending_players,
        total_collection=total_collection,
        mode_earning=mode_earning
    )

@app.route("/mark_paid/<int:player_id>")
def mark_paid(player_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE players SET paid='Paid' WHERE id=%s", (player_id,))
    conn.commit()

    cur.close()
    conn.close()
    return redirect("/admin")

@app.route("/mark_played/<int:player_id>")
def mark_played(player_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE players SET played='Yes' WHERE id=%s", (player_id,))
    conn.commit()

    cur.close()
    conn.close()
    return redirect("/admin")

@app.route("/delete/<int:player_id>", methods=["POST"])
def delete(player_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM players WHERE id=%s", (player_id,))
    conn.commit()

    cur.close()
    conn.close()
    return redirect("/admin")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == "admin" and request.form.get("password") == "Aaryan@1999":
            session["admin"] = True
            return redirect("/admin")

    return '''
    <form method="POST">
    <input name="username">
    <input type="password" name="password">
    <button>Login</button>
    </form>
    '''

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
