"""
Starting script of streamlit app.
"""

from datetime import datetime
import logging
import json
import streamlit as st

# from streamlit_chat import message
from utils import clear_input, show_empty_container, show_footer
from connections import Connections


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log(message):
    logger.info(message)


lambda_client = Connections.lambda_client


# agent_id = Connections.agent_id
# get unique sesion id
def get_response(user_input, session_id):
    """
    Get response from genai Lambda
    """
    print(f"session id: {session_id}")
    payload = {"body": {"query": user_input, "session_id": session_id}}

    lambda_function_name = Connections.lambda_function_name
    print(f"lambda_function_name: {lambda_function_name}")
    print(f"payload: {payload}")

    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    response_output = json.loads(response["Payload"].read().decode("utf-8"))
    print(f"response_output from genai lambda: {response_output}")

    return response_output


def header():
    """
    App Header setting
    """
    # --- Set up the page ---
    st.set_page_config(
        page_title="EC2 Developer Guide & Pricing Chatbot",
        page_icon=":computer:",
        layout="centered",
    )

    # Creating two columns, logo on the left and title on the right
    col1, col2 = st.columns(
        [1, 3]
    )  # The ratio between columns can be adjusted as needed

    with col1:
        st.image(
            "https://www.logicata.com/wp-content/uploads/2020/08/Amazon-EC2@4x-e1593195270371.png.webp",
            width=150,
        )

    with col2:
        st.markdown("# EC2 Developer Guide & Pricing Chatbot Demo")

    st.write("#### Ask me about Amazon EC2 in Linux and Pricing Details")
    st.write("-----")


def initialization():
    """
    Initialize sesstion_state variablesß
    """
    # --- Initialize session_state ---
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(datetime.now()).replace(" ", "_")
        st.session_state.questions = []
        st.session_state.answers = []

    if "temp" not in st.session_state:
        st.session_state.temp = ""

    # Initialize cache in session state
    if "cache" not in st.session_state:
        st.session_state.cache = {}


def show_message():
    """
    Show user question and answers
    """

    # --- Start the session when there is user input ---
    user_input = st.text_input("# **Question:** 👇", "", key="input")

    print(f"user_input: {user_input}")
    # Start a new conversation
    new_conversation = st.button(
        "New Conversation", key="clear", on_click=clear_input)
    if new_conversation:
        st.session_state.session_id = str(datetime.now()).replace(" ", "_")
        st.session_state.user_input = ""

    if user_input:
        session_id = st.session_state.session_id
        with st.spinner("Gathering info ..."):
            vertical_space = show_empty_container()
            vertical_space.empty()
            response_output = get_response(user_input, session_id)
            # response = get_agent_response(streaming_response)

            st.write("-------")
            source = 'output["source"]'
            if source.startswith("SELECT"):
                source = f"_{source}_"
            # else:
            #     source = source.replace('\n', '\n\n')
            source_title = "\n\n **Source**:" + "\n\n" + response_output["source"]
            answer = "**Answer**: \n\n" + response_output["answer"]
            st.session_state.questions.append(user_input)
            st.session_state.answers.append(answer + source_title)

    if st.session_state["answers"]:
        for i in range(len(st.session_state["answers"]) - 1, -1, -1):
            with st.chat_message(
                name="human",
                avatar="https://api.dicebear.com/7.x/notionists-neutral/svg?seed=Felix",
            ):
                st.markdown(st.session_state["questions"][i])

            with st.chat_message(
                name="ai",
                avatar="https://assets-global.website-files.com/62b1b25a5edaf66f5056b068/62d1345ba688202d5bfa6776_aws-sagemaker-eyecatch-e1614129391121.png",
            ):
                st.markdown(st.session_state["answers"][i])


def main():
    """
    Streamlit APP
    """
    # --- Section 1 ---
    header()
    # --- Section 2 ---
    initialization()
    # --- Section 3 ---
    show_message()
    # --- Foot Section ---
    show_footer()


if __name__ == "__main__":
    main()
