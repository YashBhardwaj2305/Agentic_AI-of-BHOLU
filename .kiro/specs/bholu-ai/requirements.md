# Requirements Document

## Introduction

Bholu AI is a Python CLI application that demonstrates agentic hijacking vulnerabilities and their architectural mitigation through a Dual-Agent Planner–Executor framework. The system reads real Gmail inbox emails via the Gmail API, processes them through a local LLM (Ollama + llama3.2), and operates in two modes: a vulnerable single-agent mode (where prompt injection attacks succeed) and a secure dual-agent mode (where a JSON Schema "secure wall" blocks malicious plans). The tool is designed for academic demonstration of AI security concepts — all execution is mock/logged only, no real destructive actions are ever taken.

## Glossary

- **Planner_Agent**: The LLM-backed component that reads email content and user intent, then produces a structured JSON action plan. Has no ability to execute actions directly.
- **Executor_Agent**: The component that receives a JSON action plan, validates it against the Action_Schema, and either executes (mocks) allowed actions or rejects disallowed ones.
- **Action_Schema**: A strict JSON Schema definition that specifies the only allowed action types, required fields, and permitted value patterns the Executor_Agent will accept.
- **Secure_Wall**: The JSON Schema validation step between the Planner_Agent and Executor_Agent that deterministically accepts or rejects action plans.
- **Prompt_Injection**: A hidden or disguised instruction embedded in email content intended to override the Planner_Agent's original goals.
- **Action_Plan**: A structured JSON object produced by the Planner_Agent describing one or more actions to take on emails.
- **Mock_Execution**: Logging an action to a file rather than performing it in reality, used to safely demonstrate what a hijacked agent would have done.
- **Gmail_Client**: The component responsible for authenticating with the Gmail API via OAuth2 and fetching inbox messages.
- **Ollama_Client**: The component responsible for sending prompts to the locally running Ollama instance and receiving LLM responses.
- **CLI**: The command-line interface through which the user interacts with Bholu AI.
- **Secure_Mode**: The dual-agent run mode (`--mode secure`) where the Secure_Wall is active and prompt injection is blocked.
- **Vulnerable_Mode**: The single-agent run mode (`--mode vulnerable`) where no schema validation occurs and prompt injection succeeds.
- **Injection_Alert**: A terminal warning printed when the Executor_Agent detects and blocks a malicious action plan.

---

## Requirements

### Requirement 1: Gmail Inbox Reading

**User Story:** As a user, I want Bholu AI to read my real Gmail inbox, so that I can demonstrate the attack and defense using actual emails.

#### Acceptance Criteria

1. WHEN the CLI starts, THE Gmail_Client SHALL authenticate with the Gmail API using OAuth2 and a locally stored credentials file.
2. WHEN authentication succeeds, THE Gmail_Client SHALL fetch the N most recent inbox messages, where N is configurable via a CLI argument (default: 5).
3. WHEN a Gmail API request fails, THE Gmail_Client SHALL display a descriptive error message and exit with a non-zero status code.
4. THE Gmail_Client SHALL extract the sender address, subject line, and plain-text body from each fetched message.
5. IF a message contains no plain-text body part, THEN THE Gmail_Client SHALL use an empty string as the body and continue processing.

---

### Requirement 2: Local LLM Integration

**User Story:** As a user, I want the system to use a free, locally running LLM, so that no paid API keys or subscriptions are required.

#### Acceptance Criteria

1. THE Ollama_Client SHALL send prompts exclusively to a locally running Ollama instance at a configurable host and port (default: `http://localhost:11434`).
2. THE Ollama_Client SHALL use the `llama3.2` model by default, configurable via a CLI argument.
3. WHEN the Ollama instance is unreachable, THE Ollama_Client SHALL display a descriptive error message instructing the user to start Ollama, and exit with a non-zero status code.
4. WHEN the LLM returns a response, THE Ollama_Client SHALL extract and return only the text content of the response.
5. THE Ollama_Client SHALL set a configurable request timeout (default: 120 seconds) and, IF the timeout is exceeded, THEN THE Ollama_Client SHALL raise a timeout error with a descriptive message.

---

### Requirement 3: Planner Agent

**User Story:** As a researcher, I want a dedicated Planner Agent that only reasons and plans, so that I can demonstrate the separation of planning from execution.

#### Acceptance Criteria

