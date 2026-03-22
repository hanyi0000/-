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

    video_candidates: list[tuple[int, int]] = []
    reference_node_ids: list[int] = []
    optional_controls: dict[str, int] = {}

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        if not isinstance(node_id, int):
            continue

        haystack = json.dumps(node, ensure_ascii=False).lower()
        video_score = _score_video_node(node)
        if video_score > 0:
            video_candidates.append((video_score, node_id))
        if _is_reference_image_node(node):
            reference_node_ids.append(node_id)
        if "pose" in haystack and "pose" not in optional_controls:
            optional_controls["pose"] = node_id
        if "lora" in haystack:
            lora_name = _extract_lora_name(node)
            if lora_name:
                optional_controls[f"lora:{lora_name}"] = node_id

    video_node_id = None
    if video_candidates:
        video_node_id = max(video_candidates, key=lambda item: (item[0], -item[1]))[1]

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


def _score_video_node(node: dict[str, object]) -> int:
    text_parts = _collect_node_text_parts(node)
    joined_text = " ".join(text_parts)
    widget_names = _collect_named_entries(node.get("widgets"))
    input_names = _collect_named_entries(node.get("inputs"))
    widget_values = node.get("widgets_values")

    score = 0
    if any(token in joined_text for token in ("vhs_loadvideo", "loadvideo", "load video")):
        score += 100
    if "video" in joined_text or "视频" in joined_text:
        score += 20
    if any("upload" in name for name in widget_names + input_names):
        score += 20
    if any("video" in name for name in widget_names + input_names):
        score += 30
    if isinstance(widget_values, dict) and any(key in widget_values for key in ("video", "videopreview")):
        score += 20

    if "model" in joined_text and "upload" not in joined_text and "load" not in joined_text:
        score -= 20
    return score


def _is_reference_image_node(node: dict[str, object]) -> bool:
    text_parts = _collect_node_text_parts(node)
    joined_text = " ".join(text_parts)
    widget_names = _collect_named_entries(node.get("widgets"))
    input_names = _collect_named_entries(node.get("inputs"))
    names = widget_names + input_names

    if any(token in joined_text for token in ("background", "bg_", " mask", "mask ", "pose", "output")):
        return False
    if "背景" in joined_text or "遮罩" in joined_text or "姿态" in joined_text or "输出" in joined_text:
        return False

    has_image_name = any("image" in name for name in names)
    has_upload_name = any("upload" in name for name in names)
    if "reference" in joined_text and "image" in joined_text:
        return True
    if any(token in joined_text for token in ("loadimage", "load image")):
        if not names:
            return True
        if has_image_name:
            return True
    if "图像" in joined_text and "参考" in joined_text:
        return True
    return has_image_name and has_upload_name


def _collect_node_text_parts(node: dict[str, object]) -> list[str]:
    text_parts: list[str] = []
    for key in ("title", "name", "type", "class_type"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            text_parts.append(value.strip().lower())
    text_parts.extend(_collect_named_entries(node.get("widgets")))
    text_parts.extend(_collect_named_entries(node.get("inputs")))
    return text_parts


def _collect_named_entries(entries: object) -> list[str]:
    if not isinstance(entries, list):
        return []

    values: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if isinstance(name, str) and name.strip():
            values.append(name.strip().lower())
    return values
