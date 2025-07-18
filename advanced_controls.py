import streamlit as st
import json
import os


@st.dialog("Advanced Controls")
def advanced_controls():
    if "chat_id" in st.session_state and "username" in st.session_state:
        st.text(f"Chat ID: {st.session_state.chat_id}")
        export_chat = st.button("Export Chat")
        if export_chat:
            user_export_dir = f"chat_exports/{st.session_state['username']}"
            if not os.path.exists(user_export_dir):
                os.mkdir(user_export_dir)
            file_path = (
                f"{user_export_dir}/chat_history_{st.session_state.chat_id}.json"
            )
            with open(file_path, "w") as file:
                export_data = {
                    "form": st.session_state.seleced_form,
                    "chat": st.session_state.messages,
                }
                json.dump(export_data, file, indent=4)
            st.toast("Chat history exported")
    else:
        st.warning("Chat ID not available")
