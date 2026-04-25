"""
Ollama Client — sends prompts to a locally running Ollama instance.
No paid API keys required. Runs entirely on the user's machine.
"""

import json
import sys

import requests


class OllamaTimeoutError(Exception):
    """Raised when the Ollama request exceeds the configured timeout."""
    pass


class OllamaClient:
    """Thin HTTP wrapper around the Ollama REST API."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: int = 120,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to Ollama and return the full text response.
        
        Uses the /api/generate endpoint which streams JSON lines.
        Concatenates all 'response' fields from the stream.
        """
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                stream=True,
                timeout=self.timeout,
            )
        except requests.exceptions.ConnectionError:
            print(
                "[ERROR] Cannot connect to Ollama.\n"
                "Please start Ollama by running: ollama serve\n"
                "If Ollama is not installed, download it from: https://ollama.com"
            )
            sys.exit(1)
        except requests.exceptions.Timeout:
            raise OllamaTimeoutError(
                f"Ollama request timed out after {self.timeout} seconds. "
                "Try increasing --timeout or using a smaller model."
            )

        if response.status_code != 200:
            print(
                f"[ERROR] Ollama returned HTTP {response.status_code}: {response.text[:200]}"
            )
            sys.exit(1)

        # Read streaming JSON lines and concatenate 'response' fields
        full_text = []
        try:
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        full_text.append(chunk.get("response", ""))
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except requests.exceptions.Timeout:
            raise OllamaTimeoutError(
                f"Ollama response stream timed out after {self.timeout} seconds."
            )

        return "".join(full_text)
