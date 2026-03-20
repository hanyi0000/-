from .face_analysis import FaceObservation


def choose_best_face_frame(observations: list[FaceObservation]) -> FaceObservation:
    if not observations:
        raise ValueError("observations must not be empty")
    return max(observations, key=lambda item: item.score)
