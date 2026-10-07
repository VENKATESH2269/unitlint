# Contributing to unitlint

Thanks for helping! The project is small, so the workflow is simple.

1. Fork the repository and create a branch.
2. `pip install -e ".[test]"` and run `pytest`.
3. Make your change and add tests.
4. Open a pull request explaining what changed and why.

## Adding a rule

1. Open `src/unitlint/rules.py`.
2. Write a function that takes a `UnitFile` and returns a list of
   `(line, message, hint)` tuples, and decorate it with
   `@rule("ULxxx", "short-name", severity, "why this matters")`.
3. Add a positive and a negative test in `tests/test_rules.py`.
4. Add a row to the rules table in `README.md`.

Guidelines:

- Prefer false negatives to false positives. A noisy linter gets ignored.
- Check new rules against real units (`unitlint /usr/lib/systemd/system`) and
  confirm they do not flag valid, common configurations.
- Every message should say what is wrong, and every hint how to fix it.
- Standard library only.

## Good first issues

- Lint `.socket` and `.timer` units.
- Add a SARIF output format for GitHub code scanning.
- Add rules for `Type=notify` without a notifying service, `KillMode=none`,
  or `ExecStartPre` using `PermissionsStartOnly`.
- Expand the known-directive list for newer systemd versions.
- Support drop-in directories (`foo.service.d/*.conf`).
- Add a `--config` file for per-project ignores.
- Add a man page.
