import streamlit as st


def render_inputs():
    asin = st.text_input("ASIN", placeholder="e.g. B08N5WRWNW")
    geo = st.text_input("Zip / Geo", placeholder="e.g. US, UK, DE, 10001")
    domain = st.selectbox(
        "Amazon Domain",
        ["com", "ca", "co.uk", "de", "za", "fr", "it", "ae"],
    )

    return asin.strip(), geo.strip(), domain