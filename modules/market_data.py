"""
market_data.py
Local, editable market-price dataset (free, offline-first).

Real-time African commodity price APIs are mostly paid or region-locked, so for this
free test-run version Agri_OS ships with an editable sample dataset covering several
Sub-Saharan African countries. Farmers/agronomists can correct prices live in the
"Market Prices" page (st.data_editor) and the whole app instantly uses the updated
numbers - a lightweight stand-in for a live price-feed integration later.
"""

from pathlib import Path
import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "market_prices_sample.csv"

COUNTRIES = ["Nigeria", "Kenya", "Ghana", "Tanzania", "Uganda", "Ethiopia", "South Africa"]

CURRENCY_BY_COUNTRY = {
    "Nigeria": "NGN", "Kenya": "KES", "Ghana": "GHS", "Tanzania": "TZS",
    "Uganda": "UGX", "Ethiopia": "ETB", "South Africa": "ZAR",
}


def load_market_df() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def save_market_df(df: pd.DataFrame):
    df.to_csv(DATA_PATH, index=False)


def get_price(df: pd.DataFrame, country: str, commodity: str):
    """Return (price, unit, currency) for a commodity in a country, with graceful fallback
    to the average price across all countries if that exact country/commodity combo is missing."""
    row = df[(df["country"] == country) & (df["commodity"] == commodity)]
    if not row.empty:
        r = row.iloc[0]
        return float(r["price"]), r["unit"], r["currency"]
    row = df[df["commodity"] == commodity]
    if not row.empty:
        r = row.iloc[0]
        return float(r["price"]), r["unit"], r["currency"] + " (avg, no local data)"
    return None, None, None


def commodities_for_category(df: pd.DataFrame, category: str):
    return sorted(df[df["category"] == category]["commodity"].unique().tolist())
