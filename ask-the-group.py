#!/usr/bin/env python3
"""
ask-the-group — v0.2

Reads a folder of .txt/.md files and prompts you to ask a question.
Returns a passage from those text files that may best answers it.

Standard library only. Python 3.7 or +.

Usage:
    python ask_the_group.py index <folder>
    python ask_the_group.py ask <folder> "your question"
"""

import os
import sys
import re          # for regex (text processing)
import json        # for saving/loading search index
import math        # for the TF-IDF & mathematical operations
from collections import Counter   # for counting word frequencies
from datetime import datetime     # for time-stamping

INDEX_FILENAME = ".ask_the_group_index.json"


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "get", "had",
    "has", "have", "he", "her", "him", "his", "how", "i", "if", "in",
    "is", "it", "its", "just", "me", "my", "no", "not", "of", "on",
    "or", "our", "out", "she", "should", "so", "some", "than", "that",
    "the", "their", "them", "then", "there", "these", "they", "this",
    "to", "up", "us", "was", "we", "were", "what", "when", "where",
    "which", "who", "why", "will", "with", "would", "you", "your",
}


#tokenize that is preliminary text processing
def tokenize(text):
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


#breaks a file into small overlapping windows of about 6 lines each, sliding forward 4 lines at a time.
def split_into_chunks(text, max_lines=6):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    chunks = []
    step = max(1, max_lines - 2)
    for i in range(0, len(lines), step):
        chunk = lines[i:i + max_lines]
        if chunk:
            chunks.append("\n".join(chunk))
        if i + max_lines >= len(lines):
            break
    return chunks


def find_text_files(folder):
    if not os.path.isdir(folder):
        sys.exit(f"ERROR: Not a folder: {folder}")

    files = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in sorted(filenames):
            if name.lower().endswith((".txt", ".md")):
                files.append(os.path.join(dirpath, name))
    return files


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        print(f"  (could not read {path}: {e})")
        return ""


#break every file into chunks, count how often each meaningful term-frequency in each chunk and record which words appear across how many chunks.
def build_index(folder):
    if not os.path.isdir(folder):
        answer = input(f"'{folder}' doesn't exist. Create it? [y/N] ").strip().lower()
        if answer == "y":
            os.makedirs(folder, exist_ok=True)
            print(f"Created {folder}.")
            print(f"Add your .txt or .md notes there, then run:")
            print(f"    python ask_the_group.py index {folder}")
            sys.exit(0)
        else:
            sys.exit(f"Cancelled. No folder was created.")
    files = find_text_files(folder)
    if not files:
        sys.exit(f"No .txt or .md files found in {folder}")
    docs = []
    doc_freq = Counter()
    for path in files:
        rel = os.path.relpath(path, folder)
        text = read_text(path)
        for chunk in split_into_chunks(text):
            tokens = tokenize(chunk)
            if not tokens:
                continue
            tf = Counter(tokens)
            docs.append({
                "source": rel,
                "chunk": chunk,
                "tf": dict(tf),
                "length": len(tokens),
            })
            for term in tf:
                doc_freq[term] += 1
    #converts each chunk's word counts into a TF-IDF vector 
    N = len(docs)
    for d in docs:
        vec = {}
        for term, count in d["tf"].items():
            tf = count / d["length"]
            idf = math.log((N + 1) / (1 + doc_freq[term])) + 1
            vec[term] = tf * idf
        top = sorted(vec.items(), key=lambda x: -x[1])[:40]
        d["vector"] = dict(top)
        del d["tf"]
    #return in json-like format
    return {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "folder": os.path.abspath(folder),
        "num_chunks": len(docs),
        "doc_freq": dict(doc_freq),
        "docs": docs,
    }


#save/load index
def save_index(folder, index):
    path = os.path.join(folder, INDEX_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    return path

def load_index(folder):
    path = os.path.join(folder, INDEX_FILENAME)
    if not os.path.exists(path):
        sys.exit(f"No index found in {folder}.\n"
                 f"Run: python ask_the_group.py index {folder}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


#compute cosine distance of two vectors
def cosine(a, b):
    shared = set(a) & set(b)
    if not shared:
        return 0.0
    dot = sum(a[t] * b[t] for t in shared)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


#search for best answer: tokenize the question and compute the cosine distance between the tf-idf vector and all the available chunks
def search(index, query, top_k=3):
    q_tokens = tokenize(query)
    if not q_tokens:
        return []
    q_tf = Counter(q_tokens)
    q_len = len(q_tokens)
    doc_freq = index["doc_freq"]    
    N = index["num_chunks"]

    q_vec = {}
    for term, count in q_tf.items():
        tf = count / q_len
        idf = math.log((N + 1) / (1 + doc_freq.get(term, 0))) + 1
        q_vec[term] = tf * idf

    scored = []
    for d in index["docs"]:
        score = cosine(q_vec, d["vector"])
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return scored[:top_k]


#user facing wrapper
def cmd_index(folder):
    print(f"Reading text from: {folder}")
    index = build_index(folder)
    path = save_index(folder, index)
    print(f"Indexed {index['num_chunks']} chunks from "
          f"{len({d['source'] for d in index['docs']})} file(s).")
    print(f"Index written to: {path}")


#runs the ask command's standard procedure returning top_k answers with a 0.08 confidence threshold
def cmd_ask(folder, question):
    index = load_index(folder)
    results = search(index, question, top_k=3)

    print("=" * 68)
    print(f"  QUESTION: {question}")
    print("=" * 68)
    print()

    if not results or results[0][0] < 0.08:
        print("No good answer found in the group's notes.")
        print()
        print("What to do next:")
        print("  * Ask the coordinator directly.")
        print("  * Add the answer to a file in the notes folder and re-index.")
        return

    best_score, best = results[0]
    print("BEST MATCH")
    print("-" * 10)
    print(f"  Source: {best['source']}")
    print(f"  Match:  {best_score:.2f}")
    print()
    for line in best["chunk"].splitlines():
        print(f"    {line}")
    print()

    if len(results) > 1:
        print("OTHER POSSIBLE MATCHES")
        print("-" * 22)
        for score, d in results[1:]:
            snippet = d["chunk"].splitlines()[0][:60]
            print(f"  [{score:.2f}] {d['source']}  —  {snippet}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "index":
        if len(sys.argv) < 3:
            sys.exit("Usage: python ask_the_group.py index <folder>")
        cmd_index(sys.argv[2])

    elif cmd == "ask":
        if len(sys.argv) < 4:
            sys.exit('Usage: python ask_the_group.py ask <folder> "question"')
        cmd_ask(sys.argv[2], " ".join(sys.argv[3:]))

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

##################################################################################################
