from langchain_text_splitters import RecursiveCharacterTextSplitter
from tokenizers import Tokenizer


CHUNK_SIZE = 400
SEPARATORS = ["\n\n", "\n", "। ", ". ", "? ", "! ", " ", ""]
TOKENIZER = Tokenizer.from_pretrained("BAAI/bge-m3")


def count_tokens(text):
    return len(TOKENIZER.encode(text, add_special_tokens=False).ids)


SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50,
    separators=SEPARATORS,
    length_function=count_tokens
)


def split_table(markdown, max_tokens=CHUNK_SIZE):
    lines = markdown.splitlines()
    header, rows = lines[:2], lines[2:]
    pieces, current = [], []
    for row in rows:
        if current and count_tokens("\n".join(header + current + [row])) > max_tokens:
            pieces.append("\n".join(header + current))
            current = []
        current.append(row)
    if current:
        pieces.append("\n".join(header + current))
    return pieces


def chunk_pages(pages, title):
    chunks = []
    index = 0
    
    for page in pages:
        pieces = [("text", p) for p in SPLITTER.split_text(page["text"])] if page["text"] else []
        for table in page["tables"]:
            pieces += [("table", p) for p in split_table(table)]
        for kind, piece in pieces:
            chunks.append({
                "text": piece,
                "embed_text": f"{title}\n\n{piece}",
                "source": title,
                "page": page["page"],
                "index": index,
                "type": kind,
            })
            index += 1
    return chunks