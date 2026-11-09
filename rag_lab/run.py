import json
from pathlib import Path

import numpy as np

from answer import answer
from chunking import chunk_pages
from extract import extract_pages
from providers import embed
from search import build_index, search


HERE = Path(__file__).resolve().parent
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
    
def main():
    all_chunks, all_vectors = [], []
    for pdf in sorted((HERE / "pdfs").glob("*.pdf")):
        chunks, vectors = load_pdf(pdf)
        all_chunks.extend(chunks)
        all_vectors.append(vectors)
        print(f"{pdf.name}: {len(chunks)} chunks")
        
    index = build_index(np.vstack(all_vectors))
    
    while True:
        question = input(f"\nQuestion (blank to quit): ").strip()
        if not question:
            break
        query_vector = np.array(embed([question])[0], dtype=np.float32)
        hits = search(index, all_chunks, query_vector, k=5)
        for rank, (chunk, score) in enumerate(hits, 1):
            print(f"  [{rank}] {chunk['source']} p.{chunk['page']}  score={score:.3f}")
        print("\n" + answer(question, hits))


if __name__ == "__main__":
    main()