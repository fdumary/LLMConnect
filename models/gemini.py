from models.base import BrowserModelAdapter, ModelExtractionConfig


class GeminiAdapter(BrowserModelAdapter):
	def get_config(self) -> ModelExtractionConfig:
		return ModelExtractionConfig(
			model_name="Gemini",
			input_selectors=[
				"textarea",
				"textarea[placeholder*='Message']",
				"div[contenteditable='true'][role='textbox']",
				"div[contenteditable='true'][aria-label*='prompt' i]",
				"div[contenteditable='true'][aria-label*='message' i]",
				"div[contenteditable='true']",
				"rich-textarea",
				"div[aria-label*='Enter a prompt'][contenteditable='true']",
				"div.ql-editor[contenteditable='true']",
			],
			user_message_selectors=[
				"[data-message-author-role='user']",
				"[data-message-author='user']",
				"article[data-testid*='conversation-turn'] [role='presentation']",
				"[data-test-id*='user']",
				"[class*='query-text']",
				"[class*='user']",
			],
			assistant_message_selectors=[
				"[data-message-author-role='assistant']",
				"[data-message-author='assistant']",
				"article[data-testid*='conversation-turn'] [role='presentation']",
				"[data-test-id*='model']",
				"[class*='model-response']",
				"[class*='assistant']",
				"[class*='response']",
				"[class*='model']",
			],
		)
