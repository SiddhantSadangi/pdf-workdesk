import re
from datetime import datetime

from pypdf import PdfReader


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


def extract_text(reader: PdfReader.pages, page_numbers_str: str = "all") -> str:
    text = ""

    if page_numbers_str == "all":
        for page in reader.pages:
            text = text + " " + page.extract_text()
    else:
        pages = parse_page_numbers(page_numbers_str)
        for page in pages:
            text = text + " " + reader.pages[page].extract_text()

    return text
