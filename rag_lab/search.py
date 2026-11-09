import numpy as np


def build_index(vectors):
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    
    return vectors / norms


def search(index, chunks, query_vector, k=5):
    query_norm = np.linalg.norm(query_vector)
    if query_norm > 0:
        query_unit = query_vector / query_norm
    else:
        query_unit = query_vector
    scores = index @ query_unit
    top_indices = np.argsort(-scores)[:k]
    
    return [(chunks[i], float(scores[i])) for i in top_indices]