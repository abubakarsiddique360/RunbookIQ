"""Command safety policy.

Every command a runbook suggests is classified before a human sees it as an
action: ``safe`` (read-only), ``caution`` (needs approval) or ``blocked`` (never
run from a generated plan). Unknown commands default to ``caution`` — deny by
default, allow by evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_POLICY = Path(__file__).with_name("policy.json")

SAFE = "safe"
CAUTION = "caution"
BLOCKED = "blocked"
VERDICTS = (SAFE, CAUTION, BLOCKED)


class PolicyError(ValueError):
    """Raised when the command policy file is malformed."""


@dataclass(frozen=True)
class Decision:
    verdict: str
    reason: str
    rule: str

    @property
    def allowed(self) -> bool:
        return self.verdict != BLOCKED

    def as_dict(self) -> dict:
        return {"verdict": self.verdict, "reason": self.reason, "rule": self.rule}


@dataclass(frozen=True)
class Rule:
    pattern: str
    verdict: str
    reason: str


class CommandPolicy:
    def __init__(self, rules: list[Rule], safe_prefixes: tuple[str, ...]) -> None:
        self.rules = rules
        self.safe_prefixes = tuple(prefix.lower() for prefix in safe_prefixes)

    @classmethod
    def from_dict(cls, data: dict) -> CommandPolicy:
        if not isinstance(data, dict):
            raise PolicyError("policy root must be an object")
        rules: list[Rule] = []
        for item in data.get("rules", []):
            if not isinstance(item, dict) or "pattern" not in item:
                raise PolicyError("each rule needs a 'pattern'")
            verdict = str(item.get("verdict", CAUTION)).lower()
            if verdict not in VERDICTS:
                raise PolicyError(f"invalid verdict '{verdict}'")
            rules.append(
                Rule(
                    pattern=str(item["pattern"]),
                    verdict=verdict,
                    reason=str(item.get("reason", "matched policy rule")),
                )
            )
        # escalate on the most dangerous verdict first: blocked, then caution, then safe
        ranking = {BLOCKED: 0, CAUTION: 1, SAFE: 2}
        rules.sort(key=lambda rule: ranking[rule.verdict])
        safe_prefixes = tuple(str(item) for item in data.get("safe_prefixes", []))
        return cls(rules=rules, safe_prefixes=safe_prefixes)

    @classmethod
    def from_json(cls, path: Path | str | None = None) -> CommandPolicy:
        source = Path(path) if path else DEFAULT_POLICY
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise PolicyError(f"policy not found: {source}") from exc
        except json.JSONDecodeError as exc:
            raise PolicyError(f"{source.name} is not valid JSON: {exc}") from exc
        return cls.from_dict(data)

    def classify(self, command: str) -> Decision:
        normalized = " ".join(command.strip().split())
        lowered = normalized.lower()
        for rule in self.rules:
            if re.search(rule.pattern, lowered):
                return Decision(verdict=rule.verdict, reason=rule.reason, rule=rule.pattern)
        for prefix in self.safe_prefixes:
            if lowered.startswith(prefix):
                return Decision(
                    verdict=SAFE, reason=f"read-only command ({prefix})", rule=f"prefix:{prefix}"
                )
        return Decision(
            verdict=CAUTION,
            reason="unclassified command, treat as needing approval",
            rule="default",
        )

    def classify_all(self, commands: list[str]) -> list[Decision]:
        return [self.classify(command) for command in commands]
