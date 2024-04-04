import contextlib
from io import BytesIO

import pandas as pd
import requests
import streamlit as st
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfStreamError
from streamlit import session_state
from streamlit_pdf_viewer import pdf_viewer

from utils import convert_pdf_datetime, extract_text, is_pdf_datetime

VERSION = "0.0.0"

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
                reader = PdfReader(BytesIO(pdf), password=password)
            except PdfStreamError:
                st.error("The URL does not seem to be a valid PDF file.", icon="❌")

    if pdf:
        with contextlib.suppress(NameError):
            with st.expander("**Preview**", expanded=bool(pdf)):
                pdf_viewer(pdf, height=400, width=300)

            with st.expander("**Metadata**"):
                metadata = {}
                metadata["Number of pages"] = len(reader.pages)

                for k in reader.metadata:
                    value = reader.metadata[k]
                    if is_pdf_datetime(value):
                        value = convert_pdf_datetime(value)

                    metadata[k.replace("/", "")] = value

                metadata = pd.DataFrame.from_dict(
                    metadata, orient="index", columns=["Value"]
                )
                metadata.index.name = "Metadata"

                st.dataframe(metadata)

    with open("sidebar.html", "r", encoding="UTF-8") as sidebar_file:
        sidebar_html = sidebar_file.read().replace("{VERSION}", VERSION)

    # TODO: UPDATE
    # with st.expander("Supported operations"):
    #     st.info(
    #         "* Upload image, take one with your camera, or load from a URL\n"
    #         "* Crop\n"
    #         "* Remove background\n"
    #         "* Mirror\n"
    #         "* Convert to grayscale or black and white\n"
    #         "* Rotate\n"
    #         "* Change brightness, saturation, contrast, sharpness\n"
    #         "* Generate random image from supplied image\n"
    #         "* Download results"
    #     )
    st.components.v1.html(sidebar_html, height=750)

# ---------- HEADER ----------
st.title("📄 Welcome to PDF WorkDesk!")

# ---------- INIT SESSION STATES ----------
if "extract_text" not in session_state:
    session_state["extract_text"] = False


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
# TODO: Undo last operation
# TODO: Update metadata (https://pypdf.readthedocs.io/en/stable/user/metadata.html)

if pdf:

    lcol, rcol = st.columns(2)

    with lcol.expander(label="🔍 Extract text", expanded=session_state.extract_text):

        page_numbers_str = st.text_input(
            "Pages to extract?",
            placeholder="all",
            help="""
            Format
            ------
            **all:** all pages
            **2:** 2nd page
            **1-3:** pages 1 to 3
            **2,4:** pages 2 and 4
            **1-3,5:** pages 1 to 3 and 5""",
        ).lower()

        if page_numbers_str:
            try:
                text = extract_text(reader, page_numbers_str)
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

    # TODO: Show only when the PDF has been updated
    with open("updated-pdf.pdf", "rb") as f:
        st.download_button(
            "💾 Download updated PDF",
            data=session_state.file,
            mime="application/pdf",
            use_container_width=True,
        )
else:
    st.info("👈 Upload a PDF to start")
