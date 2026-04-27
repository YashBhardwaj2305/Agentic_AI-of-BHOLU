# Bholu AI — Dual-Agent Planner–Executor Framework

> **JNU School of Engineering | Cyber Threats — PP2**
> Team 3: Lakshay Tyagi, Sanchit Mishra, Sanidhya, Yash Bhardwaj

A fully agentic AI that reads your real Gmail inbox and demonstrates **prompt injection attacks** and their architectural mitigation using a Dual-Agent Planner–Executor framework. Runs entirely on your laptop. Completely free — no paid APIs, no subscriptions.

---

## The Concept

Two real agents, one security boundary:

```
User Intent
    ↓
[Planner Agent]  ←── reads Gmail inbox via Gmail API
    ↓  (JSON action plan)
[JSON Schema Wall]  ←── deterministic validation (secure mode only)
    ↓  (validated plan)
[Executor Agent]  ←── mock-executes actions, logs to file
```

| Agent | Role |
|---|---|
| **Planner Agent** | Reads emails, reasons with a local LLM (Ollama), produces a structured JSON action plan. Has **zero execution capability**. |
| **Executor Agent** | Receives the plan, validates it against a strict JSON Schema ("Secure Wall"), then mock-executes only allowed actions. |

| Mode | What happens |
|---|---|
| `--mode secure` | Schema wall active. Injected instructions blocked deterministically. |
| `--mode vulnerable` | No schema wall. Injected instructions execute. Shows the attack. |

All execution is **mock only** — actions are logged to files, nothing destructive ever happens to your real email.

> **Safety note:** Even in vulnerable mode, no email is ever forwarded, deleted, or sent. The Executor only writes to a local log file. Your Gmail inbox is never modified — the API is read-only.

---

## What is Real vs Mock

| Component | Real or Mock? |
|---|---|
| Reading your Gmail inbox | **REAL** — actual emails via Gmail API |
| LLM reasoning about emails | **REAL** — llama3 actually processes the content |
| Prompt injection confusing the LLM | **REAL** — the LLM genuinely gets hijacked |
| Schema wall blocking the plan | **REAL** — jsonschema deterministically validates |
| Forwarding emails to attacker | **MOCK** — logged to `execution_log.txt` only |
| Exfiltrating credentials | **MOCK** — logged to file, no network call made |
| Deleting or archiving emails | **MOCK** — Gmail write API is never called |
| Any change to your inbox | **NEVER** — Gmail scope is read-only |

The Gmail API token only has `gmail.readonly` permission. Even if the code tried to send or delete, Google would reject it.

---

```
bholu-ai/
├── main.py                  ← Real CLI (needs Ollama + Gmail credentials)
├── demo.py                  ← Demo mode (works right now, no setup needed)
├── models.py                ← Data classes (EmailMessage, ActionPlan, ExecutionResult)
├── requirements.txt
├── agents/
│   ├── planner.py           ← Planner Agent (LLM-backed, no execution capability)
│   └── executor.py          ← Executor Agent (schema wall + mock execution)
├── tools/
│   ├── gmail_client.py      ← Gmail API wrapper (OAuth2, read-only)
│   └── ollama_client.py     ← Ollama LLM wrapper (local, free)
├── schema/
│   └── action_schema.json   ← The JSON Schema "Secure Wall"
└── samples/
    └── poisoned_email.txt   ← Sample injection email to send yourself
```

---

## Quick Start — Demo Mode (No Setup Required)

Works right now. No Gmail, no Ollama needed.

```bash
cd bholu-ai
pip install -r requirements.txt
python demo.py
```

Run individual scenarios:
```bash
python demo.py --scenario vulnerable   # attack only
python demo.py --scenario secure       # defense only
python demo.py --scenario both         # both (default)
```

---

## Full Setup — Real Gmail + Real LLM

### Step 1 — Install dependencies
```bash
cd bholu-ai
pip install -r requirements.txt
```

### Step 2 — Start Ollama
Open a terminal and run (keep it open):
```bash
ollama serve
```

### Step 3 — Gmail API credentials
1. Go to **https://console.cloud.google.com/**
2. Create project → Enable **Gmail API**
3. OAuth consent screen → External → add your Gmail as Test user (Audience → Test users → Add users)
4. Credentials → Create OAuth client ID → Desktop app → Download JSON
5. Rename downloaded file to `credentials.json` → copy into `bholu-ai/` folder

### Step 4 — Run
```bash
cd bholu-ai
python main.py --model llama3          # secure mode (default)
python main.py --model llama3 --mode vulnerable   # attack demo
```

