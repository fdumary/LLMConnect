import urllib.request
import json
import os


class OllamaClient:
    def __init__(self, base_url=None):
        self.base_url = base_url or os.getenv("OLLAMA_HOST")

    def categorize_chat(self, model: str, chat_text: str) -> dict:
        with open("skills/CATEGORIZE_OLLAMA.md", "r") as f:
            prompt_template = f.read()

        prompt = prompt_template.format(chat_text=chat_text)

        data = {"model": model, "prompt": prompt, "stream": False, "format": "json"}

        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result
        except Exception as e:
            print(f"Error categorizing chat: {e}")
            return {"error": str(e)}
