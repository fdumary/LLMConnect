import json


class ChatGPT:
    def __init__(self):
        self.name = "ChatGPT"
        self.role = None

    def get_browser_url(self):
        return "https://chat.openai.com"

    def set_role(self, role_name: str, role_prompt: str):
        self.role = {"name": role_name.strip(), "prompt": role_prompt.strip()}

    def categorize_chat(self, chat_text: str) -> dict:
        # For simplicity, we'll just return a dummy category based on keywords
        if "code" in chat_text.lower():
            category = "Coding"
        elif "recipe" in chat_text.lower():
            category = "Cooking"
        elif "travel" in chat_text.lower():
            category = "Travel"
        else:
            category = "General"

        return {"category": category}

    def inject_extension_widget(self, ok):
        if not ok:
            return
        js = """
        (function() {
            if (document.getElementById('llmconnect-widget')) return;

            // Initialize global variable for Python to poll
            window._llmExtractedChat = null;

            const style = document.createElement('style');
            style.textContent = `
                #llmconnect-widget {
                    position: fixed;
                    bottom: 20px;
                    left: 20px;
                    width: 286px;
                    padding: 16px;
                    border-radius: 18px;
                    border: 1px solid #262626;
                    background: rgba(17, 17, 17, 0.94);
                    color: #f5f5f5;
                    z-index: 999999;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.45);
                    backdrop-filter: blur(14px);
                }
                #llmconnect-widget h4 { margin: 0 0 4px 0; color: #f5f5f5; font-size: 14px; letter-spacing: -0.01em; }
                #llmconnect-widget p { margin: 0 0 12px 0; color: #a3a3a3; font-size: 12px; line-height: 1.5; }
                #llmconnect-widget select {
                    width: 100%;
                    padding: 10px 12px;
                    margin-bottom: 12px;
                    background: #141414;
                    color: #f5f5f5;
                    border: 1px solid #262626;
                    border-radius: 12px;
                    outline: none;
                }
                #llmconnect-widget select:focus { border-color: #3a3a3a; }
                #llmconnect-widget button {
                    width: 100%;
                    padding: 11px 12px;
                    background: linear-gradient(180deg, #f5f5f5, #d9d9d9);
                    color: #0a0a0a;
                    border: none;
                    font-weight: 700;
                    border-radius: 12px;
                    cursor: pointer;
                    transition: transform 0.16s ease, filter 0.16s ease;
                }
                #llmconnect-widget button:hover { transform: translateY(-1px); filter: brightness(1.02); }
                #llmconnect-widget button:active { transform: translateY(0); }
                #llmconnect-widget .llmconnect-kicker { display: inline-flex; align-items: center; gap: 8px; margin-bottom: 12px; font-size: 11px; color: #a3a3a3; letter-spacing: 0.14em; text-transform: uppercase; }
                #llmconnect-widget .llmconnect-dot { width: 8px; height: 8px; border-radius: 999px; background: #22c55e; }
            `;
            document.head.appendChild(style);

            const widget = document.createElement('div');
            widget.id = 'llmconnect-widget';
            const kicker = document.createElement('div');
            kicker.className = 'llmconnect-kicker';

            const dot = document.createElement('span');
            dot.className = 'llmconnect-dot';
            kicker.appendChild(dot);
            kicker.appendChild(document.createTextNode('llmConnect Persona'));

            const heading = document.createElement('h4');
            heading.textContent = 'Inject a role prompt';

            const description = document.createElement('p');
            description.textContent = 'Choose a persona before extracting the current conversation.';

            const select = document.createElement('select');
            select.id = 'llm-persona';

            const personas = [
                ['', 'None'],
                ['Adopt the persona of a visionary CEO. Keep responses strategic, high-level, and focused on business value, metrics, and leadership.', 'CEO'],
                ['Adopt the persona of a senior software engineer. Focus on clean code, architecture, performance, and provide detailed technical explanations.', 'Developer'],
                ['Adopt the persona of an academic researcher. Be highly analytical, cite concepts, provide evidence-based arguments, and explore nuances.', 'Researcher'],
            ];

            for (const [value, label] of personas) {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = label;
                select.appendChild(option);
            }

            const button = document.createElement('button');
            button.id = 'llm-extract';
            button.textContent = 'Extract & Categorize Chat';

            widget.appendChild(kicker);
            widget.appendChild(heading);
            widget.appendChild(description);
            widget.appendChild(select);
            widget.appendChild(button);
            document.body.appendChild(widget);

            const initialRolePrompt = __INITIAL_ROLE_PROMPT__;
            if (initialRolePrompt) {
                select.value = initialRolePrompt;
            }

            document.getElementById('llm-persona').addEventListener('change', (e) => {
                const personaText = e.target.value;
                const host = window.location.hostname;
                if (!personaText) return;
                
                if (host.includes('chatgpt.com')) {
                    const textarea = document.querySelector('#prompt-textarea');
                    if (textarea) {
                        textarea.value = `[System Prompt: ${personaText}]\\n\\n` + textarea.value;
                        textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                } else if (host.includes('claude.ai')) {
                    const editor = document.querySelector('.ProseMirror');
                    if (editor) {
                        editor.textContent = `[System Prompt: ${personaText}]\n\n` + editor.textContent;
                        editor.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
            });

            if (initialRolePrompt) {
                select.dispatchEvent(new Event('change', { bubbles: true }));
            }

            document.getElementById('llm-extract').addEventListener('click', () => {
                let thread = "";
                const host = window.location.hostname;
                
                if (host.includes('chatgpt.com')) {
                    const messages = document.querySelectorAll('[data-message-author-role]');
                    for (const msg of messages) {
                        const role = msg.getAttribute('data-message-author-role');
                        const text = msg.innerText.trim();
                        if (text) thread += (role === 'user' ? '\\n\\n--- USER ---\\n' : '\\n\\n--- AI ---\\n') + text;
                    }
                } else if (host.includes('claude.ai')) {
                    const messages = document.querySelectorAll('.font-user-message, .font-claude-message');
                    for (const msg of messages) {
                        const role = msg.classList.contains('font-user-message') ? 'user' : 'ai';
                        const text = msg.innerText.trim();
                        if (text) thread += (role === 'user' ? '\\n\\n--- USER ---\\n' : '\\n\\n--- AI ---\\n') + text;
                    }
                }
                
                if (thread) {
                    window._llmExtractedChat = thread;
                    const btn = document.getElementById('llm-extract');
                    btn.textContent = "Extracted! Check Dashboard";
                    btn.style.background = "#f9e2af";
                    setTimeout(() => { btn.textContent = "Extract & Categorize Chat"; btn.style.background = "#a6e3a1"; }, 3000);
                }
            });
        })();
        """
        js = js.replace("__INITIAL_ROLE_PROMPT__", json.dumps(self.role_prompt))
        self.browser.page().runJavaScript(js)

    def poll_extracted_data(self):
        js = """
        (function() {
            if (window._llmExtractedChat) {
                let data = window._llmExtractedChat;
                window._llmExtractedChat = null; 
                return data;
            }
            return null;
        })();
        """
        self.browser.page().runJavaScript(js, self._handle_polled_data)

    def _handle_polled_data(self, data):
        if data and self.on_chat_extracted_callback:
            self.on_chat_extracted_callback(data)
