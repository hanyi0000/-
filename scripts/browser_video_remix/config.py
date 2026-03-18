from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ActorConfig:
    character: str
    reference_image: Path


@dataclass(frozen=True)
class SplitConfig:
    mode: str
    seconds: int


@dataclass(frozen=True)
class ChatGptConfig:
    start_url: str
    prompt_timeout_ms: int


@dataclass(frozen=True)
class BrowserConfig:
    profile_dir: Path
    downloads_dir: Path
    default_timeout_ms: int
    headless: bool


@dataclass(frozen=True)
class RunningHubConfig:
    workflow_url: str
    poll_interval_seconds: int


@dataclass(frozen=True)
class ProjectConfig:
    source_video: Path
    split: SplitConfig
    chatgpt: ChatGptConfig
    browser: BrowserConfig
    runninghub: RunningHubConfig
    actors: dict[str, ActorConfig]


def load_project_config(config_path: Path) -> ProjectConfig:
    raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    split = raw_config.get("split", {})
    chatgpt = raw_config.get("chatgpt", {})
    browser = raw_config.get("browser", {})
    runninghub = raw_config.get("runninghub", {})
    actors = {
        name: ActorConfig(
            character=actor["character"],
            reference_image=Path(actor["reference_image"]),
        )
        for name, actor in raw_config["actors"].items()
    }

    return ProjectConfig(
        source_video=Path(raw_config["source_video"]),
        split=SplitConfig(
            mode=split.get("mode", "fixed_duration"),
            seconds=int(split.get("seconds", 0)),
        ),
        chatgpt=ChatGptConfig(
            start_url=chatgpt.get("start_url", ""),
            prompt_timeout_ms=int(chatgpt.get("prompt_timeout_ms", 90000)),
        ),
        browser=BrowserConfig(
            profile_dir=Path(browser.get("profile_dir", "browser/profile")),
            downloads_dir=Path(browser.get("downloads_dir", "work/downloads")),
            default_timeout_ms=int(browser.get("default_timeout_ms", 15000)),
            headless=bool(browser.get("headless", False)),
        ),
        runninghub=RunningHubConfig(
            workflow_url=runninghub.get("workflow_url", ""),
            poll_interval_seconds=int(runninghub.get("poll_interval_seconds", 5)),
        ),
        actors=actors,
    )
