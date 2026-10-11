# ask-the-group

One small Python script that helps volunteer coordinators find answers
and action items in the notes their group already has.

**Standard library only. No installs. No internet. No AI. No Api.**

---

## Why

Volunteer groups run on knowledge trapped in one person's head and
scattered across chat threads, old emails, and meeting notes. The same
questions get asked over and over. Action items agreed in meetings get
forgotten. New volunteers feel like they're bothering people.

This script reads the plain-text files a group already has and turns
them into answers and checklists a coordinator can actually use.

## What it does

- **`index`** — build a local search index from a folder of `.txt`
  and `.md` files.
- **`ask`** — find the passage that best answers a question.
- **`actions`** — pull action items out of meeting notes, separated
  into "clear" and "needs a human" lists.

## Usage

    python ask-the-group.py index examples/group_notes
    python ask-the-group.py ask examples/group_notes "what time is setup"
    python ask-the-group.py actions examples/group_notes

## Who it's for

The volunteer coordinator — part-time, unpaid, no programming
background, working on their own laptop.

## Design rules

- Standard library only. No installs, no dependencies.
- Plain text in, plain text out.
- Runs offline. Read-only by default.
- No AI, no API keys, no accounts.
- Errors explain what to do next, in plain language.
- Deterministic — same input, same output.

## Known limitations

The `actions` command uses keyword matching, not language
understanding. It works best on meeting notes written as statements.
It skips questions and chat-formatted lines. If your notes use
different phrasing, extend the trigger lists at the top of the script
— they're plain regex and easy to edit.

The `ask` command matches words, not meaning. "Opening hours" and
"when is the shop open" may not overlap well. It works best when the
notes and the question share vocabulary.

## Roadmap

- v0.1 — folder reader
- v0.2 — `ask` command
- v0.3 — `actions` command
- v0.4 — `expiry` command for certificates and permits
- v1.0 — polish, docs, release

## License

MIT.
