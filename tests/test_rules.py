import pytest

from unitlint.parser import parse
from unitlint.rules import RULES, run_rules

GOOD = """\
[Unit]
Description=ok
Wants=network-online.target
After=network-online.target

[Service]
ExecStart=/usr/bin/app
User=app
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
"""


def ids(text, **kw):
    return {f.rule for f in run_rules(parse(text), **kw)}


def test_good_unit_is_clean():
    assert run_rules(parse(GOOD)) == []


def test_every_rule_has_metadata():
    assert len(RULES) >= 16
    for r in RULES.values():
        assert r.explanation and r.name and r.severity in {"error", "warning", "info"}


def test_syntax_rule():
    assert "UL000" in ids("garbage\n[Service]\nExecStart=/x\n")


def test_missing_execstart():
    assert "UL001" in ids("[Service]\nUser=x\n")
    assert "UL001" not in ids("[Service]\nType=oneshot\nUser=x\n")
    assert "UL001" not in ids("[Service]\nExecStart=/x\n")


def test_relative_exec_path_only_for_paths_with_slash():
    assert "UL002" in ids("[Service]\nExecStart=bin/app\n")
    assert "UL002" in ids("[Service]\nExecStart=./app\n")
    assert "UL002" not in ids("[Service]\nExecStart=/usr/bin/app\n")
    assert "UL002" not in ids("[Service]\nExecStart=-/usr/bin/app\n")
    assert "UL002" not in ids("[Service]\nExecStart=python3 app.py\n")
    assert "UL002" not in ids("[Service]\nExecStart=%h/bin/app\n")


def test_bare_exec_name_is_suggestion():
    found = run_rules(parse("[Service]\nExecStart=python3 app.py\n"))
    assert any(f.rule == "UL016" and f.severity == "info" for f in found)
    assert "UL016" not in ids("[Service]\nExecStart=/usr/bin/python3 app.py\n")


def test_shell_syntax_detected_but_not_when_wrapped():
    assert "UL003" in ids("[Service]\nExecStart=/usr/bin/a | /usr/bin/b\n")
    assert "UL003" in ids("[Service]\nExecStart=/usr/bin/a > /tmp/out\n")
    assert "UL003" in ids("[Service]\nExecStart=/usr/bin/a && /usr/bin/b\n")
    assert "UL003" in ids("[Service]\nExecStart=/usr/bin/a $(date)\n")
    assert "UL003" not in ids("[Service]\nExecStart=/bin/sh -c '/usr/bin/a | /usr/bin/b'\n")
    assert "UL003" not in ids("[Service]\nExecStart=/usr/bin/grep 'a|b' file\n")


def test_not_installable():
    assert "UL004" in ids("[Service]\nExecStart=/x\n")
    assert "UL004" not in ids("[Service]\nExecStart=/x\n[Install]\nWantedBy=multi-user.target\n")


def test_restart_policy():
    assert "UL005" in ids("[Service]\nExecStart=/x\n")
    assert "UL005" not in ids("[Service]\nExecStart=/x\nRestart=on-failure\n")
    assert "UL005" not in ids("[Service]\nType=oneshot\nExecStart=/x\n")


def test_restart_always_needs_delay():
    assert "UL006" in ids("[Service]\nExecStart=/x\nRestart=always\n")
    assert "UL006" not in ids("[Service]\nExecStart=/x\nRestart=always\nRestartSec=3\n")
    assert "UL006" not in ids("[Service]\nExecStart=/x\nRestart=on-failure\n")


def test_forking_pidfile():
    assert "UL007" in ids("[Service]\nType=forking\nExecStart=/x\n")
    assert "UL007" not in ids("[Service]\nType=forking\nPIDFile=/run/x.pid\nExecStart=/x\n")


def test_network_online_ordering():
    assert "UL008" in ids("[Unit]\nWants=network-online.target\n[Service]\nExecStart=/x\n")
    assert "UL008" not in ids("[Unit]\nWants=network-online.target\nAfter=network-online.target\n[Service]\nExecStart=/x\n")
    assert "UL008" not in ids("[Unit]\nDescription=x\n[Service]\nExecStart=/x\n")


@pytest.mark.parametrize("extra,expected", [
    ("", True),
    ("User=root\n", True),
    ("User=app\n", False),
    ("DynamicUser=yes\n", False),
])
def test_runs_as_root(extra, expected):
    assert ("UL009" in ids(f"[Service]\nExecStart=/x\n{extra}")) is expected


@pytest.mark.parametrize("rule_id,line", [
    ("UL010", "NoNewPrivileges=yes"),
    ("UL011", "ProtectSystem=strict"),
    ("UL012", "PrivateTmp=yes"),
    ("UL013", "ProtectHome=yes"),
])
def test_hardening_rules(rule_id, line):
    assert rule_id in ids("[Service]\nExecStart=/x\n")
    assert rule_id not in ids(f"[Service]\nExecStart=/x\n{line}\n")


def test_deprecated_directives():
    found = run_rules(parse("[Service]\nExecStart=/x\nMemoryLimit=1G\nCPUShares=512\nStandardOutput=syslog\n"))
    messages = [f.hint for f in found if f.rule == "UL014"]
    assert any("MemoryMax" in m for m in messages)
    assert any("CPUWeight" in m for m in messages)
    assert any("journal" in m for m in messages)


def test_unknown_directive_typo_suggests_fix():
    found = [f for f in run_rules(parse("[Service]\nExecStart=/x\nRestar=always\n")) if f.rule == "UL015"]
    assert found and "Restart" in found[0].hint


def test_unknown_directive_ignores_custom_and_far_names():
    assert "UL015" not in ids("[Service]\nExecStart=/x\nX-Custom=1\n")
    assert "UL015" not in ids("[Service]\nExecStart=/x\nTotallyDifferentThing=1\n")
    assert "UL015" not in ids("[Unit]\nConditionPathExists=/x\n[Service]\nExecStart=/x\n")


def test_ignore_option_skips_rules():
    text = "[Service]\nExecStart=/x\n"
    assert "UL009" in ids(text)
    assert "UL009" not in ids(text, ignore=("ul009",))


def test_findings_sorted_by_line():
    found = run_rules(parse("[Service]\nExecStart=bin/x\nRestar=always\n"))
    lines = [f.line for f in found]
    assert lines == sorted(lines)
