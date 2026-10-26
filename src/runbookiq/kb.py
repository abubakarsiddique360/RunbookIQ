"""Runbook parsing.

A runbook is markdown with YAML-ish frontmatter (parsed by hand — no dependency)
and one fenced ``bash`` block per step::

    ---
    id: disk-pressure
    title: Node disk pressure
    system: kubernetes
    tags: [disk, storage]
    ---

    ## Step 1 - Inspect free space

    ```bash
    df -h
    ```
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_STEP_RE = re.compile(
    r"^#{2,3}\s+(?:(?:step\s+)?\d+\s*[-:.)]\s*)?(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_BASH_RE = re.compile(r"```bash\s*\n(.*?)```", re.DOTALL)


class RunbookError(ValueError):
    """Raised when a runbook is malformed."""


@dataclass(frozen=True)
class Step:
    title: str
    command: str
    note: str = ""


@dataclass(frozen=True)
class Runbook:
    id: str
    title: str
    system: str
    summary: str
    tags: tuple[str, ...]
    body: str
    steps: tuple[Step, ...]
    path: str = ""

    @property
    def searchable(self) -> str:
        return f"{self.title} {self.title} {self.system} {' '.join(self.tags)} {self.body}"


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.lstrip().startswith("---"):
        raise RunbookError("missing frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise RunbookError("unterminated frontmatter")
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        key, _, value = line.partition(":")
        if key.strip():
            meta[key.strip().lower()] = value.strip()
    return meta, parts[2].strip()


def _tags(raw: str) -> tuple[str, ...]:
    cleaned = raw.strip().strip("[]")
    return tuple(item.strip().strip("\"'") for item in cleaned.split(",") if item.strip())


def parse_runbook(path: Path | str) -> Runbook:
    source = Path(path)
    meta, body = _split_frontmatter(source.read_text(encoding="utf-8"))
    runbook_id = (meta.get("id") or source.stem).strip()
    if not runbook_id:
        raise RunbookError(f"{source.name}: empty id")

    steps: list[Step] = []
    headings = list(_STEP_RE.finditer(body))
    for index, heading in enumerate(headings):
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        block = body[start:end]
        match = _BASH_RE.search(block)
        if not match:
            continue
        command = " ".join(
            line.strip() for line in match.group(1).strip().splitlines() if line.strip()
        )
        note_text = block[: match.start()]
        note = " ".join(
            line.strip()
            for line in note_text.splitlines()
            if line.strip() and not line.strip().startswith((">", "-", "|"))
        )
        steps.append(Step(title=heading.group(1).strip(), command=command, note=note[:200]))

    return Runbook(
        id=runbook_id,
        title=meta.get("title", runbook_id).strip(),
        system=meta.get("system", "general").strip(),
        summary=meta.get("summary", "").strip(),
        tags=_tags(meta.get("tags", "")),
        body=body,
        steps=tuple(steps),
        path=str(source),
    )


def load_runbooks(directory: Path | str) -> list[Runbook]:
    root = Path(directory)
    if not root.exists():
        return []
    runbooks = [parse_runbook(path) for path in sorted(root.rglob("*.md"))]
    ids = [runbook.id for runbook in runbooks]
    duplicates = {runbook_id for runbook_id in ids if ids.count(runbook_id) > 1}
    if duplicates:
        raise RunbookError(f"duplicate runbook ids: {', '.join(sorted(duplicates))}")
    return runbooks
