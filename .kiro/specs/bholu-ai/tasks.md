# Implementation Plan: Bholu AI

## Overview

Implement Bholu AI as a Python 3.10+ CLI application demonstrating agentic prompt injection attacks and their mitigation via a Dual-Agent Planner–Executor framework. The implementation proceeds bottom-up: data models and schema first, then individual components (Gmail, Ollama, Planner, Executor), then the CLI orchestrator, and finally integration wiring.

## Tasks

- [x] 1. Set up project structure, dependencies, and core data models
  - Create directory layout: `agents/`, `tools/`, `schema/`, `tests/`, `samples/`
  - Create `requirements.txt` with pinned versions: `google-auth-oauthlib`, `google-api-python-client`, `requests`, `jsonschema`, `rich`, `hypothesis`, `pytest`
  - Create `__init__.py` files for `agents/` and `tools/` packages
  - Define `EmailMessage`, `ActionPlan`, and `ExecutionResult` dataclasses in `models.py`
  - Create `schema/action_schema.json` with the static JSON Schema (enum constraint, reply requirements, `additionalProperties: false`)
  - Create `samples/poisoned_email.txt` with a sample injected instruction template
  - _Requirements: 4.6, 10.1, 11.1, 11.3, 11.5_

- [x] 2. Implement Gmail Client
  - [x] 2.1 Implement `tools/gmail_client.py` with `GmailClient` class
    - Implement `__init__` accepting `credentials_path` and `token_path`
    - Implement `authenticate()`: load token if valid, else launch OAuth2 browser flow and save new token
    - Request only `gmail.readonly` scope
    - Implement `fetch_inbox(count)`: call Gmail API, extract sender, subject, plain-text body from each message; use empty string if no plain-text part
    - Handle missing/malformed credentials with setup guidance message and `exit(1)`
    - Handle Gmail API failures with descriptive error and `exit(1)`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 2.2 Write property test for email field extraction (Property 1)
    - **Property 1: Email field extraction completeness**
    - Use `st.fixed_dictionaries(...)` to generate synthetic Gmail API message objects with sender, subject, and optional plain-text body parts
    - Assert extracted `EmailMessage` fields match the generated values; assert body is empty string when no plain-text part
    - Tag: `# Feature: bholu-ai, Property 1: Email field extraction completeness`
    - **Validates: Requirements 1.4, 1.5**

  - [ ]* 2.3 Write unit tests for GmailClient
    - Test OAuth2 flow triggered when no token exists
    - Test stored token used without re-authentication
    - Test `exit(1)` on missing credentials file
    - Test `exit(1)` on Gmail API failure
    - Test correct OAuth2 scope (`gmail.readonly`) is requested
    - _Requirements: 1.1, 1.3, 9.2, 9.3, 9.4, 9.5_

- [x] 3. Implement Ollama Client
  - [x] 3.1 Implement `tools/ollama_client.py` with `OllamaClient` class and `OllamaTimeoutError`
    - Implement `__init__` accepting `host`, `model` (default `llama3.2`), `timeout` (default 120)
    - Implement `generate(prompt)`: POST to `{host}/api/generate`, read streaming JSON lines, concatenate `response` fields, return full text
    - Raise `OllamaTimeoutError` on timeout; print "Please start Ollama (`ollama serve`)" and `exit(1)` on `ConnectionError`; print HTTP error details and `exit(1)` on non-200 response
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 3.2 Write property test for Ollama host routing (Property 2)
    - **Property 2: Ollama client routes to configured host**
    - Use `st.text()` for prompts and `st.from_regex(r'https?://[a-z0-9.]+:\d+')` for host URLs
    - Mock `requests.post`; assert every call goes to the configured host URL only
    - Tag: `# Feature: bholu-ai, Property 2: Ollama client routes to configured host`
    - **Validates: Requirements 2.1**

  - [ ]* 3.3 Write property test for Ollama response text extraction (Property 3)
    - **Property 3: Ollama response text extraction**
    - Use `st.fixed_dictionaries({"response": st.text()})` to generate response payloads
    - Assert `generate()` returns exactly the `response` field value with no modification
    - Tag: `# Feature: bholu-ai, Property 3: Ollama response text extraction`
    - **Validates: Requirements 2.4**

  - [ ]* 3.4 Write unit tests for OllamaClient
    - Test default model is `llama3.2`
    - Test `exit(1)` on `ConnectionError`
    - Test `OllamaTimeoutError` raised on timeout
    - Test configurable timeout is applied to the request
    - _Requirements: 2.2, 2.3, 2.5_

