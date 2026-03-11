"""
models/prediction_model.py
---------------------------
Simple Linear Regression model to predict tomorrow's energy consumption
based on the user's historical daily usage data.

Library: scikit-learn
"""

import sqlite3
import numpy as np
from datetime import date, timedelta

try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def predict_tomorrow(user_id: int, db_path: str) -> float:
    """
    Predict tomorrow's energy consumption using Linear Regression.

    Strategy
    --------
    1. Fetch the last 30 days of daily energy totals.
    2. Use day index (0, 1, 2 …) as the feature X.
    3. Fit a LinearRegression and predict for day N+1.
    4. Clamp result to ≥ 0 kWh.

    Falls back to a simple average if sklearn is unavailable
    or if there are fewer than 3 days of data.

    Parameters
    ----------
    user_id : int  — The currently authenticated user's ID.
    db_path : str  — Absolute path to the SQLite database.

    Returns
    -------
    float — Predicted kWh for tomorrow.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    start = (date.today() - timedelta(days=29)).isoformat()
    rows  = conn.execute("""
        SELECT usage_date, SUM(energy_kwh) AS daily_total
        FROM device_usage
        WHERE user_id = ? AND usage_date >= ?
        GROUP BY usage_date
        ORDER BY usage_date ASC
    """, (user_id, start)).fetchall()
    conn.close()

    if not rows:
        return 0.0

    totals = [float(r["daily_total"]) for r in rows]

    # Fallback: simple average if not enough data or no sklearn
    if len(totals) < 3 or not SKLEARN_AVAILABLE:
        return round(sum(totals) / len(totals), 3)

    # ── Linear Regression ──
    X = np.array(range(len(totals))).reshape(-1, 1)   # Day indices
    y = np.array(totals)

    model = LinearRegression()
    model.fit(X, y)

    next_day = np.array([[len(totals)]])               # Tomorrow's index
    prediction = float(model.predict(next_day)[0])

    return round(max(prediction, 0.0), 3)
