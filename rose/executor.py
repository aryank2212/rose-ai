"""
ROSE Executor — agentic loop engine for complex multi-step tasks.
plan → execute step → evaluate → adjust → next step → report
"""

import time
import threading
import json

from rose.config import PLAN_DISPLAY_WAIT_SECONDS, MAX_AGENTIC_STEPS, AUTO_RETRY_ON_FAILURE
from rose import formatter


class Executor:
    """
    Executes complex tasks via gemma4:e4b with tool calling in an agentic loop.
    """

    def __init__(self, model_client, tool_registry):
        self._client = model_client
        self._tools = tool_registry
        self._stop_event = threading.Event()
        self._current_task: str = ""
        self._step_count = 0
        self._total_steps = 0

    @property
    def is_running(self) -> bool:
        return not self._stop_event.is_set() and self._current_task != ""

    def stop(self):
        """Signal the executor to stop after the current step."""
        self._stop_event.set()
        formatter.warn("Stop requested. Finishing current step...")

    def get_status(self) -> str:
        """Return current task status."""
        if not self._current_task:
            return "Idle — no task running."
        return f"Running: {self._current_task} (step {self._step_count}/{self._total_steps})"

    def execute(self, user_input: str) -> str:
        """
        Run the full agentic loop for a complex task.
        Returns the final summary.
        """
        self._stop_event.clear()
        self._current_task = user_input
        self._step_count = 0

        tool_functions = self._tools.get_tool_functions()

        # First call — let gemma4 plan and optionally call tools
        response = self._client.power_chat(user_input, tools=tool_functions)

        # Agentic tool-calling loop
        loop_count = 0
        while response.get("tool_calls") and loop_count < MAX_AGENTIC_STEPS:
            if self._stop_event.is_set():
                formatter.warn("Task aborted by user.")
                break

            loop_count += 1
            self._step_count = loop_count

            for tc in response["tool_calls"]:
                if self._stop_event.is_set():
                    break

                tool_name = tc["name"]
                tool_args = tc["args"]

                formatter.step(loop_count, "?", f"Calling {tool_name}({_summarize_args(tool_args)})")

                # Execute the tool
                result = self._tools.execute(tool_name, tool_args)

                # Check if tool failed and auto-retry is enabled
                try:
                    result_data = json.loads(result)
                    if isinstance(result_data, dict) and "error" in result_data and AUTO_RETRY_ON_FAILURE:
                        formatter.err(f"Tool {tool_name} failed: {result_data['error']}")
                        formatter.rose("Attempting alternative approach...")
                        # Let the model know about the failure and try again
                        result = json.dumps({
                            "error": result_data["error"],
                            "note": "First attempt failed. Please try an alternative approach."
                        })
                except (json.JSONDecodeError, TypeError):
                    pass  # Result is plain text, not JSON — that's fine

                # Feed tool result back to the model
                response = self._client.power_chat_with_tool_result(
                    tool_name=tool_name,
                    tool_result=result,
                    previous_message=response.get("raw_message"),
                    tools=tool_functions,
                )

        if loop_count >= MAX_AGENTIC_STEPS:
            formatter.warn(f"Agentic loop hit safety limit ({MAX_AGENTIC_STEPS} steps). Stopping.")

        # Final summary
        final_content = response.get("content", "")
        if final_content and not self._stop_event.is_set():
            formatter.done(f"Task complete ({loop_count} tool calls executed).")

        self._current_task = ""
        self._stop_event.clear()
        return final_content


def _summarize_args(args: dict) -> str:
    """Create a brief summary of tool arguments for display."""
    parts = []
    for k, v in args.items():
        val_str = str(v)
        if len(val_str) > 50:
            val_str = val_str[:47] + "..."
        parts.append(f"{k}={val_str}")
    return ", ".join(parts)
