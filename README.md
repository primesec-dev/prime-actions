# PR Password Scanner

A GitHub Action that scans pull request diffs for the word "password" and flags
occurrences with inline review comments. Posts a summary to the PR with total
line counts.

## Features

- Scans all added lines in PR diffs for "password" (case-insensitive)
- Posts inline review comments on flagged lines with "Remove it please :smile:"
- Adds a summary comment to the PR with total added lines and findings count
- Configurable timeout
- Handles pagination for large PRs (100+ files)

## Usage

Add this to your workflow file (e.g. `.github/workflows/password-scanner.yml`):

```yaml
name: PR Password Scanner
on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Scan for passwords
        id: scanner
        uses: primesec/prime-actions@v1
        with:
          timeout: '30'

      - name: Check results
        run: |
          echo "Total lines: ${{ steps.scanner.outputs.total-lines }}"
          echo "Findings: ${{ steps.scanner.outputs.password-findings }}"
```

## Inputs

| Input | Description | Required | Default |
| --- | --- | --- | --- |
| `timeout` | Timeout in seconds for the action to complete | No | `30` |
| `token` | GitHub token for API access | No | `${{ github.token }}` |

## Outputs

| Output | Description |
| --- | --- |
| `total-lines` | Total number of added lines in the PR |
| `password-findings` | Number of password occurrences found in added lines |

## How It Works

1. The action triggers on `pull_request` events
2. Lists all files changed in the PR via the GitHub API
3. Parses the unified diff patches to identify added lines
4. Scans added lines for the word "password" (case-insensitive)
5. Posts an inline review comment on each flagged line
6. Posts a summary comment with total line count and findings

## Development

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
uv sync --all-extras
```

### Run Tests

```bash
uv run pytest -v tests/
```

### Lint

```bash
uv run ruff check .
uv run ruff format --check .
```

### Type Check

```bash
uv run mypy src/
```

## License

MIT
