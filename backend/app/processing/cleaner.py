import re

from bs4 import BeautifulSoup


def clean_html(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ")


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" \n", "\n", text)
    return text.strip()


def clean_document(text: str, is_html: bool = False) -> str:
    if is_html:
        text = clean_html(text)
    return normalize_whitespace(text)
