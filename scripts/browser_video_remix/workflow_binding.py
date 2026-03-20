import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkflowBinding:
    workflow_id: str
    video_node_id: int | None
    reference_node_ids: list[int]
    optional_controls: dict[str, int]


def inspect_workflow_binding(workflow: dict[str, object]) -> WorkflowBinding:
    nodes = workflow.get("nodes")
    workflow_id = str(workflow.get("workflow_id", ""))
    if not isinstance(nodes, list):
        return WorkflowBinding(
            workflow_id=workflow_id,
            video_node_id=None,
            reference_node_ids=[],
            optional_controls={},
        )

    video_node_id: int | None = None
    reference_node_ids: list[int] = []
    optional_controls: dict[str, int] = {}

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        if not isinstance(node_id, int):
            continue

        haystack = json.dumps(node, ensure_ascii=False).lower()
        if video_node_id is None and "video" in haystack:
            video_node_id = node_id
        if "reference" in haystack and "image" in haystack:
            reference_node_ids.append(node_id)
        if "pose" in haystack and "pose" not in optional_controls:
            optional_controls["pose"] = node_id
        if "lora" in haystack:
            lora_name = _extract_lora_name(node)
            if lora_name:
                optional_controls[f"lora:{lora_name}"] = node_id

    return WorkflowBinding(
        workflow_id=workflow_id,
        video_node_id=video_node_id,
        reference_node_ids=reference_node_ids,
        optional_controls=optional_controls,
    )


def save_workflow_binding(path: Path, binding: WorkflowBinding) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "workflow_id": binding.workflow_id,
                "video_node_id": binding.video_node_id,
                "reference_node_ids": binding.reference_node_ids,
                "optional_controls": binding.optional_controls,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def load_workflow_binding(path: Path) -> WorkflowBinding:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return WorkflowBinding(
        workflow_id=str(raw["workflow_id"]),
        video_node_id=raw["video_node_id"],
        reference_node_ids=[int(node_id) for node_id in raw.get("reference_node_ids", [])],
        optional_controls={str(key): int(value) for key, value in raw.get("optional_controls", {}).items()},
    )


def _extract_lora_name(node: dict[str, object]) -> str | None:
    widgets_values = node.get("widgets_values")
    if isinstance(widgets_values, dict):
        for key in ("lora_name", "name"):
            value = widgets_values.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    for key in ("title", "name"):
        value = node.get(key)
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        if "lora" not in lowered:
            continue
        stripped = value.replace("LoRA", "").replace("lora", "").strip()
        normalized = stripped.replace(" ", "_")
        return normalized or None
    return None
