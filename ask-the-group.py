#!/usr/bin/env python3
"""
ask-the-group.py — v1.0

One small offline script for volunteer coordinators. Reads the
plain-text files a group already has and turns them into answers,
action items, and expiry alerts.

Four commands:

    index <folder>
        Build a local search index over the folder.

    ask <folder> "question"
        Return the passage that best answers the question.

    actions <folder>
        Pull action items out of meeting notes.

    expiry <file.csv>
        Read a CSV of certificates / permits / inspections and flag
        what's expiring.

Standard library only. Python 3.7+.

Options:
    --version    Show version and exit.
"""

import os
import sys
import re          # for regex (text processing)
import json        # for saving/loading search index
import math        # for the TF-IDF & mathematical operations
import csv
from collections import Counter   # for counting word frequencies
from datetime import datetime, timedelta, date    # for time-stamping

__version__ = "1.0"

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


# --- action-item detection ------------------------------------------------

ACTION_TRIGGERS = [
    r"\bwill\b", r"\bto-?do\b", r"\baction\b", r"\baction item\b",
    r"\bneeds to\b", r"\bmust\b", r"\bshould\b", r"\bfollow[- ]?up\b",
    r"\bassign(?:ed)?\b", r"\bvolunteer(?:s|ed)? to\b",
    r"\bnext step\b", r"\bby (?:mon|tues|wednes|thurs|fri|satur|sun)day\b",
    r"\bby next\b", r"\bby end of\b", r"\bdeadline\b",
]

NEGATIVE_TRIGGERS = [
    r"\bdiscussed\b", r"\bconsidered\b", r"\bmight\b", r"\bmaybe\b",
    r"\bwondering\b", r"\bnot sure\b", r"\btbd\b", r"\bparking lot\b",
]

BULLET_PREFIXES = re.compile(r"^\s*(?:[-*•]|\d+[.)]|\[\s?\])\s*")

CHAT_LINE = re.compile(r"^\s*\[\d{4}-\d{2}-\d{2}[^\]]*\]\s*\w+\s*:")

QUESTION_STARTERS = (
    "do i ", "does anyone", "where do i", "where is", "where are",
    "what if", "when is", "when do", "who do i", "who is",
    "how do i", "how do we", "can i ", "can we ", "is there",
    "are there", "are we ", "anyone know", "should i ",
)


# --- expiry detection -----------------------------------------------------

DATE_FORMATS = [
    "%Y-%m-%d",     # 2025-03-05  (preferred)
    "%d/%m/%Y",     # 05/03/2025
    "%m/%d/%Y",     # 03/05/2025  (ambiguous with above)
    "%d-%m-%Y",     # 05-03-2025
    "%d %b %Y",     # 05 Mar 2025
    "%d %B %Y",     # 05 March 2025
    "%b %d, %Y",    # Mar 05, 2025
    "%B %d, %Y",    # March 05, 2025
]

REQUIRED_CSV_COLUMNS = ["item", "holder", "category", "expires"]

EXPIRY_BUCKETS = [
    ("expired",  lambda d: d < 0),
    ("urgent",   lambda d: 0 <= d <= 7),
    ("soon",     lambda d: 8 <= d <= 30),
    ("quarter",  lambda d: 31 <= d <= 90),
]


def is_question(body):
    if body.rstrip().endswith("?"):
        return True
    low = body.lower()
    return any(low.startswith(w) for w in QUESTION_STARTERS)


# --- text helpers ---------------------------------------------------------

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


def strip_bullet(line):
    return BULLET_PREFIXES.sub("", line).strip()
    

#decides whether a line is an action item
def looks_like_action(text):
    low = text.lower()
    if any(re.search(p, low) for p in NEGATIVE_TRIGGERS):
        if not re.search(r"\b(will|assign(?:ed)? to|action item|deadline)\b", low):
            return False
    return any(re.search(p, low) for p in ACTION_TRIGGERS)


def parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


# --- file discovery and reading -------------------------------------------

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


# --- index ----------------------------------------------------

#break every file into chunks, count how often each meaningful term-frequency in each chunk and record which words appear across how many chunks.
def build_index(folder):
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

    return {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "version": __version__,
        "folder": os.path.abspath(folder),
        "num_chunks": len(docs),
        "doc_freq": dict(doc_freq),
        "docs": docs,
    }


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


# --- search (from v0.2) ---------------------------------------------------

#compute cosine distance of two vectors(check mathematical def.)
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


# --- actions (new in v0.3) ------------------------------------------------

