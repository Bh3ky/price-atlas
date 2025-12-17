import re

import pandas as pd
import streamlit as st

from src.db import Database

st.title("📊 Price Atlas - Competitor Analysis")

# Load products from the TinyDB-backed Database.
# Note: `data.json` is now a human-readable export; TinyDB storage lives in `tinydb.json`.
db = Database()
all_products = db.get_all_products()

# Sidebar selecting the product
product_titles = [p.get("title", f"Product {i}") for i, p in enumerate(all_products)]

if not product_titles:
    st.warning("No products found in the database.")
    st.stop()

selected_product = st.sidebar.selectbox("Select Product", product_titles)

# Get selected product record
product_record = next((prod for prod in all_products if prod.get("title") == selected_product), None)

if not product_record:
    st.info("Selected product not found in DB.")
    st.stop()

competitors_list = product_record.get("competitors", [])

if not competitors_list:
    st.info("No competitors found for this product.")
    st.stop()

# Parse competitors into DataFrame
data = []
for item in competitors_list:
    match = re.match(r"(.+?) - USD (\d+\.?\d*)", item)
    if match:
        name, price = match.groups()
        data.append({"Product Name": name, "Price (USD)": float(price)})

if not data:
    st.info("No valid competitor data to display.")
    st.stop()

df = pd.DataFrame(data)

# Display table
st.subheader("Competitor Prices Table")
st.dataframe(df)