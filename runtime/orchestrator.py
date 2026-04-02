from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass, replace
from enum import Enum
from typing import Any

from harness.evaluation.baseline_compare import BaselineComparator
from harness.evaluation.evaluation_input import build_evaluation_input_bundle
from harness.evaluation.realm_evaluator import RealmEvaluator
from harness.hooks.hook_orchestrator import HookOrchestrator
from harness.hooks.models import (
    GovernanceCheckPayload,
    JournalAppendPayload,
    ResidualFollowupPayload,
    SandboxRequiredPayload,
    VerificationReportPayload,
)
from harness.sandbox.rollback import RollbackManager
from harness.sandbox.sandbox_executor import SandboxExecutor
from harness.state.models import RiskLevel, TaskBlock
from harness.telemetry.metrics import MetricsAggregator


class Orchestrator:
    """Run the minimum single-path flow for a task contract."""

    def run(
        self,
        task_contract,
        state_manager,
        context_engine,
        skill_loader,
        tool_discovery_service,
        executor,
        verifier=None,
        methodology_router=None,
        model_router=None,
        governance_policy=None,
        learning_journal=None,
        hook_orchestrator: HookOrchestrator | None = None,
        sandbox_executor: SandboxExecutor | None = None,
        rollback_manager: RollbackManager | None = None,
        baseline_artifacts: Mapping[str, Mapping[str, Any] | Sequence[Any]] | None = None,
        baseline_comparator: BaselineComparator | None = None,
        realm_evaluator: RealmEvaluator | None = None,
    ) -> dict[str, Any]:
        active_hooks = hook_orchestrator or HookOrchestrator()
        dispatch_start_index = len(active_hooks.get_recent_dispatches())
        active_rollback = (
            rollback_manager
            or getattr(sandbox_executor, "rollback_manager", None)
            or RollbackManager()
        )
        active_sandbox = sandbox_executor or SandboxExecutor(active_rollback)
        if getattr(active_sandbox, "rollback_manager", None) is not active_rollback:
            active_sandbox.rollback_manager = active_rollback

        task_id = task_contract.task_id
        raw_snapshot = state_manager.build_state_snapshot_for_context(task_id)
        state_snapshot = self._prepare_snapshot(task_contract, raw_snapshot)
        journal_lessons = self._read_relevant_journal_lessons(learning_journal, task_contract)
        block_selection_report = self._build_block_selection_report(
            context_engine=context_engine,
            task_contract=task_contract,
            state_snapshot=state_snapshot,
            journal_lessons=journal_lessons,
        )
        working_context = context_engine.build_working_context(
            task_contract,
            state_snapshot,
            journal_lessons=journal_lessons,
        )
        selected_skills = self._load_skills(skill_loader, task_contract, working_context)

        candidate_tools = tool_discovery_service.list_candidate_tools(
            task_contract.task_type.value,
            task_contract.allowed_tools,
        )

        if not candidate_tools:
            execution_plan = {"steps": []}
            sandbox_decision = self._build_empty_sandbox_decision(task_contract)
            sandbox_result = None
            rollback_result = {
                "status": "not_required",
                "reason": "no_execution_attempt",
            }
            execution_result = {
                "status": "error",
                "tool_name": None,
                "output": None,
                "error": {
                    "type": "no_candidate_tools",
                    "message": "no tools matched the task contract constraints",
                },
                "artifacts": [],
                "metadata": {},
            }
        else:
            execution_plan = self.build_execution_plan(task_contract, working_context, candidate_tools)
            step = execution_plan["steps"][0]
            selected_tool = step["tool_name"]
            selected_tool_schema = tool_discovery_service.get_tool_schema(selected_tool)
            selected_tool_bundle = [
                {
                    **tool_discovery_service.get_tool_signature(selected_tool),
                    "schema": selected_tool_schema["schema"],
                }
            ]
            sandbox_decision = self._review_execution_gate(
                task_contract=task_contract,
                step=step,
                governance_policy=governance_policy,
            )
            if sandbox_decision["sandbox_required"]:
                self._emit_sandbox_required_event(
                    hook_orchestrator=active_hooks,
                    task_contract=task_contract,
                    sandbox_decision=sandbox_decision,
                )
                execution_result, sandbox_result, rollback_result = self._execute_with_sandbox(
                    task_contract=task_contract,
                    executor=executor,
                    sandbox_executor=active_sandbox,
                    rollback_manager=active_rollback,
                    step=step,
                    available_tools=selected_tool_bundle,
                    working_context=working_context,
                    sandbox_decision=sandbox_decision,
                )
            else:
                execution_result = executor.execute_step(step, selected_tool_bundle, working_context)
                sandbox_result = None
                rollback_result = {
                    "status": "not_required",
                    "reason": "sandbox_not_needed",
                }
            cleanup_result = tool_discovery_service.cleanup_tool_context(selected_tool)
            execution_result.setdefault("metadata", {})
            execution_result["metadata"]["cleanup"] = cleanup_result
            execution_result["metadata"]["sandboxed"] = sandbox_decision["sandbox_required"]
            execution_result["metadata"]["sandbox_reason_codes"] = list(
                sandbox_decision["reason_codes"]
            )

        verification_report = None
        residual_followup = None
        if verifier is not None:
            verification_report = verifier.verify_execution_result(
                execution_result,
                task_contract,
            )
            self._emit_verification_report_event(
                hook_orchestrator=active_hooks,
                task_contract=task_contract,
                verification_report=verification_report,
            )
            residual_followup = self.handle_residual_followup(
                task_contract=task_contract,
                execution_result=execution_result,
                verification_report=verification_report,
                verifier=verifier,
                methodology_router=methodology_router,
                model_router=model_router,
                governance_policy=governance_policy,
                hook_orchestrator=active_hooks,
            )

        result = self.finalize_run(
            task_contract=task_contract,
            working_context=working_context,
            selected_skills=selected_skills,
            candidate_tools=candidate_tools,
            execution_plan=execution_plan,
            execution_result=execution_result,
            verification_report=verification_report,
            residual_followup=residual_followup,
            sandbox_decision=sandbox_decision,
            sandbox_result=sandbox_result,
            rollback_result=rollback_result,
        )

        if residual_followup is not None:
            result["state_writeback_result"] = self._apply_minimal_writeback(
                state_manager=state_manager,
                state_writeback_payload=result["state_writeback_payload"],
                expected_version=raw_snapshot.versions["task_block"],
            )

        learning_journal_result, journal_append_artifact = self._append_learning_lesson(
            hook_orchestrator=active_hooks,
            learning_journal=learning_journal,
            task_contract=task_contract,
            execution_result=execution_result,
            verification_report=verification_report,
            state_writeback_payload=result["state_writeback_payload"],
            sandbox_result=result["sandbox_result"],
            rollback_result=result["rollback_result"],
            read_count=len(journal_lessons),
        )
        result["learning_journal"] = learning_journal_result

        dispatch_trace = self._capture_run_dispatch_trace(
            active_hooks,
            start_index=dispatch_start_index,
        )
        journal_append_trace = self._build_journal_append_trace(
            dispatch_trace=dispatch_trace,
            journal_append_artifact=journal_append_artifact,
        )
        metrics_summary = self._build_metrics_summary(
            dispatch_trace=dispatch_trace,
            working_context_summary=result["working_context_summary"],
            selected_skills=selected_skills,
            execution_result=execution_result,
            rollback_result=result["rollback_result"],
        )
        evaluation_bundle = build_evaluation_input_bundle(
            task_contract=task_contract,
            block_selection_report=block_selection_report,
            verification_report=verification_report,
            residual_followup=residual_followup,
            metrics_summary=metrics_summary,
            event_trace={
                "dispatch_trace": dispatch_trace,
                "execution_status": execution_result["status"],
            },
            journal_append_trace=journal_append_trace,
        )

        result["block_selection_report"] = block_selection_report
        result["metrics_summary"] = metrics_summary
        result["evaluation_input_bundle"] = evaluation_bundle.as_dict()
        result["baseline_compare_results"] = self._build_baseline_compare_results(
            bundle=evaluation_bundle,
            baseline_artifacts=baseline_artifacts,
            baseline_comparator=baseline_comparator,
        )
        result["realm_evaluation"] = (
            realm_evaluator or RealmEvaluator()
        ).evaluate_bundle(evaluation_bundle)
        return result

    def build_execution_plan(
        self,
        task_contract,
        working_context,
        candidate_tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        selected_tool = self._select_tool(task_contract.task_type.value, candidate_tools)
        return {
            "mode": "single_step",
            "steps": [
                {
                    "tool_name": selected_tool,
                    "reason": f"Use the first allowed candidate for {task_contract.task_type.value}.",
                    "tool_input": self._build_tool_input(selected_tool, task_contract, working_context),
                }
            ],
        }

    def handle_residual_followup(
        self,
        *,
        task_contract,
        execution_result: dict[str, Any],
        verification_report: dict[str, Any],
        verifier,
        methodology_router=None,
        model_router=None,
        governance_policy=None,
        hook_orchestrator: HookOrchestrator | None = None,
    ) -> dict[str, Any]:
        reassessment = verifier.reassess_residual_risk(
            execution_result,
            task_contract,
            verification_report,
        )
        methodology_suggestion = None
        model_suggestion = None
        governance_decision = {
            "status": "clear",
            "approved": True,
            "requires_governance_override": False,
            "issues": [],
        }

        if reassessment["needs_followup"]:
            if methodology_router is not None:
                methodology_suggestion = methodology_router.route(
                    task_contract,
                    failure_tier=reassessment["failure_tier"],
                    tool_outcome=reassessment["tool_outcome"],
                    evidence_quality=reassessment["evidence_quality"],
                    context_health=reassessment["context_health"],
                    budget_remaining=reassessment["budget_remaining"],
                )

            if model_router is not None:
                baseline_model_decision = model_router.route(task_contract)
                adjusted_contract = self._with_residual_risk(
                    task_contract,
                    reassessment["reassessed_level"],
                )
                model_suggestion = model_router.route(
                    adjusted_contract,
                    current_slot=baseline_model_decision["selected_slot"],
                    history=[baseline_model_decision],
                )

            self._emit_residual_followup_event(
                hook_orchestrator=hook_orchestrator,
                task_contract=task_contract,
                reassessment=reassessment,
                methodology_suggestion=methodology_suggestion,
                model_suggestion=model_suggestion,
            )

            governance_decision = self._review_governance(
                task_contract=task_contract,
                governance_policy=governance_policy,
                methodology_suggestion=methodology_suggestion,
                model_suggestion=model_suggestion,
            )

            self._emit_governance_check_event(
                hook_orchestrator=hook_orchestrator,
                task_contract=task_contract,
                methodology_suggestion=methodology_suggestion,
                model_suggestion=model_suggestion,
                governance_decision=governance_decision,
            )

        return {
            "status": "ok",
            "reassessment": reassessment,
            "methodology_suggestion": methodology_suggestion,
            "model_suggestion": model_suggestion,
            "governance": governance_decision,
            "auto_execution": "none",
            "telemetry_payload": {
                "residual_risk_level": reassessment["reassessed_level"],
                "residual_risk_changed": reassessment["changed"],
                "followup_required": reassessment["needs_followup"],
                "governance_required": governance_decision["requires_governance_override"],
            },
        }

    def finalize_run(
        self,
        *,
        task_contract,
        working_context,
        selected_skills: list[str],
        candidate_tools: list[dict[str, Any]],
        execution_plan: dict[str, Any],
        execution_result: dict[str, Any],
        verification_report: dict[str, Any] | None = None,
        residual_followup: dict[str, Any] | None = None,
        sandbox_decision: dict[str, Any] | None = None,
        sandbox_result: dict[str, Any] | None = None,
        rollback_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        next_actions = []
        if residual_followup and residual_followup["reassessment"]["needs_followup"]:
            methodology_suggestion = residual_followup.get("methodology_suggestion")
            if methodology_suggestion is not None:
                next_actions.append(methodology_suggestion["expected_next_action"])

        state_writeback_payload = {
            "task_id": task_contract.task_id,
            "status": execution_result["status"],
            "last_tool_name": execution_result["tool_name"],
        }
        if residual_followup is not None:
            state_writeback_payload["residual_risk"] = residual_followup["reassessment"]
            state_writeback_payload["followup_required"] = residual_followup["reassessment"][
                "needs_followup"
            ]
            state_writeback_payload["governance_required"] = residual_followup["governance"][
                "requires_governance_override"
            ]

        result = {
            "worker_mode": "single",
            "spawned_workers": 0,
            "task_contract": self._to_json_value(task_contract),
            "working_context_summary": {
                "task_note_count": len(working_context.selected_task_notes),
                "project_note_count": len(working_context.selected_project_notes),
                "global_note_count": len(working_context.selected_global_notes),
                "retrieval_packet_count": len(working_context.retrieval_packets),
                "tool_signatures": list(working_context.tool_signatures),
            },
            "selected_skills": selected_skills,
            "candidate_tools": candidate_tools,
            "execution_plan": execution_plan,
            "execution_result": execution_result,
            "next_actions": next_actions,
            "state_writeback_payload": state_writeback_payload,
            "sandbox_triggered": bool(sandbox_decision and sandbox_decision["sandbox_required"]),
            "sandbox_decision": sandbox_decision,
            "sandbox_result": sandbox_result,
            "rollback_result": rollback_result,
            "verifier_handoff": {
                "pending": verification_report is None,
                "reason": (
                    "v0.1 orchestrator only reserves the handoff slot"
                    if verification_report is None
                    else "verification completed in-process"
                ),
            },
        }
        if verification_report is not None:
            result["verification_report"] = verification_report
        if residual_followup is not None:
            result["residual_followup"] = residual_followup
        return result

    def _prepare_snapshot(self, task_contract, state_snapshot):
        if (
            not state_snapshot.task_block.current_goal
            or state_snapshot.task_block.current_goal == "No active goal recorded."
        ):
            task_block = TaskBlock(
                task_id=state_snapshot.task_block.task_id,
                current_goal=task_contract.goal,
                contract_id=task_contract.contract_id,
                next_steps=[f"Execute the {task_contract.task_type.value} task."],
            )
            return replace(state_snapshot, task_block=task_block)

        if state_snapshot.task_block.contract_id is None:
            return replace(
                state_snapshot,
                task_block=replace(
                    state_snapshot.task_block,
                    contract_id=task_contract.contract_id,
                ),
            )
        return state_snapshot

    def _build_block_selection_report(
        self,
        *,
        context_engine,
        task_contract,
        state_snapshot,
        journal_lessons: list[dict[str, Any]],
    ) -> dict[str, Any]:
        builder = getattr(context_engine, "build_block_selection_report", None)
        if not callable(builder):
            return {
                "included_blocks": [],
                "excluded_blocks": [],
                "block_order": [],
                "limits": {},
            }
        return builder(
            task_contract,
            state_snapshot,
            journal_lessons=journal_lessons,
        )

    def _capture_run_dispatch_trace(
        self,
        hook_orchestrator: HookOrchestrator,
        *,
        start_index: int,
    ) -> list[dict[str, Any]]:
        dispatches = hook_orchestrator.get_recent_dispatches()
        current_run = dispatches[start_index:] if start_index > 0 else dispatches
        return [dict(dispatch) for dispatch in current_run]

    def _build_metrics_summary(
        self,
        *,
        dispatch_trace: list[dict[str, Any]],
        working_context_summary: dict[str, Any],
        selected_skills: list[str],
        execution_result: dict[str, Any],
        rollback_result: dict[str, Any],
    ) -> dict[str, Any]:
        context_size = sum(
            int(working_context_summary.get(field_name, 0) or 0)
            for field_name in ("task_note_count", "project_note_count", "global_note_count")
        )
        trace = {
            "events": [
                {
                    "event_name": str(dispatch.get("event_name") or "unknown"),
                    "payload": {
                        "status": dispatch.get("status"),
                        "error_type": dispatch.get("error_type"),
                    },
                }
                for dispatch in dispatch_trace
            ],
            "metrics": [
                {"metric_name": "token_count", "value": 0, "tags": {}},
                {"metric_name": "latency_ms", "value": 0, "tags": {}},
                {"metric_name": "retry_count", "value": 0, "tags": {}},
                {
                    "metric_name": "rollback_count",
                    "value": 1 if rollback_result.get("status") == "rolled_back" else 0,
                    "tags": {},
                },
                {"metric_name": "tool_misuse_count", "value": 0, "tags": {}},
                {
                    "metric_name": "execution_failure_count",
                    "value": 1 if execution_result.get("status") != "success" else 0,
                    "tags": {},
                },
                {
                    "metric_name": "context_size",
                    "value": context_size,
                    "tags": {},
                },
                {"metric_name": "human_handoff_count", "value": 0, "tags": {}},
            ],
        }
        if selected_skills:
            trace["metrics"].append(
                {
                    "metric_name": "skill_hit_rate",
                    "value": 1,
                    "tags": {},
                }
            )
        return MetricsAggregator().aggregate(trace)

    def _build_journal_append_trace(
        self,
        *,
        dispatch_trace: list[dict[str, Any]],
        journal_append_artifact: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if journal_append_artifact is None:
            return None

        journal_dispatch_trace = [
            dict(dispatch)
            for dispatch in dispatch_trace
            if str(dispatch.get("event_name") or "") == "on_journal_append"
        ]
        return {
            "dispatch_trace": journal_dispatch_trace,
            **self._to_json_value(journal_append_artifact),
        }

    def _build_baseline_compare_results(
        self,
        *,
        bundle,
        baseline_artifacts: Mapping[str, Mapping[str, Any] | Sequence[Any]] | None,
        baseline_comparator: BaselineComparator | None,
    ) -> dict[str, Any]:
        if not baseline_artifacts:
            return {
                "status": "not_requested",
                "compared_artifact_types": [],
                "artifact_results": {},
            }

        comparator = baseline_comparator or BaselineComparator()
        artifact_results: dict[str, dict[str, Any]] = {}
        for artifact_type, baseline in baseline_artifacts.items():
            normalized_artifact_type = str(artifact_type)
            try:
                artifact_results[normalized_artifact_type] = comparator.compare_bundle_artifact(
                    bundle,
                    self._extract_baseline_payload(baseline),
                    artifact_type=normalized_artifact_type,
                )
            except Exception as exc:
                artifact_results[normalized_artifact_type] = {
                    "artifact_type": normalized_artifact_type,
                    "status": "error",
                    "missing_fields": [],
                    "unexpected_fields": [],
                    "type_mismatches": [],
                    "value_drifts": [],
                    "summary": f"baseline compare failed: {exc}",
                    "reason_codes": [type(exc).__name__],
                }

        status_counts: dict[str, int] = {}
        for artifact_result in artifact_results.values():
            artifact_status = str(artifact_result.get("status") or "unknown")
            status_counts[artifact_status] = status_counts.get(artifact_status, 0) + 1
        return {
            "status": "completed",
            "compared_artifact_types": list(artifact_results.keys()),
            "artifact_results": artifact_results,
            "status_counts": status_counts,
        }

    def _extract_baseline_payload(
        self,
        baseline: Mapping[str, Any] | Sequence[Any],
    ) -> Mapping[str, Any] | Sequence[Any]:
        if isinstance(baseline, Mapping) and "data" in baseline and "status" in baseline:
            baseline_status = str(baseline.get("status") or "")
            if baseline_status != "ok":
                raise ValueError("baseline load result is not usable for comparison")
            return baseline.get("data")
        return baseline

    def _load_skills(self, skill_loader, task_contract, working_context) -> list[str]:
        if skill_loader is None:
            return []
        if hasattr(skill_loader, "load_for_task"):
            return list(skill_loader.load_for_task(task_contract, working_context))
        if hasattr(skill_loader, "load_skills"):
            return list(skill_loader.load_skills(task_contract, working_context))
        if callable(skill_loader):
            return list(skill_loader(task_contract, working_context))
        return []

    def _build_tool_input(self, tool_name: str, task_contract, working_context) -> dict[str, Any]:
        goal = task_contract.goal
        task_focus = working_context.selected_task_notes[0] if working_context.selected_task_notes else goal
        if tool_name == "search_docs":
            return {"query": goal}
        if tool_name == "read_file":
            return {"path": goal}
        if tool_name == "write_file":
            return {"path": "artifacts/output.txt", "content": task_focus}
        if tool_name == "run_command":
            return {"command": f"echo {task_focus}"}
        return {}

    def _review_governance(
        self,
        *,
        task_contract,
        governance_policy,
        methodology_suggestion,
        model_suggestion,
    ) -> dict[str, Any]:
        if governance_policy is not None:
            return governance_policy.review_followup(
                task_contract=task_contract,
                methodology_decision=methodology_suggestion,
                model_decision=model_suggestion,
            )

        if methodology_suggestion and methodology_suggestion.get("requires_governance_override"):
            return {
                "status": "review_required",
                "approved": False,
                "requires_governance_override": True,
                "issues": [
                    {
                        "code": "methodology_out_of_contract",
                        "message": "methodology suggestion exceeds the contract boundary",
                        "candidate": methodology_suggestion.get("selected_methodology"),
                    }
                ],
            }

        return {
            "status": "clear",
            "approved": True,
            "requires_governance_override": False,
            "issues": [],
        }

    def _build_empty_sandbox_decision(self, task_contract) -> dict[str, Any]:
        return {
            "status": "direct_execution_allowed",
            "sandbox_required": False,
            "governance_required": False,
            "reason_codes": [],
            "issues": [],
            "risk_level": task_contract.residual_risk_level.value,
            "write_permission_level": task_contract.write_permission_level.value,
            "action": None,
        }

    def _review_execution_gate(
        self,
        *,
        task_contract,
        step: dict[str, Any],
        governance_policy,
    ) -> dict[str, Any]:
        if governance_policy is not None and hasattr(governance_policy, "review_execution_gate"):
            return governance_policy.review_execution_gate(
                task_contract=task_contract,
                action=step,
            )
        sandbox_required = (
            task_contract.write_permission_level.value in {"write", "destructive_write"}
            or task_contract.residual_risk_level.value == "high"
        )
        return {
            "status": "sandbox_required" if sandbox_required else "direct_execution_allowed",
            "sandbox_required": sandbox_required,
            "governance_required": False,
            "reason_codes": self._build_sandbox_reason_codes(task_contract),
            "issues": [],
            "risk_level": task_contract.residual_risk_level.value,
            "write_permission_level": task_contract.write_permission_level.value,
            "action": step.get("tool_name"),
        }

    def _build_sandbox_reason_codes(self, task_contract) -> list[str]:
        reason_codes: list[str] = []
        if task_contract.write_permission_level.value in {"write", "destructive_write"}:
            reason_codes.append("high_write_permission")
        if task_contract.residual_risk_level.value == "high":
            reason_codes.append("high_risk_level")
        return reason_codes

    def _execute_with_sandbox(
        self,
        *,
        task_contract,
        executor,
        sandbox_executor: SandboxExecutor,
        rollback_manager: RollbackManager,
        step: dict[str, Any],
        available_tools: list[dict[str, Any]],
        working_context,
        sandbox_decision: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        rollback_target = {
            "task_id": task_contract.task_id,
            "tool_name": step.get("tool_name"),
            "status": "pending",
        }
        sandbox_payload = {
            "step": {
                "tool_name": step.get("tool_name"),
                "tool_input": dict(step.get("tool_input") or {}),
            },
            "available_tools": [tool.get("name") for tool in available_tools],
            "reason_codes": list(sandbox_decision["reason_codes"]),
            "rollback_target": rollback_target,
            "runner": lambda: executor.execute_step(step, available_tools, working_context),
        }
        sandbox_result = sandbox_executor.execute("execute_step", sandbox_payload)
        execution_result = self._extract_execution_result_from_sandbox(step, sandbox_result)

        if sandbox_result["status"] == "error":
            rollback_result = rollback_manager.rollback(sandbox_result["snapshot_ref"])
        else:
            rollback_result = {
                "status": "not_required",
                "reason": "sandbox_succeeded",
            }

        execution_result.setdefault("metadata", {})
        execution_result["metadata"]["sandbox_snapshot_ref"] = sandbox_result["snapshot_ref"]
        execution_result["metadata"]["rollback_status"] = rollback_result["status"]
        return execution_result, sandbox_result, rollback_result

    def _extract_execution_result_from_sandbox(
        self,
        step: dict[str, Any],
        sandbox_result: dict[str, Any],
    ) -> dict[str, Any]:
        sandbox_output = sandbox_result.get("output")
        if isinstance(sandbox_output, dict):
            embedded_result = sandbox_output.get("execution_result")
            if isinstance(embedded_result, dict):
                execution_result = {
                    "status": embedded_result.get("status", sandbox_result["status"]),
                    "tool_name": embedded_result.get("tool_name", step.get("tool_name")),
                    "output": embedded_result.get("output"),
                    "error": embedded_result.get("error"),
                    "artifacts": list(embedded_result.get("artifacts", [])),
                    "metadata": dict(embedded_result.get("metadata", {})),
                }
                execution_result["metadata"]["sandboxed"] = True
                return execution_result

        return {
            "status": sandbox_result["status"],
            "tool_name": step.get("tool_name"),
            "output": sandbox_output,
            "error": sandbox_result.get("error"),
            "artifacts": [],
            "metadata": {"sandboxed": True},
        }

    def _emit_verification_report_event(
        self,
        *,
        hook_orchestrator: HookOrchestrator,
        task_contract,
        verification_report: dict[str, Any],
    ) -> None:
        payload = VerificationReportPayload(
            task_id=task_contract.task_id,
            contract_id=task_contract.contract_id,
            verification_report=verification_report,
            residual_risk_hint=str(verification_report.get("residual_risk_hint") or "low"),
        )
        hook_orchestrator.emit("on_verification_report", payload)

    def _emit_residual_followup_event(
        self,
        *,
        hook_orchestrator: HookOrchestrator | None,
        task_contract,
        reassessment: dict[str, Any],
        methodology_suggestion: dict[str, Any] | None,
        model_suggestion: dict[str, Any] | None,
    ) -> None:
        if hook_orchestrator is None:
            return
        payload = ResidualFollowupPayload(
            task_id=task_contract.task_id,
            contract_id=task_contract.contract_id,
            residual_reassessment=reassessment,
            methodology_advice=methodology_suggestion,
            model_advice=model_suggestion,
        )
        hook_orchestrator.emit("on_residual_followup", payload)

    def _emit_governance_check_event(
        self,
        *,
        hook_orchestrator: HookOrchestrator | None,
        task_contract,
        methodology_suggestion: dict[str, Any] | None,
        model_suggestion: dict[str, Any] | None,
        governance_decision: dict[str, Any],
    ) -> None:
        if hook_orchestrator is None:
            return
        payload = GovernanceCheckPayload(
            task_id=task_contract.task_id,
            contract_id=task_contract.contract_id,
            advice_summary={
                "methodology_advice": methodology_suggestion,
                "model_advice": model_suggestion,
                "issue_codes": [
                    str(issue.get("code"))
                    for issue in governance_decision.get("issues", [])
                    if isinstance(issue, dict) and issue.get("code")
                ],
            },
            governance_required=bool(governance_decision.get("requires_governance_override")),
        )
        hook_orchestrator.emit("on_governance_check", payload)

    def _emit_sandbox_required_event(
        self,
        *,
        hook_orchestrator: HookOrchestrator | None,
        task_contract,
        sandbox_decision: dict[str, Any],
    ) -> None:
        if hook_orchestrator is None:
            return
        payload = SandboxRequiredPayload(
            task_id=task_contract.task_id,
            contract_id=task_contract.contract_id,
            action=str(sandbox_decision.get("action") or "execute_step"),
            risk_level=str(sandbox_decision.get("risk_level") or task_contract.residual_risk_level.value),
            write_permission_level=str(
                sandbox_decision.get("write_permission_level")
                or task_contract.write_permission_level.value
            ),
        )
        hook_orchestrator.emit("on_sandbox_required", payload)

    def _with_residual_risk(self, task_contract, risk_level: str):
        return replace(task_contract, residual_risk_level=RiskLevel(risk_level))

    def _select_tool(
        self,
        task_type: str,
        candidate_tools: list[dict[str, Any]],
    ) -> str:
        preferred_by_task_type = {
            "retrieval": ("search_docs", "read_file"),
            "research": ("search_docs", "read_file"),
            "generation": ("search_docs", "read_file"),
            "planning": ("search_docs", "read_file"),
            "coding": ("write_file", "run_command", "read_file"),
            "review": ("read_file", "search_docs"),
            "qa": ("run_command", "read_file"),
            "execution": ("run_command", "write_file", "read_file"),
        }
        preferred = preferred_by_task_type.get(task_type, ())
        names = {tool["name"] for tool in candidate_tools}

        for tool_name in preferred:
            if tool_name in names:
                return tool_name
        return candidate_tools[0]["name"]

    def _read_relevant_journal_lessons(self, learning_journal, task_contract) -> list[dict[str, Any]]:
        if learning_journal is None:
            return []
        return list(
            learning_journal.read_relevant_lessons(
                task_type=task_contract.task_type.value,
                limit=2,
            )
        )

    def _append_learning_lesson(
        self,
        *,
        hook_orchestrator: HookOrchestrator,
        learning_journal,
        task_contract,
        execution_result: dict[str, Any],
        verification_report: dict[str, Any] | None,
        state_writeback_payload: dict[str, Any],
        sandbox_result: dict[str, Any] | None,
        rollback_result: dict[str, Any] | None,
        read_count: int,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        if learning_journal is None:
            return (
                {
                    "status": "disabled",
                    "read_count": read_count,
                    "written_entry_id": None,
                },
                None,
            )

        entry = learning_journal.build_lesson_entry(
            task_id=task_contract.task_id,
            task_type=task_contract.task_type.value,
            execution_result=execution_result,
            verification_report=verification_report,
            residual_snapshot=state_writeback_payload,
            sandbox_result=sandbox_result,
            rollback_result=rollback_result,
        )
        payload = JournalAppendPayload(
            task_id=task_contract.task_id,
            contract_id=task_contract.contract_id,
            lesson_entry=entry,
            source=str(entry["source"]),
        )

        def persist_journal_entry(event_payload: JournalAppendPayload) -> dict[str, Any]:
            return learning_journal.append_lesson(event_payload.lesson_entry)

        hook_orchestrator.register("on_journal_append", persist_journal_entry)
        try:
            results = hook_orchestrator.emit("on_journal_append", payload)
        finally:
            hook_orchestrator.unregister("on_journal_append", persist_journal_entry)

        appended = dict(results[-1])
        learning_journal_result = {
            "status": "written",
            "read_count": read_count,
            "written_entry_id": appended["entry_id"],
            "written_source": appended["source"],
        }
        journal_append_artifact = {
            "payload": self._to_json_value(payload),
            "journal_entry": appended,
            "learning_journal": learning_journal_result,
        }
        return learning_journal_result, journal_append_artifact

    def _apply_minimal_writeback(
        self,
        *,
        state_manager,
        state_writeback_payload: dict[str, Any],
        expected_version: int,
    ) -> dict[str, Any]:
        required_fields = {"task_id", "residual_risk", "followup_required", "governance_required"}
        if not required_fields.issubset(state_writeback_payload):
            return {
                "status": "skipped",
                "reason": "no_residual_writeback_payload",
            }

        try:
            updated = state_manager.apply_residual_writeback(
                state_writeback_payload,
                expected_version=expected_version,
            )
        except Exception as exc:
            task_id = state_writeback_payload.get("task_id")
            raise RuntimeError(
                f"failed to persist residual writeback for task '{task_id}': {exc}"
            ) from exc

        return {
            "status": "persisted",
            "task_id": updated.value.task_id,
            "version": updated.version,
        }

    def _to_json_value(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return {key: self._to_json_value(item) for key, item in asdict(value).items()}
        if isinstance(value, dict):
            return {str(key): self._to_json_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._to_json_value(item) for item in value]
        return value


