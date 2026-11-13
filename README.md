# 🛰️ Keplix

> **Status: 🚧 Active Development (Architecture & Foundation Phase)**  
> *Building a multi-agent harness that keeps LLMs locked in deterministic orbits.*

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Orchestration](https://img.shields.io/badge/orchestration-LangGraph-green.svg)](https://langchain-ai.github.io/langgraph/)
[![AST Engine](https://img.shields.io/badge/AST-Tree--sitter%20%2B%20NetworkX-teal.svg)](https://tree-sitter.github.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Most multi-agent demos are basically five LLMs in a group chat hallucinating about a codebase while silently burning through API credits.

**Keplix** is an open-source experiment in fixing that. I am currently designing and building a **contract-first, model-agnostic multi-agent orchestration harness**. Instead of letting agents ramble in unstructured prose and overwrite each other's files, the goal is to wrap non-deterministic models inside a rigid systems shell: a **LangGraph** state machine for dynamic fan-out, a **Tree-sitter** AST knowledge graph for code awareness and subgraph file locking, and disposable **Docker** sandboxes with automatic Git rollbacks.

Think of it less like a chatbot and more like mission control—currently under construction on the launchpad.

---

## 🧠 Core Design Principles (The Blueprint)

Here are the architectural decisions guiding how Keplix is being built from Day 1:

* **🪐 Contract-First Swarm, Not a Chatroom:** Agents won't pass bloated chat histories around. A Dynamic Supervisor drafts typed Pydantic/OpenAPI contracts, fans out isolated parallel workers via LangGraph's `Send()`, and reconciles outputs on a typed blackboard.
* **🌲 AST-Aware Code Engine (`CodeEngineProtocol`):** Built first in pure Python (`tree-sitter` + `networkx`) behind a strict protocol interface so the core orchestration ships fast. It maps symbol dependencies, calculates blast-radius impact, prunes noisy stack traces, and enforces **subgraph write-locks** so parallel workers never collide mid-flight—with a drop-in **Rust (`PyO3` / `maturin`)** acceleration backend planned for `v0.2`.
* **🔌 Model-Agnostic by Default:** Powered by LangChain's `BaseChatModel` factory and `keplix.toml` capability tiers—letting you pair Claude or GPT-4o for architecture, DeepSeek for heavy coding, Groq for fast linting, or local Ollama models offline.
* **🛡️ Sandboxed & Reversible:** Untrusted agent code runs inside ephemeral Docker containers bound to your workspace. Every edit is preceded by a `GitPython` checkpoint—if a worker breaks the build and blows its retry budget, Keplix reverts to the last green commit automatically.
* **🔐 Zero-Leak Credential Handling:** API keys live in your OS encrypted Keyring (or `.env`), never in `keplix.toml`, SQLite checkpoints, or telemetry traces. Missing a key mid-run triggers a clean LangGraph `interrupt()` prompt without losing state.

---

## 🏗️ Planned Architecture

```text
                        [ User Goal / Spec ]
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │      Dynamic Supervisor       │ ◄── Capability Tiers (keplix.toml)
                  │   (LangGraph + Pydantic v2)   │
                  └───────────────┬───────────────┘
                                  │ Command(goto=[Send(...), Send(...)])
                ┌─────────────────┴─────────────────┐
                ▼ (Isolated Context)                ▼ (Isolated Context)
      ┌───────────────────┐               ┌───────────────────┐
      │   Worker Agent A  │               │   Worker Agent B  │
      └─────────┬─────────┘               └─────────┬─────────┘
                │                                   │
                └─────────────────┬─────────────────┘
                                  ▼
          ┌───────────────────────────────────────────────┐
          │         Code Engine (CodeEngineProtocol)      │
          │  • Tree-sitter AST & NetworkX Blast-Radius    │
          │  • Subgraph Concurrency Write-Locks           │
          │  • Atomic Diff Patcher & Log Pruner           │
          │  • [v0.2] Drop-in Rust (PyO3) Acceleration    │
          └───────────────────────┬───────────────────────┘
                                  │
                                  ▼
          ┌───────────────────────────────────────────────┐
          │        Docker Sandbox + Git Guardrails        │
          │  • Ephemeral execution  • Auto-revert on fail │
          └───────────────────────────────────────────────┘
```

---

## 🎯 Target Developer Experience

Once the initial milestones land, spinning up a multi-agent build will look like this:

```bash
# 1. Clone and install dependencies with uv
git clone [https://github.com/your-username/keplix-ai.git](https://github.com/your-username/keplix-ai.git)
cd keplix-ai
uv sync

# 2. Initialize config and store API keys in your OS Keyring
uv run keplix init

# 3. Launch an orchestrated run
uv run keplix run --goal "Build a FastAPI + React weather dashboard with pytest suite"
```

### Target `keplix.toml` Config

```toml
[execution]
max_retries = 3
budget_usd = 2.50
sandbox_image = "python:3.12-slim"

[models.architect]
provider = "anthropic"
model_name = "claude-sonnet-4-5"

[models.coder]
provider = "deepseek"
model_name = "deepseek-chat"

[models.fast]
provider = "groq"
model_name = "llama-3.3-70b-versatile"
```

---

## 🗺️ Build Roadmap

- [x] **Phase 0 — Architecture & Spec:** `uv` workspace layout, `CodeEngineProtocol` interface, context-isolation model, and 3-tier secret flow
- [ ] **Phase 1 — Foundations & Sandbox:** `pydantic-settings` config loader, OS Keyring auth, and Docker runner with `GitPython` auto-checkpoints
- [ ] **Phase 2 — Python AST Code Engine:** `tree-sitter` symbol parser, `networkx` dependency & PageRank indexer, subgraph write-locks, and diff patcher
- [ ] **Phase 3 — LangGraph Orchestrator:** Dynamic Supervisor (`Command` + `Send()` fan-out), SQLite state persistence, and `interrupt()` HITL flows
- [ ] **Phase 4 — Tooling & Media Pipeline:** Scoped tool registry, headless Playwright demo recording, and Marp slide generation
- [ ] **Phase 5 — CLI & Trace Replayer:** `Typer` + `Rich` terminal UI, Langfuse telemetry hooks, and static React Flow trace viewer
- [ ] **v0.2 — Rust Systems Upgrade:** Native `PyO3` + `maturin` backend (`petgraph` + `tree-sitter`) swapping seamlessly behind `CodeEngineProtocol`

---

## 🤝 Following Along

This project is being built openly from scratch. Architecture notes, benchmarks, and design tradeoffs will be documented in `/docs` as each milestone ships. Feedback, issues, and architectural critiques are welcome!

## 📄 License

MIT — built for developers who prefer deterministic orbits over agentic chaos
