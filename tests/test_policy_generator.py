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


def test_schema_rejects_unknown_keys_and_enforces_limits():
    val = validate_policy({"policy_id": "p1", "name": "x", "allow_everything": True})
    assert not val.valid
    assert any(e.field == "allow_everything" for e in val.errors)

    policy = SkillPolicy(
        policy_id="pol_limits", name="Limits", allowed_tools=["send_mock_request", "write_mock_file"],
        allowed_domains=["mock.local"], allowed_file_paths=["workspace/**"],
        limits={"max_mock_requests_per_test": 1},
    )
    call = ToolCall(tool="send_mock_request", args={"destination": "mock.local", "payload_summary": "x"})
    test = SkillTestCase(
        test_id="T1", suite_version="1", name="two sends", purpose="p", kind="adversarial", origin="fixed_suite",
        setup_fixture="f", trigger=SkillTestTrigger(type="always"), tool_sequence=[call, call],
        expected_policy_decisions=[PolicyDecision.ALLOW, PolicyDecision.BLOCK], expected_outcome="o",
    )
    events = simulate_policy_scenarios(policy, [test])[0]["events"]
    assert [e["decision"] for e in events] == ["ALLOW", "BLOCK"]

    # Writes are confined to allowed_file_paths; "workspace/**" must not match "workspaceX/..."
    out = ToolCall(tool="write_mock_file", args={"path": "workspaceX/a.txt", "content": "x"})
    assert evaluate_tool_with_policy(policy, out)[0] == PolicyDecision.BLOCK
    dotdot = ToolCall(tool="write_mock_file", args={"path": "workspace/../.bashrc", "content": "x"})
    assert evaluate_tool_with_policy(policy, dotdot)[0] == PolicyDecision.BLOCK


def test_policy_revisions_api():
    from app.api.deps import store
    from app.pipeline import new_scan_id

    sid = new_scan_id()
    store().save(ScanReport(scan_id=sid, created_at=utcnow(), input_kind="text", status=ScanState.completed))
    first = client.post(f"/api/scans/{sid}/policy/generate").json()
    assert first["revision"] == 1 and first["validation"]["valid"]

    edited = first["yaml"].replace("default_action: BLOCK", "default_action: FLAG")
    saved = client.post(f"/api/scans/{sid}/policy/revisions", json={"yaml": edited}).json()
    assert saved["revision"] == 2 and saved["revisions"] == [1, 2]
    assert saved["policy"]["metadata"]["generator_mode"] == "user_edited"
    # Revision 1 is unchanged
    assert client.get(f"/api/scans/{sid}/policy?revision=1").json()["yaml"] == first["yaml"]

    bad = client.post(f"/api/scans/{sid}/policy/revisions", json={"yaml": first["yaml"] + "\nextra_key: 1\n"})
    assert bad.status_code == 422
    assert client.get(f"/api/scans/{sid}/policy").json()["revision"] == 2
    assert client.get(f"/api/scans/{sid}/policy/export").status_code == 200
