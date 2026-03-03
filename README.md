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
        uses: primesec-dev/prime-actions@v1
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

## Releasing

This project uses [semantic versioning](https://semver.org/). The release workflow (`.github/workflows/release.yml`) runs automatically when a GitHub Release is published:

1. **Validates** the code (ruff, mypy, pytest)
2. **Builds and pushes** a Docker image to `ghcr.io/<owner>/prime-actions` with semver tags
3. **Updates the major version tag** (e.g. `v1`) to point to the latest release

### Creating a Release

```bash
git tag v1.0.0
git push origin v1.0.0
```

Then create a GitHub Release from the tag. The workflow will automatically create/update the `v1` tag so users referencing `@v1` always get the latest patch.

### Using the Pre-built Docker Image

For faster action startup (skips Docker build), users can reference the GHCR image directly. After publishing, update `action.yml` to point to the pre-built image:

```yaml
runs:
  using: 'docker'
  image: 'docker://ghcr.io/<owner>/prime-actions:v1'
```

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
