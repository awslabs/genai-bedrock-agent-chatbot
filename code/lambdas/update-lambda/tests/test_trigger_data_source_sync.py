"""Unit tests for trigger_data_source_sync.trigger_data_source_sync.

A fake Bedrock client stands in for the real API; time.sleep is patched so
the backoff loop runs instantly. Run from the repo root:

    python -m unittest discover -s code/lambdas/update-lambda/tests -v
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), ".."),
)

from trigger_data_source_sync import trigger_data_source_sync


class FakeBedrockAgent:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.starts = 0
        self.checks = 0

    def start_ingestion_job(self, knowledgeBaseId, dataSourceId):
        self.starts += 1
        assert knowledgeBaseId == "kb-1"
        assert dataSourceId == "ds-1"
        return {"ingestionJob": {"ingestionJobId": "job-1"}}

    def get_ingestion_job(self, knowledgeBaseId, dataSourceId, ingestionJobId):
        self.checks += 1
        assert ingestionJobId == "job-1"
        return {"ingestionJob": {"status": self.statuses.pop(0)}}


class TestTriggerDataSourceSync(unittest.TestCase):
    def test_complete_first_try_never_sleeps(self):
        agent = FakeBedrockAgent(["COMPLETE"])
        with mock.patch("time.sleep") as sleep:
            trigger_data_source_sync(agent, "kb-1", "ds-1")
        self.assertEqual((agent.starts, agent.checks), (1, 1))
        sleep.assert_not_called()

    def test_in_progress_retries_with_backoff_then_succeeds(self):
        agent = FakeBedrockAgent(["IN_PROGRESS", "STARTING", "COMPLETE"])
        with mock.patch("time.sleep") as sleep:
            trigger_data_source_sync(agent, "kb-1", "ds-1")
        self.assertEqual((agent.starts, agent.checks), (1, 3))
        self.assertEqual(
            [c.args[0] for c in sleep.call_args_list], [5, 10]
        )

    def test_backoff_caps_at_sixty_seconds(self):
        agent = FakeBedrockAgent(["IN_PROGRESS"] * 10)
        with mock.patch("time.sleep") as sleep:
            trigger_data_source_sync(agent, "kb-1", "ds-1")
        waits = [c.args[0] for c in sleep.call_args_list]
        self.assertEqual(len(waits), 10)
        self.assertLessEqual(max(waits), 60)
        self.assertIn(60, waits)

    def test_start_failure_propagates(self):
        class BrokenAgent(FakeBedrockAgent):
            def start_ingestion_job(self, knowledgeBaseId, dataSourceId):
                raise RuntimeError("throttled")

        with self.assertRaises(RuntimeError):
            trigger_data_source_sync(BrokenAgent([]), "kb-1", "ds-1")


if __name__ == "__main__":
    unittest.main()
