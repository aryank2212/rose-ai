"""
ROSE Models — Ollama API wrapper for dual-model chat.
"""

import ollama
from rose.config import (
    QUICK_MODEL, POWER_MODEL, OLLAMA_HOST,
    QUICK_SYSTEM_PROMPT, POWER_SYSTEM_PROMPT, CLASSIFIER_SYSTEM_PROMPT,
)
from rose import formatter


class ModelClient:
    """Wraps Ollama API for quick (gemma3:1b) and power (gemma4:e4b) models."""

    def __init__(self, memory_context: str = ""):
        self._client = ollama.Client(host=OLLAMA_HOST)
        self._memory_context = memory_context
        self._conversation: list[dict] = []  # Shared conversation history
        self._max_history = 40  # Max messages to retain

    def update_memory_context(self, ctx: str):
        """Update the memory context injected into system prompts."""
        self._memory_context = ctx

    def _build_system(self, base_prompt: str) -> str:
        """Build system prompt with optional memory context."""
        if self._memory_context:
            return f"{base_prompt}\n\n--- User Context ---\n{self._memory_context}"
        return base_prompt

    def _trim_history(self):
        """Keep conversation history within bounds."""
        if len(self._conversation) > self._max_history:
            # Keep system messages and last N messages
            self._conversation = self._conversation[-self._max_history:]

    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history."""
        self._conversation.append({"role": role, "content": content})
        self._trim_history()

    def get_last_user_message(self) -> str | None:
        """Get the last user message from history."""
        for msg in reversed(self._conversation):
            if msg["role"] == "user":
                return msg["content"]
        return None

    def discard_last_exchange(self):
        """Remove the last user message and any assistant response after it."""
        # Remove from end until we hit and remove the last user message
        while self._conversation:
            msg = self._conversation.pop()
            if msg["role"] == "user":
                break

    def classify(self, user_input: str) -> str:
        """
        Use gemma3:1b to classify input as QUICK or COMPLEX.
        Fast, non-streaming, ~200ms.
        """
        try:
            response = self._client.chat(
                model=QUICK_MODEL,
                messages=[
                    {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                ],
                stream=False,
            )
            result = response.message.content.strip().upper()
            # Normalize — only accept QUICK or COMPLEX
            if "COMPLEX" in result:
                return "COMPLEX"
            return "QUICK"
        except Exception as e:
            formatter.err(f"Classification failed: {e}. Defaulting to QUICK.")
            return "QUICK"

    def quick_chat(self, user_input: str) -> str:
        """
        Send to gemma3:1b for fast, streaming response.
        Returns the full response text.
        """
        self.add_to_history("user", user_input)

        messages = [
            {"role": "system", "content": self._build_system(QUICK_SYSTEM_PROMPT)},
            *self._conversation,
        ]

        try:
            stream = self._client.chat(
                model=QUICK_MODEL,
                messages=messages,
                stream=True,
            )

            formatter.stream_start()
            full_response = []
            for chunk in stream:
                token = chunk.message.content
                if token:
                    formatter.stream_token(token)
                    full_response.append(token)
            formatter.stream_end()

            response_text = "".join(full_response)
            self.add_to_history("assistant", response_text)
            return response_text

        except Exception as e:
            formatter.err(f"Quick model error: {e}")
            return ""

    def power_chat(self, user_input: str, tools: list | None = None) -> dict:
        """
        Send to gemma4:e4b for complex tasks with optional tool calling.
        Returns dict with 'content' and optional 'tool_calls'.
        """
        self.add_to_history("user", user_input)

        messages = [
            {"role": "system", "content": self._build_system(POWER_SYSTEM_PROMPT)},
            *self._conversation,
        ]

        try:
            kwargs = {
                "model": POWER_MODEL,
                "messages": messages,
                "stream": True,
            }
            if tools:
                kwargs["tools"] = tools
                # When tools are provided, we need non-streaming for tool_calls
                kwargs["stream"] = False
                response = self._client.chat(**kwargs)

                if response.message.tool_calls:
                    # Model wants to call tools — return them for executor
                    self.add_to_history("assistant", response.message.content or "")
                    return {
                        "content": response.message.content or "",
                        "tool_calls": [
                            {
                                "name": tc.function.name,
                                "args": tc.function.arguments,
                            }
                            for tc in response.message.tool_calls
                        ],
                        "raw_message": response.message,
                    }
                else:
                    # No tool calls — just a text response
                    content = response.message.content or ""
                    self.add_to_history("assistant", content)
                    formatter.stream_start()
                    formatter.stream_token(content)
                    formatter.stream_end()
                    return {"content": content, "tool_calls": []}
            else:
                # No tools — stream the response
                stream = self._client.chat(**kwargs)
                formatter.stream_start()
                full_response = []
                for chunk in stream:
                    token = chunk.message.content
                    if token:
                        formatter.stream_token(token)
                        full_response.append(token)
                formatter.stream_end()

                response_text = "".join(full_response)
                self.add_to_history("assistant", response_text)
                return {"content": response_text, "tool_calls": []}

        except Exception as e:
            formatter.err(f"Power model error: {e}")
            return {"content": "", "tool_calls": []}

    def power_chat_with_tool_result(self, tool_name: str, tool_result: str,
                                     previous_message, tools: list | None = None) -> dict:
        """
        Continue a tool-calling conversation by sending tool results back.
        """
        # Add tool response to history
        self._conversation.append({
            "role": "tool",
            "content": tool_result,
        })

        messages = [
            {"role": "system", "content": self._build_system(POWER_SYSTEM_PROMPT)},
            *self._conversation,
        ]

        try:
            kwargs = {
                "model": POWER_MODEL,
                "messages": messages,
                "stream": False,
            }
            if tools:
                kwargs["tools"] = tools

            response = self._client.chat(**kwargs)

            if response.message.tool_calls:
                self.add_to_history("assistant", response.message.content or "")
                return {
                    "content": response.message.content or "",
                    "tool_calls": [
                        {
                            "name": tc.function.name,
                            "args": tc.function.arguments,
                        }
                        for tc in response.message.tool_calls
                    ],
                    "raw_message": response.message,
                }
            else:
                content = response.message.content or ""
                self.add_to_history("assistant", content)
                formatter.stream_start()
                formatter.stream_token(content)
                formatter.stream_end()
                return {"content": content, "tool_calls": []}

        except Exception as e:
            formatter.err(f"Power model tool continuation error: {e}")
            return {"content": "", "tool_calls": []}

    def verify_models(self) -> bool:
        """Verify both models are available in Ollama."""
        try:
            models = self._client.list()
            available = {m.model for m in models.models} if hasattr(models, 'models') else set()
            # Also check by name prefix (ollama sometimes includes :latest)
            available_names = set()
            for m in available:
                available_names.add(m)
                available_names.add(m.split(":")[0])

            quick_ok = any(QUICK_MODEL.split(":")[0] in m for m in available)
            power_ok = any(POWER_MODEL.split(":")[0] in m for m in available)

            if not quick_ok:
                formatter.err(f"Quick model '{QUICK_MODEL}' not found in Ollama.")
            if not power_ok:
                formatter.err(f"Power model '{POWER_MODEL}' not found in Ollama.")

            return quick_ok and power_ok
        except Exception as e:
            formatter.err(f"Cannot connect to Ollama at {OLLAMA_HOST}: {e}")
            return False
