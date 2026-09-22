"""Advisor registry: declared authority becomes an enforced type property."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Sequence

TRUST_CEILING = 0.97


class AuthorityViolation(RuntimeError):
    pass


@dataclass(frozen=True)
class Advisor:
    repo: str
    organ: str
    role: str
    tags: Sequence[str] = field(default_factory=tuple)

    @property
    def may_label(self) -> bool:
        return False

    @property
    def may_lower_axis(self) -> bool:
        return "abstain-retrain" in self.tags or "conscience" in self.tags

    @property
    def may_propose(self) -> bool:
        return "proposal-only" in self.tags or "retrieval" in self.tags

    @property
    def loadable(self) -> bool:
        return "no-weights" not in self.tags and "curriculum-only" not in self.tags


REGISTRY = (
    Advisor("SZLHOLDINGS/chaski-r2", "BRAIN/YACHAY", "propose spans and terms; never decide",
            ("proposal-only", "research-only", "lora")),
    Advisor("SZLHOLDINGS/chaski-5050", "BRAIN/YACHAY", "propose cuts for review",
            ("proposal-only", "research-only", "lora")),
    Advisor("SZLHOLDINGS/khipu-r3", "HEART/YUYAY", "supply the integrity axis by abstaining",
            ("abstain-retrain", "governed-agent", "lora")),
    Advisor("SZLHOLDINGS/KHIPU-R2", "HEART/YUYAY", "supply the integrity axis by abstaining",
            ("abstain-retrain", "proposal-only", "research-only")),
    Advisor("SZLHOLDINGS/brain-navigator-r2", "BRAIN/YACHAY", "retrieve handles and evidence pointers",
            ("retrieval", "grounded-only", "governed-agent")),
    Advisor("SZLHOLDINGS/WILLAY", "conscience", "lower the reported ceiling; never raise",
            ("conscience", "identity")),
    Advisor("SZLHOLDINGS/SZL-Khipu-1.5B-abstain", "HEART/YUYAY", "curriculum reference only",
            ("no-weights", "curriculum-only", "abstain-retrain")),
)


def assert_label_authority(advisor: Advisor, label: Optional[str]) -> None:
    if label is not None and not advisor.may_label:
        raise AuthorityViolation(advisor.repo + " returned a label: " + str(label))


def assert_loadable(advisor: Advisor) -> None:
    if not advisor.loadable:
        raise AuthorityViolation(advisor.repo + " is no-weights/curriculum-only and cannot be loaded")


def apply_ceiling(value: float) -> float:
    return min(float(value), TRUST_CEILING)


def ouroboros_pass(advisors: Sequence[Advisor], cap: int) -> dict:
    consulted = [a for a in advisors if a.loadable and (a.may_propose or a.may_lower_axis)][:cap]
    return {"cap": cap, "consulted": [a.repo for a in consulted],
            "skipped_not_loadable": [a.repo for a in advisors if not a.loadable],
            "labels_permitted": 0,
            "closure": "every consulted advisor returns proposals or an axis value; none returns a verdict"}