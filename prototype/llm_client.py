import instructor

from prototype.config import Config
from prototype.schemas import ReceiptResult


DEFAULT_MODEL = "gpt-5.5"
DEFAULT_TEMPERATURE = 1


class LLMClientError(Exception):
    pass


def generate_receipt(prompt: str, config: Config, model: str = DEFAULT_MODEL) -> ReceiptResult:
    if not config.openai_api_key:
        raise LLMClientError("OPENAI_API_KEY is required to generate a receipt")

    try:
        client = instructor.from_provider(f"openai/{model}", api_key=config.openai_api_key)
        return client.create(
            response_model=ReceiptResult,
            messages=[{"role": "user", "content": prompt}],
            temperature=DEFAULT_TEMPERATURE,
        )
    except Exception as error:
        raise LLMClientError(f"could not generate receipt with OpenAI: {error}") from error
