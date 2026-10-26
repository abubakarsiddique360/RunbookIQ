from __future__ import annotations

import json

from runbookiq.cli import main


def test_list_runbooks(capsys) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "disk-pressure" in out
    assert "4 runbook(s)" in out


def test_search_output(capsys) -> None:
    assert main(["search", "disk full on node"]) == 0
    assert "disk-pressure" in capsys.readouterr().out


def test_search_json(capsys) -> None:
    assert main(["search", "vpn tunnel down", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["id"] == "vpn-tunnel-down"


def test_plan_human_output(capsys) -> None:
    assert main(["plan", "certificate expired on the load balancer"]) == 0
    out = capsys.readouterr().out
    assert "Runbook :" in out
    assert "Source:" in out


def test_plan_json_contains_citation(capsys) -> None:
    assert main(["plan", "pod crashloop backoff", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["runbook"]["id"] == "pod-crashloop"
    assert payload["steps"][0]["verdict"] in {"safe", "caution"}


def test_plan_without_match(capsys) -> None:
    assert main(["plan", "how do I bake bread"]) == 0
    assert "No runbook matched" in capsys.readouterr().out


def test_check_safe_command_exits_zero(capsys) -> None:
    assert main(["check", "kubectl get pods"]) == 0
    assert "safe" in capsys.readouterr().out


def test_check_blocked_command_exits_one(capsys) -> None:
    assert main(["check", "rm -rf /"]) == 1
    assert "blocked" in capsys.readouterr().out


def test_invalid_policy_path_exits_two(tmp_path, capsys) -> None:
    assert main(["--policy", str(tmp_path / "nope.json"), "check", "df -h"]) == 2
    assert "error" in capsys.readouterr().err
