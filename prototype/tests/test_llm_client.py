from unittest.mock import patch

import pytest

from prototype.schemas import OwnershipRubricAnswer, PrivateEvaluation, PublicReceipt, ReceiptResult


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
    def test_missing_api_key_fails_before_creating_client(self, from_provider, monkeypatch):
        from prototype.llm_client import LLMClientError, generate_receipt

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(LLMClientError, match="OPENAI_API_KEY is required to generate a receipt"):
            generate_receipt("prompt")

        from_provider.assert_not_called()

    def test_requests_structured_receipt_with_default_settings(self, from_provider, monkeypatch):
        from prototype.llm_client import DEFAULT_TEMPERATURE, generate_receipt
        from prototype.schemas import ReceiptResult

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        expected_result = make_receipt_result()
        from_provider.return_value.create.return_value = expected_result

        result = generate_receipt("receipt prompt")

        assert result == expected_result
        from_provider.assert_called_once_with("openai/gpt-5.5", api_key="test-key")
        from_provider.return_value.create.assert_called_once_with(
            response_model=ReceiptResult,
            messages=[{"role": "user", "content": "receipt prompt"}],
            temperature=DEFAULT_TEMPERATURE,
        )

    def test_uses_model_override(self, from_provider, monkeypatch):
        from prototype.llm_client import generate_receipt

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        from_provider.return_value.create.return_value = make_receipt_result()

        generate_receipt("receipt prompt", model="gpt-5.4-mini")

        from_provider.assert_called_once_with("openai/gpt-5.4-mini", api_key="test-key")

    def test_wraps_provider_failures(self, from_provider, monkeypatch):
        from prototype.llm_client import LLMClientError, generate_receipt

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        from_provider.return_value.create.side_effect = RuntimeError("boom")

        with pytest.raises(LLMClientError, match="could not generate receipt with OpenAI: boom"):
            generate_receipt("receipt prompt")