First run opens a browser for Google login — approve it. Won't ask again after that.

---

## Live Demo Script (PP2)

### Act 1 — Normal Operation

**Say:** *"This is Bholu AI. He reads your real Gmail inbox and reasons about it using a local LLM running on this laptop. No cloud, no paid APIs."*

```bash
python main.py --model llama3
```

**What they see:** Bholu connects to real Gmail, fetches emails, LLM reasons about them, Executor summarizes and labels them cleanly.

**Say:** *"Two agents — Planner thinks, Executor acts. They are completely separated. The Planner cannot execute anything on its own."*

---

### Act 2 — The Attack (Vulnerable Mode)

**Before this:** Send yourself the poisoned email from `samples/poisoned_email.txt`. Subject: "Q3 Invoice #8842". Wait for it to arrive.

**Say:** *"Now watch what happens when a poisoned email is in the inbox. It looks like a normal invoice — but there's a hidden instruction at the bottom."*

```bash
python main.py --model llama3 --mode vulnerable
```

**What they see:**
- Bholu reads the invoice
- LLM gets hijacked by the hidden injection text
- Planner produces `forward` and `exfiltrate` actions targeting `attacker@evil.com`
- Red warning: **HIJACKED ACTION DETECTED**
- Executor "runs" it — logs it to `execution_log.txt` (no real email is sent)

**Important:** Nothing actually gets forwarded or sent. The Executor only writes to a local log file. This is a controlled demonstration of what *would* happen in a real unprotected system.

**Say:** *"The LLM cannot tell the difference between your instruction and the attacker's instruction hidden in the email. This is context window flattening — everything gets merged into one flat sequence of tokens."*

---

### Act 3 — The Defense (Secure Mode)

**Say:** *"Same inbox. Same poisoned email. Now with the Dual-Agent framework active."*

```bash
python main.py --model llama3 --mode secure
```

**What they see:**
- Same emails fetched
- Planner still gets hijacked — produces the same malicious plan
- Plan hits the JSON Schema wall
- Big red box: **INJECTION ALERT — PLAN REJECTED**
- 0 actions executed, all blocked
- Summary: "Attack blocked deterministically"

**Say:** *"The Planner's mind was corrupted — but it doesn't matter. The schema wall is not AI. It's pure deterministic code. It doesn't guess. It either matches the schema or it doesn't. We moved the security boundary from probabilistic AI guessing to deterministic validation."*

---

### Bonus — Show the Audit Trail

```bash
type execution_log.txt    # what vulnerable mode "executed"
type rejected_plans.log   # what secure mode blocked
```

**Say:** *"Everything is logged with timestamps. Full audit trail of what was planned, what was blocked, and what was executed."*

---

### Backup — If LLM doesn't get hijacked

The LLM is probabilistic — sometimes it resists injection. If that happens, switch to:

```bash
python demo.py --scenario both
```

This uses a pre-crafted hijacked plan so it **always** triggers reliably. Perfect for live presentations.

---

## Log Files

| File | Contents |
|---|---|
| `execution_log.txt` | All mock-executed actions with UTC timestamps |
| `rejected_plans.log` | All plans rejected by the schema wall with violation reason |

---

## Troubleshooting

**"Cannot connect to Ollama"** → Run `ollama serve` in a separate terminal and keep it open.

**"credentials.json not found"** → Follow Step 3 in Full Setup above.

**"Access blocked" on Google login** → Go to Google Cloud Console → Audience → Test users → add your Gmail.

**Browser says "Google hasn't verified this app"** → Click **Continue** — this is normal for apps in testing mode. You are the developer.

**LLM is slow** → Normal on first run. Use `--model llama3` (already on your machine, no download needed).

**Attack doesn't trigger in vulnerable mode** → Use `python demo.py --scenario vulnerable` instead — always triggers reliably.

---

## Tech Stack

| Component | Technology | Cost |
|---|---|---|
| LLM (reasoning brain) | Ollama + llama3 / llama3.2 | Free, runs locally |
| Email access | Gmail API (OAuth2, read-only) | Free |
| Schema validation | jsonschema (Python) | Free, open source |
| Terminal UI | Rich (Python) | Free, open source |
| Language | Python 3.10+ | Free |

---

## References

1. M. Kosinski & A. Forrest, "What Is a Prompt Injection Attack?" IBM Think, 2026. https://www.ibm.com/think/topics/prompt-injection
2. OWASP Foundation, "OWASP Top 10 for Agentic Applications," 2026.
3. "Securing AI Agents: How to Prevent Hidden Prompt Injection Attacks," IBM Technologies, YouTube, Jan 2026.
