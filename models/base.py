from dataclasses import dataclass


@dataclass(frozen=True)
class ModelExtractionConfig:
    model_name: str
    input_selectors: list[str]
    user_message_selectors: list[str]
    assistant_message_selectors: list[str]


class BrowserModelAdapter:
    """Defines model-specific selectors for input injection and chat extraction."""

    def get_config(self) -> ModelExtractionConfig:
        raise NotImplementedError()
