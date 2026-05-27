from models.base import BrowserModelAdapter, ModelExtractionConfig


class ChatGPTAdapter(BrowserModelAdapter):
    def get_config(self) -> ModelExtractionConfig:
        return ModelExtractionConfig(
            model_name="ChatGPT",
            input_selectors=[
                "#prompt-textarea",
                "textarea[placeholder*='Message']",
                "div[contenteditable='true'][id='prompt-textarea']",
            ],
            user_message_selectors=[
                "[data-message-author-role='user']",
            ],
            assistant_message_selectors=[
                "[data-message-author-role='assistant']",
            ],
        )
