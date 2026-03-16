from scripts.browser_video_remix.media import parse_ffprobe_video_stream


def test_parse_ffprobe_video_stream_reads_dimensions() -> None:
    stream = {
        "width": 1920,
        "height": 1080,
        "r_frame_rate": "24/1",
        "duration": "3.2",
    }

    metadata = parse_ffprobe_video_stream(stream)

    assert metadata.width == 1920
    assert metadata.height == 1080
    assert metadata.frame_rate == 24.0
