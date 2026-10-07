"""Lint rules. Each rule inspects a parsed UnitFile and reports findings."""

from __future__ import annotations

import difflib
import os
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Tuple

from .knownkeys import DEPRECATED, INSTALL_KEYS, SERVICE_KEYS, UNIT_KEYS
from .parser import UnitFile

ERROR, WARNING, INFO = "error", "warning", "info"
SEVERITY_RANK = {INFO: 0, WARNING: 1, ERROR: 2}

# (line, message, hint)
Hit = Tuple[int, str, str]


@dataclass(frozen=True)
class Finding:
    rule: str
    name: str
    severity: str
    message: str
    line: int
    hint: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    severity: str
    explanation: str
    func: Callable[[UnitFile], List[Hit]]


RULES: Dict[str, Rule] = {}


def rule(rule_id: str, name: str, severity: str, explanation: str):
    def decorator(func: Callable[[UnitFile], List[Hit]]):
        RULES[rule_id] = Rule(rule_id, name, severity, explanation, func)
        return func

    return decorator


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "yes", "true", "on"}


def _service_line(unit: UnitFile) -> int:
    return unit.section_line("Service")


def _is_service(unit: UnitFile) -> bool:
    return unit.has_section("Service")


EXEC_KEYS = (
    "ExecStart", "ExecStartPre", "ExecStartPost",
    "ExecCondition", "ExecReload", "ExecStop", "ExecStopPost",
)


# ---------------------------------------------------------------- UL000 syntax


@rule(
    "UL000", "syntax-error", ERROR,
    "The file could not be parsed as a unit file. systemd will skip lines it "
    "cannot understand, so the service may behave differently than you expect.",
)
def _syntax(unit: UnitFile) -> List[Hit]:
    return [
        (line, f"Syntax problem: {msg}.", "Fix the line so it reads Key=Value inside a [Section].")
        for line, msg in unit.syntax_errors
    ]


# ------------------------------------------------------------- service basics


@rule(
    "UL001", "missing-execstart", ERROR,
    "Every service except Type=oneshot must define ExecStart=. Without it "
    "systemd refuses to load the unit.",
)
def _missing_execstart(unit: UnitFile) -> List[Hit]:
    if not _is_service(unit):
        return []
    if unit.value("Service", "Type", "simple").lower() == "oneshot":
        return []
    if unit.all("Service", "ExecStart"):
        return []
    return [(_service_line(unit), "[Service] has no ExecStart=.", "Add ExecStart=/absolute/path/to/program")]


@rule(
    "UL002", "relative-exec-path", ERROR,
    "A command that contains a slash must be an absolute path. A relative "
    "path such as bin/app or ./app is rejected by systemd. (A bare program "
    "name like 'python3' is allowed; see UL016.)",
)
def _relative_exec(unit: UnitFile) -> List[Hit]:
    hits: List[Hit] = []
    for key in EXEC_KEYS:
        for d in unit.all("Service", key):
            command = d.value.lstrip("@-:+! ").lstrip("\"'")
            if not command:
                continue  # an empty value resets the list
            first = command.split()[0]
            if "/" in first and not first.startswith(("/", "%")):
                hits.append((
                    d.line,
                    f"{key}= uses relative path '{first}'.",
                    f"Use the full path, for example {key}=/opt/app/{os.path.basename(first)}",
                ))
    return hits


@rule(
    "UL003", "shell-syntax-in-exec", WARNING,
    "systemd runs ExecStart= directly, not through a shell. Pipes, redirects "
    "and && are passed to the program as plain arguments and do not work.",
)
def _shell_syntax(unit: UnitFile) -> List[Hit]:
    operators = {"&&", "||", "|", ">", ">>", "<", "<<", "2>&1", "&"}
    hits: List[Hit] = []
    for key in EXEC_KEYS:
        for d in unit.all("Service", key):
            words = d.value.split()
            wrapped = any(os.path.basename(w) in {"sh", "bash", "dash"} for w in words) and "-c" in words
            if wrapped:
                continue
            bad = [w for w in words if w in operators or w.startswith((">", "2>"))]
            if bad or "$(" in d.value or "`" in d.value:
                found = bad[0] if bad else "command substitution"
                hits.append((
                    d.line,
                    f"{key}= contains shell syntax ('{found}') but is not run by a shell.",
                    f"Wrap it: {key}=/bin/sh -c '...your command...'",
                ))
    return hits


