"""Exports clean trace.json and React Flow graph.json for web replay."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Optional

from keplix.engine.log_pruner import LogPruner
from keplix.graph.state import KeplixState, PlanContract


class TraceExporter:
    """Collects runtime execution milestones and exports JSON artifacts for the Next.js web replayer."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.pruner = LogPruner()

    def record_event(
        self,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
        status: str = "success",
    ) -> None:
        """Record an individual timeline event with timestamp and sanitized data."""
        # Sanitize any string fields for secrets
        clean_payload: dict[str, Any] = {}
        for k, v in payload.items():
            if isinstance(v, str):
                clean_payload[k] = self.pruner.redact_secrets(v)
            else:
                clean_payload[k] = v

        self.events.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "actor": actor,
            "status": status,
            "payload": clean_payload,
        })

    def export_trace(self, output_path: Path = Path("trace.json")) -> Path:
        """Serialize timeline trace events to JSON."""
        output_path.write_text(json.dumps(self.events, indent=2), encoding="utf-8")
        return output_path

    def export_graph(
        self,
        state: KeplixState,
        output_path: Path = Path("graph.json"),
    ) -> Path:
        """Export React Flow compatible node-and-edge graph structure."""
        nodes: list[dict[str, Any]] = [
            {
                "id": "supervisor",
                "type": "supervisorNode",
                "data": {"label": "Dynamic Supervisor", "role": "planner"},
                "position": {"x": 250, "y": 50},
            }
        ]
        edges: list[dict[str, Any]] = []

        plan: Optional[PlanContract] = state.get("plan")
        if plan:
            x_offset = 50
            for idx, task in enumerate(plan.tasks):
                node_id = f"worker_{task.task_id}"
                nodes.append({
                    "id": node_id,
                    "type": "workerNode",
                    "data": {
                        "label": f"Worker: {task.role}",
                        "taskId": task.task_id,
                        "status": str(task.status),
                        "targets": task.target_files,
                    },
                    "position": {"x": x_offset + (idx * 220), "y": 200},
                })
                edges.append({
                    "id": f"edge_sup_{node_id}",
                    "source": "supervisor",
                    "target": node_id,
                    "animated": True,
                })

        graph_payload = {
            "goal": state.get("goal", ""),
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "total_events": len(self.events),
            },
        }

        output_path.write_text(json.dumps(graph_payload, indent=2), encoding="utf-8")
        return output_path

