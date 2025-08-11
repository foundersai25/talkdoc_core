import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
import streamlit as st
import copy

curent_dir = Path(__file__).resolve().parent


# with open(Path(f"{curent_dir}/.streamlit/config.yaml")) as file:
#     config = yaml.load(file, Loader=SafeLoader)


def to_dict(obj):
    """Recursively converts an AttrDict to a standard dictionary."""
    if isinstance(obj, st.runtime.secrets.AttrDict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj  # Return value as-is if it's not a dict


def auth():
    credentials_ = to_dict(st.secrets.get("credentials", {}))
    cookies_ = to_dict(st.secrets.get("cookie", {}))

    credentials = copy.deepcopy(credentials_)
    cookies = copy.deepcopy(cookies_)

    credentials = stauth.Hasher.hash_passwords(credentials)

    authenticator = stauth.Authenticate(
        credentials,
        cookies["name"],
        cookies["key"],
        cookies["expiry_days"],
    )

    return credentials, authenticator

