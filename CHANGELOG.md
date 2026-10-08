# Changelog

## v0.2 — Ask
- `index` command: builds a local search index from .txt/.md files in the folder.
- `ask` command: returns the best-matching passage for a given question.
- Uses TF-IDF scoring (standard library only — no AI, no API, no network).
- Index saved as a hidden JSON file inside the examples folder.

## v0.1 — Folder reader
- Initial repo structure: README, LICENSE, .gitignore.
- Script reads a folder of .txt/.md files and prints a summary.
- No dependencies. Standard library only.
- Project skeleton and structure design.
