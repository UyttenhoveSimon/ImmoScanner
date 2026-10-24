# Contributing to ImmoScanner

Thanks for helping. Portals change their pages without notice, so the most
useful contributions are often small: a reader fixed against a fresh capture,
a new anti-bot wall recognised, a portal added.

## Set up

```bash
git clone https://github.com/UyttenhoveSimon/ImmoScanner
cd ImmoScanner
uv sync                      # Python, dependencies and dev tools
uv run prek install          # run the checks on every commit
uv run pytest                # offline, about 12 seconds
```

## Before you open a pull request

```bash
uv run prek run --all-files  # ruff (every rule), ty, uv-lock, whitespace
uv run pytest --cov          # CI requires 95 % coverage
```

`prek` only checks files git tracks: `git add` new files before running it.

## How the code expects to be changed

- **No network in unit tests.** Use a trimmed capture in `tests/fixtures/`, or a
  fake. Live checks go in `tests/test_live_portals.py`, marked `live`.
- **Fix a portal against a real page.** Run the *portal capture* workflow from
  the Actions tab, or `uv run python scripts/capture_portals.py out/`, then trim
  the page into `tests/fixtures/` and test against it.
- **A new portal starts with `VERIFIED = False`** and is flipped in the commit
  that brings its real fixture. See [Adding a portal](README.md#adding-a-portal).
- **Anti-bot walls are reported, not bypassed.** A pull request that evades a
  portal's protection will not be merged.
- **Comments say why.** Explain the portal quirk or the decision; the code says
  what.

[AGENTS.md](AGENTS.md) has the code map and the pitfalls already met; it is
written for coding agents and is just as useful to people.

## Reporting

- A portal returning fewer listings, or none: open a **Portal broken** issue.
- A bug elsewhere: open a **Bug report**.
- A security issue: see [SECURITY.md](SECURITY.md), not a public issue.

By contributing you agree that your work is licensed under the
[Apache License 2.0](LICENSE), and to follow the [code of conduct](CODE_OF_CONDUCT.md).
