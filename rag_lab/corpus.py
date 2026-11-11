import json
from pathlib import Path

import numpy as np

from chunking import chunk_pages
from extract import extract_pages
from providers import embed
from search import build_index


HERE = Path(__file__).resolve().parent
PDFS = HERE / "pdfs"
CACHE = HERE / "cache"


def load_pdf(path):
    CACHE.mkdir(exist_ok=True)
    chunks_file = CACHE / f"{path.stem}.json"
    vectors_file = CACHE / f"{path.stem}.npy"
    if chunks_file.exists() and vectors_file.exists():
        return json.loads(chunks_file.read_text(encoding="utf-8")), np.load(vectors_file)
    
    chunks = chunk_pages(extract_pages(path), title=path.stem)
    vectors = np.array(embed([c["embed_text"] for c in chunks]), dtype=np.float32)
    chunks_file.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    np.save(vectors_file, vectors)
    return chunks, vectors


def load_corpus(verbose=True):
    all_chunks, all_vectors = [], []
    for pdf in sorted(PDFS.glob("*.pdf")):
        chunks, vectors = load_pdf(pdf)
        all_chunks.extend(chunks)
        all_vectors.append(vectors)
        if verbose:
            print(f"{pdf.name}: {len(chunks)} chunks")
    return all_chunks, build_index(np.vstack(all_vectors))