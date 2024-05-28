import contextlib
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from random import random
from typing import Callable, Dict, Literal, Optional, Tuple, Union

import pandas as pd
import requests
import streamlit as st
from PIL import Image
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.errors import PdfReadError, PdfStreamError
from streamlit import session_state
from streamlit.runtime.uploaded_file_manager import UploadedFile
from streamlit_pdf_viewer import pdf_viewer


@st.cache_data
def image_to_pdf(stamp_img: Union[Path, str]) -> PdfReader:
    img = Image.open(stamp_img)
    img_as_pdf = BytesIO()
    img.save(img_as_pdf, "pdf")
    return PdfReader(img_as_pdf)


@st.cache_data
def watermark_img(
    reader: PdfReader,
    stamp_img: UploadedFile,
) -> None:
    # Convert the image to a PDF
    stamp_pdf = image_to_pdf(stamp_img)

    # Then use the same stamp code from above
    stamp_page = stamp_pdf.pages[0]

    writer = PdfWriter()

    writer.append(reader)

    for content_page in writer.pages:
        content_page.merge_transformed_page(
            stamp_page, Transformation(), expand=True, over=False
        )

    # TODO: Write to byte_stream
    with open("watermarked.pdf", "wb") as fp:
        writer.write(fp)


def get_option(key: Literal["main", "merge"]) -> str:
    return st.radio(
        label="Upload a PDF, or load PDF from a URL",
        options=(
            "Upload a PDF ⬆️",
            "Load PDF from a URL 🌐",
        ),
        horizontal=True,
        help="PDFs are deleted from the server when you\n"
        "* upload another PDF, or\n"
        "* clear the file uploader, or\n"
        "* close the browser tab.",
        key=f"upload_{key}",
    )


def get_password(key: Literal["main", "merge"]) -> Optional[str]:
    password = st.text_input(
        "PDF Password",
        type="password",
        placeholder="Required if PDF is protected",
        key=f"password_{key}",
    )
    return password if password != "" else None


def upload_pdf(
    key: Literal["main", "merge"], password: Optional[str]
) -> Optional[Tuple[bytes, PdfReader]]:
    if file := st.file_uploader(
        label="Upload a PDF",
        type=["pdf"],
        key=f"file_{key}",
    ):
        session_state["file"] = file
        session_state["name"] = file.name
        pdf = file.getvalue()
        try:
            reader = PdfReader(BytesIO(pdf), password=password)
        except PdfReadError:
            reader = PdfReader(BytesIO(pdf))
        return pdf, reader
    return None, None


def load_pdf_from_url(
    key: Literal["main", "merge"], password: Optional[str]
) -> Optional[Tuple[bytes, PdfReader]]:
    url = st.text_input(
        "PDF URL",
        key=f"url_{key}",
        value="https://getsamplefiles.com/download/pdf/sample-1.pdf",
    )

    @st.cache_data
    def _cached_get_url(url: str) -> requests.Response:
        return requests.get(url)

    if url != "":
        try:
            response = _cached_get_url(url)
            session_state["file"] = pdf = response.content
            session_state["name"] = url.split("/")[-1]
            try:
                reader = PdfReader(BytesIO(pdf), password=password)
            except PdfReadError:
                reader = PdfReader(BytesIO(pdf))
            return pdf, reader
        except PdfStreamError:
            st.error("The URL does not seem to be a valid PDF file.", icon="❌")
    return None, None


def load_pdf(
    key: Literal["main", "merge"] = "main",
) -> Optional[Tuple[bytes, PdfReader, str, bool]]:
    option = get_option(key)
    password = get_password(key)

    # Map options to functions
    option_functions: Dict[str, Callable[[str, str], Tuple[bytes, PdfReader]]] = {
        "Upload a PDF ⬆️": upload_pdf,
        "Load PDF from a URL 🌐": load_pdf_from_url,
    }

    if function := option_functions.get(option):
        pdf, reader = function(key, password)

        if pdf:
            preview_pdf(
                reader,
                pdf,
                key,
                password,
            )
            return pdf, reader, password, reader.is_encrypted

    return None, None, "", False


