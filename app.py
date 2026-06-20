from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = "medtrack123"
DB = {
    "host": os.environ.get("MYSQLHOST", "localhost"),
    "user": os.environ.get("MYSQLUSER", "root"),
    "password": os.environ.get("MYSQLPASSWORD", "root123"),
    "database": os.environ.get("MYSQLDATABASE", "medicine_db"),
    "port": int(os.environ.get("MYSQLPORT", 3306))
}

def get_db():
    return mysql.connector.connect(**DB)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100),
        password VARCHAR(100),
        role VARCHAR(50))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS medicines (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200),
        quantity INT,
        manufacture_date DATE,
        expiry_date DATE)""")
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'Admin')")
        cur.execute("INSERT INTO users (username, password, role) VALUES ('staff', 'staff123', 'Staff')")
        cur.execute("INSERT INTO users (username, password, role) VALUES ('doctor', 'doctor123', 'Doctor')")
    conn.commit()
    cur.close()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        role = request.form["role"]
        password = request.form["password"]
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE role=%s AND password=%s", (role, password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session["user"] = user[1]
            session["role"] = user[3]
            return redirect("/dashboard")
        else:
            error = "Invalid role or password!"
    return render_template("login.html", error=error)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM medicines")
    total = cur.fetchone()[0]
    cur.execute("SELECT SUM(quantity) FROM medicines")
    total_qty = cur.fetchone()[0] or 0
    today = date.today()
    alert_date = today + timedelta(days=30)
    cur.execute("SELECT COUNT(*) FROM medicines WHERE expiry_date <= %s", (alert_date,))
    alerts = cur.fetchone()[0]
    cur.execute("SELECT name, quantity FROM medicines ORDER BY quantity DESC LIMIT 6")
    top_medicines = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("dashboard.html",
        total=total,
        total_qty=total_qty,
        alerts=alerts,
        top_medicines=top_medicines,
        user=session["user"],
        role=session["role"])

@app.route("/medicines")
def medicines():
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM medicines ORDER BY expiry_date ASC")
    meds = cur.fetchall()
    cur.close()
    conn.close()
    today = date.today()
    alert_date = today + timedelta(days=30)
    return render_template("medicines.html",
        meds=meds,
        today=today,
        alert_date=alert_date,
        user=session["user"],
        role=session["role"])

@app.route("/add", methods=["GET", "POST"])
def add():
    if "user" not in session:
        return redirect("/")
    if session["role"] == "Doctor":
        return redirect("/medicines")
    if request.method == "POST":
        name = request.form["name"]
        qty = request.form["quantity"]
        mfg = request.form["manufacture_date"]
        exp = request.form["expiry_date"]
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO medicines (name, quantity, manufacture_date, expiry_date) VALUES (%s,%s,%s,%s)",
            (name, qty, mfg, exp))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/medicines")
    return render_template("add.html", user=session["user"], role=session["role"])

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user" not in session:
        return redirect("/")
    if session["role"] == "Doctor":
        return redirect("/medicines")
    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST":
        name = request.form["name"]
        qty = request.form["quantity"]
        mfg = request.form["manufacture_date"]
        exp = request.form["expiry_date"]
        cur.execute("UPDATE medicines SET name=%s, quantity=%s, manufacture_date=%s, expiry_date=%s WHERE id=%s",
            (name, qty, mfg, exp, id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/medicines")
    cur.execute("SELECT * FROM medicines WHERE id=%s", (id,))
    med = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("edit.html", med=med, user=session["user"], role=session["role"])

@app.route("/delete/<int:id>")
def delete(id):
    if "user" not in session:
        return redirect("/")
    if session["role"] == "Doctor":
        return redirect("/medicines")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM medicines WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/medicines")

@app.route("/alerts")
def alerts():
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    today = date.today()
    alert_date = today + timedelta(days=30)
    cur.execute("SELECT * FROM medicines WHERE expiry_date <= %s ORDER BY expiry_date ASC", (alert_date,))
    meds = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("alerts.html",
        meds=meds,
        today=today,
        user=session["user"],
        role=session["role"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
init_db()

if __name__ == "__main__":
    app.run(debug=True)
