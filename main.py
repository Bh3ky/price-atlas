import streamlit as st

from src.db import Database
from actions.scraping import scrape_product, refresh_competitors
from actions.analysis import run_llm_analysis
from ui.header import render_header
from ui.inputs import render_inputs
from ui.product_list import render_product_card
from ui.competitor_insights import render_competitor_insights
from state import get_selected_asin


def main():
    st.set_page_config(
        page_title="Amazon Competitor Analysis",
        page_icon="🫟",
        layout="wide",
    )

    render_header()
    asin, geo, domain = render_inputs()

    # --- Scrape product ---
    if st.button("Scrape Product") and asin:
        if not (len(asin) == 10 and asin.isalnum()):
            st.error("Invalid ASIN. Must be 10 alphanumeric characters.")
        else:
            with st.spinner("Scraping product..."):
                scrape_product(asin, geo, domain)
            st.success("Product scraped successfully")

    # --- Product list ---
    db = Database()
    products = [p for p in db.get_all_products() if not p.get("parent_asin")]

    if products:
        st.divider()
        st.subheader("Scraped Products")

        for idx, product in enumerate(products):
            render_product_card(product, idx)

    # --- Competitor analysis ---
    selected_asin = get_selected_asin()
    if selected_asin:
        st.divider()
        st.subheader(f"Competitor analysis for {selected_asin}")

        refresh_clicked = st.button("Refresh Competitors")
        if refresh_clicked:
            with st.spinner("Refreshing competitors..."):
                refresh_competitors(selected_asin, geo, domain)
            st.success("Competitors refreshed")

        # ✅ Render ONCE, full width
        render_competitor_insights(selected_asin)

        if st.button("Analyze with LLM", type="primary"):
            with st.spinner("Running LLM analysis..."):
                analysis = run_llm_analysis(selected_asin)
            st.markdown(analysis)


if __name__ == "__main__":
    main()