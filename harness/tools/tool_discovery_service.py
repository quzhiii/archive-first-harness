from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    signature: dict[str, Any]
    schema: dict[str, Any]
    risk_level: str
    task_types: tuple[str, ...]
    capability_aliases: tuple[str, ...] = ()


class ToolDiscoveryService:
    """Expose a small tool surface first and only fetch schema on demand."""

    def __init__(self) -> None:
        self._registry = self._build_registry()

    def list_candidate_tools(
        self,
        task_type: str,
        allowed_tools: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        task_type_key = (task_type or "").strip().lower()
        allowed = {value.strip().lower() for value in (allowed_tools or []) if value.strip()}
        candidates: list[dict[str, Any]] = []

        for tool in self._registry.values():
            if task_type_key and task_type_key not in tool.task_types:
                continue
            if allowed and not self._is_allowed(tool, allowed):
                continue
            candidates.append(self.get_tool_signature(tool.name))

        return candidates

    def get_tool_signature(self, tool_name: str) -> dict[str, Any]:
        tool = self._get_tool(tool_name)
        return {
            "name": tool.name,
            "description": tool.description,
            "signature": dict(tool.signature),
            "risk_level": tool.risk_level,
        }

    def get_tool_schema(self, tool_name: str) -> dict[str, Any]:
        tool = self._get_tool(tool_name)
        return {
            "name": tool.name,
            "schema": dict(tool.schema),
            "risk_level": tool.risk_level,
        }

    def cleanup_tool_context(self, tool_name: str) -> dict[str, Any]:
        tool = self._get_tool(tool_name)
        return {
            "tool_name": tool.name,
            "status": "cleaned",
            "removed_context": True,
        }

    def _is_allowed(self, tool: ToolDefinition, allowed: set[str]) -> bool:
        names = {tool.name.lower(), *{alias.lower() for alias in tool.capability_aliases}}
        return not names.isdisjoint(allowed)

    def _get_tool(self, tool_name: str) -> ToolDefinition:
        normalized_name = tool_name.strip().lower()
        if normalized_name not in self._registry:
            raise KeyError(f"unknown tool: {tool_name}")
        return self._registry[normalized_name]

    def _build_registry(self) -> dict[str, ToolDefinition]:
        tools = [
            ToolDefinition(
                name="read_file",
                description="Read a file and return a lightweight preview.",
                signature={"input": {"path": "str"}},
                schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                risk_level="low",
                task_types=("coding", "review", "qa", "retrieval", "research"),
                capability_aliases=("read_file", "read_files"),
            ),
            ToolDefinition(
                name="write_file",
                description="Write file content in a controlled stubbed way.",
                signature={"input": {"path": "str", "content": "str"}},
                schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
                risk_level="medium",
                task_types=("coding", "execution"),
                capability_aliases=("write_file", "edit_files"),
            ),
            ToolDefinition(
                name="search_docs",
                description="Search project notes or documentation.",
                signature={"input": {"query": "str"}},
                schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                risk_level="low",
                task_types=("research", "retrieval", "planning", "review", "generation"),
                capability_aliases=("search_docs", "search", "search_notes"),
            ),
            ToolDefinition(
                name="run_command",
                description="Run a shell command in a stubbed, non-retrying executor.",
                signature={"input": {"command": "str"}},
                schema={
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
                risk_level="medium",
                task_types=("coding", "execution", "qa"),
                capability_aliases=("run_command", "run_tests"),
            ),
        ]
        return {tool.name.lower(): tool for tool in tools}
