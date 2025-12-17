import streamlit as st
import pandas as pd
import plotly.express as px

from src.db import Database

# Utility function to parse dates
from datetime import datetime
from typing import Any


def _parse_created_at_iso(created_at: str) -> float:
    try:
        return datetime.fromisoformat(created_at).timestamp()
    except Exception:
        return 0.0


def _product_sort_ts(p: dict) -> float:
    ts = p.get("scraped_at")
    if isinstance(ts, (int, float)):
        return float(ts)
    created_at = p.get("created_at")
    if isinstance(created_at, str) and created_at:
        return _parse_created_at_iso(created_at)
    return 0.0


def _safe_price(x: Any) -> float | None:
    try:
        v = float(x)
    except Exception:
        return None
    if v <= 0:
        return None
    return v


def _to_dt_from_record(p: dict) -> datetime | None:
    ts = p.get("scraped_at")
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(float(ts))
        except Exception:
            pass
    created_at = p.get("created_at")
    if isinstance(created_at, str) and created_at:
        try:
            return datetime.fromisoformat(created_at)
        except Exception:
            return None
    return None


def _records_to_df(records: list[dict]) -> pd.DataFrame:
    rows = []
    for r in records or []:
        dt = _to_dt_from_record(r)
        rows.append(
            {
                "asin": r.get("asin"),
                "title": r.get("title") or r.get("asin"),
                "brand": r.get("brand") or "Unknown",
                "price": _safe_price(r.get("price")),
                "currency": r.get("currency") or "",
                "rating": r.get("rating"),
                "amazon_domain": r.get("amazon_domain") or "",
                "geo_location": (r.get("geo_location") or "").strip() or "Unknown",
                "parent_asin": r.get("parent_asin"),
                "source": r.get("source") or ("competitor" if r.get("parent_asin") else "target"),
                "created_at": r.get("created_at"),
                "scraped_at": r.get("scraped_at"),
                "dt": dt,
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
    return df


def _latest_by_asin(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df2 = df.copy()
    if "dt" not in df2.columns:
        df2["dt"] = pd.NaT
    df2 = df2.sort_values(["asin", "dt"], ascending=[True, True], na_position="first")
    latest = df2.groupby("asin", as_index=False).tail(1)
    return latest


def render_competitor_insights(selected_asin: str):
    """
    Full-featured competitor insights UI.
    """
    db = Database()
    parent = db.get_product(selected_asin) or {}
    parent_price = _safe_price(parent.get("price"))
    parent_currency = parent.get("currency") or ""
    parent_title = parent.get("title") or selected_asin

    comp_records = db.search_products({"parent_asin": selected_asin})
    if not comp_records:
        st.info("No competitor records yet. Click “Refresh Competitors” to populate data.")
        return

    df_all = _records_to_df(comp_records)
    df_latest = _latest_by_asin(df_all)

    df_priced = df_latest.dropna(subset=["price"]).copy()

    st.caption(f"Target: {parent_title} | Price: {parent_currency} {parent_price if parent_price is not None else 'N/A'}")

    tab_price, tab_trends, tab_regions, tab_overview = st.tabs(
        ["Price Snapshot", "Trends", "Regions", "Overview & Alerts"]
    )

    # ------------------ Price Snapshot Tab ------------------
    with tab_price:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Competitors (latest)", int(df_latest["asin"].nunique()))
        c2.metric("With price", int(df_priced["asin"].nunique()))
        if parent_price is not None and not df_priced.empty:
            cheaper = int((df_priced["price"] < parent_price).sum())
            c3.metric("Cheaper than target", cheaper)
            c4.metric(
                "Avg competitor price",
                f"{parent_currency} {df_priced['price'].mean():,.2f}" if parent_currency else f"{df_priced['price'].mean():,.2f}"
            )
        else:
            c3.metric("Cheaper than target", "—")
            c4.metric("Avg competitor price", "—")

        if not df_priced.empty:
            df_bar = df_priced.sort_values("price", ascending=True)
            fig_bar = px.bar(
                df_bar,
                x="price",
                y="title",
                orientation="h",
                color="brand",
                hover_data=["asin", "amazon_domain", "geo_location", "rating"],
                title="Price Comparison Across Competitors (latest snapshot)",
            )
            if parent_price is not None:
                fig_bar.add_vline(
                    x=parent_price,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="Target price",
                    annotation_position="top",
                )
            st.plotly_chart(fig_bar, use_container_width=True)

            fig_scatter = px.scatter(
                df_priced,
                x="rating",
                y="price",
                color="brand",
                hover_data=["title", "asin", "amazon_domain", "geo_location"],
                title="Price vs Rating (latest snapshot)",
            )
            if parent_price is not None:
                fig_scatter.add_hline(
                    y=parent_price,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="Target price",
                    annotation_position="top left",
                )
            st.plotly_chart(fig_scatter, use_container_width=True)

            # Tabular view with deltas
            df_table = df_priced[["title", "asin", "brand", "price", "currency", "rating", "amazon_domain", "geo_location"]].copy()
            if parent_price is not None:
                df_table["delta"] = df_table["price"] - parent_price
                df_table["delta_pct"] = (df_table["price"] / parent_price - 1.0) * 100.0
                df_table = df_table.sort_values("delta")
            st.dataframe(df_table, use_container_width=True)

    # ------------------ Trends Tab ------------------
    with tab_trends:
        st.caption("Trend charts appear once you scrape multiple times (snapshots).")
        df_hist = df_all.dropna(subset=["asin", "dt"]).copy()
        df_hist["price"] = pd.to_numeric(df_hist["price"], errors="coerce")
        df_hist = df_hist.dropna(subset=["price"])
        base_hist = _records_to_df(
            [r for r in db.search_products({"asin": selected_asin}) if not r.get("parent_asin")]
        )
        if not base_hist.empty:
            base_hist = base_hist.dropna(subset=["dt"])
            base_hist["price"] = pd.to_numeric(base_hist["price"], errors="coerce")
            base_hist["asin"] = f"{selected_asin} (target)"
            base_hist["title"] = parent_title
            df_hist2 = pd.concat([df_hist, base_hist], ignore_index=True)
        else:
            df_hist2 = df_hist

        if df_hist2.empty or df_hist2["dt"].nunique() < 2:
            st.info("Not enough history yet. Click “Refresh Competitors” multiple times to build series.")
        else:
            series = sorted(df_hist2["asin"].dropna().unique().tolist())
            default_series = series[: min(6, len(series))]
            chosen = st.multiselect("Series to plot", options=series, default=default_series, key=f"trend_select_{selected_asin}")
            df_plot = df_hist2[df_hist2["asin"].isin(chosen)].copy()
            fig_line = px.line(
                df_plot.sort_values("dt"),
                x="dt",
                y="price",
                color="asin",
                markers=True,
                hover_data=["title", "amazon_domain", "geo_location"],
                title="Price Trends Over Time (snapshots)",
            )
            st.plotly_chart(fig_line, use_container_width=True)

    # ------------------ Regions Tab ------------------
    with tab_regions:
        if df_priced.empty:
            st.info("No priced competitor rows available for region charts.")
        else:
            # Domain-level distribution
            by_domain = (
                df_priced.groupby("amazon_domain", as_index=False)["price"]
                .agg(avg_price="mean", min_price="min", max_price="max", count="count")
                .sort_values("avg_price")
            )
            fig_domain = px.bar(
                by_domain,
                x="amazon_domain",
                y="avg_price",
                hover_data=["count", "min_price", "max_price"],
                title="Country/Domain-wise Price Distribution (avg price by amazon domain)",
            )
            st.plotly_chart(fig_domain, use_container_width=True)

            geos = df_priced["geo_location"].fillna("Unknown")
            unique_geos = geos.unique().tolist()
            if len(unique_geos) <= 15 and df_priced["amazon_domain"].nunique() > 1:
                pivot = (
                    df_priced.assign(geo_location=geos)
                    .groupby(["geo_location", "amazon_domain"])["price"]
                    .mean()
                    .reset_index()
                    .pivot(index="geo_location", columns="amazon_domain", values="price")
                )
                fig_heat = px.imshow(
                    pivot,
                    aspect="auto",
                    title="Heatmap: Avg Price by Geo Location × Domain",
                    color_continuous_scale="Blues",
                )
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.caption("Heatmap hidden (too many geos or only one domain).")

    # ------------------ Overview & Alerts Tab ------------------
    with tab_overview:
        if df_latest.empty:
            st.info("No competitor data available.")
            return

        # Deal threshold slider
        threshold_pct = st.slider(
            "Deal alert threshold (% cheaper than target)",
            min_value=1,
            max_value=50,
            value=10,
            step=1,
            key=f"deal_threshold_{selected_asin}"
        )

        df_bucket = df_latest.copy()
        df_bucket["has_price"] = df_bucket["price"].notna()
        if parent_price is None:
            df_bucket["bucket"] = df_bucket["has_price"].map(lambda x: "Has price" if x else "Missing price")
        else:
            def _bucket(p):
                if p is None or pd.isna(p):
                    return "Missing price"
                if p < parent_price * (1 - threshold_pct / 100.0):
                    return f"Deal (≥{threshold_pct}% cheaper)"
                if p < parent_price:
                    return "Cheaper"
                if abs(p - parent_price) / parent_price <= 0.05:
                    return "Within ±5%"
                return "More expensive"
            df_bucket["bucket"] = df_bucket["price"].apply(_bucket)

        pie = df_bucket.groupby("bucket", as_index=False).size()
        fig_pie = px.pie(pie, values="size", names="bucket", title="Top Competitors Overview (price buckets)")
        st.plotly_chart(fig_pie, use_container_width=True)

        brand_counts = (
            df_latest.groupby("brand", as_index=False)
            .size()
            .sort_values("size", ascending=False)
            .head(10)
        )
        fig_brand = px.bar(brand_counts, x="brand", y="size", title="Top Brands in Competitor Set (listing count)")
        st.plotly_chart(fig_brand, use_container_width=True)

        if parent_price is not None and not df_priced.empty:
            deals = df_priced[df_priced["price"] < parent_price * (1 - threshold_pct / 100.0)].copy()
            deals["delta"] = deals["price"] - parent_price
            deals["delta_pct"] = (deals["price"] / parent_price - 1.0) * 100.0
            deals = deals.sort_values("delta")

            st.subheader("Deal Detection / Alerts")
            if deals.empty:
                st.info("No competitors meet the current deal threshold.")
            else:
                st.success(f"Found {len(deals)} deal(s) at ≥{threshold_pct}% cheaper than the target.")
                st.dataframe(
                    deals[["title", "asin", "brand", "price", "currency", "delta", "delta_pct", "amazon_domain", "geo_location"]],
                    use_container_width=True,
                )