import json
from pathlib import Path

import numpy as np

from answer import answer
from providers import embed
from search import search
from corpus import load_corpus


HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

    
def main():
    chunks, index = load_corpus()
    
    while True:
        question = input(f"\nQuestion (blank to quit): ").strip()
        if not question:
            break
        query_vector = np.array(embed([question])[0], dtype=np.float32)
        hits = search(index, chunks, query_vector, k=5)
        for rank, (chunk, score) in enumerate(hits, 1):
            print(f"  [{rank}] {chunk['source']} p.{chunk['page']}  score={score:.3f}")
        print("\n" + answer(question, hits))


if __name__ == "__main__":
    main()