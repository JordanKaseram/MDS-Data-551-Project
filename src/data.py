from pathlib import Path
import pandas as pd

# Load Superstore CSV robustly, regardless of where you run app.py from
# Expected repo structure:
#   project/
#     data/raw/SuperStoreOrders.csv
#     src/data.py
#     src/app.py
BASE_DIR = Path(__file__).resolve().parents[1]   # .../project
DATA_FILE = BASE_DIR / "data" / "raw" / "SuperStoreOrders.csv"

df = pd.read_csv(DATA_FILE)

# ---- Standardize column names (if needed) ----
# (Your dataset already looks consistent, this is just a safety net.)
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

# ---- Dates ----
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
df["ship_date"] = pd.to_datetime(df["ship_date"], errors="coerce")

df["shipping_delay"] = (df["ship_date"] - df["order_date"]).dt.days

df["year"] = df["order_date"].dt.year.astype("Int64")
df["month_num"] = df["order_date"].dt.month.astype("Int64")
df["month_name"] = df["order_date"].dt.month_name()

# ---- Season (derived from month_num) ----
df["season"] = df["month_num"].map({
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Fall", 10: "Fall", 11: "Fall",
})

# ---- Numeric safety ----
for col in ["sales", "profit", "discount"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
