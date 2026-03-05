"""
Smart Energy Consumption Tracking and Prediction System
--------------------------------------------------------
Main Flask application entry point.
Handles routing, authentication, API endpoints, and database interaction.
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import sqlite3
import os
import hashlib
import secrets
from datetime import datetime, timedelta, date
import json

# Internal modules
from models.prediction_model import predict_tomorrow
from utils.energy_calculator import calculate_energy, DEVICE_POWER_RATINGS
from utils.report_generator import generate_pdf_report

# ─────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "energy.db")


# ─────────────────────────────────────────────
# Database Helpers
# ─────────────────────────────────────────────

def get_db():
    """Return a database connection with row_factory for dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema if tables don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                name      TEXT    NOT NULL,
                email     TEXT    UNIQUE NOT NULL,
                password  TEXT    NOT NULL,
                created   TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS device_usage (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                device      TEXT    NOT NULL,
                hours_used  REAL    NOT NULL,
                energy_kwh  REAL    NOT NULL,
                usage_date  TEXT    NOT NULL,
                created     TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)


# ─────────────────────────────────────────────
# Auth Utilities
# ─────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plain-text password with SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def login_required(fn):
    """Decorator: redirect to login if user is not in session."""
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
# Routes — Authentication
# ─────────────────────────────────────────────

@app.route("/")
def index():
    """Redirect root to dashboard or login."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE email = ? AND password = ?",
                (email, hash_password(password))
            ).fetchone()

        if user:
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid email or password."

    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Handle new user registration."""
    error = None
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            try:
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                        (name, email, hash_password(password))
                    )
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "An account with that email already exists."

    return render_template("signup.html", error=error)


@app.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.clear()
    return redirect(url_for("login"))


# ─────────────────────────────────────────────
# Routes — Dashboard
# ─────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    """Render the main dashboard page."""
    user_id = session["user_id"]
    today   = date.today().isoformat()

    with get_db() as conn:
        # Today's total kWh
        today_kwh = conn.execute("""
            SELECT COALESCE(SUM(energy_kwh), 0) AS total
            FROM device_usage
            WHERE user_id = ? AND usage_date = ?
        """, (user_id, today)).fetchone()["total"]

        # Weekly total (last 7 days)
        week_start = (date.today() - timedelta(days=6)).isoformat()
        week_kwh = conn.execute("""
            SELECT COALESCE(SUM(energy_kwh), 0) AS total
            FROM device_usage
            WHERE user_id = ? AND usage_date >= ?
        """, (user_id, week_start)).fetchone()["total"]

        # Monthly total (last 30 days)
        month_start = (date.today() - timedelta(days=29)).isoformat()
        month_kwh = conn.execute("""
            SELECT COALESCE(SUM(energy_kwh), 0) AS total
            FROM device_usage
            WHERE user_id = ? AND usage_date >= ?
        """, (user_id, month_start)).fetchone()["total"]

        # Recent records for the data table (last 20)
        records = conn.execute("""
            SELECT usage_date, device, hours_used, energy_kwh
            FROM device_usage
            WHERE user_id = ?
            ORDER BY usage_date DESC, id DESC
            LIMIT 20
        """, (user_id,)).fetchall()

    # ML prediction for tomorrow
    predicted = predict_tomorrow(user_id, DB_PATH)

    return render_template(
        "dashboard.html",
        user_name    = session["user_name"],
        today_kwh    = round(today_kwh, 3),
        week_kwh     = round(week_kwh, 3),
        month_kwh    = round(month_kwh, 3),
        predicted    = round(predicted, 3),
        records      = [dict(r) for r in records],
        devices      = list(DEVICE_POWER_RATINGS.keys()),
    )


# ─────────────────────────────────────────────
# API — Device Usage (AJAX)
# ─────────────────────────────────────────────

