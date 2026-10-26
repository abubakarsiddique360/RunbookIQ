from __future__ import annotations

from pathlib import Path

import pytest

from runbookiq.kb import load_runbooks
from runbookiq.planner import build_plan
from runbookiq.policy import CommandPolicy
from runbookiq.search import RunbookIndex

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"


@pytest.fixture(scope="module")
def policy() -> CommandPolicy:
    return CommandPolicy.from_json()


@pytest.fixture(scope="module")
def index() -> RunbookIndex:
    return RunbookIndex(load_runbooks(KNOWLEDGE))


def test_plan_cites_the_matching_runbook(index: RunbookIndex, policy: CommandPolicy) -> None:
    plan = build_plan("disk is full on the worker node", index, policy)
    assert plan is not None
    assert plan.runbook.id == "disk-pressure"
    assert plan.citation.startswith("Node disk pressure")
    assert plan.steps


def test_plan_marks_approval_when_a_step_changes_state(
    index: RunbookIndex, policy: CommandPolicy
) -> None:
    plan = build_plan("disk is full on the worker node", index, policy)
    assert plan is not None
    assert plan.needs_approval is True
    verdicts = {step.verdict for step in plan.steps}
    assert "caution" in verdicts


def test_plan_serialises(index: RunbookIndex, policy: CommandPolicy) -> None:
    plan = build_plan("tls certificate expired", index, policy)
    assert plan is not None
    payload = plan.as_dict()
    assert payload["runbook"]["id"] == "certificate-rotation"
    assert payload["steps"]
    assert isinstance(payload["blocked"], list)


def test_blocked_steps_are_removed_from_the_plan(tmp_path, policy: CommandPolicy) -> None:
    (tmp_path / "danger.md").write_text(
        """---
id: danger
title: Danger runbook
system: linux
summary: Contains a destructive step.
tags: [danger]
---

## Step 1 - Check

```bash
df -h
```

## Step 2 - Delete everything

```bash
rm -rf /
```
""",
        encoding="utf-8",
    )
    index = RunbookIndex(load_runbooks(tmp_path))
    plan = build_plan("danger runbook", index, policy)
    assert plan is not None
    assert plan.blocked, "the destructive step must be reported"
    assert all(step.command != "rm -rf /" for step in plan.steps)
    assert plan.blocked[0].verdict == "blocked"


def test_unknown_query_returns_no_plan(index: RunbookIndex, policy: CommandPolicy) -> None:
    assert build_plan("make me a sandwich", index, policy) is None


def test_step_order_is_stable(index: RunbookIndex, policy: CommandPolicy) -> None:
    plan = build_plan("pod crashloop restart", index, policy)
    assert plan is not None
    assert [step.order for step in plan.steps] == list(range(1, len(plan.steps) + 1))
