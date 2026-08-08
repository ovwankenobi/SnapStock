# Public Market POS — Technical Docs (MkDocs site)

Developer-facing documentation: architecture, data-flow diagrams, API reference, and database
schema. Built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) and native
Mermaid diagram rendering (`pymdownx.superfences`).

This is a separate deliverable from `/docs-manuals` (the plain-Markdown seller/buyer user
manuals) — do not mix the two. This site is for developers; `/docs-manuals` is for end users and
is written to convert cleanly to Word, not to be built as a site.

## Setup

```bash
cd docs-technical
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## Preview locally

```bash
mkdocs serve
```

Serves at `http://127.0.0.1:8000` with live reload as you edit files under `docs/`.

## Build a static site

```bash
mkdocs build
```

Outputs static HTML to `site/` (gitignored — regenerate it, don't commit it).

## Deploy

- **GitHub Pages** (if this repo has a GitHub remote): `mkdocs gh-deploy` builds and pushes
  `site/` to the `gh-pages` branch in one step.
- **Anywhere else**: run `mkdocs build` and serve the resulting `site/` directory as static
  files (any static host / nginx / S3, etc.) — no server-side component is required.
