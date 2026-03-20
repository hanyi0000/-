from pathlib import Path

from .manifest import ClipTask, build_clip_task


def build_shot_tasks(
    source_video: Path,
    boundaries: list[tuple[int, int]],
    shots_dir: Path,
) -> list[ClipTask]:
    del source_video

    tasks: list[ClipTask] = []
    for index, (start_ms, end_ms) in enumerate(boundaries, start=1):
        clip_id = f"clip-{index:04d}"
        tasks.append(
            build_clip_task(
                clip_id=clip_id,
                clip_path=shots_dir / f"{clip_id}.mp4",
                frame_path=Path(""),
                width=0,
                height=0,
                start_ms=start_ms,
                end_ms=end_ms,
            )
        )
    return tasks


def detect_shot_boundaries(
    source_video: Path,
    threshold: float = 30.0,
    min_seconds: float = 1.0,
) -> list[tuple[int, int]]:
    from scenedetect import ContentDetector, SceneManager, open_video

    video = open_video(str(source_video))
    frame_rate = float(video.frame_rate) if video.frame_rate else 0.0
    min_scene_len = max(1, int(round(min_seconds * frame_rate))) if frame_rate else 1

    scene_manager = SceneManager()
    scene_manager.add_detector(
        ContentDetector(
            threshold=threshold,
            min_scene_len=min_scene_len,
        )
    )
    scene_manager.detect_scenes(video)
    scenes = scene_manager.get_scene_list()

    if not scenes:
        duration = getattr(video, "duration", None)
        if duration is None:
            return []
        return [(0, int(duration.get_seconds() * 1000))]

    return [
        (int(start_time.get_seconds() * 1000), int(end_time.get_seconds() * 1000))
        for start_time, end_time in scenes
    ]
