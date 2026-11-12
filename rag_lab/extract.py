import pymupdf
import re


LEADER = re.compile(r"(?:\.\s?){8,}") # Matches 8 or more dots, with or 
# without spaces between them. This is done mainly for header and page number
MIN_LEADER_LINES = 5


def is_contents_page(text):
    leader_lines = sum(1 for line in text.splitlines() if LEADER.search(line))
    return leader_lines >= MIN_LEADER_LINES


def extract_pages(path):
    doc = pymupdf.open(path)
    pages = []
    for page in doc:
        text = page.get_text("text").replace("\u200b", "").strip()
        if not text or is_contents_page(text):
            continue
        pages.append({"page": page.number + 1, "text": text})
    return pages