@app.route("/api/log_usage", methods=["POST"])
@login_required
def log_usage():
    """Log a new device usage entry and return updated summaries."""
    data       = request.get_json()
    device     = data.get("device", "Other")
    hours      = float(data.get("hours", 0))
    usage_date = data.get("date", date.today().isoformat())
    user_id    = session["user_id"]

    # Calculate energy
    energy_kwh = calculate_energy(device, hours)

    with get_db() as conn:
        conn.execute(
            "INSERT INTO device_usage (user_id, device, hours_used, energy_kwh, usage_date) VALUES (?,?,?,?,?)",
            (user_id, device, hours, energy_kwh, usage_date)
        )

    # Return refreshed summary numbers
    return jsonify({
        "success":    True,
        "energy_kwh": round(energy_kwh, 3),
        "message":    f"Logged {round(energy_kwh, 3)} kWh for {device}."
    })


@app.route("/api/chart_data")
@login_required
def chart_data():
    """
    Return chart data for the selected period.
    Query param: ?period=daily|weekly|monthly|hourly
    """
    period  = request.args.get("period", "daily")
    user_id = session["user_id"]

    with get_db() as conn:
        if period == "daily":
            # Last 14 days, grouped by date
            start = (date.today() - timedelta(days=13)).isoformat()
            rows  = conn.execute("""
                SELECT usage_date AS label, ROUND(SUM(energy_kwh),3) AS value
                FROM device_usage
                WHERE user_id = ? AND usage_date >= ?
                GROUP BY usage_date
                ORDER BY usage_date ASC
            """, (user_id, start)).fetchall()

        elif period == "weekly":
            # Last 8 weeks, grouped by ISO week
            start = (date.today() - timedelta(weeks=8)).isoformat()
            rows  = conn.execute("""
                SELECT strftime('%Y-W%W', usage_date) AS label,
                       ROUND(SUM(energy_kwh),3)       AS value
                FROM device_usage
                WHERE user_id = ? AND usage_date >= ?
                GROUP BY label
                ORDER BY label ASC
            """, (user_id, start)).fetchall()

        elif period == "monthly":
            # Last 12 months, grouped by year-month
            start = (date.today() - timedelta(days=365)).isoformat()
            rows  = conn.execute("""
                SELECT strftime('%Y-%m', usage_date) AS label,
                       ROUND(SUM(energy_kwh),3)      AS value
                FROM device_usage
                WHERE user_id = ? AND usage_date >= ?
                GROUP BY label
                ORDER BY label ASC
            """, (user_id, start)).fetchall()

        else:
            # Hourly — show per-entry today (approximated)
            today = date.today().isoformat()
            rows  = conn.execute("""
                SELECT device AS label, ROUND(SUM(energy_kwh),3) AS value
                FROM device_usage
                WHERE user_id = ? AND usage_date = ?
                GROUP BY device
                ORDER BY value DESC
            """, (user_id, today)).fetchall()

    labels = [r["label"] for r in rows]
    values = [r["value"] for r in rows]
    return jsonify({"labels": labels, "values": values})


@app.route("/api/table_data")
@login_required
def table_data():
    """Return paginated table data as JSON."""
    user_id = session["user_id"]
    with get_db() as conn:
        rows = conn.execute("""
            SELECT usage_date, device, hours_used, energy_kwh
            FROM device_usage WHERE user_id = ?
            ORDER BY usage_date DESC, id DESC
            LIMIT 50
        """, (user_id,)).fetchall()
    return jsonify([dict(r) for r in rows])


# ─────────────────────────────────────────────
# Route — Export PDF Report
# ─────────────────────────────────────────────

@app.route("/export_report")
@login_required
def export_report():
    """Generate and serve the PDF energy report."""
    user_id   = session["user_id"]
    user_name = session["user_name"]

    with get_db() as conn:
        records = conn.execute("""
            SELECT usage_date, device, hours_used, energy_kwh
            FROM device_usage WHERE user_id = ?
            ORDER BY usage_date DESC
            LIMIT 100
        """, (user_id,)).fetchall()
        records = [dict(r) for r in records]

        total_kwh = conn.execute(
            "SELECT COALESCE(SUM(energy_kwh), 0) AS t FROM device_usage WHERE user_id=?",
            (user_id,)
        ).fetchone()["t"]

    predicted = predict_tomorrow(user_id, DB_PATH)
    pdf_path  = generate_pdf_report(user_name, records, total_kwh, predicted)

    return send_file(pdf_path, as_attachment=True, download_name="energy_report.pdf")


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("database", exist_ok=True)
    init_db()
    app.run(debug=False, port=8080)
