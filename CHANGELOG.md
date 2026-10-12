# Changelog

## v1.0 — Polish and release
- `expiry` command added: reads a CSV of certificates, permits, and
  inspections and flags what's expiring (7 / 30 / 90 day buckets).
- `--version` flag added.
- Consistent output headers across all four commands.
- Version stamp included in the search index.

## v0.4 — Expiry
- `expiry` command: parses expiry CSVs and reports urgency.
- Supports eight date formats, flags unreadable ones.
- Detects missing required columns and items with no expiry date.

## v0.3 — Actions
- `actions` command: pulls action items out of meeting notes.
- Filters out discussion lines ("discussed", "might", "TBD").
- Separates clear items (named owner or date) from unclear ones.
- Shows file and line number for every item found.
- Skips questions and chat-log lines to reduce false positives.
- Dropped "please" from triggers — too common in informational text.

## v0.2 — Ask
- `index` command: builds a local search index from .txt/.md files.
- `ask` command: returns the best-matching passage for a question.
- Uses TF-IDF scoring (standard library only — no AI, no network).
- Index saved as a hidden JSON file inside the notes folder.

## v0.1 — Folder reader
- Initial repo structure: README, LICENSE, .gitignore.
- Script reads a folder of .txt/.md files and prints a summary.
- No dependencies. Standard library only.
