"""Tests for Feature C: SKILL_POLICY.yaml generator, validator, and evaluator."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.policy.evaluator import evaluate_tool_with_policy, simulate_policy_scenarios
from app.policy.generator import generate_least_privilege_policy
from app.policy.schema import SkillPolicy
from app.policy.validator import validate_policy
from app.policy.yaml_export import from_yaml, to_yaml
from app.schemas import (
    Detector,
    EvidenceType,
    FileEntry,
    Finding,
    PolicyDecision,
    ScanReport,
    ScanState,
    Severity,
    TestCase as SkillTestCase,
    TestTrigger as SkillTestTrigger,
    ToolCall,
    utcnow,
)

SkillTestCase.__test__ = False
SkillTestTrigger.__test__ = False

client = TestClient(app)


def test_valid_policy_generation_and_validation():
    report = ScanReport(
        scan_id="scan_policy_test_01",
        created_at=utcnow(),
        input_kind="text",
        status=ScanState.completed,
        skill_name="Test Skill",
        files=[
            FileEntry(
                file_id="F1",
                relative_path="references/guide.md",
                size_bytes=100,
                scanned=True,
                sha256="abc",
            )
        ],
        findings=[],
    )

    policy = generate_least_privilege_policy(report)
    assert policy.default_action == "BLOCK"
    assert "read_public_file" in policy.allowed_tools
    assert "references/guide.md" in policy.allowed_file_paths

    val = validate_policy(policy)
    assert val.valid is True
    assert len(val.errors) == 0


def test_validator_rejects_unknown_tools():
    policy = SkillPolicy(
        policy_id="pol_bad_tool",
        name="Bad Tool Policy",
        allowed_tools=["read_public_file", "execute_arbitrary_shell"],
        default_action="BLOCK",
    )
    val = validate_policy(policy)
    assert val.valid is False
    assert any(e.code == "UNKNOWN_TOOL" for e in val.errors)


def test_validator_rejects_wildcards():
    policy = SkillPolicy(
        policy_id="pol_wildcard",
        name="Wildcard Policy",
        allowed_tools=["*"],
        allowed_domains=["*"],
        allowed_file_paths=["*"],
        default_action="BLOCK",
    )
    val = validate_policy(policy)
    assert val.valid is False
    codes = [e.code for e in val.errors]
    assert codes.count("UNRESTRICTED_WILDCARD") >= 3


def test_validator_rejects_path_traversal_and_absolute_paths():
    policy = SkillPolicy(
        policy_id="pol_traversal",
        name="Traversal Policy",
        allowed_file_paths=["/etc/passwd", "../outside.txt", "safe/../../bad.txt"],
        default_action="BLOCK",
    )
    val = validate_policy(policy)
    assert val.valid is False
    codes = [e.code for e in val.errors]
    assert "ABSOLUTE_PATH_FORBIDDEN" in codes
    assert "PATH_TRAVERSAL_FORBIDDEN" in codes


def test_validator_rejects_invalid_domains():
    policy = SkillPolicy(
        policy_id="pol_domains",
        name="Domain Policy",
        allowed_domains=["https://api.example.com/v1", "user:pass@example.com"],
        default_action="BLOCK",
    )
    val = validate_policy(policy)
    assert val.valid is False
    assert any(e.code == "INVALID_DOMAIN_FORMAT" for e in val.errors)


def test_yaml_round_trip():
    policy = SkillPolicy(
        policy_id="pol_roundtrip",
        name="Roundtrip Policy",
        allowed_tools=["read_public_file"],
        allowed_domains=["api.example.com"],
        allowed_file_paths=["references/**"],
        forbidden_actions=["read_canary_file"],
        default_action="BLOCK",
    )
    yaml_text = to_yaml(policy)
    assert "policy_id: pol_roundtrip" in yaml_text
    reloaded, val = from_yaml(yaml_text)
    assert val.valid is True
    assert reloaded is not None
    assert reloaded.policy_id == policy.policy_id
    assert reloaded.allowed_domains == ["api.example.com"]


def test_policy_evaluator_enforcement():
    policy = SkillPolicy(
        policy_id="pol_eval",
        name="Evaluator Policy",
        allowed_tools=["read_public_file"],
        allowed_domains=[],
        allowed_file_paths=["references/**"],
        forbidden_actions=["read_canary_file", "send_mock_request"],
        default_action="BLOCK",
    )

    # 1. Allowed file read
    call_allowed = ToolCall(tool="read_public_file", args={"path": "references/doc.md"})
    dec, _ = evaluate_tool_with_policy(policy, call_allowed)
    assert dec == PolicyDecision.ALLOW

    # 2. File read outside allowed_file_paths
    call_blocked_path = ToolCall(tool="read_public_file", args={"path": "secrets/token.txt"})
    dec, _ = evaluate_tool_with_policy(policy, call_blocked_path)
    assert dec == PolicyDecision.BLOCK

    # 3. Tool explicitly forbidden
    call_forbidden = ToolCall(tool="read_canary_file", args={"name": "CANARY"})
    dec, _ = evaluate_tool_with_policy(policy, call_forbidden)
    assert dec == PolicyDecision.BLOCK

    # 4. Outbound request blocked because allowed_domains is empty and forbidden
    call_outbound = ToolCall(tool="send_mock_request", args={"destination": "mock.local"})
    dec, _ = evaluate_tool_with_policy(policy, call_outbound)
    assert dec == PolicyDecision.BLOCK
