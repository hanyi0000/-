from scripts.browser_video_remix.resume import filter_pending_clip_ids


def test_filter_pending_clip_ids_skips_completed_jobs() -> None:
    clip_ids = ["clip-0001", "clip-0002", "clip-0003"]
    state_map = {
        "clip-0001": {"state": "done"},
        "clip-0002": {"state": "runninghub_complete"},
        "clip-0003": {"state": "submit_failed"},
    }

    assert filter_pending_clip_ids(clip_ids, state_map) == ["clip-0003"]
