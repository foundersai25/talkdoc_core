import logging
import streamlit as st

from talkdoc_core.gptservice import GPTService
from talkdoc_core.pdf_ops import fillPDF
from talkdoc_core.agents import get_json_from_chat_history_agent

import tempfile
from dotenv import load_dotenv
import uuid
import json
import os
import shutil
from pathlib import Path
from authentication import auth

from advanced_controls import advanced_controls

# Settings and configurations
st.set_page_config(
    page_title="TalkDoc", page_icon="🔥", initial_sidebar_state="expanded"
)
st.markdown(
    """
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}

        /* App-Hintergrund überall - alle Container */
        body, .stApp, .stAppViewContainer, .block-container, 
        .stMainBlockContainer, .stMain, .stAppHeader, .stBottom,
        [data-testid="stMainBlockContainer"], [data-testid="stAppScrollToBottomContainer"],
        [data-testid="stBottom"], [data-testid="stHeader"], [data-testid="stBottomBlockContainer"],
        .stChatInput, [data-testid="stChatInput"], .st-emotion-cache-hzygls {
            background-color: #F5F6FA !important;
        }

        /* Chat message containers: Avatar + Content (funktioniert mit aktuellem Streamlit) */
        div[data-testid="stChatMessageAvatarAssistant"] + div[data-testid="stChatMessageContent"] {
            background: #808D64 !important;
            color: white !important;
            border-radius: 10px;
            padding: 10px;
            margin: 5px 0;
        }
        div[data-testid="stChatMessageAvatarUser"] + div[data-testid="stChatMessageContent"] {
            background: #88ADD5 !important;
            color: white !important;
            border-radius: 10px;
            padding: 10px;
            margin: 5px 0;
        }

        /* Sidebar und Button Styles bleiben wie gehabt */
        .stSidebar {
            background-color: #808D64 !important;
        }
        .stSidebar .stButton {
            color: #white !important;
        }
        .stSidebar .stButton:hover {
            color: white !important;
        }
        .stButton > button:hover {
            color: white !important;
        }
        [data-testid="stButton"] button:hover {
            color: white !important;
        }
        .stDownloadButton button:hover {
            color: white !important;
        }
        .stSidebar [data-testid="stButton"] button:hover {
            color: white !important;
        }
        h2{
            color:#88ADD5 !important;
            }
        .st-ep{
            color: white !important;
            background-color: #88ADD5 !important;
        }
            .st-emotion-cache-s1k4sy{
                color: white !important;
                background-color: #F5F6FA !important;
            }
        
        
        /* Spezifischerer Submit Button Selektor */
        [data-testid="stChatInputSubmitButton"]:hover {
            background-color: #88ADD5 !important;
        }
        
        /* Dunkleres Blau für .st-bc mit heller Schrift */
        .st-bc {
            background-color: #88ADD5 !important;
            color: #white !important;
        }
        .st-emotion-cache-jh76sn{
            color: #white !important;
            background-color: #88ADD5 !important;
        }
        /* Chat Input Container mit Rahmen */
        [data-baseweb="textarea"], [data-baseweb="base-input"] {
            background-color: white !important;
            border: 1px solid #88ADD5 !important;
        }
        

    </style>
""",
    unsafe_allow_html=True,
)
load_dotenv(".env")
logging.basicConfig(level=logging.INFO)

with open("form_mapping.json", "r") as file:
    form_mapping = json.load(file)

st.session_state.pdf = False

# Authentication
try:
    credentials, authenticator = auth()
    authenticator.login()
except Exception as e:
    st.error(f"Authentication failed: {e}")
    st.stop()


# Main
if st.session_state["authentication_status"]:
    users = credentials["usernames"]
    st.session_state.open_ai_api_key = users[st.session_state["username"]][
        "OPENAI_API_KEY"
    ]

    authenticator.logout(location="sidebar")

    with st.sidebar:
        st.title("TalkDOC 🔥")

        # settings = st.button("⚙️", key="settings")
        # if settings:
        #     advanced_controls()

        valid_api_key = False

        if st.session_state.open_ai_api_key:
            gpt = GPTService(st.session_state.open_ai_api_key)
            valid_api_key = gpt.check_openai_api_key()

        selected_form = st.selectbox(
            "Select the form to fill",
            form_mapping.keys(),
            index=None,
            placeholder="Select the form to fill",
        )

        logging.info(f"Selected form: {selected_form}")

        if "selected_form" not in st.session_state:
            st.session_state.selected_form = None

        else:
            st.session_state.selected_form = selected_form

        if st.session_state.selected_form is not None:
            st.session_state.pdf = True
            st.session_state.seleced_form = selected_form
            template_json_path = form_mapping[selected_form]["template_path"]
            pdf_path = form_mapping[selected_form]["pdf_path"]
            form_id = form_mapping[selected_form]["id"]

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                temp_pdf_path = tmp.name

            shutil.copy(pdf_path, temp_pdf_path)

            with open(template_json_path, "r") as template_json_file:
                st.session_state.form_dict = json.load(template_json_file)

            # rag_flag = st.toggle("Knowledge Assistant")
            rag_flag = os.getenv("RAG_FLAG")
            fill_pdf_button = st.button("Fill PDF")

    if st.session_state.pdf and valid_api_key:
        st.header(selected_form)
        messages = gpt.add_system_prompt_for_chat(st.session_state.form_dict)
        if "chat_id" not in st.session_state:
            st.session_state.chat_id = uuid.uuid4()
            logging.info(f"Chat ID: {st.session_state.chat_id}")

        # First run - if there are no messages in the session state
        if "messages" not in st.session_state:
            st.session_state.messages = []
            st.session_state.messages.append(*messages)
            response = gpt.chat(st.session_state.messages, stream=False)
            st.session_state.messages.append({"role": "assistant", "content": response})

        # Display Message
        for message in st.session_state.messages:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Chat input
        if user_response := st.chat_input("Type your response here..."):
            st.session_state.messages.append({"role": "user", "content": user_response})

            with st.chat_message("user"):
                st.markdown(user_response)

            with st.chat_message("assistant"):
                if rag_flag:
                    logging.info("Answering using RAG")
                    # response = get_rag_response(form_id, user_response)
                    st.write("Knowledge Assistant is not implemented yet")
                else:
                    response = gpt.chat(st.session_state.messages)
                    response = st.write_stream(response)

                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

        if fill_pdf_button:
            response = get_json_from_chat_history_agent(
                gpt, st.session_state.messages, st.session_state.form_dict
            )
            st.toast("PDF is being filled, please wait...")

            filled_pdf = fillPDF(temp_pdf_path, st.session_state.form_dict, response)

            if filled_pdf:
                with open(temp_pdf_path, "rb") as file:
                    st.download_button(
                        data=file,
                        label="Download PDF",
                        file_name=f"filled_{form_id}.pdf",
                        mime="application/octet-stream",
                    )
