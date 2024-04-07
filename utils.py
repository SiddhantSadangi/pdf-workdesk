import contextlib
import re
from datetime import datetime
from io import BytesIO
from typing import Literal, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError, PdfStreamError
from streamlit import session_state
from streamlit_pdf_viewer import pdf_viewer


def load_pdf() -> Optional[Tuple[bytes, PdfReader]]:
    pdf = None
    option = st.radio(
        label="Upload a PDF, or load image from a URL",
        options=(
            "Upload a PDF ⬆️",
            "Load PDF from a URL 🌐",
        ),
        horizontal=True,
        help="PDFs are deleted from the server when you\n"
        "* upload another PDF, or\n"
        "* clear the file uploader, or\n"
        "* close the browser tab.",
    )

    password = st.text_input(
        "PDF Password", type="password", placeholder="Required if PDF is protected"
    )
    password = password if password != "" else None

    if option == "Upload a PDF ⬆️":
        if file := st.file_uploader(
            label="Upload a PDF",
            type=["pdf"],
        ):
            session_state["file"] = file
            session_state["name"] = file.name
            pdf = file.getvalue()
            try:
                reader = PdfReader(BytesIO(pdf), password=password)
            except PdfReadError:
                reader = PdfReader(BytesIO(pdf))

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
                try:
                    reader = PdfReader(BytesIO(pdf), password=password)
                except PdfReadError:
                    reader = PdfReader(BytesIO(pdf))
            except PdfStreamError:
                st.error("The URL does not seem to be a valid PDF file.", icon="❌")

    if pdf:
        preview_pdf(pdf, reader, password)

        return pdf, reader

    return None, None


def preview_pdf(pdf: bytes, reader: PdfReader, password: str = "") -> None:
    with contextlib.suppress(NameError):
        with st.expander("📄 **Preview**", expanded=bool(pdf)):
            if reader.is_encrypted:
                if password:
                    session_state["decrypted_filename"] = (
                        f"unprotected_{session_state['name']}"
                    )
                    decrypt_pdf(
                        reader,
                        password,
                        filename=session_state["decrypted_filename"],
                    )

                    pdf_viewer(
                        f"unprotected_{session_state['name']}",
                        height=400,
                        width=300,
                    )
                else:
                    st.error("Password required", icon="🔒")
            else:
                pdf_viewer(pdf, height=400, width=300)

        with st.expander("🗄️ **Metadata**"):
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


def is_pdf_datetime(s: str) -> bool:
    pattern = r"^D:\d{14}\+\d{2}\'\d{2}\'$"
    return bool(re.match(pattern, s))


def convert_pdf_datetime(pdf_datetime: str) -> str:
    # Remove the 'D:' at the beginning
    pdf_datetime = pdf_datetime[2:]

    # Extract the date, time, and timezone components
    date_str = pdf_datetime[:8]
    time_str = pdf_datetime[8:14]
    tz_str = pdf_datetime[14:]

    # Convert the date and time to a datetime object
    dt = (
        datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S").strftime(
            "%Y-%m-%d %H:%M:%S "
        )
        + tz_str
    )

    return dt


def parse_page_numbers(page_numbers_str):

    # Split the input string by comma or hyphen
    parts = page_numbers_str.split(",")

    # Initialize an empty list to store parsed page numbers
    parsed_page_numbers = []

    # Iterate over each part
    for part in parts:

        # Remove any leading/trailing spaces
        part = part.strip()

        # If the part contains a hyphen, it represents a range
        if "-" in part:
            start, end = map(int, part.split("-"))
            parsed_page_numbers.extend(range(start, end + 1))
        else:
            # Otherwise, it's a single page number
            parsed_page_numbers.append(int(part))

    return [i - 1 for i in parsed_page_numbers]


def extract_text(
    reader: PdfReader.pages,
    page_numbers_str: str = "all",
    mode: Literal["plain", "layout"] = "plain",
) -> str:
    text = ""

    if page_numbers_str == "all":
        for page in reader.pages:
            text = text + " " + page.extract_text(extraction_mode=mode)
    else:
        pages = parse_page_numbers(page_numbers_str)
        for page in pages:
            text = text + " " + reader.pages[page].extract_text()

    return text


def extract_images(reader: PdfReader.pages, page_numbers_str: str = "all") -> str:
    images = {}
    if page_numbers_str == "all":
        for page in reader.pages:
            images.update({image.data: image.name for image in page.images})

    else:
        pages = parse_page_numbers(page_numbers_str)
        for page in pages:
            images.update(
                {image.data: image.name for image in reader.pages[page].images}
            )

    return images


def decrypt_pdf(reader: PdfReader, password: str, filename: str) -> None:
    reader.decrypt(password)

    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    with open(filename, "wb") as f:
        writer.write(f)
