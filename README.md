# ask-the-group

One standalone Python script for volunteer coordinators. Reads the notes, texts and memos a
group already has and helps find answers in them.

Standard library only. No dependencies. No servers. No Api calls. No AI.

## Status

- v0.1 — reads a folder of .txt files and lists what's in them.
- v0.2 — ask a question; finds the passage that best answers it.


## Usage

the first command must be run once in order to set up the index and must be run again when examples foulder gets updated
after running the first command once, the user may use the ask command by itself to get answers to qeustions
    
# Build the index (run once, and again after any change to the text files)
python ask-the-group.py index examples/group_notes

# Ask where to park on match days
python ask-the-group.py ask examples/group_notes "where do I park on match days"

# Ask what time setup starts
python ask-the-group.py ask examples/group_notes "what time is setup"

# Ask what to bring to a shift
python ask-the-group.py ask examples/group_notes "do I need to bring anything"

# Ask a question the group hasn't answered yet
python ask-the-group.py ask examples/group_notes "who do I contact about the newsletter"


## License

MIT.
