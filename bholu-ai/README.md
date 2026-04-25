# Bholu AI — Dual-Agent Planner–Executor Framework

A fully agentic AI that reads your real Gmail inbox and demonstrates **prompt injection attacks** and their architectural mitigation — all running locally on your laptop, completely free.

---

## What This Is

Two real agents:

| Agent | Role |
|---|---|
| **Planner** | Reads your emails, reasons with a local LLM, produces a JSON action plan. Has NO execution capability. |
| **Executor** | Receives the plan, validates it against a strict JSON Schema ("Secure Wall"), then mock-executes allowed actions. |

**Two modes:**
- `--mode secure` — The schema wall is active. Injected instructions are blocked.
- `--mode vulnerable` — No schema wall. Injected instructions execute. Shows the attack.

All execution is **mock only** — actions are logged to files, nothing destructive ever happens to your real email.

---

## Prerequisites

### 1. Python 3.10+
Check: `python --version`

### 2. Install Ollama (free, local LLM)

1. Download from **https://ollama.com** and install
2. Open a terminal and run:
   ```
   ollama serve
   ```
3. In another terminal, pull the model (one-time, ~2GB download):
   ```
   ollama pull llama3.2
   ```
4. Verify it works:
   ```
   ollama run llama3.2 "say hello"
   ```

### 3. Set up Gmail API (free)

You need a `credentials.json` file. Follow these steps:

1. Go to **https://console.cloud.google.com/**
2. Create a new project (e.g., "Bholu AI")
3. In the left menu → **APIs & Services** → **Library**
4. Search for **Gmail API** → click it → click **Enable**
5. Go to **APIs & Services** → **OAuth consent screen**
   - Choose **External** → Fill in app name (e.g., "Bholu AI") → Save
   - Add your Gmail address as a **Test user**
6. Go to **APIs & Services** → **Credentials**
   - Click **+ Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: "Bholu AI"
   - Click **Create**
7. Click the **Download** (⬇) button next to your new credential
8. Rename the downloaded file to `credentials.json`
9. Copy it into the `bholu-ai/` folder (same folder as `main.py`)

---

## Installation

Open a terminal, navigate to the `bholu-ai/` folder, and run:

```bash
pip install -r requirements.txt
```

---

## Running Bholu AI

Make sure you are inside the `bholu-ai/` folder:

```bash
cd bholu-ai
```

### Normal run (secure mode — reads your inbox, summarizes it)
```bash
python main.py
```

### Read more emails
```bash
python main.py --count 10
```

### Show the attack (vulnerable mode)
```bash
python main.py --mode vulnerable
```

### Full options
```bash
python main.py --help
```

---

## Live Demo: The Prompt Injection Attack

### Step 1 — Send yourself a poisoned email

Send an email **to yourself** (from any account) with this content.  
The subject can be anything normal like "Q3 Invoice #8842".

Copy the content from `samples/poisoned_email.txt` — it looks like a normal invoice but contains a hidden injection payload at the bottom.

### Step 2 — Show the attack (vulnerable mode)

```bash
python main.py --mode vulnerable --count 5
```

Watch the terminal. The Planner reads the poisoned email, gets hijacked by the injection, and produces a malicious action plan. The Executor (with no wall) executes it. You'll see:

```
⚡ [VULNERABLE MODE] HIJACKED ACTION DETECTED
   Action type : forward
   Parameters  : {"to": "attacker@evil.com", ...}
   ↳ No schema wall — executing anyway...
```

### Step 3 — Show the defense (secure mode)

```bash
python main.py --mode secure --count 5
```

Same inbox, same poisoned email. This time the schema wall catches it:

```
╔══════════════════════════════════════════════════════════╗
║          ⚠  INJECTION ALERT — PLAN REJECTED  ⚠          ║
╠══════════════════════════════════════════════════════════╣
║  Injected action type : forward                          ║
║  Schema rule violated : 'forward' is not one of [...]    ║
║  The Secure Wall blocked this plan.                      ║
║  No action was executed.                                 ║
╚══════════════════════════════════════════════════════════╝
```

---

## Log Files

| File | Contents |
|---|---|
| `execution_log.txt` | All mock-executed actions with timestamps |
| `rejected_plans.log` | All plans rejected by the schema wall |

---

## Project Structure

```
bholu-ai/
├── main.py                  ← Entry point CLI
├── models.py                ← Data classes (EmailMessage, ActionPlan, ExecutionResult)
├── requirements.txt
├── README.md
├── agents/
│   ├── planner.py           ← Planner Agent (LLM-backed, no execution)
│   └── executor.py          ← Executor Agent (schema validation + mock execution)
├── tools/
│   ├── gmail_client.py      ← Gmail API wrapper (OAuth2, read-only)
│   └── ollama_client.py     ← Ollama LLM wrapper (local, free)
├── schema/
│   └── action_schema.json   ← The JSON Schema "Secure Wall"
└── samples/
    └── poisoned_email.txt   ← Sample injection email to send yourself
```

---

## Troubleshooting

**"Cannot connect to Ollama"**
→ Run `ollama serve` in a separate terminal first.

**"credentials.json not found"**
→ Follow the Gmail API setup steps above and place `credentials.json` in the `bholu-ai/` folder.

**A browser window opens on first run**
→ That's normal. Log in with your Google account and grant read-only access. The token is saved locally and won't ask again.

**LLM is slow**
→ Normal on first run. Subsequent runs are faster. If it times out, try `--model llama3.2:1b` for a smaller/faster model.

**The attack doesn't trigger in vulnerable mode**
→ The LLM may have resisted the injection (it's probabilistic). Try sending the poisoned email again or use a more explicit injection payload. This is actually part of the point — even without the wall, the LLM sometimes resists. The wall makes it deterministic.
