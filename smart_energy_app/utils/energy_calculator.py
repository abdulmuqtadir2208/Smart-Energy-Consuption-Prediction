"""
utils/energy_calculator.py
--------------------------
Utility functions for calculating device energy consumption.

Formula:  Energy (kWh) = Power (kW) × Time (hours)
"""

# ─────────────────────────────────────────────
# Default Power Ratings (Watts)
# Source: typical household appliance ratings
# ─────────────────────────────────────────────
DEVICE_POWER_RATINGS: dict[str, float] = {
    "Fan":              75.0,
    "Air Conditioner":  1500.0,
    "Washing Machine":  500.0,
    "Refrigerator":     150.0,
    "TV":               120.0,
    "Lights":           60.0,
    "Other":            100.0,
}


def calculate_energy(device: str, hours: float) -> float:
    """
    Calculate energy consumption in kWh.

    Parameters
    ----------
    device : str
        Name of the device (must match a key in DEVICE_POWER_RATINGS).
    hours  : float
        Duration the device was used (hours).

    Returns
    -------
    float
        Energy consumed in kilowatt-hours (kWh).
    """
    power_watts = DEVICE_POWER_RATINGS.get(device, DEVICE_POWER_RATINGS["Other"])
    power_kw    = power_watts / 1000.0          # Convert W → kW
    energy_kwh  = power_kw * hours              # E = P × t
    return round(energy_kwh, 4)


def get_power_rating(device: str) -> float:
    """Return the wattage for a given device name."""
    return DEVICE_POWER_RATINGS.get(device, DEVICE_POWER_RATINGS["Other"])
