import contextlib
from io import BytesIO

import pandas as pd
import requests
import streamlit as st
from pypdf import PdfReader
from pypdf.errors import PdfStreamError
from streamlit_pdf_viewer import pdf_viewer

from utils import convert_pdf_datetime, is_pdf_datetime

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
with open("sidebar.html", "r", encoding="UTF-8") as sidebar_file:
    sidebar_html = sidebar_file.read().replace("{VERSION}", VERSION)

with st.sidebar:
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


# ---------- FUNCTIONS ----------
def _reset(key: str) -> None:
    if key == "all":
        st.session_state["rotate_slider"] = 0
        st.session_state["brightness_slider"] = st.session_state[
            "saturation_slider"
        ] = st.session_state["contrast_slider"] = 100
        st.session_state["bg"] = st.session_state["crop"] = st.session_state[
            "mirror"
        ] = st.session_state["gray_bw"] = 0
    elif key == "rotate_slider":
        st.session_state["rotate_slider"] = 0
    elif key == "checkboxes":
        st.session_state["crop"] = st.session_state["mirror"] = st.session_state[
            "gray_bw"
        ] = 0
    else:
        st.session_state[key] = 100


# ---------- OPERATIONS ----------

option = st.radio(
    label="Upload a PDF, or load image from a URL",
    options=(
        "Upload a PDF ⬆️",
        "Load PDF from a URL 🌐",
    ),
    horizontal=True,
    help="All PDFs are deleted from the server when you\n* upload another PDF\n* clear the file uploader\n* close the browser tab",
)

password = st.text_input("Password", type="password", placeholder="Optional")
password = password if password != "" else None

if option == "Upload a PDF ⬆️":
    if file := st.file_uploader(
        label="Upload a PDF",
        type=["pdf"],
    ):
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
            pdf = response.content
            reader = PdfReader(BytesIO(pdf), password=password)
        except PdfStreamError:
            st.error("The URL does not seem to be a valid PDF file.", icon="❌")

with contextlib.suppress(NameError):
    if pdf is not None:
        with st.expander("**Preview**", expanded=True):
            pdf_viewer(pdf, height=500)

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

        # if flag:
        #     Image.fromarray(final_image).save("final_image.png")
        # else:
        #     final_image.save("final_image.png")

        # col1, col2, col3 = st.columns(3)
        # if col1.button(
        #     "↩️ Reset All",
        #     on_click=_reset,
        #     use_container_width=True,
        #     kwargs={"key": "all"},
        # ):
        #     st.success(body="Image reset to original!", icon="↩️")
        # if col2.button(
        #     "🔀 Surprise Me!",
        #     on_click=_randomize,
        #     use_container_width=True,
        # ):
        #     st.success(body="Random image generated", icon="🔀")
        # with open("final_image.png", "rb") as file:
        #     col3.download_button(
        #         "💾Download final image",
        #         data=file,
        #         mime="image/png",
        #         use_container_width=True,
        #     )
