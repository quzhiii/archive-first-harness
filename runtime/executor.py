from __future__ import annotations

from typing import Any


class Executor:
    """Run a single execution step and return a structured result."""

    def execute_step(
        self,
        step: dict[str, Any],
        available_tools: list[dict[str, Any]],
        working_context,
    ) -> dict[str, Any]:
        tool_name = str(step.get("tool_name") or "").strip()
        tool_input = dict(step.get("tool_input") or {})
        tool_names = {tool.get("name") for tool in available_tools}

        if not tool_name or tool_name not in tool_names:
            return self.format_execution_result(
                status="error",
                tool_name=tool_name or None,
                output=None,
                error={
                    "type": "tool_not_available",
                    "message": f"tool '{tool_name}' is not available for this step",
                },
                artifacts=[],
                metadata={"available_tools": sorted(name for name in tool_names if name)},
            )

        try:
            tool_output = self.run_tool(tool_name, tool_input)
        except Exception as exc:
            return self.format_execution_result(
                status="error",
                tool_name=tool_name,
                output=None,
                error={"type": type(exc).__name__, "message": str(exc)},
                artifacts=[],
                metadata={"tool_input": tool_input},
            )

        return self.format_execution_result(
            status="success",
            tool_name=tool_name,
            output=tool_output["output"],
            error=None,
            artifacts=tool_output.get("artifacts", []),
            metadata={
                "tool_input": tool_input,
                "available_tool_count": len(available_tools),
                "task_note_count": len(getattr(working_context, "selected_task_notes", [])),
            },
        )

    def run_tool(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "read_file":
            path = str(tool_input.get("path") or "unknown")
            return {
                "output": {
                    "summary": f"stub-read:{path}",
                    "path": path,
                    "content_preview": f"Preview for {path}",
                },
                "artifacts": [],
            }

        if tool_name == "write_file":
            path = str(tool_input.get("path") or "unknown")
            content = str(tool_input.get("content") or "")
            return {
                "output": {
                    "summary": f"stub-write:{path}",
                    "path": path,
                    "bytes_written": len(content.encode("utf-8")),
                },
                "artifacts": [{"type": "file_change", "path": path}],
            }

        if tool_name == "search_docs":
            query = str(tool_input.get("query") or "")
            return {
                "output": {
                    "summary": f"stub-search:{query}",
                    "query": query,
                    "matches": [f"match-for:{query}"] if query else [],
                },
                "artifacts": [],
            }

        if tool_name == "run_command":
            command = str(tool_input.get("command") or "")
            return {
                "output": {
                    "summary": f"stub-command:{command}",
                    "command": command,
                    "exit_code": 0,
                    "stdout": f"Executed: {command}",
                },
                "artifacts": [],
            }

        raise ValueError(f"unsupported tool: {tool_name}")

    def format_execution_result(
        self,
        *,
        status: str,
        tool_name: str | None,
        output: Any,
        error: dict[str, Any] | None,
        artifacts: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": status,
            "tool_name": tool_name,
            "output": output,
            "error": error,
            "artifacts": artifacts,
            "metadata": metadata,
        }