def handle_encrypted_pdf(reader: PdfReader, password: str, key: str) -> None:
    if password:
        session_state["decrypted_filename"] = f"unprotected_{session_state['name']}"
        decrypt_pdf(
            reader,
            password,
            filename=session_state["decrypted_filename"],
        )
        pdf_viewer(
            f"unprotected_{session_state['name']}",
            height=400 if key == "main" else 250,
            width=300,
            key=random(),
        )
    else:
        st.error("Password required", icon="🔒")


def handle_unencrypted_pdf(pdf: bytes, key: str) -> None:
    pdf_viewer(
        pdf,
        height=400 if key == "main" else 250,
        width=300,
        key=random(),
    )


def display_metadata(reader: PdfReader) -> None:
    metadata = {"Number of pages": len(reader.pages)}
    for k in reader.metadata:
        value = reader.metadata[k]
        if is_pdf_datetime(value):
            value = convert_pdf_datetime(value)

        metadata[k.replace("/", "")] = value

    metadata = pd.DataFrame.from_dict(metadata, orient="index", columns=["Value"])
    metadata.index.name = "Metadata"

    st.dataframe(metadata)


def preview_pdf(
    reader: PdfReader,
    pdf: bytes = None,
    key: Literal["main", "other"] = "main",
    password: str = "",
) -> None:
    with contextlib.suppress(NameError):
        if key == "main":
            with st.expander("📄 **Preview**", expanded=bool(pdf)):
                if reader.is_encrypted:
                    handle_encrypted_pdf(reader, password, key)
                else:
                    handle_unencrypted_pdf(pdf, key)

            with st.expander("🗄️ **Metadata**"):
                display_metadata(reader)
        elif reader.is_encrypted:
            handle_encrypted_pdf(reader, password, key)
        else:
            handle_unencrypted_pdf(pdf, key)


@st.cache_data
def is_pdf_datetime(s: str) -> bool:
    pattern = r"^D:\d{14}\+\d{2}\'\d{2}\'$"
    return bool(re.match(pattern, s))


@st.cache_data
def convert_pdf_datetime(pdf_datetime: str) -> str:
    # Remove the 'D:' at the beginning
    pdf_datetime = pdf_datetime[2:]

    # Extract the date, time, and timezone components
    date_str = pdf_datetime[:8]
    time_str = pdf_datetime[8:14]
    tz_str = pdf_datetime[14:]

    return (
        datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S").strftime(
            "%Y-%m-%d %H:%M:%S "
        )
        + tz_str
    )


@st.cache_data
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
            images |= {image.data: image.name for image in page.images}

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


@st.cache_data
def remove_images(pdf: bytes, remove_images: bool, password: str) -> bytes:
    reader = PdfReader(BytesIO(pdf))

    if reader.is_encrypted:
        reader.decrypt(password)

    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata(reader.metadata)

    if remove_images:
        writer.remove_images()

    bytes_stream = BytesIO()
    writer.write(bytes_stream)

    bytes_stream.seek(0)

    return bytes_stream.getvalue()


def reduce_image_quality(pdf: bytes, quality: int, password: str) -> bytes:
    reader = PdfReader(BytesIO(pdf))

    if reader.is_encrypted:
        reader.decrypt(password)

    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata(reader.metadata)

    for page in writer.pages:
        for img in page.images:
            img.replace(img.image, quality=quality)

    bytes_stream = BytesIO()
    writer.write(bytes_stream)

    bytes_stream.seek(0)

    return bytes_stream.getvalue()


@st.cache_data
def compress_pdf(pdf: bytes, password: str) -> bytes:
    reader = PdfReader(BytesIO(pdf))

    if reader.is_encrypted:
        reader.decrypt(password)

    writer = PdfWriter(clone_from=reader)

    for page in writer.pages:
        page.compress_content_streams()  # This is CPU intensive!

    bytes_stream = BytesIO()
    writer.write(bytes_stream)
    bytes_stream.seek(0)

    return bytes_stream.getvalue()
