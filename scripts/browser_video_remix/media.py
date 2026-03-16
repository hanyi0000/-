from dataclasses import dataclass


@dataclass(frozen=True)
class VideoMetadata:
    width: int
    height: int
    frame_rate: float
    duration: float


def parse_ffprobe_video_stream(stream: dict[str, str | int]) -> VideoMetadata:
    numerator, denominator = str(stream["r_frame_rate"]).split("/")

    return VideoMetadata(
        width=int(stream["width"]),
        height=int(stream["height"]),
        frame_rate=float(numerator) / float(denominator),
        duration=float(stream["duration"]),
    )
