import contextlib
import os
from io import BytesIO

import pandas as pd
import requests
import streamlit as st
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfStreamError
from streamlit import session_state
from streamlit_pdf_viewer import pdf_viewer

import utils

VERSION = "0.0.2"

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

# ---------- SIDEBAR ----------
with st.sidebar:

    # TODO: Update
    with st.expander("✅ Supported operations"):
        st.info(
            "* Upload PDF or load from a URL\n"
            "* Preview PDF contents and metadata\n"
            "* Extract text and images\n"
            "* Add password\n"
        )

    pdf = None
    option = st.radio(
        label="Upload a PDF, or load image from a URL",
        options=(
            "Upload a PDF ⬆️",
            "Load PDF from a URL 🌐",
        ),
        horizontal=True,
        help="All PDFs are deleted from the server when you\n* upload another PDF\n* clear the file uploader\n* close the browser tab",
    )

    password = st.text_input("PDF Password", type="password", placeholder="Optional")
    password = password if password != "" else None

    if option == "Upload a PDF ⬆️":
        if file := st.file_uploader(
            label="Upload a PDF",
            type=["pdf"],
        ):
            session_state["file"] = file
            session_state["name"] = file.name
            pdf = file.getvalue()
            reader = PdfReader(BytesIO(pdf), password=password)

    elif option == "Load PDF from a URL 🌐":
        url = st.text_input(
            "PDF URL",
            key="url",
            value="https://getsamplefiles.com/download/pdf/sample-1.pdf",
        )

        if url != "":
            try:
                response = requests.get(url)
                session_state["file"] = pdf = response.content
                session_state["name"] = url.split("/")[-1]
                reader = PdfReader(BytesIO(pdf), password=password)
            except PdfStreamError:
                st.error("The URL does not seem to be a valid PDF file.", icon="❌")

    if pdf:
        with contextlib.suppress(NameError):
            with st.expander("📄 **Preview**", expanded=bool(pdf)):
                pdf_viewer(pdf, height=400, width=300)

            with st.expander("🗄️ **Metadata**"):
                metadata = {}
                metadata["Number of pages"] = len(reader.pages)

                for k in reader.metadata:
                    value = reader.metadata[k]
                    if utils.is_pdf_datetime(value):
                        value = utils.convert_pdf_datetime(value)

                    metadata[k.replace("/", "")] = value

                metadata = pd.DataFrame.from_dict(
                    metadata, orient="index", columns=["Value"]
                )
                metadata.index.name = "Metadata"

                st.dataframe(metadata)

    with open("sidebar.html", "r", encoding="UTF-8") as sidebar_file:
        sidebar_html = sidebar_file.read().replace("{VERSION}", VERSION)

    # TODO: UPDATE
    st.components.v1.html(sidebar_html, height=750)

# ---------- HEADER ----------
st.title("📄 Welcome to PDF WorkDesk!")

# ---------- INIT SESSION STATES ----------
SESSION_STATES = ("extract_text", "extract_images", "add_password", "password")

for state in SESSION_STATES:
    if state in ("password"):
        session_state[state] = ""
    else:
        session_state[state] = (
            False if state not in session_state else session_state[state]
        )


# ---------- FUNCTIONS ----------
def _reset(key: str) -> None:
    if key == "all":
        session_state["rotate_slider"] = 0
        session_state["brightness_slider"] = session_state["saturation_slider"] = (
            session_state["contrast_slider"]
        ) = 100
        session_state["bg"] = session_state["crop"] = session_state["mirror"] = (
            session_state["gray_bw"]
        ) = 0
    elif key == "rotate_slider":
        session_state["rotate_slider"] = 0
    elif key == "checkboxes":
        session_state["crop"] = session_state["mirror"] = session_state["gray_bw"] = 0
    else:
        session_state[key] = 100


def _extract_text() -> None:
    session_state["extract_text"] = True


# ---------- OPERATIONS ----------
# TODO: Extract attachments (https://pypdf.readthedocs.io/en/stable/user/extract-attachments.html)
# TODO: Undo last operation
# TODO: Update metadata (https://pypdf.readthedocs.io/en/stable/user/metadata.html)

if pdf:

    lcol, rcol = st.columns(2)

    with lcol.expander(label="🔍 Extract text", expanded=session_state.extract_text):

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

                with open("text.txt", "w") as f:
                    f.write(text)

                with open("text.txt") as f:
                    st.download_button(
                        "💾 Download extracted text",
                        data=f,
                        use_container_width=True,
                    )

    with rcol.expander(label="️🖼️ Extract images", expanded=session_state.extract_images):

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

    with lcol.expander("🔐 Add password", expanded=session_state.add_password):

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

else:
    st.info("👈 Upload a PDF to start")
