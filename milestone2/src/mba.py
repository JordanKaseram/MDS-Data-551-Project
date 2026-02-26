import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules


import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

def get_mba_rules(df, segment="ALL", min_support=0.002, min_lift=1.0):
    df_use = df.copy()

    if segment != "ALL":
        df_use = df_use[df_use["segment"] == segment]

    # Remove single-item baskets
    basket_size = df_use.groupby("order_id")["sub_category"].nunique()
    valid_orders = basket_size[basket_size >= 2].index
    df_use = df_use[df_use["order_id"].isin(valid_orders)]

    # Basket matrix
    basket = (
        df_use.groupby(["order_id", "sub_category"])
        .size()
        .unstack(fill_value=0)
    )

    basket = (basket > 0)  # bool

    freq = apriori(basket, min_support=min_support, use_colnames=True)

    rules = association_rules(freq, metric="lift", min_threshold=min_lift)

    if rules.empty:
        return pd.DataFrame()

    # Keep only 1-to-1 rules (pairs)
    rules = rules[(rules["antecedents"].apply(len) == 1) & (rules["consequents"].apply(len) == 1)]

    # Stable extraction
    rules["prod1"] = rules["antecedents"].apply(lambda x: sorted(list(x))[0] if len(x) else None)
    rules["prod2"] = rules["consequents"].apply(lambda x: sorted(list(x))[0] if len(x) else None)

    rules_df = rules[["prod1", "prod2", "support", "confidence", "lift"]].sort_values("lift", ascending=False)
    return rules_df.reset_index(drop=True)

def prepare_rules_table(rules_df, top_n=20, min_lift=1.0, min_conf=0.0):
    """
    Filter + format rules for showing in a table.
    """
    if rules_df is None or rules_df.empty:
        return pd.DataFrame(columns=["prod1", "prod2", "support", "confidence", "lift"])

    out = rules_df.copy()

    # filter
    out = out[(out["lift"] >= min_lift) & (out["confidence"] >= min_conf)]

    # sort by lift
    out = out.sort_values(["lift", "confidence", "support"], ascending=False)

    # keep top n
    out = out.head(top_n)

    # nicer formatting for display
    out["support"] = out["support"].round(4)
    out["confidence"] = out["confidence"].round(4)
    out["lift"] = out["lift"].round(3)

    return out.reset_index(drop=True)