from __future__ import annotations

from pathlib import Path

import pytest

from runbookiq.kb import RunbookError, load_runbooks, parse_runbook

SAMPLE = """---
id: demo
title: Demo runbook
system: linux
summary: A tiny runbook for tests.
tags: [demo, disk]
---

## Step 1 - Check space

Read only.

```bash
df -h
```

## Step 2 - Restart the agent

Changes state.

```bash
systemctl restart agent
```
"""

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"


def test_parse_runbook_reads_steps(tmp_path) -> None:
    path = tmp_path / "demo.md"
    path.write_text(SAMPLE, encoding="utf-8")
    runbook = parse_runbook(path)
    assert runbook.id == "demo"
    assert runbook.system == "linux"
    assert runbook.tags == ("demo", "disk")
    assert [step.title for step in runbook.steps] == ["Check space", "Restart the agent"]
    assert runbook.steps[0].command == "df -h"
    assert runbook.steps[1].command == "systemctl restart agent"


def test_parse_runbook_collapses_multiline_commands(tmp_path) -> None:
    path = tmp_path / "multi.md"
    path.write_text(
        SAMPLE.replace("df -h", "du -xh --max-depth=1 /var/log \\\n  | sort -h"),
        encoding="utf-8",
    )
    command = parse_runbook(path).steps[0].command
    assert command.startswith("du -xh")
    assert "\n" not in command


def test_missing_frontmatter_raises(tmp_path) -> None:
    path = tmp_path / "bad.md"
    path.write_text("# no frontmatter", encoding="utf-8")
    with pytest.raises(RunbookError):
        parse_runbook(path)


def test_duplicate_ids_raise(tmp_path) -> None:
    (tmp_path / "a.md").write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "b.md").write_text(SAMPLE, encoding="utf-8")
    with pytest.raises(RunbookError, match="duplicate"):
        load_runbooks(tmp_path)


def test_bundled_runbooks_are_usable() -> None:
    runbooks = load_runbooks(KNOWLEDGE)
    assert len(runbooks) == 4
    for runbook in runbooks:
        assert runbook.title
        assert runbook.summary
        assert len(runbook.steps) >= 3


def test_missing_directory_returns_empty(tmp_path) -> None:
    assert load_runbooks(tmp_path / "nope") == []
