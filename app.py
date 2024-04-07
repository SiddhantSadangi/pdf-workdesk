import os
import traceback

import streamlit as st
from pypdf import PdfWriter
from streamlit import session_state

import utils

VERSION = "0.0.6"

PAGE_STR_HELP = """
Format
------
**all:** all pages  
**2:** 2nd page  
**1-3:** pages 1 to 3  
**2,4:** pages 2 and 4  
**1-3,5:** pages 1 to 3 and 5"""

st.set_page_config(
    page_title="PDF WorkDesk",
    page_icon="📄",
    menu_items={
        "About": f"PDF WorkDesk v{VERSION}  "
        f"\nApp contact: [Siddhant Sadangi](mailto:siddhant.sadangi@gmail.com)",
        "Report a Bug": "https://github.com/SiddhantSadangi/pdf-workdesk/issues/new",
        "Get help": None,
    },
    layout="wide",
)

# ---------- HEADER ----------
st.title("📄 Welcome to PDF WorkDesk!")

try:
    # ---------- INIT SESSION STATES ----------
    SESSION_STATES = (
        "decrypted_filename",
        "password",
    )

    for state in SESSION_STATES:
        if state in ("password"):
            session_state[state] = ""
        else:
            session_state[state] = (
                False if state not in session_state else session_state[state]
            )

    # ---------- SIDEBAR ----------
    with st.sidebar:

        # TODO: Update
        with st.expander("✅ Supported operations"):
            st.info(
                "* Upload PDF or load from a URL\n"
                "* Preview PDF contents and metadata\n"
                "* Extract text and images\n"
                "* Add and remove password\n"
            )

        pdf, reader = utils.load_pdf()

        with open("sidebar.html", "r", encoding="UTF-8") as sidebar_file:
            sidebar_html = sidebar_file.read().replace("{VERSION}", VERSION)

        st.components.v1.html(sidebar_html, height=750)

    # ---------- OPERATIONS ----------
    # TODO: Extract attachments (https://pypdf.readthedocs.io/en/stable/user/extract-attachments.html)
    # TODO: Undo last operation
    # TODO: Update metadata (https://pypdf.readthedocs.io/en/stable/user/metadata.html)

    if pdf:

        lcol, rcol = st.columns(2)

        with lcol.expander(label="🔍 Extract text"):

            extract_text_lcol, extract_text_rcol = st.columns(2)

            page_numbers_str = extract_text_lcol.text_input(
                "Pages to extract from?",
                placeholder="all",
                help=PAGE_STR_HELP,
                key="extract_text_pages",
            ).lower()

            mode = extract_text_rcol.radio(
                "Extraction mode",
                options=["plain", "layout"],
                horizontal=True,
                help="Layout mode extracts text in a format resembling the layout of the source PDF",
            )

            if page_numbers_str:
                try:
                    text = utils.extract_text(reader, page_numbers_str, mode)
                except (IndexError, ValueError):
                    st.error("Specified pages don't exist. Check the format.", icon="⚠️")
                else:
                    st.text(text)

                    with open("text.txt", "w", encoding="utf-8") as f:
                        f.write(text)

                    with open("text.txt") as f:
                        st.download_button(
                            "💾 Download extracted text",
                            data=f,
                            use_container_width=True,
                        )

        with rcol.expander(label="️🖼️ Extract images"):

            page_numbers_str = st.text_input(
                "Pages to extract from?",
                placeholder="all",
                help=PAGE_STR_HELP,
                key="extract_image_pages",
            ).lower()

            if page_numbers_str:
                try:
                    images = utils.extract_images(reader, page_numbers_str)
                except (IndexError, ValueError):
                    st.error("Specified pages don't exist. Check the format.", icon="⚠️")
                else:
                    if images:
                        for data, name in images.items():
                            st.image(data, caption=name)
                    else:
                        st.info("No images found")

        with lcol.expander("🔐 Add password"):

            session_state["password"] = st.text_input(
                "Enter password",
                type="password",
            )

            algorithm = st.selectbox(
                "Algorithm",
                options=[
                    "RC4-40",
                    "RC4-128",
                    "AES-128",
                    "AES-256-R5",
                    "AES-256",
                ],
                index=3,
                help="Use `RC4` for compatibility and `AES` for security",
            )

            filename = f"protected_{session_state['name']}"

            if st.button(
                "🔒 Submit",
                use_container_width=True,
                disabled=(len(session_state.password) == 0),
            ):
                writer = PdfWriter()

                # Add all pages to the writer
                for page in reader.pages:
                    writer.add_page(page)

                # Add a password to the new PDF
                writer.encrypt(session_state["password"], algorithm=algorithm)

                # Save the new PDF to a file
                with open(filename, "wb") as f:
                    writer.write(f)

            if os.path.exists(filename):
                st.download_button(
                    "⬇️ Download protected PDF",
                    data=open(filename, "rb"),
                    mime="application/pdf",
                    file_name=filename,
                    use_container_width=True,
                )

        with rcol.expander("🔓 Remove password"):
            if reader.is_encrypted:
                st.download_button(
                    "⬇️ Download unprotected PDF",
                    data=open(session_state["decrypted_filename"], "rb"),
                    mime="application/pdf",
                    file_name=session_state["decrypted_filename"],
                    use_container_width=True,
                )
            else:
                st.info("PDF does not have a password")

        # with st.expander("➕ Merge PDFs"):

    else:
        st.info("👈 Upload a PDF to start")

except Exception as e:
    st.error(
        f"""The app has encountered an error:  
        `{e}`  
        Please create an issue [here](https://github.com/SiddhantSadangi/st_deepgram_playground/issues/new) 
        with the below traceback""",
        icon="🥺",
    )
    st.code(traceback.format_exc())
