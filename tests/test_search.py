from __future__ import annotations

from pathlib import Path

import pytest

from runbookiq.kb import load_runbooks
from runbookiq.search import RunbookIndex, tokenize

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"


@pytest.fixture(scope="module")
def index() -> RunbookIndex:
    return RunbookIndex(load_runbooks(KNOWLEDGE))


def test_tokenize_removes_stopwords() -> None:
    assert "the" not in tokenize("the disk is full")
    assert "disk" in tokenize("the disk is full")


def test_disk_query_matches_disk_runbook(index: RunbookIndex) -> None:
    hits = index.search("node disk is full, eviction pressure")
    assert hits
    assert hits[0].runbook.id == "disk-pressure"


def test_certificate_query_matches_certificate_runbook(index: RunbookIndex) -> None:
    hits = index.search("tls certificate expired, https chain invalid")
    assert hits[0].runbook.id == "certificate-rotation"


def test_crashloop_query_matches_pod_runbook(index: RunbookIndex) -> None:
    hits = index.search("pod keeps restarting with CrashLoopBackOff")
    assert hits[0].runbook.id == "pod-crashloop"


def test_vpn_query_matches_vpn_runbook(index: RunbookIndex) -> None:
    hits = index.search("vpn tunnel down, ipsec child sa not established")
    assert hits[0].runbook.id == "vpn-tunnel-down"


def test_unrelated_query_returns_nothing(index: RunbookIndex) -> None:
    assert index.search("how do I bake sourdough bread") == []


def test_empty_query_returns_nothing(index: RunbookIndex) -> None:
    assert index.search("") == []


def test_hits_carry_matched_terms(index: RunbookIndex) -> None:
    hits = index.search("disk full", limit=2)
    assert hits[0].matched
    assert len(hits) <= 2
