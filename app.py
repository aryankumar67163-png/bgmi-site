from flask import Flask, render_template, request, redirect, session
import psycopg
import os

app = Flask(_name_)
app.secret_key = "secret123"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")

def get_db():
    return psycopg.connect(DATABASE_URL)

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
    "TDM": {"limit": 8, "fee": 100},
    "Erangel": {"limit": 100, "fee": 20},
    "Solo": {"limit": 100, "fee": 20},
    "Squad": {"limit": 100, "fee": 30},
    "Mega TDM": {"limit": 8, "fee": 400},
    "Mega Erangel": {"limit": 100, "fee": 100}
}

def safe_int(value):
    try:
        return int(value or 0)
    except:
        return 0

def get_players():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players ORDER BY id DESC")
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
    return len([p for p in players if p.get("mode") == mode])

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

def build_leaderboard(players):
    ranked = sorted(
        players,
        key=lambda p: safe_int(p.get("kills")),
        reverse=True
    )

    last_kills = None
    current_rank = 0
    display_rank = 0

    for p in ranked:
        current_rank += 1
        kills = safe_int(p.get("kills"))

        if kills != last_kills:
            display_rank = current_rank
            last_kills = kills

        p["auto_rank"] = display_rank
        p["score"] = kills * 2

    return ranked

@app.route("/")
def home():
    players = get_players()
    mode_slots, full_modes = get_mode_slots(players)

    leaderboard_mode = request.args.get("lb_mode", "")
    leaderboard_players = players

    if leaderboard_mode:
        leaderboard_players = [p for p in players if p.get("mode") == leaderboard_mode]

    leaderboard = build_leaderboard(leaderboard_players)[:10]

    return render_template("index.html",
        players=players,
        mode_slots=mode_slots,
        full_modes=full_modes,
        leaderboard=leaderboard,
        leaderboard_mode=leaderboard_mode
    )

@app.route("/register", methods=["POST"])
def register():
    payment_ref = request.form.get("payment_ref")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM players WHERE payment_ref=%s", (payment_ref,))
    existing = cur.fetchone()

    if existing:
        cur.close()
        conn.close()
        return "Duplicate UPI Transaction ID. Please check payment reference."

    cur.execute("""
    INSERT INTO players (name, uid, phone, mode, payment_ref, paid, played, kills, rank, win_ratio)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        request.form.get("name"),
        request.form.get("uid"),
        request.form.get("phone"),
        request.form.get("mode"),
        payment_ref,
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

    search = request.args.get("search", "").lower()
    status_filter = request.args.get("status", "")
    mode_filter = request.args.get("mode", "")
    sort_filter = request.args.get("sort", "")

    if search:
        players = [
            p for p in players
            if search in p.get("name", "").lower()
            or search in p.get("uid", "").lower()
            or search in p.get("phone", "").lower()
        ]

    if status_filter:
        players = [p for p in players if p.get("paid") == status_filter]

    if mode_filter:
        players = [p for p in players if p.get("mode") == mode_filter]

    if sort_filter == "kills_desc":
        players = sorted(players, key=lambda p: safe_int(p.get("kills")), reverse=True)

    if sort_filter == "unpaid_first":
        players = sorted(players, key=lambda p: p.get("paid") == "Paid")

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

@app.route("/mark_pending/<int:player_id>")
def mark_pending(player_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE players SET paid='Pending' WHERE id=%s", (player_id,))
    conn.commit()

    cur.close()
    conn.close()
    return redirect("/admin")

@app.route("/mark_rejected/<int:player_id>")
def mark_rejected(player_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE players SET paid='Rejected' WHERE id=%s", (player_id,))
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

@app.route("/quick_kill/<int:player_id>")
def quick_kill(player_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE players SET kills = COALESCE(NULLIF(kills,''),'0')::int + 1 WHERE id=%s", (player_id,))
    conn.commit()

    cur.close()
    conn.close()
    return redirect("/admin")

@app.route("/set_rank/<int:player_id>/<rank>")
def set_rank(player_id, rank):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE players SET rank=%s WHERE id=%s", (rank, player_id))
    conn.commit()

    cur.close()
    conn.close()
    return redirect("/admin")

@app.route("/edit/<int:player_id>", methods=["GET", "POST"])
def edit_player(player_id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute("""
        UPDATE players
        SET kills=%s, rank=%s, win_ratio=%s
        WHERE id=%s
        """, (
            request.form.get("kills"),
            request.form.get("rank"),
            request.form.get("win_ratio"),
            player_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/admin")

    cur.execute("SELECT id, name, kills, rank, win_ratio FROM players WHERE id=%s", (player_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return redirect("/admin")

    player = {
        "id": row[0],
        "name": row[1],
        "kills": row[2],
        "rank": row[3],
        "win_ratio": row[4]
    }

    return render_template("edit.html", p=player)

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

if _name_ == "_main_":
    app.run(debug=True)
