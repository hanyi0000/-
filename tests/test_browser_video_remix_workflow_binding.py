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


def test_inspect_workflow_binding_prefers_real_video_upload_node_over_earlier_video_mentions() -> None:
    workflow = {
        "workflow_id": "2034283586668466178",
        "nodes": [
            {
                "id": 50,
                "type": "WanVideoModel",
                "inputs": [
                    {"name": "model"},
                    {"name": "block_swap_args"},
                ],
            },
            {
                "id": 57,
                "type": "LoadImage",
                "widgets": [
                    {"name": "image"},
                    {"name": "upload"},
                ],
                "inputs": [
                    {"name": "image"},
                    {"name": "upload"},
                ],
            },
            {
                "id": 63,
                "title": "Load Video (Upload)",
                "type": "VHS_LoadVideo",
                "widgets": [
                    {"name": "video"},
                    {"name": "choose video to upload"},
                ],
                "widgets_values": {
                    "video": "existing.mp4",
                    "videopreview": {
                        "params": {
                            "filename": "existing.mp4",
                            "type": "input",
                        }
                    },
                },
                "inputs": [
                    {"name": "video"},
                    {"name": "force_rate"},
                ],
            },
        ],
    }

    binding = inspect_workflow_binding(workflow)

    assert binding.video_node_id == 63
    assert binding.reference_node_ids == [57]
