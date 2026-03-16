def filter_pending_clip_ids(
    clip_ids: list[str],
    state_map: dict[str, dict[str, str]],
) -> list[str]:
    finished_states = {"done", "runninghub_complete"}

    return [
        clip_id
        for clip_id in clip_ids
        if state_map.get(clip_id, {}).get("state") not in finished_states
    ]
