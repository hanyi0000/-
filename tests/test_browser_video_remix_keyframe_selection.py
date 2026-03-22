from pathlib import Path

from scripts.browser_video_remix.face_analysis import FaceObservation
from scripts.browser_video_remix.keyframe_selection import choose_best_face_frame


def test_choose_best_face_frame_prefers_large_sharp_frontal_face() -> None:
    candidates = [
        FaceObservation(frame_path=Path("a.png"), person_id="actor_a", score=0.42, confidence=0.70),
        FaceObservation(frame_path=Path("b.png"), person_id="actor_a", score=0.88, confidence=0.93),
        FaceObservation(frame_path=Path("c.png"), person_id="actor_a", score=0.61, confidence=0.81),
    ]

    selected = choose_best_face_frame(candidates)

    assert selected.frame_path == Path("b.png")
