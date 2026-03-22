from dataclasses import dataclass
from pathlib import Path
from math import sqrt


@dataclass(frozen=True)
class FaceObservation:
    frame_path: Path
    person_id: str | None
    score: float
    confidence: float


@dataclass(frozen=True)
class FaceEmbedding:
    frame_path: Path
    vector: list[float]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    numerator = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=False))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def match_known_identities(
    *,
    candidate: FaceEmbedding,
    known_identities: dict[str, list[FaceEmbedding]],
    similarity_threshold: float,
) -> str | None:
    best_person_id: str | None = None
    best_similarity = similarity_threshold
    for person_id, embeddings in known_identities.items():
        for embedding in embeddings:
            similarity = cosine_similarity(candidate.vector, embedding.vector)
            if similarity >= best_similarity:
                best_person_id = person_id
                best_similarity = similarity
    return best_person_id


class FaceAnalyzer:
    def detect_faces(self, frame_path: Path) -> list[FaceObservation]:
        del frame_path
        return []
