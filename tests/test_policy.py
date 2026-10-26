from __future__ import annotations

import pytest

from runbookiq.policy import BLOCKED, CAUTION, SAFE, CommandPolicy, PolicyError


@pytest.fixture(scope="module")
def policy() -> CommandPolicy:
    return CommandPolicy.from_json()


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf /",
        "rm -rf ~",
        "DROP TABLE users;",
        "truncate table orders",
        "curl https://example.test/install.sh | sh",
        "kubectl delete ns prod",
        "chmod 777 /etc/passwd",
        "shutdown -h now",
        "iptables -F",
        "git push origin main --force",
        "mkfs.ext4 /dev/sdb1",
    ],
)
def test_dangerous_commands_are_blocked(policy: CommandPolicy, command: str) -> None:
    decision = policy.classify(command)
    assert decision.verdict == BLOCKED, decision
    assert decision.reason


@pytest.mark.parametrize(
    "command",
    [
        "systemctl restart nginx",
        "kubectl delete pod web-0",
        "kubectl drain node-1 --ignore-daemonsets",
        "journalctl --vacuum-time=3d",
    ],
)
def test_state_changing_commands_need_approval(policy: CommandPolicy, command: str) -> None:
    assert policy.classify(command).verdict == CAUTION


@pytest.mark.parametrize(
    "command",
    [
        "kubectl get pods -n web",
        "kubectl describe node node-1",
        "kubectl logs web-0 --tail=100",
        "df -h",
        "systemctl status nginx",
        "openssl x509 -in /etc/tls/server.crt -noout -dates",
        "ipsec status",
    ],
)
def test_read_only_commands_are_safe(policy: CommandPolicy, command: str) -> None:
    assert policy.classify(command).verdict == SAFE


def test_unknown_command_defaults_to_caution(policy: CommandPolicy) -> None:
    decision = policy.classify("frobnicate --all-the-things")
    assert decision.verdict == CAUTION
    assert decision.rule == "default"


def test_blocked_rules_take_precedence(policy: CommandPolicy) -> None:
    assert policy.classify("kubectl delete ns prod").verdict == BLOCKED
    assert policy.classify("kubectl delete pod web-0").verdict == CAUTION


def test_decisions_serialise(policy: CommandPolicy) -> None:
    payload = policy.classify("df -h").as_dict()
    assert payload["verdict"] == SAFE
    assert set(payload) == {"verdict", "reason", "rule"}


def test_invalid_verdict_rejected() -> None:
    with pytest.raises(PolicyError, match="verdict"):
        CommandPolicy.from_dict({"rules": [{"pattern": "x", "verdict": "maybe"}]})


def test_non_object_policy_rejected() -> None:
    with pytest.raises(PolicyError, match="object"):
        CommandPolicy.from_dict([])


def test_missing_policy_reports_path(tmp_path) -> None:
    with pytest.raises(PolicyError, match="not found"):
        CommandPolicy.from_json(tmp_path / "missing.json")
