import json
from pathlib import Path

from scripts.browser_video_remix.workflow_binding import (
    WorkflowBinding,
    inspect_workflow_binding,
    load_workflow_binding,
    save_workflow_binding,
)


def test_inspect_wan_workflow_finds_video_reference_and_optional_control_nodes() -> None:
    workflow = json.loads(
        Path("D:/codex-worktrees/browser-video-remix-phase2/tests/fixtures/runninghub_wan_animate_workflow.json").read_text(
            encoding="utf-8"
        )
    )

    binding = inspect_workflow_binding(workflow)

    assert binding.video_node_id is not None
    assert len(binding.reference_node_ids) >= 2
    assert "pose" in binding.optional_controls


def test_save_and_load_workflow_binding_round_trip(tmp_path: Path) -> None:
    binding_path = tmp_path / "binding.json"
    binding = WorkflowBinding(
        workflow_id="2034283586668466178",
        video_node_id=63,
        reference_node_ids=[57, 58],
        optional_controls={"pose": 77, "lora:jett_v1": 88},
    )

    save_workflow_binding(binding_path, binding)
    restored = load_workflow_binding(binding_path)

    assert restored == binding
