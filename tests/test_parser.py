from unitlint.parser import parse


def test_basic_sections_and_values():
    u = parse("[Unit]\nDescription=Hello\n\n[Service]\nExecStart=/bin/true\n")
    assert u.has_section("Unit") and u.has_section("Service")
    assert u.value("Unit", "Description") == "Hello"
    assert u.get("Service", "ExecStart").line == 5


def test_comments_and_blank_lines_ignored():
    u = parse("# comment\n; also comment\n\n[Service]\n# inside\nUser=bob\n")
    assert u.value("Service", "User") == "bob"
    assert not u.syntax_errors


def test_duplicate_keys_last_wins():
    u = parse("[Service]\nExecStart=/a\nExecStart=/b\n")
    assert len(u.all("Service", "ExecStart")) == 2
    assert u.value("Service", "ExecStart") == "/b"


def test_line_continuation_joins_lines():
    u = parse("[Service]\nExecStart=/usr/bin/app \\\n  --flag one \\\n  --flag two\nUser=x\n")
    assert u.value("Service", "ExecStart").split() == ["/usr/bin/app", "--flag", "one", "--flag", "two"]
    assert "--flag two" in u.value("Service", "ExecStart")
    assert u.get("Service", "User").line == 5


def test_value_may_contain_equals():
    u = parse("[Service]\nEnvironment=A=1 B=2\n")
    assert u.value("Service", "Environment") == "A=1 B=2"


def test_syntax_errors_reported():
    u = parse("Orphan=1\n[Service]\nthis is not valid\n[Broken\n")
    messages = " ".join(m for _, m in u.syntax_errors)
    assert "before any [Section]" in messages
    assert "not a 'Key=Value'" in messages
    assert "malformed section header" in messages


def test_tokens_collects_across_assignments():
    u = parse("[Unit]\nAfter=a.target b.target\nAfter=c.target\n")
    assert u.tokens("Unit", "After") == ["a.target", "b.target", "c.target"]
