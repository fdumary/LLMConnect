from models.base import BrowserModelAdapter, ModelExtractionConfig


class ClaudeAdapter(BrowserModelAdapter):
	def get_config(self) -> ModelExtractionConfig:
		return ModelExtractionConfig(
			model_name="Claude",
			input_selectors=[
				".ProseMirror[contenteditable='true']",
				"div[contenteditable='true'][aria-label*='message']",
				"div[contenteditable='true'][role='textbox']",
			],
			user_message_selectors=[
				".font-user-message",
				"[data-testid*='user']",
			],
			assistant_message_selectors=[
				".font-claude-message",
				"[data-testid*='assistant']",
			],
		)
