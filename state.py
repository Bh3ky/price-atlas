import streamlit as st


def set_selected_asin(asin: str) -> None:
    st.session_state["analyzing_asin"] = asin


def get_selected_asin() -> str | None:
    return st.session_state.get("analyzing_asin")