def find_action_items(folder):
    files = find_text_files(folder)
    if not files:
        sys.exit(f"No .txt or .md files found in {folder}")

    actions = []
    unclear = []

    for path in files:
        rel = os.path.relpath(path, folder)
        text = read_text(path)
        section = ""

        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue

            # Track section headings (# Heading, or a short line ending in :)
            if line.startswith("#") or (line.endswith(":") and len(line) < 60):
                section = strip_bullet(line.lstrip("# ").rstrip(":"))
                continue

            body = strip_bullet(line)
            if len(body.split()) < 3:
                continue
            if CHAT_LINE.match(line):
                continue
            if is_question(body):
                continue
            if not looks_like_action(body):
                continue

            entry = {
                "file": rel,
                "line": lineno,
                "section": section,
                "text": body,
            }

            # A line is "clear" if it names someone or a date.
            has_name = bool(re.match(r"^[A-Z][a-z]+", body))
            has_date = bool(re.search(
                r"\b(mon|tues|wednes|thurs|fri|satur|sun)day\b|"
                r"\bnext week\b|\bend of\b|\bby \d|\b\d{4}-\d{2}-\d{2}\b",
                body.lower()))
            if has_name or has_date:
                actions.append(entry)
            else:
                unclear.append(entry)

    return actions, unclear
    

# --- expiry (new in v0.4) -------------------------------------------------

def load_csv(path):
    if not os.path.exists(path):
        sys.exit(f"ERROR: file not found: {path}")
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            sys.exit(f"ERROR: {path} has no header row.")
        headers = [h.strip().lower().replace(" ", "_")
                   for h in reader.fieldnames]
        rows = []
        for raw in reader:
            row = {h.strip().lower().replace(" ", "_"): (v or "").strip()
                   for h, v in raw.items() if h is not None}
            if any(row.values()):
                rows.append(row)
    return rows, headers
    

def analyze_expiry(rows, today):
    result = {
        "expired": [], "urgent": [], "soon": [], "quarter": [],
        "later": [], "no_date": [], "bad_dates": [], "missing_fields": [],
    }

    for i, row in enumerate(rows, start=2):
        label = row.get("holder") or row.get("item") or f"(row {i})"

        for col in REQUIRED_CSV_COLUMNS:
            if not row.get(col, ""):
                result["missing_fields"].append((i, col, label))

        raw_date = row.get("expires", "")
        if not raw_date:
            result["no_date"].append((i, label, row.get("category", "")))
            continue

        parsed = parse_date(raw_date)
        if parsed is None:
            result["bad_dates"].append((i, label, raw_date))
            continue

        days = (parsed - today).days
        entry = {
            "row": i,
            "item": row.get("item", ""),
            "holder": row.get("holder", ""),
            "category": row.get("category", ""),
            "owner": row.get("owner", ""),
            "expires": parsed,
            "days": days,
        }

        placed = False
        for name, test in EXPIRY_BUCKETS:
            if test(days):
                result[name].append(entry)
                placed = True
                break
        if not placed:
            result["later"].append(entry)

    return result


# --- commands -------------------------------------------------------------

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


#action items wrapper
def cmd_actions(folder):
    actions, unclear = find_action_items(folder)

    print("=" * 68)
    print("  ACTION ITEMS")
    print(f"  From: {folder}")
    print("=" * 68)
    print()

    if not actions and not unclear:
        print("No action items found.")
        print()
        print("The script looks for lines with words like 'will', 'should',")
        print("'needs to', 'follow up', or 'by <day>'. If your notes use")
        print("different phrasing, that's why nothing was caught.")
        return

    print(f"CLEAR ACTION ITEMS ({len(actions)})")
    print("-" * 24)
    if not actions:
        print("  None.")
    else:
        current = None
        for a in actions:
            if a["section"] and a["section"] != current:
                current = a["section"]
                print(f"\n  [{current}]")
            print(f"  {a['file']}:{a['line']}  {a['text']}")
    print()

    print(f"NEEDS A HUMAN ({len(unclear)})")
    print("-" * 15)
    print("These look like actions but don't name a person or a date.")
    print()
    if not unclear:
        print("  None.")
    else:
        for a in unclear:
            print(f"  {a['file']}:{a['line']}  {a['text']}")

    print()
    print("SUGGESTED NEXT STEPS")
    print("-" * 21)
    if unclear:
        print(f"  * Assign owners to {len(unclear)} item(s) above.")
    if actions:
        print(f"  * Follow up on {len(actions)} clear item(s).")
    if not unclear and not actions:
        print("  * Nothing to do.")



