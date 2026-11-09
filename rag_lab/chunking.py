from langchain_text_splitters import RecursiveCharacterTextSplitter
from tokenizers import Tokenizer


TOKENIZER = Tokenizer.from_pretrained("BAAI/bge-m3")
SEPARATORS = ["\n\n", "\n", "। ", ". ", "? ", "! ", " ", ""]


def count_tokens(text):
    return len(TOKENIZER.encode(text, add_special_tokens=False).ids)


SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50,
    separators=SEPARATORS,
    length_function=count_tokens
)


def chunk_pages(pages, title):
    chunks = []
    index = 0
    
    for page in pages:
        for piece in SPLITTER.split_text(page["text"]):
            chunks.append({
                "text": piece,
                "embed_text": f"{title}\n\n{piece}",
                "source": title,
                "page": page["page"],
                "index": index
            })
            index += 1
    return chunks