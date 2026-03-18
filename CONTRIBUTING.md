# Contributing to li-toolkit

Thanks for your interest in contributing! Here's how to get started.

## Development setup

1. Clone the repo
2. Install dependencies and run tests:

```bash
cd server
uv run pytest -v
```

## Making changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Add or update tests if applicable
4. Run `uv run pytest -v` to make sure all tests pass
5. Run `uv run ruff check .` to check for linting issues
6. Open a pull request

## What to contribute

Here are some areas where contributions are especially welcome:

- **Selector updates** — LinkedIn changes their DOM frequently. If you notice the extension stopped working, submit a PR updating the CSS selectors in `popup.js` and `content.js`.
- **New analytics** — ideas for new metrics or insights that would be useful for content creators.
- **MCP tool improvements** — better tool descriptions, new tools, or more useful output formats.
- **Bug fixes** — if something doesn't work as documented, please file an issue or fix it.
- **Localization** — the analytics engine currently detects Italian and English. Adding more languages to the stopword list and language detection would help international users.

## Reporting issues

- Check existing issues first to avoid duplicates
- Include steps to reproduce the problem
- For selector issues, include the output from the **Diagnostics** button in the extension

## Code style

- Python: follow the existing style, enforced by `ruff` (config in `pyproject.toml`)
- JavaScript: vanilla JS, no build tools, keep it simple

## Pull request guidelines

- Keep PRs focused — one change per PR
- Write a clear description of what changed and why
- Add tests for new server functionality
- Don't include personal data (database files, strategy files, etc.)
