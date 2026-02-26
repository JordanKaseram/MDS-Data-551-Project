# src/data.py
import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "SuperStoreOrders.csv"

df_raw = pd.read_csv(DATA_PATH)
df = df_raw.copy()

df["sales"] = (
    df["sales"].astype(str).str.replace(",", "", regex=False).str.strip()
)
df["sales"] = pd.to_numeric(df["sales"], errors="coerce")
df["margin"] = df["profit"] / df["sales"]

df["order_date"] = pd.to_datetime(df["order_date"], format="mixed", dayfirst=True, errors="coerce")
df["ship_date"]  = pd.to_datetime(df["ship_date"],  format="mixed", dayfirst=True, errors="coerce")
df["shipping_delay"] = (df["ship_date"] - df["order_date"]).dt.days

# --- Seasons ---
df["month"] = df["order_date"].dt.month

df["season"] = np.select(
    [
        df["month"].isin([12, 1, 2]),
        df["month"].isin([3, 4, 5]),
        df["month"].isin([6, 7, 8]),
        df["month"].isin([9, 10, 11]),
    ],
    ["Winter", "Spring", "Summer", "Fall"],
    default="Unknown"
)