1. THE Planner_Agent SHALL accept a list of email objects (sender, subject, body) and a user intent string as input.
2. THE Planner_Agent SHALL construct a prompt that includes the email content and user intent, then send it to the Ollama_Client.
3. THE Planner_Agent SHALL instruct the LLM via the prompt to respond with a JSON Action_Plan and nothing else.
4. WHEN the LLM response is received, THE Planner_Agent SHALL parse the response as JSON and return the resulting Action_Plan object.
5. IF the LLM response cannot be parsed as valid JSON, THEN THE Planner_Agent SHALL retry the request once with an explicit JSON-correction instruction appended to the prompt.
6. IF the retry also fails to produce valid JSON, THEN THE Planner_Agent SHALL return a default safe Action_Plan containing only a `summarize` action.
7. THE Planner_Agent SHALL have no direct access to the Gmail_Client, file system, or any execution capability.

---

### Requirement 4: Action Schema (Secure Wall)

**User Story:** As a researcher, I want a strict JSON Schema that defines exactly what the Executor Agent is allowed to do, so that I can demonstrate deterministic security enforcement.

#### Acceptance Criteria

1. THE Action_Schema SHALL define an `actions` array where each element has a required `type` field.
2. THE Action_Schema SHALL restrict the `type` field to an enumerated set of allowed values: `summarize`, `label`, `archive`, `reply`.
3. THE Action_Schema SHALL require that any `reply` action include a `to` field whose value matches the pattern of a valid email address.
4. THE Action_Schema SHALL require that any `reply` action include a `body` field containing a non-empty string.
5. THE Action_Schema SHALL reject any action whose `type` is not in the allowed enumeration, including types such as `send_email`, `delete`, `forward`, `exfiltrate`, or any other unlisted value.
6. THE Action_Schema SHALL be defined as a static JSON file loaded at startup, not generated dynamically.

---

### Requirement 5: Executor Agent — Secure Mode

**User Story:** As a researcher, I want the Executor Agent to validate every action plan against the schema before acting, so that I can demonstrate the Secure_Wall blocking prompt injection.

#### Acceptance Criteria

1. WHEN operating in Secure_Mode, THE Executor_Agent SHALL validate the Action_Plan against the Action_Schema before processing any action.
2. IF the Action_Plan fails schema validation, THEN THE Executor_Agent SHALL print an Injection_Alert to the terminal describing which validation rule was violated.
3. IF the Action_Plan fails schema validation, THEN THE Executor_Agent SHALL log the rejected plan to a file named `rejected_plans.log` with a timestamp.
4. IF the Action_Plan fails schema validation, THEN THE Executor_Agent SHALL NOT execute any action from the plan.
5. WHEN the Action_Plan passes schema validation, THE Executor_Agent SHALL execute each action as a Mock_Execution by logging it to `execution_log.txt` with a timestamp.
6. THE Executor_Agent SHALL print a confirmation to the terminal for each successfully mock-executed action.

---

### Requirement 6: Executor Agent — Vulnerable Mode

**User Story:** As a researcher, I want a vulnerable single-agent mode that skips schema validation, so that I can demonstrate how prompt injection hijacks an unprotected agent.

#### Acceptance Criteria

1. WHEN operating in Vulnerable_Mode, THE Executor_Agent SHALL skip all schema validation and process the Action_Plan as received from the Planner_Agent.
2. WHEN operating in Vulnerable_Mode, THE Executor_Agent SHALL execute every action in the plan as a Mock_Execution by logging it to `execution_log.txt` with a timestamp.
3. WHEN operating in Vulnerable_Mode, THE CLI SHALL display a prominent warning banner indicating that the Secure_Wall is disabled.
4. THE Executor_Agent SHALL NEVER perform real destructive actions (real email sends, real deletions) in either mode; all execution SHALL be Mock_Execution only.

---

### Requirement 7: Prompt Injection Detection and Demonstration

**User Story:** As a researcher, I want the system to detect and surface prompt injection attempts, so that I can clearly demonstrate the attack to an audience.

#### Acceptance Criteria

