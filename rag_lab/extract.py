import pymupdf
import re


LEADER = re.compile(r"(?:\.\s?){8,}") # Matches 8 or more dots, with or 
# without spaces between them. This is done mainly for header and page number
MIN_LEADER_LINES = 5
MIN_TABLE_ROWS = 2
MIN_TABLE_COLS = 2


def is_contents_page(text):
    leader_lines = sum(1 for line in text.splitlines() if LEADER.search(line))
    return leader_lines >= MIN_LEADER_LINES


def clean_cell(cell):
    if cell is None:
        return ""
    return " ".join(cell.replace("\u200b", "").split()).replace("|", "\\|")
    

def table_to_markdown(table):
    rows = table.extract()
    if table.header.external:
        rows = [table.header.names] + rows
    width = max(len(row) for row in rows)
    rows = [[clean_cell(c) for c in row] + [""] * (width - len(row)) for row in rows]
    header, *body = rows
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * width]
    lines += ["| " + " | ".join(row) + " |" for row in body]
    return "\n".join(lines)


def text_outside(page, rects):
    kept = []
    for x0, y0, x1, y1, text, _, block_type in page.get_text("blocks"):
        if block_type != 0:
            return None
        center = pymupdf.Point((x0 + y0)/2, (x1 + y1)/2)
        if not any(center in rect for rect in rects):
            kept.append(text)
    return "\n".join(kept)


def extract_pages(path):
    pages = []
    for number, page in enumerate(pymupdf.open(path), 1):
        tables = [
            t for t in page.find_tables().tables
            if t.row_count >= MIN_TABLE_ROWS and t.col_count >= MIN_TABLE_COLS
        ]
        if tables:
            text = text_outside(page, [pymupdf.Rect(t.bbox) for t in tables])
        else:
            text = page.get_text("text")
        text = text.replace("\u200b", "").strip()
        if text and is_contents_page(text):
            continue
        markdown = [table_to_markdown(t) for t in tables]
        if text or markdown:
            pages.append({"page": number, "text": text, "tables": markdown})
    return pages