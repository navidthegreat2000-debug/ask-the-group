# Changelog

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
