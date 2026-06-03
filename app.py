from flask import Flask, render_template, request, redirect, session
import os
import json

app = Flask(__name__)
app.secret_key = "secret123"

DATA_FILE = "data.json"

MATCH_CONFIG = {
    "TDM": {"limit": 8, "fee": 100},
    "Erangel": {"limit": 100, "fee": 20},
    "Solo": {"limit": 100, "fee": 20},
    "Squad": {"limit": 100, "fee": 30},
    "Mega TDM": {"limit": 8, "fee": 400},
    "Mega Erangel": {"limit": 100, "fee": 100}
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"players": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "players" not in data:
            data["players"] = []

        return data
    except:
        return {"players": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_players():
    data = load_data()
    return data.get("players", [])

def next_player_id(players):
    if not players:
        return 1

    return max([int(p.get("id", 0)) for p in players]) + 1

def safe_int(value):
    try:
        return int(value or 0)
    except:
        return 0

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

    return render_template(
        "index.html",
        players=players,
        mode_slots=mode_slots,
        full_modes=full_modes,
        leaderboard=leaderboard,
        leaderboard_mode=leaderboard_mode
    )

@app.route("/register", methods=["POST"])
def register():
    data = load_data()
    players = data.get("players", [])

    payment_ref = request.form.get("payment_ref", "").strip()

    for p in players:
        if p.get("payment_ref") == payment_ref:
            return "Duplicate UPI Transaction ID. Please check payment reference."

    player = {
        "id": next_player_id(players),
        "name": request.form.get("name", "").strip(),
        "uid": request.form.get("uid", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "mode": request.form.get("mode", "").strip(),
        "payment_ref": payment_ref,
        "paid": "Pending",
        "played": "No",
        "kills": "0",
        "rank": "",
        "win_ratio": ""
    }

    players.append(player)
    data["players"] = players
    save_data(data)

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

def update_player(player_id, updates):
    data = load_data()
    players = data.get("players", [])

    for p in players:
        if int(p.get("id")) == int(player_id):
            p.update(updates)
            break

    data["players"] = players
    save_data(data)

@app.route("/mark_paid/<int:player_id>")
def mark_paid(player_id):
    update_player(player_id, {"paid": "Paid"})
    return redirect("/admin")

@app.route("/mark_pending/<int:player_id>")
def mark_pending(player_id):
    update_player(player_id, {"paid": "Pending"})
    return redirect("/admin")

@app.route("/mark_rejected/<int:player_id>")
def mark_rejected(player_id):
    update_player(player_id, {"paid": "Rejected"})
    return redirect("/admin")

@app.route("/mark_played/<int:player_id>")
def mark_played(player_id):
    update_player(player_id, {"played": "Yes"})
    return redirect("/admin")

@app.route("/quick_kill/<int:player_id>")
def quick_kill(player_id):
    data = load_data()
    players = data.get("players", [])

    for p in players:
        if int(p.get("id")) == int(player_id):
            p["kills"] = str(safe_int(p.get("kills")) + 1)
            break

    data["players"] = players
    save_data(data)

    return redirect("/admin")

@app.route("/set_rank/<int:player_id>/<rank>")
def set_rank(player_id, rank):
    update_player(player_id, {"rank": rank})
    return redirect("/admin")

@app.route("/edit/<int:player_id>", methods=["GET", "POST"])
def edit_player(player_id):
    data = load_data()
    players = data.get("players", [])

    player = None
    for p in players:
        if int(p.get("id")) == int(player_id):
            player = p
            break

    if not player:
        return redirect("/admin")

    if request.method == "POST":
        player["kills"] = request.form.get("kills", "0")
        player["rank"] = request.form.get("rank", "")
        player["win_ratio"] = request.form.get("win_ratio", "")

        data["players"] = players
        save_data(data)

        return redirect("/admin")

    return render_template("edit.html", p=player)

@app.route("/delete/<int:player_id>", methods=["POST"])
def delete(player_id):
    data = load_data()
    players = data.get("players", [])

    players = [p for p in players if int(p.get("id")) != int(player_id)]

    data["players"] = players
    save_data(data)

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
