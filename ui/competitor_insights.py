import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from typing import Any

from src.db import Database


def _safe_price(x: Any) -> float | None:
    try:
        v = float(x)
        return v if v > 0 else None
    except Exception:
        return None


def _to_dt(record: dict) -> datetime | None:
    if isinstance(record.get("scraped_at"), (int, float)):
        return datetime.fromtimestamp(record["scraped_at"])
    try:
        return datetime.fromisoformat(record.get("created_at", ""))
    except Exception:
        return None


def render_competitor_insights(selected_asin: str):
    db = Database()
    parent = db.get_product(selected_asin) or {}
    parent_price = _safe_price(parent.get("price"))
    currency = parent.get("currency", "")
    title = parent.get("title", selected_asin)

    records = db.search_products({"parent_asin": selected_asin})
    if not records:
        st.info("No competitor data available yet.")
        return

    rows = []
    for r in records:
        rows.append({
            "asin": r.get("asin"),
            "title": r.get("title"),
            "brand": r.get("brand", "Unknown"),
            "price": _safe_price(r.get("price")),
            "rating": r.get("rating"),
            "dt": _to_dt(r),
        })

    df = pd.DataFrame(rows).dropna(subset=["price"])

    st.caption(f"Target: {title} — {currency} {parent_price}")

    threshold_pct = st.slider(
        "Deal alert threshold (% cheaper than target)",
        1,
        50,
        10,
        key=f"deal_threshold_{selected_asin}",
    )

    fig = px.bar(
        df.sort_values("price"),
        x="price",
        y="title",
        color="brand",
        orientation="h",
        title="Price Comparison (Latest)",
    )

    if parent_price:
        fig.add_vline(
            x=parent_price,
            line_dash="dash",
            line_color="red",
        )

    st.plotly_chart(fig, use_container_width=True)

    deals = df[df["price"] < parent_price * (1 - threshold_pct / 100)]
    st.subheader("Deal Alerts")

    if deals.empty:
        st.info("No deals found at current threshold.")
    else:
        st.success(f"{len(deals)} deal(s) found")
        st.dataframe(deals, use_container_width=True)