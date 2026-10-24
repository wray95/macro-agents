# Macro Agents

A small standalone, Cindy-inspired five-agent deliberation CLI. Five roles independently propose answers, read **each other's** answers, challenge or revise their views, and a sixth *synthesis call* produces one response. This is **not** a fork or a drop-in integration with Cindy; Cindy's hosted login and private service are not reused. Inspired by Cindy's multi-harness orchestration concept ([source](https://github.com/makecindy/cindy)); this implementation is original and uses only Python's standard library.

## Run

Python 3.10+ required. No external Python dependencies are needed for direct use. Optionally install a shell command with `python3 -m pip install .` (this requires setuptools); then use `macro-agents` instead of `python3 orchestrator.py`. Choose one of Cindy's supported local CLI harnesses if you already have it installed and authenticated:

```sh
python3 orchestrator.py --backend claude "How should we design an onboarding flow?"
python3 orchestrator.py --backend codex --show-debate "How should we design an onboarding flow?"
```

Or use an OpenAI-compatible chat-completions provider with your **own** API key:

```sh
export AI_API_KEY='your-key'
export AI_MODEL='your-model'
# optional: export AI_BASE_URL='https://your-provider.example/v1'
python3 orchestrator.py --backend api --show-debate "How should we design an onboarding flow?"
```

Use `--rounds 0` for independent proposals only, or `--rounds 2` for a longer debate (max 3). Default is 1. One round costs **11 model calls** (5 proposals + 5 rebuttals + 1 synthesis); use a paid provider with care. Five calls per phase run concurrently. No tools or browsing are provided; claims are not automatically fact-checked. Multiple roles using one model are not truly independent models and debate cannot guarantee better answers.

Tests: `python3 -m unittest discover -s tests -v`.

## Shared memory

Store facts or preferences explicitly; **all five roles and the synthesizer receive the same relevant memory** on each run. It persists in a local SQLite file (`~/.macro-agents/memory.sqlite3` by default; use `--memory-file PATH` to change it).

```sh
python3 orchestrator.py --remember "Our product supports offline use"
python3 orchestrator.py --list-memory
python3 orchestrator.py --forget 1
python3 orchestrator.py --backend claude "How should our product onboard users?"
```

Memory is selected by keyword overlap (up to 8 entries / 3000 characters), not semantic search. No model-generated claims are saved automatically: only explicitly added notes persist. Avoid storing secrets or sensitive data; the local database is not encrypted. Review and delete outdated notes as needed.

## Compact competitive mode

The default debate now asks every role to challenge its strongest rival **by name** and improve its own proposal. The final call compares answers on correctness, relevance, feasibility and uncertainty, then synthesizes the strongest ideas. This is a *qualitative model judgment*, not an independent benchmark or guaranteed improvement. To keep runs smoother, agent responses are requested at ~120 words, API output is capped at 350 tokens, and each peer contribution passed to the next round is truncated to 900 characters. One debate round still makes 11 calls; `--rounds 0` makes 6 calls when cost and latency matter more than debate.

## Project status and limitations

The source, CLI, memory operations, package metadata, and automated tests are ready. Live answers require an installed/authenticated Claude or Codex CLI, or a configured compatible API; no credentials are bundled. The five agents are **roles**, not five distinct AI models. All roles share memory and use the same configured backend/model. Responses are bounded for speed, so very long answers may be truncated in later rounds. Keep memory factual and review it periodically; it is not automatically updated from conversations. For a production deployment, add authentication, rate limits, privacy controls, and provider-specific error handling.

## Recommended provider setup

**Recommended:** use an OpenAI-compatible API provider you already trust, with your own key and a low-cost model that supports chat completions. This works on machines without enough RAM to host a local model. Set credentials in your own terminal, never in a chat message or committed file. `--doctor` checks whether configuration is present without displaying the key:

```sh
export AI_API_KEY='paste-your-own-key-locally'
export AI_MODEL='a-chat-completions-model-you-have-access-to'
python3 orchestrator.py --doctor
python3 orchestrator.py --backend api --show-debate < challenge.txt
```

For a custom OpenAI-compatible endpoint, set `AI_BASE_URL` to its API root ending in `/v1`. For a Claude/Codex subscription-based workflow, install and authenticate the respective official CLI locally, then use `--backend claude` or `--backend codex`. The project cannot create accounts, provide API keys, or use Cindy's hosted credentials. Run `--rounds 0` for a six-call low-cost smoke test before a full 11-call debate.

## Freebuff interactive bridge

Freebuff 0.2.34 documents an **interactive terminal agent**, not a supported one-shot prompt/output interface. To use it without inventing an undocumented CLI API, generate one five-perspective prompt and paste it into Freebuff:

```sh
python3 orchestrator.py --freebuff-prompt "How should we launch?" > freebuff-prompt.txt
freebuff
# In Freebuff's terminal UI, paste the contents of freebuff-prompt.txt.
```

This bridge carries relevant shared memory and five competing roles into **one Freebuff conversation**. It is *not* five isolated concurrent calls and cannot automatically capture Freebuff's answer. Freebuff is a coding agent with possible file/tool access: review its permissions and privacy terms before sharing sensitive material. No authentication or Freebuff account is included in this project.

## Topic feedback and project context

Use `--memory-file project-memory.sqlite3` to load the curated summaries of the supplied card-game plans, Facebook exports, and crypto/stocks research goals. Raw CSVs are not pasted into every prompt. The two Statue Prank Kids exports overlap; their views must not be double-counted. These are user-provided source summaries, not verified market research.

```sh
python3 orchestrator.py --memory-file project-memory.sqlite3 --backend api --model YOUR_MODEL "Research a crypto project's risks"
python3 orchestrator.py --memory-file project-memory.sqlite3 --rate Critic crypto 5 "Flagged unsupported return claim"
python3 orchestrator.py --memory-file project-memory.sqlite3 --ratings crypto
```

Ratings are **explicit user feedback**, tracked separately by domain (`crypto`, `stocks`, `content`, `game`, `general`). They influence the contextual feedback shown to the agents on later runs; they do not fine-tune model weights or prove that an answer was correct. Agents challenge specific claims and evidence rather than winning by persuasion alone. Market research needs live price data and dated sources; none are bundled here. Do not make trades solely from agent outputs.

## Market research mode

```
export AI_MODEL=...            # plus AI_API_KEY, or use --backend claude/codex
python orchestrator.py --market "Where could gold, silver, crypto and future tech go if inflation cools?"
```

Five specialists (Macro Economist, Crypto Analyst, Equities & Future Tech Analyst, Metals & Commodities Analyst,
Risk Skeptic) debate over a live, timestamped data snapshot (CoinGecko, Stooq, FRED) and the synthesizer returns
base/bull/bear scenarios, catalysts and risk management. It never guarantees a winner; research only, not financial advice.

## Security

- Memories and feedback notes are encrypted at rest (Fernet/AES + HMAC); data dir is `0700`, files `0600`.
- Strongest: `export MACRO_AGENTS_PASSPHRASE=...` (scrypt-derived key, nothing secret stored on disk).
  Without it a random `.key` file is created beside the database.
- Encrypt older plaintext data: `python orchestrator.py --encrypt-existing`.
- API keys are read from the environment only; `AI_BASE_URL` must be https (localhost excepted).
- `.gitignore` blocks databases, keys and `.env`.
