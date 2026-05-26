import urllib.request
import json

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url

    def categorize_chat(self, model: str, chat_text: str) -> dict:
        prompt = f"""
        You are an AI research assistant. Read the following chat thread and extract the following:
        1. A concise, descriptive title (max 5 words).
        2. A single word category for this chat (e.g., Coding, Research, Writing, General).

        Output ONLY valid JSON in this exact format:
        {{
            "title": "Your Title Here",
            "category": "Your Category Here"
        }}

        Chat Thread:
        {chat_text[:4000]}
        """
        
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        req = urllib.request.Request(f"{self.base_url}/api/generate", data=json.dumps(data).encode('utf-8'))
        req.add_header("Content-Type", "application/json")
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                response_text = result.get("response", "{}")
                return json.loads(response_text)
        except Exception as e:
            print(f"Ollama error: {e}")
            return {"title": "Untitled Chat", "category": "Uncategorized"}
