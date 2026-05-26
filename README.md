# llmConnect

llmConnect is a PyQt6-based desktop application designed to streamline interactions with various Large Language Models (LLMs) such as ChatGPT, Claude, Gemini, and DeepSeek. It functions as a specialized web browser with integrated data extraction, categorization, and dashboarding capabilities.

## Features

- **Multi-Model Support:** Seamlessly switch between different AI models within a single application using isolated tabs.
- **Data Extraction:** Injects custom JavaScript into supported chat interfaces (ChatGPT and Claude) to add a floating widget. This widget allows you to extract full chat threads directly from the webpage.
- **Persona Injection:** Quickly inject predefined system prompts (e.g., CEO, Developer, Researcher) into the chat input area of the web interfaces.
- **Auto-Categorization (Local AI):** Utilizes a local Ollama instance to automatically generate concise titles and single-word categories for your extracted chats via prompting.
- **Dashboard UI:** An elegant, dark-themed HTML/CSS/JS dashboard built into the application to browse and read your saved chats, organized by category.
- **Local Storage:** Stores all extracted chats locally in a SQLite database (`.llmconnect_data`).

## Architecture & Code Structure

The project is structured into modular components: core engine logic and the user interface.

- `main.py`: Entry point for the application. Sets up the PyQt6 `QApplication` and styles the interface using Qt Style Sheets (QSS).
- `requirements.txt`: Python dependencies (`PyQt6`, `PyQt6-WebEngine`, `pydantic`, `pathspec`).

### Engine (`engine/`)

The engine directory handles background processes, storage, and AI generation logic.

- `db.py`: Manages local storage using SQLite. Implements a `SavedChat` dataclass and the `Database` class for safely saving and retrieving chat histories.
- `ollama_client.py`: Provides an interface to interact with a local Ollama server (defaulting to `http://localhost:11434`) to perform title and category extraction via structured JSON generation.
- `repo_indexer.py`: A utility to parse a project's `.gitignore` and generate a hierarchical text representation of a repository's file structure. This is a foundational module for mapping local codebases for context.

### User Interface (`ui/`)

The UI directory contains the PyQt6 widgets and layouts.

- `main_window.py`: Defines the `MainWindow` class containing the central tab widget. Manages opening, naming, and closing browser tabs for different AI platforms.
- `browser_tab.py`: Implements `BrowserTab` containing a `QWebEngineView`. It creates an isolated profile per tab to prevent session overlap, injects the extraction/persona widget upon page load, and utilizes a `QTimer` to poll the browser DOM for extracted chat data.
- `home_tab.py`: The `HomeTab` renders the primary Dashboard. It acts as an integration point, receiving extracted chats, querying the `OllamaClient` for categorization, and saving them to the `Database`. It then dynamically populates an internal web view using a robust HTML/CSS template to provide a beautiful reading experience.

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.com/) running locally with the `llama3` model installed.

## Setup and Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   cd llmConnect
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Linux/macOS
   # .venv\Scripts\activate   # On Windows
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Ensure Ollama is running in the background:
   ```bash
   ollama serve
   ```
   *Note: Make sure you have the required model pulled: `ollama pull llama3`*

## Usage

1. Start the application:
   ```bash
   python main.py
   ```
2. **Dashboard:** The default tab is the Dashboard, where your categorized chats will appear.
3. **Adding Models:** Click the `+` button in the top-right of the tab bar to open a new tab and select an AI platform (e.g., ChatGPT, Claude).
4. **Extracting Chats:** In the supported tabs (ChatGPT, Claude), you will see a floating "llmConnect Persona" widget in the bottom left corner. Click **"Extract & Categorize Chat"** to scrape the conversation. The app will automatically categorize it via Ollama and update the Dashboard.
5. **Personas:** Use the dropdown in the floating widget to prepend persona instructions directly to your chat input field.

## Limitations

- **DOM Reliance:** Chat extraction currently relies on specific DOM elements (`[data-message-author-role]` for ChatGPT, `.font-user-message` / `.font-claude-message` for Claude). These selectors are subject to break if the respective platforms update their UI.
- **Local AI Speed:** The auto-categorization step relies on the performance of your local Ollama instance and the `llama3` model. During extraction, there may be a brief delay while the model processes the text.
