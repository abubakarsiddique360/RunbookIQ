"""Turn a question into a safe, cited step plan."""

from __future__ import annotations

from dataclasses import dataclass, field

from runbookiq.kb import Runbook
from runbookiq.policy import BLOCKED, CAUTION, CommandPolicy
from runbookiq.search import RunbookIndex


@dataclass(frozen=True)
class PlanStep:
    order: int
    title: str
    command: str
    verdict: str
    reason: str
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "order": self.order,
            "title": self.title,
            "command": self.command,
            "verdict": self.verdict,
            "reason": self.reason,
            "note": self.note,
        }


@dataclass
class Plan:
    runbook: Runbook
    score: float
    matched: tuple[str, ...]
    steps: list[PlanStep] = field(default_factory=list)
    blocked: list[PlanStep] = field(default_factory=list)

    @property
    def needs_approval(self) -> bool:
        return any(step.verdict == CAUTION for step in self.steps)

    @property
    def citation(self) -> str:
        return f"{self.runbook.title} ({self.runbook.id})"

    def as_dict(self) -> dict:
        return {
            "runbook": {
                "id": self.runbook.id,
                "title": self.runbook.title,
                "system": self.runbook.system,
            },
            "score": round(self.score, 3),
            "matched": list(self.matched),
            "needs_approval": self.needs_approval,
            "steps": [step.as_dict() for step in self.steps],
            "blocked": [step.as_dict() for step in self.blocked],
        }


def build_plan(
    query: str,
    index: RunbookIndex,
    policy: CommandPolicy,
    max_steps: int = 8,
) -> Plan | None:
    """Return the best matching runbook as a gated plan, or ``None`` if unsure."""

    hits = index.search(query, limit=1)
    if not hits:
        return None
    hit = hits[0]
    plan = Plan(runbook=hit.runbook, score=hit.score, matched=hit.matched)
    for order, step in enumerate(hit.runbook.steps[:max_steps], start=1):
        decision = policy.classify(step.command)
        plan_step = PlanStep(
            order=order,
            title=step.title,
            command=step.command,
            verdict=decision.verdict,
            reason=decision.reason,
            note=step.note,
        )
        if decision.verdict == BLOCKED:
            plan.blocked.append(plan_step)
        else:
            plan.steps.append(plan_step)
    return plan
