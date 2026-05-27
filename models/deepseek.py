from models.base import BrowserModelAdapter, ModelExtractionConfig


class DeepSeekAdapter(BrowserModelAdapter):
	def get_config(self) -> ModelExtractionConfig:
		return ModelExtractionConfig(
			model_name="DeepSeek",
			input_selectors=[
				"#chat-input",
				"textarea",
				"div[contenteditable='true'][role='textbox']",
			],
			user_message_selectors=[
				"[data-role='user']",
				"[class*='user']",
			],
			assistant_message_selectors=[
				"[data-role='assistant']",
				"[class*='assistant']",
			],
		)
