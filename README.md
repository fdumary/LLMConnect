# llmConnect

llmConnect is a local-first desktop workspace for browser-based AI chats and encrypted API profiles. It uses PyQt6 to keep browser sessions isolated, extract structured chat history, and organize everything in a dashboard that stays on your machine.

## Why this exists

AI usage tends to fragment across browser tabs, sessions, and API accounts. llmConnect brings that work into one place so you can:

- keep browser sessions separated,
- save conversations locally,
- organize chats by category and project,
- manage API profiles securely,
- and review structured chat history later instead of losing it in the browser.

## What it does

- Opens separate browser tabs for supported providers.
- Injects lightweight browser tools for persona prompts and extraction.
- Stores extracted chats in SQLite.
- Stores API profiles encrypted on disk.
- Categorizes chats into titles, categories, and projects.
- Renders recent chats in a thread-style dashboard.

## Documentation

Start with [.docs/README.md](.docs/README.md).

Recommended reading:

- [.docs/architecture.md](.docs/architecture.md)
- [.docs/limitations-and-roadmap.md](.docs/limitations-and-roadmap.md)

## Project structure

- `main.py`: Application entry point.
- `engine/`: Storage, classification, and local integration logic.
- `models/`: Browser/provider selector definitions.
- `ui/`: Main window, browser tabs, and dashboard screens.
- `skills/`: Prompt and role markdown files for browser and API workflows.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Current limitations

- Extraction depends on the current browser DOM of each provider.
- Browser tools can stop working if a site changes its UI or script restrictions.
- Validation and categorization depend on provider availability and network access.

See [.docs/limitations-and-roadmap.md](.docs/limitations-and-roadmap.md) for the detailed discussion and future direction.
