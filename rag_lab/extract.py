import pymupdf


def extract_pages(path):
    doc = pymupdf.open(path)
    pages = []
    for page in doc:
        text = page.get_text("text").strip()
        if not text:
            continue
        pages.append({"page": page.number + 1, "text": text})
    return pages