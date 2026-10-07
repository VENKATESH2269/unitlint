import io
import json

import pytest

from unitlint import cli

BAD = "[Service]\nExecStart=bin/app\n"
CLEAN = (
    "[Unit]\nDescription=x\n[Service]\nExecStart=/usr/bin/app\nUser=a\nRestart=on-failure\n"
    "NoNewPrivileges=yes\nProtectSystem=strict\nProtectHome=yes\nPrivateTmp=yes\n"
    "[Install]\nWantedBy=multi-user.target\n"
)


@pytest.fixture
def files(tmp_path):
    bad = tmp_path / "bad.service"
    bad.write_text(BAD)
    good = tmp_path / "good.service"
    good.write_text(CLEAN)
    return bad, good


def test_clean_file_exits_zero(files, capsys):
    assert cli.main([str(files[1]), "--no-color"]) == 0
    assert "no problems found" in capsys.readouterr().out


def test_error_exits_one_and_prints_fix(files, capsys):
    assert cli.main([str(files[0]), "--no-color"]) == 1
    out = capsys.readouterr().out
    assert "UL002" in out and "fix:" in out and ":2:" in out


def test_fail_on_levels(tmp_path):
    f = tmp_path / "w.service"
    f.write_text("[Service]\nExecStart=/usr/bin/x\n")  # only warnings/info
    assert cli.main([str(f)]) == 0
    assert cli.main([str(f), "--fail-on", "warning"]) == 1
    assert cli.main([str(f), "--fail-on", "never"]) == 0


def test_min_severity_filters(files, capsys):
    cli.main([str(files[0]), "--min-severity", "error", "--no-color"])
    out = capsys.readouterr().out
    assert "UL002" in out and "UL010" not in out


def test_ignore_rules(files, capsys):
    code = cli.main([str(files[0]), "--ignore", "UL002", "--no-color"])
    assert code == 0
    assert "UL002" not in capsys.readouterr().out


def test_json_output(files, capsys):
    cli.main([str(files[0]), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["files"][0]["path"].endswith("bad.service")
    assert any(f["rule"] == "UL002" for f in data["files"][0]["findings"])


def test_directory_is_scanned(files, capsys):
    cli.main([str(files[0].parent), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert len(data["files"]) == 2


def test_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(BAD))
    assert cli.main(["-", "--no-color"]) == 1
    assert "<stdin>" in capsys.readouterr().out


def test_missing_file_exits_two(capsys):
    assert cli.main(["/nonexistent/x.service"]) == 2
    assert "no such file" in capsys.readouterr().err


def test_list_and_explain(capsys):
    assert cli.main(["--list-rules"]) == 0
    assert "UL003" in capsys.readouterr().out
    assert cli.main(["--explain", "ul003"]) == 0
    assert "shell" in capsys.readouterr().out.lower()
    assert cli.main(["--explain", "NOPE"]) == 2


def test_no_paths_is_usage_error():
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 2
