import streamlit as st
from state import set_selected_asin


def render_product_card(product: dict, idx: int):
    """Render a single product card with proper rounded borders, image, info, and analyze button."""
    
    # Create a container with custom styling for the card border
    with st.container():
        st.markdown(
            """
            <style>
            div[data-testid="stVerticalBlock"] > div:has(div.product-card-content) {
                border: 1px solid #e6e6e6;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 15px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        # Add a marker class for styling
        st.markdown('<div class="product-card-content"></div>', unsafe_allow_html=True)
        
        # Create columns for image and info
        cols = st.columns([1, 2])

        # --- Left column: image ---
        with cols[0]:
            try:
                images = product.get("images", [])
                if images and len(images) > 0:
                    st.image(images[0], width=200)
                else:
                    st.write("No image available.")
            except Exception:
                st.write("Error loading image")

        # --- Right column: product info ---
        with cols[1]:
            st.subheader(product.get("title") or product["asin"])
            info_cols = st.columns(3)
            currency = product.get("currency", "")
            price = product.get("price", "-")
            info_cols[0].metric("Price", f"{currency} {price}" if currency else price)
            info_cols[1].write(f"**Brand:** {product.get('brand', '-')}")
            info_cols[2].write(f"**Category:** {product.get('product', '-')}")

            domain_info = f"amazon.{product.get('amazon_domain', 'com')}"
            geo_info = product.get("geo_location", "-")
            st.caption(f"Domain: {domain_info} | Geo Location: {geo_info}")

            st.write(product.get("url", "-"))

            # --- Analyze button (unique key per product) ---
            if st.button(
                "Start analyzing competitors",
                key=f"analyze_{product['asin']}_{idx}"
            ):
                set_selected_asin(product["asin"])
