# ask-the-group.py

One small offline Python script for volunteer coordinators. Reads the
plain-text files a group already has and turns them into answers,
action items, and expiry alerts.

**Standard library only. No installs. No internet. No AI. No Api.**

---

## Why

Volunteer groups run on knowledge trapped in one person's head and
scattered across chat threads, old emails and meeting notes. The same
questions get asked over and over. Action items agreed in meetings get
forgotten. Certificates and inspections quietly expire. New volunteers
feel like they're bothering people.

This script reads the plain-text files a group already has and turns
them into answers and checklists a coordinator can actually use.

## What it does

- **`index`** — build a local search index from a folder of `.txt`
  and `.md` files.
- **`ask`** — find the passage that best answers a question.
- **`actions`** — pull action items out of meeting notes.
- **`expiry`** — read a CSV of certificates / permits / inspections
  and flag what's expiring.

## Usage

    python ask-the-group.py index   examples/group_notes
    python ask-the-group.py ask     examples/group_notes "where do I park"
    python ask-the-group.py actions examples/group_notes
    python ask-the-group.py expiry  examples/expiry/items.csv
    python ask-the-group.py --version

## Who it's for

The volunteer coordinator — part-time, unpaid, no programming
background, working on their own laptop.

## Design rules

- Standard library only. No installs, no dependencies.
- Plain text in, plain text out.
- Runs offline. Read-only by default.
- No AI, no API keys, no accounts.
- Errors explain what to do next, in plain language.
- Deterministic — same input, always same output.

## Known limitations

- **`ask`** matches words, not meaning. It works best when the notes
  and the question share vocabulary.
- **`actions`** uses keyword matching. It works best on meeting notes
  written as statements. It skips questions and chat-log lines.
- **`expiry`** needs a CSV with columns `item, holder, category,
  expires`. Dates in `YYYY-MM-DD` are safest.

Trigger lists and column names are plain regex and easy to extend at
the top of the script.

## Example data

The `examples/` folder contains a small, realistic set of files:

- `examples/group_notes/` — meeting notes, a chat export, an onboarding
  doc, and a scratch file. All feed `index`, `ask`, and `actions`.
- `examples/expiry/items.csv` — certificates, inspections, and policies
  with expiry dates. Feeds `expiry`.

## Roadmap

- v0.1 — folder reader
- v0.2 — `ask` command
- v0.3 — `actions` command
- v0.4 — `expiry` command
- v1.0 — polish, docs, release

## License

MIT.
