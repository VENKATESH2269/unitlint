# unitlint

A friendly linter for **systemd service unit files**. It finds mistakes that
systemd would silently ignore or reject, and tells you *how to fix each one*.

```console
$ unitlint examples/bad.service
examples/bad.service:6: error UL002 ExecStart= uses relative path 'bin/app'.
    fix: Use the full path, for example ExecStart=/opt/app/app
examples/bad.service:6: warning UL003 ExecStart= contains shell syntax ('|') but is not run by a shell.
    fix: Wrap it: ExecStart=/bin/sh -c '...your command...'
examples/bad.service:7: warning UL015 Unknown directive 'Restar' in [Service].
    fix: Did you mean 'Restart'?
examples/bad.service:8: warning UL014 MemoryLimit= is deprecated.
    fix: Use MemoryMax instead.
...
```

`systemd-analyze verify` checks that a unit loads, and `systemd-analyze
security` scores exposure. unitlint complements them by catching common
mistakes with plain-English explanations and concrete fixes, and it runs on any
machine without systemd installed (useful in CI).

## What it checks

| Rule  | Severity | What it catches |
|-------|----------|-----------------|
| UL000 | error    | Syntax problems (lines that are not `Key=Value`, text before a section) |
| UL001 | error    | Missing `ExecStart=` (except `Type=oneshot`) |
| UL002 | error    | Relative paths in `Exec*` lines such as `bin/app` |
| UL003 | warning  | Shell syntax (`\|`, `>`, `&&`, `$(...)`) in `Exec*` lines, which systemd does not run through a shell |
| UL004 | info     | No `[Install]` / `WantedBy=`, so `systemctl enable` does nothing |
| UL005 | info     | No `Restart=` policy for a long-running service |
| UL006 | warning  | `Restart=always` without `RestartSec=` (fast crash loops) |
| UL007 | info     | `Type=forking` without `PIDFile=` |
| UL008 | warning  | `Wants=network-online.target` without `After=network-online.target` |
| UL009 | warning  | Service runs as root |
| UL010-013 | info | Missing hardening: `NoNewPrivileges`, `ProtectSystem`, `PrivateTmp`, `ProtectHome` |
| UL014 | warning  | Deprecated directives (`MemoryLimit`, `CPUShares`, `StandardOutput=syslog`, ...) |
| UL015 | warning  | Misspelled directives (`Restar=` instead of `Restart=`) |
| UL016 | info     | Bare program name instead of a full path in `Exec*` lines |

Run `unitlint --list-rules` for the list, or `unitlint --explain UL003` for the
reasoning behind a rule.

## Install

```bash
git clone https://github.com/VENKATESH2269/unitlint.git
cd unitlint
pip install .
```

Python 3.9+, standard library only.

## Usage

```bash
unitlint myapp.service                    # one file
unitlint /etc/systemd/system              # every *.service in a directory
cat myapp.service | unitlint -            # from stdin
unitlint --json myapp.service             # machine-readable
unitlint --min-severity warning x.service # hide suggestions
unitlint --ignore UL009 UL013 x.service   # skip rules
unitlint --fail-on warning x.service      # stricter exit status
```

### Exit status

| Code | Meaning |
|------|---------|
| 0    | No findings at or above `--fail-on` (default: `error`) |
| 1    | At least one finding at or above `--fail-on` |
| 2    | Usage error or a file could not be read |

### Use it in CI

```yaml
- run: pip install unitlint
- run: unitlint --fail-on warning deploy/*.service
```

## A note on system units

System-provided units intentionally break some of these rules (many run as
root and skip hardening, and `getty` restarts immediately by design). unitlint
is meant for services *you write*, so expect findings if you run it on
`/usr/lib/systemd/system`. Use `--ignore` or `--min-severity` to tune it.

## Known limitations

- Only `.service` files are linted (not `.socket`, `.timer`, and so on yet).
- Typo detection uses a list of known directive names and only reports names
  that closely resemble a real directive, so it can miss typos and may not know
  directives added in very new systemd versions.
- It does not expand specifiers (`%h`), drop-in directories, or template
  instances.

## Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
pytest
```

## Building the snap

```bash
sudo snap install snapcraft --classic
snapcraft
sudo snap install --dangerous ./unitlint_0.1.0_amd64.snap
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). New rules are welcome.

## License

MIT, see [LICENSE](LICENSE).
