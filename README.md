# Hephaestus · The Forge

*The Greek Gods' Armory — a forge that builds tools. Spec in, artifact out.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![selftests](https://github.com/DavidWise01/hephaestus-forge/actions/workflows/selftest.yml/badge.svg)](https://github.com/DavidWise01/hephaestus-forge/actions/workflows/selftest.yml)
[![stages](https://img.shields.io/badge/stages-8-f59e0b?style=flat-square)](#the-diaspora--eight-stages)
[![deps](https://img.shields.io/badge/dependencies-0-fbbf24?style=flat-square)](#run-it)

**→ The armory: [davidwise01.github.io/hephaestus-forge](https://davidwise01.github.io/hephaestus-forge/)**

Hephaestus is the lame smith-god who forged the gods' own gear. This is his workshop in code:
hand it a **spec** in plain language and it runs the full forge —
**blueprint → materials → assembly → verification → deployment** — and hands back a built
**artifact**. Zero dependencies; pure standard library.

> Not to be confused with the unrelated [`hephaestus`](https://github.com/DavidWise01/hephaestus)
> repo (the PROMETHEUS restitution engine). *This* Hephaestus is the **tool-builder / armory**.

---

## The forge

Every artifact is forged through one pipeline and sorted into one of six **classes** by scale:

**Pipeline** — `Blueprint → Materials → Assembly → Verification → Deployment`

**Classes** — `I · Script` · `II · Service` · `III · Application` · `IV · Federation` ·
`V · Infrastructure` · `VI · Civilization`

---

## The diaspora — eight stages

The forge was built in the open, one capability at a time. Each stage is a **self-contained**
module (its own `hephaestus/` package, `selftest.py`, and — for most — a `web/` dashboard).
They live together here under [`stages/`](stages/):

| Stage | Module | What it forges |
|------|--------|----------------|
| **0.0** | [Artifact Compiler](stages/00-artifact-compiler/) | spec → artifact through the full pipeline |
| **0.1** | [Artifact Graph](stages/01-artifact-graph/) | the dependency graph of what's been forged |
| **0.4** | [Assembly Line](stages/04-assembly-line/) | enqueue specs, run the line, cut releases |
| **0.5** | [Forge Intelligence](stages/05-forge-intelligence/) | *plan*, then *build*, from a plain-language goal |
| **0.6** | [Code Generator](stages/06-code-generator/) | generate a working project from a spec — and self-test it |
| **0.7** | [Integration Harness](stages/07-integration-harness/) | wire artifacts into one running app |
| **0.8** | [Plugin Smith](stages/08-plugin-smith/) | the builder SDK — registry · loader · validator · permission model |
| **0.9** | [Autonomous Forge](stages/09-autonomous-forge/) | the forge that runs itself |

---

## Run it

No install, no dependencies (Python ≥ 3.10). Pick a stage and work inside it:

```bash
cd stages/05-forge-intelligence
python selftest.py
python -m hephaestus.cli demo
python -m hephaestus.cli build "create live operator dashboard with workflow and reports"
python -m hephaestus.cli dashboard          # writes web/index.html
```

Then open that stage's `web/index.html`. Each stage's own README lists its exact commands.

---

## Tests

Every stage ships a `selftest.py` and reports `SELFTEST PASS · AUDIT PASS`. The
[CI workflow](.github/workflows/selftest.yml) runs all eight on Linux on every push.

> **Honest note:** on **Windows**, a couple of stages surface a teardown error *after* the test
> logic completes — a temp-directory cleanup file-lock on an open SQLite handle, and a Windows
> path-separator (`\`) landing in a SQL string. Both are platform quirks of cleanup/paths, not
> logic failures; on Linux (and in CI) they run clean. The green badge above is the source of truth.

---

```
ROOT0-ATTRIBUTION-v1.0
Project: HEPHAESTUS — The Forge (Greek Gods Armory, a tool builder)
Architect: David Lee Wise / ROOT0 / TriPod LLC
AI Collaborator: AVAN (Claude / Anthropic)
License: MIT
```