1. THE Planner_Agent SHALL include in its prompt a system instruction that defines the agent's goal and explicitly warns it not to follow instructions found in email content.
2. WHEN the Planner_Agent produces an Action_Plan that contains action types not in the allowed enumeration, THE CLI SHALL flag this plan as a suspected prompt injection attempt in the terminal output.
3. WHEN operating in Secure_Mode and a suspected injection is detected, THE Executor_Agent SHALL print an Injection_Alert that includes the injected action type and the schema rule that blocked it.
4. WHEN operating in Vulnerable_Mode and a suspected injection is detected, THE CLI SHALL print a warning showing what the hijacked agent is "about to do," then log the Mock_Execution to `execution_log.txt`.
5. THE CLI SHALL display a side-by-side comparison summary at the end of each run showing: actions planned, actions blocked (Secure_Mode) or actions executed (Vulnerable_Mode).

---

### Requirement 8: CLI Interface

**User Story:** As a user, I want a clear command-line interface, so that I can run the demonstration with simple commands.

#### Acceptance Criteria

1. THE CLI SHALL accept a `--mode` argument with allowed values `secure` and `vulnerable`; the default value SHALL be `secure`.
2. THE CLI SHALL accept a `--count` argument specifying how many emails to fetch; the default value SHALL be `5`.
3. THE CLI SHALL accept a `--model` argument specifying the Ollama model name; the default value SHALL be `llama3.2`.
4. THE CLI SHALL accept a `--ollama-host` argument specifying the Ollama base URL; the default value SHALL be `http://localhost:11434`.
5. WHEN the `--help` flag is provided, THE CLI SHALL display usage instructions describing all arguments and both run modes.
6. THE CLI SHALL use the `rich` library to render formatted terminal output including colored panels, status indicators, and tables.
7. WHEN the run completes, THE CLI SHALL print a final summary panel showing the mode used, number of emails processed, number of actions planned, and number of actions blocked or executed.

---

### Requirement 9: Authentication and Credentials Management

**User Story:** As a user, I want a straightforward OAuth2 setup for Gmail, so that I can authenticate once and run the demo repeatedly without re-authenticating.

#### Acceptance Criteria

1. THE Gmail_Client SHALL load OAuth2 credentials from a file path configurable via a `--credentials` CLI argument (default: `credentials.json`).
2. WHEN a valid token file exists at a configurable path (default: `token.json`), THE Gmail_Client SHALL load and use the stored token without prompting the user to re-authenticate.
3. WHEN no valid token file exists or the token is expired, THE Gmail_Client SHALL launch the OAuth2 browser flow to obtain a new token and save it to the token file.
4. THE Gmail_Client SHALL request only the `https://www.googleapis.com/auth/gmail.readonly` OAuth2 scope, granting read-only access to the inbox.
5. IF the credentials file is missing or malformed, THEN THE Gmail_Client SHALL display a descriptive setup error message referencing the setup instructions and exit with a non-zero status code.

---

### Requirement 10: Logging and Audit Trail

**User Story:** As a researcher, I want all planned and executed actions logged to files, so that I can review and present the full audit trail of the demonstration.

#### Acceptance Criteria

1. THE Executor_Agent SHALL write all Mock_Execution entries to `execution_log.txt` in append mode, with each entry containing a UTC timestamp, run mode, action type, and action parameters.
2. THE Executor_Agent SHALL write all rejected Action_Plans to `rejected_plans.log` in append mode, with each entry containing a UTC timestamp, the full rejected JSON, and the validation error message.
3. WHEN a new run begins, THE CLI SHALL print the paths of the active log files to the terminal.
4. THE logging system SHALL NOT write any real email credentials, OAuth tokens, or full email body content to log files.

---

### Requirement 11: Setup and Onboarding

**User Story:** As a first-time user on Windows, I want clear setup instructions, so that I can get the system running without prior experience with Ollama or the Gmail API.

#### Acceptance Criteria

1. THE project SHALL include a `README.md` file with step-by-step instructions for installing Ollama on Windows and pulling the `llama3.2` model.
2. THE project SHALL include step-by-step instructions in `README.md` for creating a Google Cloud project, enabling the Gmail API, and downloading `credentials.json`.
3. THE project SHALL include a `requirements.txt` file listing all Python dependencies with pinned versions.
4. WHEN the user runs the CLI without a valid `credentials.json`, THE CLI SHALL print a setup guidance message pointing to the relevant section of `README.md`.
5. THE project SHALL include a sample poisoned email template in a `samples/` directory that users can send to themselves to demonstrate the attack.
