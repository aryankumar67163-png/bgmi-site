from flask import Flask, render_template, request, redirect, session
import json
import os

app = Flask(__name__)
app.secret_key = "secret123"

FILE = "data.json"

ADMIN_USER = "admin"
ADMIN_PASS = "Aaryan@1999"

MATCH_LIMITS = {
    "TDM": 8,
    "Erangel": 100,
    "Solo": 100,
    "Squad": 100
}

def load_data():
    if not os.path.exists(FILE):
        with open(FILE, "w") as f:
            json.dump([], f)

    with open(FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

def fix_old_data(players):
    for i, p in enumerate(players):
        p["id"] = i
        if "paid" not in p:
            p["paid"] = "Pending"
        if "played" not in p:
            p["played"] = "No"
        if "kills" not in p:
            p["kills"] = "0"
        if "rank" not in p:
            p["rank"] = ""
        if "win_ratio" not in p:
            p["win_ratio"] = ""
    return players

def mode_count(players, mode):
    return len([p for p in players if p.get("mode") == mode])

def get_mode_slots(players):
    mode_slots = {}
    full_modes = []

    for mode, limit in MATCH_LIMITS.items():
        used = mode_count(players, mode)
        left = limit - used

        mode_slots[mode] = {
            "used": used,
            "limit": limit,
            "left": left,
            "full": used >= limit
        }

        if used >= limit:
            full_modes.append(mode)

    return mode_slots, full_modes

@app.route("/")
def home():
    players = fix_old_data(load_data())
    save_data(players)

    mode_slots, full_modes = get_mode_slots(players)

    return render_template(
        "index.html",
        players=players,
        mode_slots=mode_slots,
        full_modes=full_modes
    )

@app.route("/register", methods=["POST"])
def register():
    players = fix_old_data(load_data())

    mode = request.form.get("mode")
    limit = MATCH_LIMITS.get(mode, 100)

    if mode_count(players, mode) >= limit:
        return f"{mode} SLOT FULL ❌"

    player = {
        "id": len(players),
        "name": request.form.get("name"),
        "uid": request.form.get("uid"),
        "phone": request.form.get("phone"),
        "mode": mode,
        "payment_ref": request.form.get("payment_ref"),
        "paid": "Pending",
        "played": "No",
        "kills": "0",
        "rank": "",
        "win_ratio": ""
    }

    players.append(player)
    save_data(players)

    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        password = request.form.get("password")

        if user == ADMIN_USER and password == ADMIN_PASS:
            session["admin"] = True
            return redirect("/admin")

    return '''
    <h2>Admin Login</h2>
    <form method="POST">
        Username: <input name="username"><br><br>
        Password: <input type="password" name="password"><br><br>
        <button>Login</button>
    </form>
    '''

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    players = fix_old_data(load_data())
    save_data(players)

    mode_slots, full_modes = get_mode_slots(players)

    return render_template(
        "admin.html",
        players=players,
        mode_slots=mode_slots,
        full_modes=full_modes
    )

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

@app.route("/mark_paid/<int:player_id>")
def mark_paid(player_id):
    if not session.get("admin"):
        return redirect("/login")

    players = fix_old_data(load_data())

    for p in players:
        if p["id"] == player_id:
            p["paid"] = "Paid"

    save_data(players)
    return redirect("/admin")

@app.route("/mark_played/<int:player_id>")
def mark_played(player_id):
    if not session.get("admin"):
        return redirect("/login")

    players = fix_old_data(load_data())

    for p in players:
        if p["id"] == player_id:
            p["played"] = "Yes" if p.get("played") != "Yes" else "No"

    save_data(players)
    return redirect("/admin")

@app.route("/delete/<int:player_id>", methods=["POST"])
def delete(player_id):
    if not session.get("admin"):
        return redirect("/login")

    players = fix_old_data(load_data())
    players = [p for p in players if p["id"] != player_id]

    players = fix_old_data(players)
    save_data(players)

    return redirect("/admin")

@app.route("/edit/<int:player_id>", methods=["GET", "POST"])
def edit(player_id):
    if not session.get("admin"):
        return redirect("/login")

    players = fix_old_data(load_data())
    player = next((p for p in players if p["id"] == player_id), None)

    if player is None:
        return redirect("/admin")

    if request.method == "POST":
        old_mode = player.get("mode")
        new_mode = request.form.get("mode")
        limit = MATCH_LIMITS.get(new_mode, 100)

        if old_mode != new_mode and mode_count(players, new_mode) >= limit:
            return f"{new_mode} SLOT FULL ❌"

        player["name"] = request.form.get("name") or ""
        player["uid"] = request.form.get("uid") or ""
        player["phone"] = request.form.get("phone") or ""
        player["mode"] = new_mode or ""
        player["payment_ref"] = request.form.get("payment_ref") or ""
        player["paid"] = request.form.get("paid") or "Pending"
        player["played"] = request.form.get("played") or "No"
        player["kills"] = request.form.get("kills") or "0"
        player["rank"] = request.form.get("rank") or ""
        player["win_ratio"] = request.form.get("win_ratio") or ""

        save_data(players)
        return redirect("/admin")

    return render_template("edit.html", p=player, match_limits=MATCH_LIMITS)

if __name__ == "__main__":
    app.run(debug=True)
