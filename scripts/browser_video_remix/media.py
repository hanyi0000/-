from dataclasses import dataclass
from pathlib import Path


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


def build_split_command(source_video: Path, output_pattern: Path, seconds: int) -> list[str]:
    return [
        "ffmpeg",
        "-i",
        source_video.as_posix(),
        "-f",
        "segment",
        "-segment_time",
        str(seconds),
        output_pattern.as_posix(),
    ]


def build_frame_command(clip_path: Path, frame_path: Path) -> list[str]:
    return [
        "ffmpeg",
        "-i",
        clip_path.as_posix(),
        "-frames:v",
        "1",
        frame_path.as_posix(),
    ]
