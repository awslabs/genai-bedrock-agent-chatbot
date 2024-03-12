import streamlit as st


def clear_input():
    """
    Clear input when clicking `Clear conversation`.
    """
    # st.session_state.session_id = ""
    st.session_state.questions = []
    st.session_state.answers = []
    st.session_state["temp"] = st.session_state["input"]
    st.session_state["input"] = ""


def show_empty_container(height: int = 100) -> st.container:
    """
    Display empty container to hide UI elements below while thinking

    Parameters
    ----------
    height : int
        Height of the container (number of lines)

    Returns
    -------
    st.container
        Container with large vertical space
    """
    empty_placeholder = st.empty()
    with empty_placeholder.container():
        st.markdown("<br>" * height, unsafe_allow_html=True)
    return empty_placeholder


def show_footer() -> None:
    """
    Show footer with AWS copyright
    """

    st.markdown("---")
    st.markdown(
        "<div style='text-align: right'> © 2023 Amazon Web Services </div>",
        unsafe_allow_html=True,
    )
