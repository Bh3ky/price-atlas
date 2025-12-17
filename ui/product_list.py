import streamlit as st
from state import set_selected_asin


def render_product_card(product: dict, idx: int):
    with st.container(border=True):
        st.subheader(product.get("title") or product["asin"])
        st.caption(f"ASIN: {product['asin']}")

        if st.button(
            "Start analyzing competitors",
            key=f"analyze_{product['asin']}_{idx}",
        ):
            set_selected_asin(product["asin"])