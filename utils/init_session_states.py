from streamlit import session_state


def init():
    session_state["decrypted_filename"] = (
        None
        if "decrypted_filename" not in session_state
        else session_state["decrypted_filename"]
    )
    session_state["password"] = (
        "" if "password" not in session_state else session_state["password"]
    )
    session_state["is_encrypted"] = (
        False if "is_encrypted" not in session_state else session_state["is_encrypted"]
    )


if __name__ == "__main__":
    init()
