from pathlib import Path

from scripts.browser_video_remix.face_analysis import FaceEmbedding, match_known_identities


def test_match_known_identities_returns_person_id_when_similarity_is_high() -> None:
    known_identities = {
        "actor_a": [FaceEmbedding(frame_path=Path("a.png"), vector=[0.92, 0.08])],
        "actor_b": [FaceEmbedding(frame_path=Path("b.png"), vector=[0.18, 0.82])],
    }

    matched_person_id = match_known_identities(
        candidate=FaceEmbedding(frame_path=Path("candidate.png"), vector=[0.90, 0.10]),
        known_identities=known_identities,
        similarity_threshold=0.95,
    )

    assert matched_person_id == "actor_a"
