"""
Starting script of streamlit app.
"""

from datetime import datetime
import logging
import json
import streamlit as st
from pathlib import Path
import os

# from streamlit_chat import message
from utils import clear_input, show_empty_container, show_footer
from connections import Connections

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log(message):
    logger.info(message)


lambda_client = Connections.lambda_client

# os.getenv("save_folder")
SAVE_FOLDER = "/tmp"


def get_response(user_input, session_id):
    """
    Get response from genai Lambda
    """
    log(f"session id: {session_id}")
    payload = {"body": {"query": user_input, "session_id": session_id}}

    lambda_function_name = Connections.lambda_function_name
    log(f"lambda_function_name: {lambda_function_name}")
    log(f"payload: {payload}")

    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    response_output = json.loads(response["Payload"].read().decode("utf-8"))
    log(f"response_output from genai lambda: {response_output}")

    return response_output


def header():
    """
    App Header setting
    """
    # --- Set up the page ---
    st.set_page_config(
        page_title="Tools & Hardware Guide & Pricing Chatbot",
        page_icon=":computer:",
        layout="centered",
    )

    # Creating two columns, logo on the left and title on the right
    col1, col2 = st.columns(
        [1, 3]
    )  # The ratio between columns can be adjusted as needed

    with col1:
        st.image(
            "https://cdn.pixabay.com/photo/2014/04/02/14/09/hammer-306313_640.png",
            width=150,
        )

    with col2:
        st.markdown("# Image-to-SQL Chatbot Demo")

    st.write("#### Ask me about tools and hardware!")
    st.write("-----")


def initialization():
    """
    Initialize session_state variables
    """
    # --- Initialize session_state ---
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(datetime.now()).replace(" ", "_")
        st.session_state.questions = []
        st.session_state.answers = []
        st.session_state.image_filename = ""

    if "temp" not in st.session_state:
        st.session_state.temp = ""

    # Initialize cache in session state
    if "cache" not in st.session_state:
        st.session_state.cache = {}


def show_message():
    """
    Show user question and answers
    """

    # Start a new conversation
    new_conversation = st.button("New Conversation", key="clear", on_click=clear_input)

    with st.form(key="user_input_form"):
        user_input = st.text_input("# **Question1:** 👇", "", key="input")
        submit_button = st.form_submit_button(label="Submit")

    if submit_button and user_input:
        log(f"\n\nuser_input: {user_input}")
        # Incdlue image file name if present
        if st.session_state.image_filename:
            user_input += f"\n[<image_file_name>{st.session_state.image_filename}</image_file_name>]"
            st.session_state.image_filename = ""
        log(f"Combined user input: {user_input}")
        session_id = st.session_state.session_id
        with st.spinner(
            f"Gathering info ...{st.session_state.image_filename} - filename"
        ):
            vertical_space = show_empty_container()
            vertical_space.empty()
            response_output = get_response(user_input, session_id)
            st.write("-------")
            log(f"response_output: {response_output}")
            st.write(user_input)
            st.write(response_output)
            source = response_output.get("source", "")
            source = "No source" if not source else source
            log(f"source: {source}")

            if source.startswith("SELECT"):
                source = f"_{source}_"
            source_title = "\n\n **Source**:" + "\n\n" + source
            answer = "**Answer**: \n\n" + response_output.get("answer", "")
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


def image_input_section():
    """
    Image input section for the Streamlit app.
    """
    st.header("Image Input and Question Section")

    with st.container():
        st.subheader("Image File Upload:")
        uploaded_file = st.file_uploader(
            "Upload an Image", type=["png", "jpg", "jpeg"], key="new"
        )
        log(f"uploaded_file: {uploaded_file}")

        if uploaded_file is not None:
            st.image(uploaded_file)
            save_folder = SAVE_FOLDER
            file_name = st.session_state.session_id + "_" + uploaded_file.name
            save_path = Path(save_folder, file_name)
            log(f"save_path: {save_path}")
            with open(save_path, mode="wb") as w:
                w.write(uploaded_file.getvalue())

            if save_path.exists():
                log("\n save path exists")
                st.success(f"Image {uploaded_file.name} is successfully saved!")
                key = f"assets/images/{file_name}"
                st.session_state.image_filename = file_name
                # st.write(f"upload file::{save_path}, {Connections.BUCKET_NAME}, {key}")
                s3_client = Connections.s3_client
                s3_client.upload_file(
                    save_path,
                    Connections.BUCKET_NAME,
                    key,
                )
        else:
            st.session_state.image_filename = ""

        # if st.button("Process an Image"):
        #     if st.session_state.image_filename:
        #         st.write(f"Image {st.session_state.image_filename} processed.")


def main():
    """
    Streamlit APP
    """
    header()
    initialization()
    image_input_section()
    show_message()
    show_footer()


if __name__ == "__main__":
    main()
