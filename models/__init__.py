from models.base import BrowserModelAdapter, ModelExtractionConfig
from models.chatgpt import ChatGPTAdapter
from models.claude import ClaudeAdapter
from models.gemini import GeminiAdapter
from models.deepseek import DeepSeekAdapter


def get_model_adapter(model_name: str) -> BrowserModelAdapter:
    normalized = (model_name or "").strip().lower()
    if normalized == "chatgpt":
        return ChatGPTAdapter()
    if normalized == "claude":
        return ClaudeAdapter()
    if normalized == "gemini":
        return GeminiAdapter()
    if normalized == "deepseek":
        return DeepSeekAdapter()
    return ChatGPTAdapter()
