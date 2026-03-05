"""
seed_demo.py
─────────────────────────────────────────────────────────
Run this ONCE before your demo to fill the database with
90 days of realistic household energy data.

Usage:
    python seed_demo.py

It creates a demo account and populates it with data.
Demo login:
    Email    : demo@smartenergy.com
    Password : demo1234
─────────────────────────────────────────────────────────
"""

import sqlite3
import hashlib
import random
import os
from datetime import date, timedelta

# ── Config ────────────────────────────────────
DB_PATH     = os.path.join("database", "energy.db")
DEMO_NAME   = "Abdul Muqatdir"
DEMO_EMAIL  = "demo@smartenergy.com"
DEMO_PASS   = "demo1234"
DAYS_BACK   = 90          # 3 months of data

# ── Device power ratings (Watts) ─────────────
DEVICES = {
    "Fan":              75,
    "Air Conditioner":  1500,
    "Washing Machine":  500,
    "Refrigerator":     150,
    "TV":               120,
    "Lights":           60,
}

# ── Realistic daily usage patterns ───────────
# (device, min_hours, max_hours, probability_of_use)
DAILY_PATTERNS = [
    ("Refrigerator",     22,  24,  1.00),   # Always running
    ("Lights",            4,   8,  1.00),   # Every day
    ("Fan",               2,   8,  0.85),   # Most days
    ("TV",                1,   5,  0.80),   # Most evenings
    ("Air Conditioner",   1,   6,  0.60),   # Hot days
    ("Washing Machine",   1,   2,  0.30),   # Few times a week
]

# ── Helpers ───────────────────────────────────

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            email    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created  TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS device_usage (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            device     TEXT NOT NULL,
            hours_used REAL NOT NULL,
            energy_kwh REAL NOT NULL,
            usage_date TEXT NOT NULL,
            created    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

def calculate_kwh(device, hours):
    watts = DEVICES.get(device, 100)
    return round((watts / 1000) * hours, 4)


# ── Main seeder ───────────────────────────────

def seed():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # ── Create or get demo user ───────────────
    existing = conn.execute(
        "SELECT id FROM users WHERE email = ?", (DEMO_EMAIL,)
    ).fetchone()

    if existing:
        user_id = existing["id"]
        print(f"✅ Demo user already exists (id={user_id})")
        # Clear old data so we start fresh
        conn.execute("DELETE FROM device_usage WHERE user_id = ?", (user_id,))
        print("🗑  Old data cleared — refilling with fresh data...")
    else:
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?,?,?)",
            (DEMO_NAME, DEMO_EMAIL, hash_password(DEMO_PASS))
        )
        conn.commit()
        user_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", (DEMO_EMAIL,)
        ).fetchone()["id"]
        print(f"✅ Demo user created (id={user_id})")

    # ── Generate 90 days of usage data ───────
    total_records = 0
    total_kwh     = 0.0

    # Simulate seasonal variation — summer months use more AC
    today = date.today()

    for day_offset in range(DAYS_BACK, 0, -1):
        current_date = today - timedelta(days=day_offset)
        date_str     = current_date.isoformat()

        # Weekend flag — more usage on weekends
        is_weekend = current_date.weekday() >= 5

        for device, min_h, max_h, prob in DAILY_PATTERNS:
            # Adjust probability on weekends
            adjusted_prob = min(1.0, prob + (0.10 if is_weekend else 0))

            if random.random() > adjusted_prob:
                continue   # Skip this device today

            # Randomise hours with slight seasonal variation
            hours = round(random.uniform(min_h, max_h), 1)

            # Boost AC usage in recent 30 days (summer simulation)
            if device == "Air Conditioner" and day_offset <= 30:
                hours = round(min(hours * 1.4, 8), 1)

            kwh = calculate_kwh(device, hours)

            conn.execute(
                """INSERT INTO device_usage
                   (user_id, device, hours_used, energy_kwh, usage_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, device, hours, kwh, date_str)
            )
            total_records += 1
            total_kwh     += kwh

    conn.commit()
    conn.close()

    # ── Summary ───────────────────────────────
    print()
    print("━" * 45)
    print("  🎉  DEMO DATA SEEDED SUCCESSFULLY!")
    print("━" * 45)
    print(f"  📅  Days of data   : {DAYS_BACK} days")
    print(f"  📋  Total records  : {total_records}")
    print(f"  ⚡  Total energy   : {round(total_kwh, 2)} kWh")
    print()
    print("  🔐  Demo Login Credentials:")
    print(f"      Email    : {DEMO_EMAIL}")
    print(f"      Password : {DEMO_PASS}")
    print()
    print("  ▶   Now run:  python app.py")
    print("      Open  :  http://127.0.0.1:8080")
    print("━" * 45)


if __name__ == "__main__":
    seed()
