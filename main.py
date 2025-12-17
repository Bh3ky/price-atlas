import streamlit as st
from src.llm import analyze_competitors
from src.services import scrape_and_store_product, fetch_and_store_competitors
from src.db import Database
from datetime import datetime


def render_header():
    st.title("Amazon Competitor Analysis")
    st.caption("Enter your ASIN to get product insights")


def render_inputs():
    asin = st.text_input("ASIN", placeholder="e.g., BOVK234XYZ")
    geo = st.text_input(
        "Zip/Postal Code",
        placeholder="e.g., 10001, United States, US, UK, DE",
    )
    domain = st.selectbox(
        "Domain",
        ["com", "ca", "co.uk", "de", "za", "fr", "it", "ae"],
    )
    return asin.strip(), geo.strip(), domain


def render_product_card(product, idx=0):
    with st.container(border=True):
        cols = st.columns([1, 2])

        try:
            images = product.get("images", [])
            if images and len(images) > 0:
                cols[0].image(images[0], width=200)
            else:
                cols[0].write("No image found.")

        except Exception:
            cols[0].write("Error loading images")

        with cols[1]:
            st.subheader(product.get("title") or product["asin"])
            info_cols = st.columns(3)
            currency = product.get("currency", "")
            price = product.get("price", "-")
            info_cols[0].metric("price", f"{currency} {price}" if currency else price)
            info_cols[1].write(f"Brand: {product.get('brand', '-')}")
            info_cols[2].write(f"Product: {product.get('product', '-')}")

            domain_info = f"amazon.{product.get('amazon_domain', 'com')}"
            geo_info = product.get("geo_location", "-")
            st.caption(f"Domain: {domain_info} | Geo Location: {geo_info}")

            st.write(product.get("url", ""))
            # Make button keys unique 
            # Include both the ASIN and the stable index coming from the paginated loop
            if st.button("Start analyzing competitors", key=f"analyze_{product['asin']}_{idx}"):
                st.session_state["analyzing_asin"] = product["asin"]

def _parse_created_at_iso(created_at: str) -> float:
    """Best-effort parse of legacy DB records that only have created_at."""
    try:
        return datetime.fromisoformat(created_at).timestamp()
    except Exception:
        return 0.0


def _product_sort_ts(p: dict) -> float:
    """
    Sorting uses scraped_at when available.
    Fallback to created_at (legacy records) so older rows still sort sensibly.
    """
    ts = p.get("scraped_at")
    if isinstance(ts, (int, float)):
        return float(ts)
    created_at = p.get("created_at")
    if isinstance(created_at, str) and created_at:
        return _parse_created_at_iso(created_at)
    return 0.0


def main():
    st.set_page_config(page_title="Amazon Competitor Analysis", page_icon="🫟", layout="wide")
    render_header()
    asin, geo, domain = render_inputs()

    if st.button("Scrape Product") and asin:
        # Quick client-side validation: ASINs are typically 10 alphanumeric characters
        if not (len(asin) == 10 and asin.isalnum()):
            st.error("Invalid ASIN. Please enter a 10-character alphanumeric ASIN.")
        else:
            with st.spinner("Scraping product..."):
                data = scrape_and_store_product(asin, geo, domain)
            if data:
                # Auto-reset pagination so the newly scraped product appears immediately on page 1
                st.session_state["products_page"] = 1
                st.success("Product scraped successfully")
            else:
                st.warning("Scrape failed; nothing was stored. See the error above for details.")

    db = Database()
    products = db.get_all_products()

    items_per_page = 10

    # Optional sort toggle: allow switching between latest-first and oldest-first.
    # We store the choice in session_state so it persists across reruns.
    sort_choice = st.radio(
        "Sort order",
        options=["Latest first", "Oldest first"],
        horizontal=True,
        key="products_sort_order",
    )
    latest_first = sort_choice == "Latest first"

    # Ensure the most recently scraped products appear first (page 1).
    products = sorted(products, key=_product_sort_ts, reverse=latest_first)

    if products:
        st.divider()
        st.subheader("Product Scraped")

        total_pages = (len(products) + items_per_page - 1) // items_per_page

        # Pagination should be stateful and robust when list size / sort order changes.
        if "products_page" not in st.session_state:
            st.session_state["products_page"] = 1
        st.session_state["products_page"] = int(
            max(1, min(total_pages, st.session_state["products_page"]))
        )

        col_left, col_mid, col_right = st.columns([2, 3, 2])
        with col_mid:
            page_num = st.number_input(
                "Page",
                min_value=1,
                max_value=total_pages,
                value=int(st.session_state["products_page"]),
                step=1,
                key="products_page",
            )
        page_idx = int(page_num) - 1

        start_idx = page_idx * items_per_page
        end_idx = min(start_idx + items_per_page, len(products))

        st.write(f"Showing {start_idx + 1} - {end_idx} of {len(products)} products")

        # Important: pass a stable index derived from the paginated slice so per-card
        # widgets (buttons) get unique keys across pages.
        for global_idx, p in enumerate(products[start_idx:end_idx], start=start_idx):
            render_product_card(p, global_idx)

    selected_asin = st.session_state.get("analyzing_asin")
    if selected_asin:
        st.divider()
        st.subheader(f"Competitor analysis for {selected_asin}")

        db = Database()
        existing_comps = db.search_products({"parent_asin": selected_asin})

        if not existing_comps:
            with st.spinner("Searching..."):
                comps = fetch_and_store_competitors(selected_asin, domain, geo)

            st.success(f"Found {len(comps)} competitors")
        else:
            st.info(f"Found {len(existing_comps)} competitors in the database")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Refresh Competitors"):
            with st.spinner("Refreshing..."):
                comps = fetch_and_store_competitors(selected_asin, domain, geo)
            st.success(f"Refreshed {len(comps)} competitors")

    with col1:
        if st.button("Analyze with LLM", type="primary"):
            with st.spinner("Running LLM..."):
                analysis = analyze_competitors(selected_asin)
                st.markdown(analysis)


if __name__ == "__main__":
    main()