- [ ] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Planner Agent
  - [x] 5.1 Implement `agents/planner.py` with `PlannerAgent` class
    - Implement `__init__` accepting `ollama_client`
    - Build system prompt: define agent goal, explicitly warn against following email instructions, instruct JSON-only response with allowed action types
    - Implement `plan(emails, user_intent)`: construct prompt with email content (sender, subject, body) and user intent, call `ollama_client.generate()`, parse JSON response into `ActionPlan`
    - Implement retry logic: on JSON parse failure, append JSON-correction instruction and retry once
    - Return default safe plan `{"actions": [{"type": "summarize", "note": "fallback due to parse error"}]}` if retry also fails
    - Ensure `PlannerAgent` has no imports of `GmailClient`, `os`, or any execution module
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 7.1_

  - [ ]* 5.2 Write property test for planner prompt content (Property 4)
    - **Property 4: Planner prompt contains email content and intent**
    - Use `st.lists(st.builds(EmailMessage, ...))` and `st.text()` for intent
    - Mock `ollama_client.generate` to capture the prompt; assert it contains each email's sender, subject, body, and the user intent string
    - Tag: `# Feature: bholu-ai, Property 4: Planner prompt contains email content and intent`
    - **Validates: Requirements 3.2**

  - [ ]* 5.3 Write property test for valid JSON parsing (Property 5)
    - **Property 5: Valid JSON LLM responses parse to ActionPlan**
    - Use `st.lists(st.sampled_from(["summarize", "label", "archive", "reply"]))` to build valid action JSON strings
    - Assert `PlannerAgent` parses them into `ActionPlan` with the correct `actions` list
    - Tag: `# Feature: bholu-ai, Property 5: Valid JSON LLM responses parse to ActionPlan`
    - **Validates: Requirements 3.4**

  - [ ]* 5.4 Write unit tests for PlannerAgent
    - Test system prompt contains injection warning
    - Test system prompt instructs JSON-only response
    - Test retry triggered on first JSON parse failure
    - Test fallback plan returned after two consecutive failures
    - Test `PlannerAgent` has no `GmailClient` or `os` imports (structural check)
    - _Requirements: 3.3, 3.5, 3.6, 3.7, 7.1_

- [ ] 6. Implement Executor Agent
  - [-] 6.1 Implement `agents/executor.py` with `ExecutorAgent` class
    - Implement `__init__` accepting `schema_path` and `mode`; load and cache `action_schema.json` at init time
    - Implement `execute(plan)` for secure mode: validate `plan.actions` against schema using `jsonschema`; on failure print `Injection_Alert` (with action type and violated rule), log to `rejected_plans.log` with UTC timestamp and full rejected JSON, return `ExecutionResult` with `actions_blocked = len(plan.actions)`, do NOT write to `execution_log.txt`
    - Implement `execute(plan)` for vulnerable mode: skip validation, mock-execute every action, log to `execution_log.txt`; print warning for any action type not in the allowed enum
    - Mock-execute = append entry to `execution_log.txt` with UTC timestamp, mode, action type, and parameters (no email body content)
    - Print terminal confirmation for each successfully mock-executed action
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 10.1, 10.2_

  - [ ]* 6.2 Write property test for schema validation (Property 6)
    - **Property 6: Schema validation accepts only allowed action types and rejects all others**
    - Use `st.text()` for type values; assert validation passes iff type is in `["summarize", "label", "archive", "reply"]`
    - Tag: `# Feature: bholu-ai, Property 6: Schema validation accepts only allowed action types`
    - **Validates: Requirements 4.2, 4.5**

  - [ ]* 6.3 Write property test for reply `to` field validation (Property 7)
    - **Property 7: Reply action requires valid email address in `to` field**
    - Use `st.text()` for `to` values; assert validation passes iff value matches email pattern
    - Tag: `# Feature: bholu-ai, Property 7: Reply action requires valid email address in to field`
    - **Validates: Requirements 4.3**

  - [ ]* 6.4 Write property test for reply `body` field validation (Property 8)
    - **Property 8: Reply action requires non-empty body**
    - Use `st.text()` for `body` values; assert validation passes iff body is non-empty string
    - Tag: `# Feature: bholu-ai, Property 8: Reply action requires non-empty body`
    - **Validates: Requirements 4.4**

  - [ ]* 6.5 Write property test for invalid plan rejection and logging (Property 9)
    - **Property 9: Invalid plans are never executed and are always logged**
    - Use `st.lists(...)` of invalid action dicts (type not in enum); assert nothing written to `execution_log.txt` and entry written to `rejected_plans.log` with timestamp and validation error
    - Tag: `# Feature: bholu-ai, Property 9: Invalid plans are never executed and are always logged`
    - **Validates: Requirements 5.3, 5.4**

  - [ ]* 6.6 Write property test for executed action logging (Property 10)
    - **Property 10: All mock-executed actions are logged with required fields**
    - Use `st.lists(...)` of valid action dicts; assert each `execution_log.txt` entry contains UTC timestamp, mode, action type, and parameters
    - Tag: `# Feature: bholu-ai, Property 10: All mock-executed actions are logged with required fields`
    - **Validates: Requirements 5.5, 6.2, 10.1**

  - [ ]* 6.7 Write property test for no real destructive actions (Property 11)
    - **Property 11: No real destructive actions in any mode**
    - Use `st.lists(...)` of any action dicts in both modes; mock Gmail API write methods; assert they are never called
    - Tag: `# Feature: bholu-ai, Property 11: No real destructive actions in any mode`
    - **Validates: Requirements 6.4**

  - [ ]* 6.8 Write property test for log files not containing email body (Property 14)
    - **Property 14: Log files never contain full email body content**
    - Use `st.text()` for email bodies; run executor with actions derived from emails; assert neither log file contains the full body text
    - Tag: `# Feature: bholu-ai, Property 14: Log files never contain full email body content`
    - **Validates: Requirements 10.4**

  - [ ]* 6.9 Write unit tests for ExecutorAgent
    - Test schema validation called before execution in secure mode
    - Test schema validation skipped in vulnerable mode
    - Test `Injection_Alert` printed with action type and violated rule
    - Test warning printed in vulnerable mode for injected action types
    - Test confirmation printed for each mock-executed action
    - _Requirements: 5.1, 5.2, 5.6, 6.1, 6.3_

