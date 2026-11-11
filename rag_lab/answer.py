from providers import chat


REFUSAL = "I couldn't find this in your notes."

SYSTEM_PROMPT = f"""
You answer questions using only the numbered sources from the student's own notes.
Rules:
1. Use only facts that are stated in the sources.
2. Cite every claim with its own source number in square brackets, like [1], [2] ... etc
3. If the sources do not contain the answer, reply with EXACTLY this English sentence, whatever the language of the question: "{REFUSAL}"
4. Reply in the language of the question. Keep technical terms in English where the notes do.
"""

def format_sources(hits):
    ref = []
    for i, (chunk, score) in enumerate(hits, 1):
        ref.append(f"[{i}] ({chunk['source']}, page {chunk['page']})\n{chunk['text']}")
    return "\n\n".join(ref)


def answer(question, hits):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Sources:\n\n{format_sources(hits)}\n\nQuestion: {question}"},
    ]
    return chat(messages)