def cmd_expiry(csv_path, today=None):
    today = today or date.today()
    rows, headers = load_csv(csv_path)

    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in headers]
    if missing:
        print(f"WARNING: CSV is missing expected columns: {', '.join(missing)}")
        print()

    result = analyze_expiry(rows, today)

    print("=" * 68)
    print("  EXPIRY & RENEWAL TRACKER")
    print(f"  File:  {csv_path}")
    print(f"  Today: {today.isoformat()}")
    print("=" * 68)
    print()

    total_action = (len(result["expired"]) + len(result["urgent"])
                    + len(result["soon"]))

    print("AT A GLANCE")
    print("-" * 11)
    print(f"  EXPIRED ................ {len(result['expired']):>3}  ** renew now **")
    print(f"  Urgent (within 7 days) . {len(result['urgent']):>3}")
    print(f"  Soon   (within 30 days)  {len(result['soon']):>3}")
    print(f"  This quarter (<=90d) ... {len(result['quarter']):>3}")
    print(f"  Later ................. {len(result['later']):>3}")
    print(f"  Missing date info ..... {len(result['no_date']):>3}")
    print(f"  Data problems ......... "
          f"{len(result['bad_dates']) + len(result['missing_fields']):>3}")
    print()
    if total_action == 0:
        print("  Nothing needs renewal right now.")
    elif result["expired"]:
        print(f"  *** {len(result['expired'])} item(s) already expired. ***")
    print()

    def section(title, items):
        if not items:
            return
        print(title)
        print("-" * len(title))
        for e in sorted(items, key=lambda x: x["days"]):
            who = e["holder"] or "(no holder)"
            cat = e["category"] or "(no category)"
            if e["days"] < 0:
                timing = f"EXPIRED {-e['days']} days ago"
            elif e["days"] == 0:
                timing = "EXPIRES TODAY"
            elif e["days"] == 1:
                timing = "expires tomorrow"
            else:
                timing = f"in {e['days']} days"
            owner = e["owner"] or "** no owner assigned **"
            print(f"  [{e['row']:>3}] {e['item'][:44]}")
            print(f"        holder: {who}   category: {cat}")
            print(f"        expires: {e['expires'].isoformat()}  ({timing})")
            print(f"        contact: {owner}")
        print()

    section("EXPIRED — RENEW IMMEDIATELY", result["expired"])
    section("URGENT — DUE WITHIN 7 DAYS", result["urgent"])
    section("COMING UP — WITHIN 30 DAYS", result["soon"])
    section("PLAN AHEAD — THIS QUARTER", result["quarter"])

    if result["later"]:
        print("LATER (beyond 90 days)")
        print("-" * 22)
        print(f"  {len(result['later'])} item(s) — no action needed yet")
        print()

    problems = (result["no_date"] or result["bad_dates"]
                or result["missing_fields"])
    if problems:
        print("DATA PROBLEMS TO FIX")
        print("-" * 21)
        if result["missing_fields"]:
            print("  Missing required fields:")
            for rownum, field, label in result["missing_fields"]:
                print(f"    row {rownum:>3}  {label:<22}  missing: {field}")
            print()
        if result["bad_dates"]:
            print("  Unreadable expiry dates:")
            for rownum, label, raw in result["bad_dates"]:
                print(f"    row {rownum:>3}  {label:<22}  '{raw}'")
            print()
        if result["no_date"]:
            print("  Items with no expiry date:")
            for rownum, label, cat in result["no_date"]:
                print(f"    row {rownum:>3}  {label:<22}  {cat}")
            print()

    print("SUGGESTED NEXT STEPS")
    print("-" * 21)
    steps = []
    if result["expired"]:
        steps.append(f"Contact owners of {len(result['expired'])} expired item(s) today.")
    if result["urgent"]:
        steps.append(f"Send reminders for {len(result['urgent'])} item(s) expiring this week.")
    if result["soon"]:
        steps.append(f"Book renewals for {len(result['soon'])} item(s) within 30 days.")
    if result["bad_dates"] or result["no_date"]:
        steps.append("Clean up unreadable or missing dates in the CSV.")
    if not steps:
        steps.append("Nothing urgent — come back next month.")
    for s in steps:
        print(f"  * {s}")
    print()
    print("=" * 68)


# --- entry point ----------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] in ("--version", "-v"):
        print(f"ask-the-group {__version__}")
        return

    cmd = sys.argv[1]

    if cmd == "index":
        if len(sys.argv) < 3:
            sys.exit("Usage: python ask_the_group.py index <folder>")
        cmd_index(sys.argv[2])

    elif cmd == "ask":
        if len(sys.argv) < 4:
            sys.exit('Usage: python ask_the_group.py ask <folder> "question"')
        cmd_ask(sys.argv[2], " ".join(sys.argv[3:]))

    elif cmd == "actions":
        if len(sys.argv) < 3:
            sys.exit("Usage: python ask_the_group.py actions <folder>")
        cmd_actions(sys.argv[2])

    elif cmd == "expiry":
        if len(sys.argv) < 3:
            sys.exit("Usage: python ask_the_group.py expiry <file.csv>")
        cmd_expiry(sys.argv[2])

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

##################################################################################################