@rule(
    "UL004", "not-installable", INFO,
    "Without an [Install] section with WantedBy= (or similar), "
    "'systemctl enable' does nothing, so the service will not start at boot.",
)
def _not_installable(unit: UnitFile) -> List[Hit]:
    if not _is_service(unit):
        return []
    has_target = any(
        unit.all("Install", key) for key in ("WantedBy", "RequiredBy", "Alias", "Also")
    )
    if has_target:
        return []
    return [(_service_line(unit), "No [Install] WantedBy= found, so the unit cannot be enabled.", "Add an [Install] section containing WantedBy=multi-user.target")]


# -------------------------------------------------------------- reliability


@rule(
    "UL005", "no-restart-policy", INFO,
    "Long-running services should usually restart on failure, otherwise a "
    "single crash leaves the service down until someone notices.",
)
def _no_restart(unit: UnitFile) -> List[Hit]:
    if not _is_service(unit):
        return []
    if unit.value("Service", "Type", "simple").lower() == "oneshot":
        return []
    if unit.value("Service", "Restart", "no").lower() != "no":
        return []
    return [(_service_line(unit), "No Restart= policy: the service stays down after a crash.", "Add Restart=on-failure and RestartSec=5")]


@rule(
    "UL006", "restart-always-no-delay", WARNING,
    "Restart=always with no RestartSec= restarts after only 100 ms. A service "
    "that fails instantly will loop quickly and hit systemd's start limit.",
)
def _restart_no_delay(unit: UnitFile) -> List[Hit]:
    d = unit.get("Service", "Restart")
    if d and d.value.strip().lower() == "always" and not unit.get("Service", "RestartSec"):
        return [(d.line, "Restart=always without RestartSec=.", "Add RestartSec=5 to space out restarts.")]
    return []


@rule(
    "UL007", "forking-without-pidfile", INFO,
    "For Type=forking, systemd tracks the main process more reliably when "
    "PIDFile= points at the file the daemon writes its PID to.",
)
def _forking_no_pid(unit: UnitFile) -> List[Hit]:
    d = unit.get("Service", "Type")
    if d and d.value.strip().lower() == "forking" and not unit.get("Service", "PIDFile"):
        return [(d.line, "Type=forking without PIDFile=.", "Add PIDFile=/run/yourdaemon.pid")]
    return []


@rule(
    "UL008", "network-online-ordering", WARNING,
    "Wants=network-online.target only pulls the target in. Without "
    "After=network-online.target the service may still start before the "
    "network is up.",
)
def _network_online(unit: UnitFile) -> List[Hit]:
    wanted = unit.tokens("Unit", "Wants") + unit.tokens("Unit", "Requires")
    if "network-online.target" not in wanted:
        return []
    if "network-online.target" in unit.tokens("Unit", "After"):
        return []
    d = unit.get("Unit", "Wants") or unit.get("Unit", "Requires")
    return [(d.line if d else 1, "network-online.target is requested but not ordered with After=.", "Add After=network-online.target")]


# ------------------------------------------------------------------ security


@rule(
    "UL009", "runs-as-root", WARNING,
    "A service running as root can damage the whole system if it is "
    "compromised. Prefer an unprivileged user or DynamicUser=yes.",
)
def _runs_as_root(unit: UnitFile) -> List[Hit]:
    if not _is_service(unit) or truthy(unit.value("Service", "DynamicUser")):
        return []
    user = unit.get("Service", "User")
    if user and user.value.strip() not in {"root", "0"}:
        return []
    return [(
        user.line if user else _service_line(unit),
        "Service runs as root.",
        "Add User=<name> (or DynamicUser=yes) unless it truly needs root.",
    )]


@rule(
    "UL010", "no-new-privileges", INFO,
    "NoNewPrivileges=yes stops the service and its children from gaining "
    "privileges through setuid binaries.",
)
def _no_new_privs(unit: UnitFile) -> List[Hit]:
    if _is_service(unit) and not truthy(unit.value("Service", "NoNewPrivileges")):
        return [(_service_line(unit), "NoNewPrivileges is not enabled.", "Add NoNewPrivileges=yes")]
    return []


