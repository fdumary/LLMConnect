# Architecture

## Overview

llmConnect is organized into three main layers:

1. Browser workflow
2. Data and classification engine
3. Dashboard and storage

## Browser workflow

Browser tabs are handled by `ui/browser_tab.py` and managed from `ui/main_window.py`.

- Each tab gets an isolated browser profile.
- The tab injects lightweight page tools for persona prompts and chat extraction.
- The browser layer produces structured chat payloads instead of plain flattened text.

## Data and classification engine

The engine layer handles persistence and chat classification.

- `engine/db.py` stores extracted chats in SQLite.
- `engine/secure_store.py` stores API profiles securely and validates provider access.
- `engine/chat_classifier.py` generates titles, categories, projects, and summaries.

Classification prefers local Ollama when available and can fall back to configured API profiles.

## Dashboard

`ui/home_tab.py` builds the dashboard payloads and feeds the HTML views in `ui/pages/`.

- Recent chats are rendered as thread-style cards.
- Categories and projects are derived from saved chat metadata.
- Browser models and API models are shown side by side for quick inspection.

## Prompt and role structure

The project keeps browser and API roles separate.

- Browser roles live in `skills/BROWSER`.
- API roles live in `skills/API`.
- The browser layer uses browser roles for page interaction.
- The API layer uses API roles for saved profiles and provider workflows.
