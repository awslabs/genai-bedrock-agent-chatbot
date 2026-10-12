"""Unit tests for fix_agent_thinking_config.requires_adaptive_thinking.

Pure logic, no AWS credentials needed. Run from the repo root:

    python -m unittest discover -s code/lambdas/update-lambda/tests -v
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), ".."),
)

from fix_agent_thinking_config import (
    ADAPTIVE_THINKING_MODELS,
    requires_adaptive_thinking,
)


class TestRequiresAdaptiveThinking(unittest.TestCase):
    def test_exact_model_ids_match(self):
        for model in ADAPTIVE_THINKING_MODELS:
            self.assertTrue(requires_adaptive_thinking(model))

    def test_arn_and_inference_profile_forms_match(self):
        self.assertTrue(
            requires_adaptive_thinking(
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-opus-4-8"
            )
        )
        self.assertTrue(
            requires_adaptive_thinking("global.anthropic.claude-fable-5-v1:0")
        )

    def test_other_models_do_not_match(self):
        for model in (
            "anthropic.claude-sonnet-4-5",
            "amazon.titan-embed-text-v2:0",
            "claude-opus-4-7",
        ):
            self.assertFalse(requires_adaptive_thinking(model))

    def test_empty_string_does_not_match(self):
        self.assertFalse(requires_adaptive_thinking(""))

    def test_null_does_not_crash(self):
        self.assertFalse(requires_adaptive_thinking(None))


if __name__ == "__main__":
    unittest.main()
