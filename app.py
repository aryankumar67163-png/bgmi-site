from flask import Flask, render_template, request, redirect, session
import json
import os

app = Flask(__name__)
app.secret_key = "secret123"

FILE = "data.json"

ADMIN_USER = "admin"
ADMIN_PASS = "Aaryan@1999"

def load_data():
    if not os.path.exists(FILE):
        with open(FILE, "w") as f:
            json.dump([], f)
    with open(FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/")
def home():
    players = load_data()
    MAX_SLOTS = 100

    total = len(players)
    slots_left = MAX_SLOTS - total

    return render_template(
    "index.html",
    players=players,
    total=total,
    slots_left=slots_left,
    is_full=(total >= MAX_SLOTS)
)

@app.route("/register", methods=["POST"])
def register():
    players = load_data()

    MAX_SLOTS = 100
    if len(players) >= MAX_SLOTS:
        return "MATCH FULL ❌"

    player = {
        "id": len(players),
        "name": request.form.get("name"),
        "uid": request.form.get("uid"),
        "phone": request.form.get("phone"),
        "mode": request.form.get("mode"),
        "payment_ref": request.form.get("payment_ref"),
        "paid": "Pending"
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

    players = load_data()
    return render_template("admin.html", players=players)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

@app.route("/mark_paid/<int:player_id>")
def mark_paid(player_id):
    if not session.get("admin"):
        return redirect("/login")

    players = load_data()

    for p in players:
        if p["id"] == player_id:
            p["paid"] = "Paid"

    save_data(players)
    return redirect("/admin")

@app.route("/delete/<int:player_id>")
def delete(player_id):
    if not session.get("admin"):
        return redirect("/login")

    players = load_data()
    players = [p for p in players if p["id"] != player_id]

    for i, p in enumerate(players):
        p["id"] = i

    save_data(players)
    return redirect("/admin")

if __name__ == "__main__":
    app.run(debug=True)
