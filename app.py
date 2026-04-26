from flask import Flask, render_template, request, redirect, Response
import json
import os
from functools import wraps

app = Flask(__name__)
FILE = "data.json"

def check_auth(username, password):
    return username == os.environ.get("ADMIN_USER") and password == os.environ.get("ADMIN_PASS")

def authenticate():
    return Response("Login required", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

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
    return render_template("index.html", players=players)

@app.route("/register", methods=["POST"])
def register():
    players = load_data()

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

@app.route("/admin")
@requires_auth
def admin():
    players = load_data()
    return render_template("admin.html", players=players)

@app.route("/mark_paid/<int:player_id>")
@requires_auth
def mark_paid(player_id):
    players = load_data()

    for p in players:
        if p["id"] == player_id:
            p["paid"] = "Paid"

    save_data(players)
    return redirect("/admin")

@app.route("/delete/<int:player_id>")
@requires_auth
def delete(player_id):
    players = load_data()
    players = [p for p in players if p["id"] != player_id]

    for i, p in enumerate(players):
        p["id"] = i

    save_data(players)
    return redirect("/admin")

if __name__ == "__main__":
    app.run(debug=True)
