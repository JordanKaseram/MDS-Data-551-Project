import pandas as pd


df_raw = pd.read_csv("data/SuperStoreOrders.csv")
df = df_raw.copy()
df["sales"] = (
    df["sales"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
)

df["sales"] = pd.to_numeric(df["sales"], errors="coerce")
df["margin"] = df["profit"] / df["sales"]

df["order_date"] = pd.to_datetime(df["order_date"], format="mixed", dayfirst=True, errors="coerce")
df["ship_date"]  = pd.to_datetime(df["ship_date"],  format="mixed", dayfirst=True, errors="coerce")
df["shipping_delay"] = (df["ship_date"] - df["order_date"]).dt.days
df["year"] = df["order_date"].dt.year.astype("Int64")
df["month_num"] = df["order_date"].dt.month.astype("Int64")
df["month_name"] = df["order_date"].dt.month_name()


