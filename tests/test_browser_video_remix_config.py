from pathlib import Path

from scripts.browser_video_remix.config import load_project_config


def test_load_project_config_reads_actor_mapping(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "source_video: input/source.mp4\n"
        "actors:\n"
        "  actor_a:\n"
        "    character: jett\n"
        "    reference_image: input/jett.png\n",
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.source_video.as_posix() == "input/source.mp4"
    assert config.actors["actor_a"].character == "jett"


def test_load_project_config_reads_browser_and_split_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "source_video: input/source.mp4\n"
        "split:\n"
        "  mode: fixed_duration\n"
        "  seconds: 2\n"
        "browser:\n"
        "  profile_dir: browser/profile\n"
        "  headless: false\n"
        "runninghub:\n"
        "  workflow_url: https://example.com/workflow\n"
        "actors:\n"
        "  actor_a:\n"
        "    character: jett\n"
        "    reference_image: input/jett.png\n",
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.split.mode == "fixed_duration"
    assert config.split.seconds == 2
    assert config.browser.profile_dir.as_posix() == "browser/profile"
    assert config.runninghub.workflow_url == "https://example.com/workflow"


def test_load_project_config_reads_live_browser_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "source_video: input/source.mp4\n"
        "chatgpt:\n"
        "  start_url: https://chatgpt.com/g/test\n"
        "  prompt_timeout_ms: 90000\n"
        "browser:\n"
        "  profile_dir: browser/profile\n"
        "  downloads_dir: work/downloads\n"
        "  default_timeout_ms: 15000\n"
        "  headless: false\n"
        "runninghub:\n"
        "  workflow_url: https://example.com/workflow\n"
        "  poll_interval_seconds: 5\n"
        "actors:\n"
        "  actor_a:\n"
        "    character: jett\n"
        "    reference_image: input/jett.png\n",
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.chatgpt.start_url == "https://chatgpt.com/g/test"
    assert config.chatgpt.prompt_timeout_ms == 90000
    assert config.browser.downloads_dir.as_posix() == "work/downloads"
    assert config.browser.default_timeout_ms == 15000
    assert config.runninghub.poll_interval_seconds == 5