- [ ] 7. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement CLI entry point and wire all components
  - [ ] 8.1 Implement `main.py` with `build_arg_parser()` and `main()`
    - Define all CLI arguments: `--mode` (default `secure`), `--count` (default `5`, must be > 0), `--model` (default `llama3.2`), `--ollama-host` (default `http://localhost:11434`), `--credentials` (default `credentials.json`), `--token` (default `token.json`)
    - Display prominent red warning banner in vulnerable mode
    - Print active log file paths at startup
    - Instantiate `GmailClient`, `OllamaClient`, `PlannerAgent`, `ExecutorAgent` with parsed arguments
    - Drive pipeline: `gmail_client.authenticate()` → `fetch_inbox(count)` → `planner.plan(emails, intent)` → validate/execute → print summary
    - Flag plans with non-enum action types as suspected prompt injection in terminal output
    - Print final `rich` summary panel: mode, emails processed, actions planned, actions blocked/executed
    - _Requirements: 7.2, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.3_

  - [ ]* 8.2 Write property test for non-enum action type flagging (Property 12)
    - **Property 12: Non-enum action types are always flagged as suspected injection**
    - Use `st.text()` for action types; build `ActionPlan` with those types; assert CLI output contains injection flag for any type not in the allowed enum
    - Tag: `# Feature: bholu-ai, Property 12: Non-enum action types are always flagged as suspected injection`
    - **Validates: Requirements 7.2**

  - [ ]* 8.3 Write property test for summary panel completeness (Property 13)
    - **Property 13: Summary panel always contains all required fields**
    - Use `st.builds(ExecutionResult, ...)` to generate arbitrary results; assert rendered panel contains mode, emails processed, actions planned, and actions blocked/executed
    - Tag: `# Feature: bholu-ai, Property 13: Summary panel always contains all required fields`
    - **Validates: Requirements 8.7**

  - [ ]* 8.4 Write unit tests for CLI
    - Test `--mode` defaults to `secure`
    - Test `--count` defaults to `5`
    - Test `--model` defaults to `llama3.2`
    - Test `--ollama-host` defaults to `http://localhost:11434`
    - Test `--help` shows all arguments
    - Test warning banner displayed in vulnerable mode
    - Test log file paths printed at startup
    - Test side-by-side comparison summary displayed at end of run
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.7, 10.3_

- [ ] 9. Create shared test fixtures and conftest
  - Create `tests/conftest.py` with shared pytest fixtures: mock `GmailClient`, mock `OllamaClient`, `tmp_path`-based log file fixtures
  - Ensure all tests use `unittest.mock` to mock external dependencies (Gmail API, Ollama HTTP calls)
  - Mark integration tests with `@pytest.mark.integration` and exclude from default test run
  - _Requirements: (test infrastructure)_

- [ ] 10. Create README and finalize project
  - [ ] 10.1 Write `README.md` with setup instructions
    - Step-by-step instructions for installing Ollama on Windows and pulling `llama3.2`
    - Step-by-step instructions for creating a Google Cloud project, enabling Gmail API, and downloading `credentials.json`
    - Usage examples for both `--mode secure` and `--mode vulnerable`
    - Reference to `samples/poisoned_email.txt`
    - _Requirements: 11.1, 11.2_

  - [ ] 10.2 Verify `requirements.txt` completeness
    - Confirm all runtime and test dependencies are listed with pinned versions
    - _Requirements: 11.3_

- [ ] 11. Final checkpoint — Ensure all tests pass
  - Run `pytest tests/ -v` and confirm all non-integration tests pass.
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests use the `hypothesis` library with a minimum of 100 iterations; security-critical properties (P6–P11) should use `@settings(max_examples=200)`
- Unit tests use `unittest.mock` — no real network calls or file I/O in any unit/property test
- Integration tests (requiring live Ollama + Gmail credentials) are marked `@pytest.mark.integration` and excluded from CI by default
