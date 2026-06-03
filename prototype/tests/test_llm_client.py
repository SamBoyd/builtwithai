from unittest.mock import patch

import pytest

from prototype.config import Config
from prototype.schemas import (
    OwnershipRubricAnswer,
    PrivateEvaluation,
    PublicReceipt,
    ReceiptResult,
)


def make_receipt_result():
    return ReceiptResult(
        public_receipt=PublicReceipt(
            status="Caution",
            policy_fit="No policy found.",
            human_ownership="The transcript shows weak ownership evidence.",
            ai_role="AI drafted the implementation.",
            evidence_reviewed="Transcript and GitHub PR metadata.",
            tests_checks_run="pytest prototype/tests -q.",
            reviewer_attention_requested="Review the implementation boundary.",
            known_risks_or_unknowns="No issue or policy context was provided.",
            recommended_next_step="Review with caution.",
            receipt_binding="PR #3.",
        ),
        private_evaluation=PrivateEvaluation(
            ownership_rubric_answers=[
                OwnershipRubricAnswer(
                    question="Did they steer the work rather than merely accept generated output?",
                    evidence_level="weak",
                    evidence="The transcript shows limited contributor steering.",
                )
            ]
        ),
    )


@patch("prototype.llm_client.instructor.from_provider")
class TestGenerateReceipt:
    def test_missing_api_key_fails_before_creating_client(self, from_provider):
        from prototype.llm_client import LLMClientError, generate_receipt

        with pytest.raises(
            LLMClientError,
            match="ANTHROPIC_API_KEY is required to generate a receipt with anthropic",
        ):
            generate_receipt(
                "prompt",
                Config(
                    github_token=None,
                    provider_api_keys={"anthropic": None},
                ),
            )

        from_provider.assert_not_called()

    def test_requests_structured_receipt_with_default_settings(self, from_provider):
        from prototype.llm_client import DEFAULT_TEMPERATURE, generate_receipt
        from prototype.schemas import ReceiptResult

        expected_result = make_receipt_result()
        from_provider.return_value.create.return_value = expected_result

        result = generate_receipt(
            "receipt prompt",
            Config(
                github_token=None,
                provider_api_keys={"anthropic": "anthropic-key"},
            ),
        )

        assert result == expected_result
        from_provider.assert_called_once_with(
            "anthropic/claude-sonnet-4-6",
            api_key="anthropic-key",
        )
        from_provider.return_value.create.assert_called_once_with(
            response_model=ReceiptResult,
            messages=[{"role": "user", "content": "receipt prompt"}],
            temperature=DEFAULT_TEMPERATURE,
        )

    def test_uses_configured_anthropic_model_and_key(self, from_provider):
        from prototype.llm_client import generate_receipt

        from_provider.return_value.create.return_value = make_receipt_result()

        generate_receipt(
            "receipt prompt",
                Config(
                    github_token=None,
                    llm_model="anthropic/claude-sonnet-4-6",
                    provider_api_keys={"anthropic": "anthropic-key"},
                ),
            )

        from_provider.assert_called_once_with(
            "anthropic/claude-sonnet-4-6",
            api_key="anthropic-key",
        )

    def test_uses_google_key_for_generative_ai_provider(self, from_provider):
        from prototype.llm_client import generate_receipt

        from_provider.return_value.create.return_value = make_receipt_result()

        generate_receipt(
            "receipt prompt",
            Config(
                github_token=None,
                llm_model="generative-ai/gemini-2.5-flash-preview-04-17",
                provider_api_keys={"generative-ai": "google-key"},
            ),
        )

        from_provider.assert_called_once_with(
            "generative-ai/gemini-2.5-flash-preview-04-17",
            api_key="google-key",
        )

    def test_malformed_model_fails_before_creating_client(self, from_provider):
        from prototype.llm_client import LLMClientError, generate_receipt

        with pytest.raises(
            LLMClientError,
            match='LLM_MODEL must use model string format, like "anthropic/claude-sonnet-4-6"',
        ):
            generate_receipt(
                "receipt prompt",
                Config(
                    github_token=None,
                    llm_model="gpt-5.5",
                    provider_api_keys={"openai": "test-key"},
                ),
            )

        from_provider.assert_not_called()

    def test_wraps_provider_failures(self, from_provider):
        from prototype.llm_client import LLMClientError, generate_receipt

        from_provider.return_value.create.side_effect = RuntimeError("boom")

        with pytest.raises(
            LLMClientError,
            match="could not generate receipt with openai/gpt-5.5: boom",
        ):
            generate_receipt(
                "receipt prompt",
                Config(
                    github_token=None,
                    llm_model="openai/gpt-5.5",
                    provider_api_keys={"openai": "test-key"},
                ),
            )

    def test_suggests_provider_extra_when_optional_sdk_is_missing(self, from_provider):
        from prototype.llm_client import LLMClientError, generate_receipt

        from_provider.side_effect = RuntimeError(
            "The google package is required to use the Google provider."
        )

        with pytest.raises(LLMClientError) as error:
            generate_receipt(
                "receipt prompt",
                Config(
                    github_token=None,
                    llm_model="google/gemini-2.5-flash-preview-04-17",
                    provider_api_keys={"google": "google-key"},
                ),
            )

        assert "builtwithai[google]" in str(error.value)

    def test_suggests_reinstall_when_default_sdk_is_missing(self, from_provider):
        from prototype.llm_client import LLMClientError, generate_receipt

        from_provider.side_effect = RuntimeError(
            "The anthropic package is required to use the Anthropic provider."
        )

        with pytest.raises(LLMClientError) as error:
            generate_receipt(
                "receipt prompt",
                Config(
                    github_token=None,
                    provider_api_keys={"anthropic": "anthropic-key"},
                ),
            )

        assert "included in the base BuiltWithAI install" in str(error.value)
        assert "reinstall or upgrade BuiltWithAI" in str(error.value)