@rule(
    "UL011", "protect-system", INFO,
    "ProtectSystem=full or strict makes /usr, /boot and /etc read-only for the "
    "service, limiting what an attacker can change.",
)
def _protect_system(unit: UnitFile) -> List[Hit]:
    if _is_service(unit) and unit.value("Service", "ProtectSystem").lower() not in {"yes", "true", "full", "strict"}:
        return [(_service_line(unit), "ProtectSystem is not set.", "Add ProtectSystem=strict (or full).")]
    return []


@rule(
    "UL012", "private-tmp", INFO,
    "PrivateTmp=yes gives the service its own /tmp so it cannot read or "
    "tamper with other programs' temporary files.",
)
def _private_tmp(unit: UnitFile) -> List[Hit]:
    if _is_service(unit) and not truthy(unit.value("Service", "PrivateTmp")):
        return [(_service_line(unit), "PrivateTmp is not enabled.", "Add PrivateTmp=yes")]
    return []


@rule(
    "UL013", "protect-home", INFO,
    "ProtectHome=yes hides /home, /root and /run/user from the service.",
)
def _protect_home(unit: UnitFile) -> List[Hit]:
    value = unit.value("Service", "ProtectHome").lower()
    if _is_service(unit) and value in {"", "no", "false", "0", "off"}:
        return [(_service_line(unit), "ProtectHome is not set.", "Add ProtectHome=yes (or read-only).")]
    return []


# ------------------------------------------------------------------- hygiene


@rule(
    "UL014", "deprecated-directive", WARNING,
    "These directives still work on some systems but are deprecated and may "
    "be removed. Use the modern replacement.",
)
def _deprecated(unit: UnitFile) -> List[Hit]:
    hits: List[Hit] = []
    for d in unit.directives:
        if d.section == "Service" and d.key in DEPRECATED:
            hits.append((d.line, f"{d.key}= is deprecated.", f"Use {DEPRECATED[d.key]} instead."))
        if d.section == "Service" and d.key in {"StandardOutput", "StandardError"} and d.value.strip().startswith("syslog"):
            hits.append((d.line, f"{d.key}={d.value.strip()} is deprecated.", f"Use {d.key}=journal instead."))
    return hits


@rule(
    "UL015", "unknown-directive", WARNING,
    "systemd silently ignores directives it does not recognise, so a typo "
    "means your setting has no effect. unitlint reports names that look like "
    "a misspelling of a real directive.",
)
def _unknown(unit: UnitFile) -> List[Hit]:
    known = {"Unit": UNIT_KEYS, "Service": SERVICE_KEYS, "Install": INSTALL_KEYS}
    hits: List[Hit] = []
    for d in unit.directives:
        keys = known.get(d.section)
        if keys is None or d.key in keys or d.key.startswith(("X-", "Condition", "Assert")):
            continue
        close = difflib.get_close_matches(d.key, keys, n=1, cutoff=0.85)
        if close and close[0].lower()[0] == d.key.lower()[0]:
            hits.append((d.line, f"Unknown directive '{d.key}' in [{d.section}].", f"Did you mean '{close[0]}'?"))
    return hits


@rule(
    "UL016", "bare-exec-name", INFO,
    "systemd (v239 and newer) finds a bare program name in a fixed list of "
    "directories, but older versions reject it and a full path is clearer "
    "and safer.",
)
def _bare_exec(unit: UnitFile) -> List[Hit]:
    hits: List[Hit] = []
    for key in EXEC_KEYS:
        for d in unit.all("Service", key):
            command = d.value.lstrip("@-:+! ").lstrip("\"'")
            if not command:
                continue
            first = command.split()[0]
            if "/" not in first and not first.startswith("%"):
                hits.append((
                    d.line,
                    f"{key}= uses bare program name '{first}'.",
                    f"Prefer the full path, e.g. {key}=/usr/bin/{first}",
                ))
    return hits


def run_rules(unit: UnitFile, ignore: Tuple[str, ...] = ()) -> List[Finding]:
    """Run every non-ignored rule and return findings sorted by line."""
    ignored = {r.upper() for r in ignore}
    findings: List[Finding] = []
    for r in RULES.values():
        if r.id in ignored:
            continue
        for line, message, hint in r.func(unit):
            findings.append(Finding(r.id, r.name, r.severity, message, line, hint))
    return sorted(findings, key=lambda f: (f.line, f.rule))
