import argparse
import csv
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

from answer import REFUSAL, answer, format_sources
from chunking import SPLITTER
from corpus import load_corpus
from providers import FALLBACK_LLM_MODEL, LLM_MODEL, chat, embed
from search import search


HERE = Path(__file__).resolve().parent
GOLD = HERE / "eval" / "gold.jsonl"
RESULTS = HERE / "eval" / "results"
HISTORY = HERE / "eval" / "history.csv"

K = 5
MRR_DEPTH = 20
JUDGE_MODELS = (FALLBACK_LLM_MODEL,)
PAUSE_SECONDS = 8 # 4

JUDGE_PROMPT = """
You grade answers produced by a study assisstant that must answer only from a student's notes.
You get the question, the sources the assisstant was given, a reference answer written by the student,
and the assisstant's answer.
Choose exactly one label:
1. "correct": The assistant gives the reference's primary facts. Different wording, a different language, 
or extra detail is fine, unless the extra detail contradicts the reference or creates specific details 
(numbers, names) that neither the reference nor the sources support. Details that the sources support
are not invented.
2. "refused": The assistant says the information is not in the notes and gives no substantial answer.
3. "incomplete": Everything the assistant says is supported by the sources, but it misses some of the
reference's primary facts.
4. "wrong": The assistant contradicts the reference or the sources, or states specific details that
neither supports.
Reply with JSON ONLY: {"label": "correct" | "refused" | "incomplete"  | "wrong", "reason": "<one-short-sentence>"}
"""


def load_gold():
    lines = GOLD.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def is_match(chunk, item):
    return (
        item["source"] is not None
        and chunk["source"] == item["source"]
        and chunk["page"] in item["pages"]
    )
    

def first_match_rank(ranked, item):
    for rank, (chunk, score) in enumerate(ranked, 1):
        if is_match(chunk, item):
            return rank
    return None


def cited_numbers(text):
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", text)})


def parse_judge(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    label = data.get("label")
    if label not in ("correct", "refused", "wrong", "incomplete"):
        return "unjudged", text.strip()[:200]
    return label, data.get("reason", "")


def judge(item, response, top):
    messages = [
        {"role": "system", "content": JUDGE_PROMPT},
        {
            "role": "user",
            "content": f"Question: {item['question']}\n\n"
                       f"Sources:\n\n{format_sources(top)}\n\n"
                       f"Reference answer: {item['answer']}\n\n"
                       f"Assistant's answer: {response}",
        },
    ]
    text, _ = chat(messages, models=JUDGE_MODELS)
    return parse_judge(text)


def evaluate_item(item, query_vector, chunks, index, with_llm):
    ranked = search(index, chunks, query_vector, k=MRR_DEPTH)
    top = ranked[:K]
    row = {
        "question": item["question"],
        "kind": item["kind"],
        "source": item["source"],
        "pages": item["pages"],
        "retrieved": [f"{c['source']} p.{c['page']}" for c, _ in top],
        "top_score": round(top[0][1], 3),
    }
    
    if item["source"] is not None:
        rank = first_match_rank(ranked, item)
        row["rank"] = rank
        row["hit"] = rank is not None and rank <= K
        row["rr"] = 1 / rank if rank else 0.0
        
    if with_llm:
        start = time.perf_counter()
        response, answer_model = answer(item["question"], top)
        row["latency"] = round(time.perf_counter() - start, 2)
        row["response"] = response
        
        cited = cited_numbers(response)
        row["invalid_citations"] = [n for n in cited if not 1 <= n <= len(top)]
        row["cited_right_page"] = any(
            is_match(top[n-1][0], item) for n in cited if 1 <= n <= len(top)
        )
        
        if REFUSAL.lower() in response.lower():
            row["label"], row["reason"] = "refused", "gave the refusal sentence"
        elif item["source"] is None:
            row["label"], row["reason"] = "wrong", "answered a question the notes do not cover"
        else:
            row["label"], row["reason"] = judge(item, response, top)
        default = "refused" if item["source"] is None else "correct"
        expected = item.get("expected", default)
        row["success"] = row["label"] in expected
        row["answer_model"] = answer_model
    return row


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["kind"]].append(row)
    groups["ALL"] = rows
    
    summary = {}
    for kind, group in groups.items():
        answerable = [r for r in group if r["source"] is not None]
        judged = [r for r in group if "label" in r]
        stats = {"n": len(group)}
        if answerable:
            stats["hit@5"] = round(sum(r["hit"] for r in answerable) / len(answerable), 3)
            stats["mrr"] = round(sum(r["rr"] for r in answerable) / len(answerable), 3)
        if judged:
            stats["success"] = round(sum(r["success"] for r in judged) / len(judged), 3)
            for label in ("correct", "refused", "incomplete", "wrong", "unjudged"):
                stats[label] = sum(r["label"] == label for r in judged)
            stats["avg_latency"] = round(sum(r["latency"] for r in judged) / len(judged), 2)
        summary[kind] = stats
    return summary


def print_summary(summary):
    columns = ["n", "hit@5", "mrr", "success", "correct", "refused", "incomplete", "wrong", "unjudged", "avg_latency"]
    print("\n" + "kind".ljust(10) + "".join(c.rjust(12) for c in columns))
    for kind in sorted(summary, key=lambda k: (k == "ALL", k)):
        stats = summary[kind]
        print(kind.ljust(10) + "".join(str(stats.get(c, "-")).rjust(12) for c in columns))


def save(rows, summary, note, with_llm):
    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    config = {
        "chunk_size": getattr(SPLITTER, "_chunk_size", None),
        "chunk_overlap": getattr(SPLITTER, "_chunk_overlap", None),
        "k": K,
        "llm_model": LLM_MODEL if with_llm else "",
        "note": note,
    }
    out = RESULTS / f"{stamp}.json"
    out.write_text(
        json.dumps(
            {"config": config, "summary": summary, "rows": rows},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    
    overall = summary["ALL"]
    history_row = {
        "timestamp": stamp,
        **config,
        **{k: overall.get(k, "") for k in 
           ("n", "hit@5", "mrr", "success", "correct", "refused", "incomplete", "wrong")
        },
    }
    new_file = not HISTORY.exists()
    with HISTORY.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(history_row))
        if new_file:
            writer.writeheader()
        writer.writerow(history_row)
    print(f"\nSaved {out.relative_to(HERE)} and appended to {HISTORY.relative_to(HERE)}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate retrieval and answers against eval/gold.jsonl")
    parser.add_argument("--retrieval-only", action="store_true", 
        help="skip the LLM and measure the retrieval only"
    )
    parser.add_argument("--note", default="",
        help="what changed in this run, saved with the results."
    )
    args = parser.parse_args()
    with_llm = not args.retrieval_only
    
    gold = load_gold()
    chunks, index = load_corpus(verbose=False)
    query_vectors = np.array(embed([g["question"] for g in gold]), dtype=np.float32)

    rows = []
    for i, (item, query_vector) in enumerate(zip(gold, query_vectors), 1):
        row = evaluate_item(item, query_vector, chunks, index, with_llm)
        rows.append(row)
        print(f"[{i:>2}/{len(gold)}] {row['kind']:<8} rank={str(row.get('rank', '-')):<5} "
              f"{row.get('label', ''):<9} {item['question'][:60]}")
        if with_llm and i < len(gold):
            time.sleep(PAUSE_SECONDS)
            
    summary = summarize(rows)
    print_summary(summary)
    save(rows, summary, args.note, with_llm)
    

if __name__ == "__main__":
    main()