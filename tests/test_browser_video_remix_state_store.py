from pathlib import Path

from scripts.browser_video_remix.state_store import FileStateStore


def test_state_store_persists_clip_state(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path / "tasks.json")

    store.update("clip-0001", state="chatgpt_complete")

    reloaded = FileStateStore(tmp_path / "tasks.json")

    assert reloaded.get("clip-0001")["state"] == "chatgpt_complete"
