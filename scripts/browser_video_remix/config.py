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
class BrowserConfig:
    profile_dir: Path
    headless: bool


@dataclass(frozen=True)
class RunningHubConfig:
    workflow_url: str


@dataclass(frozen=True)
class ProjectConfig:
    source_video: Path
    split: SplitConfig
    browser: BrowserConfig
    runninghub: RunningHubConfig
    actors: dict[str, ActorConfig]


def load_project_config(config_path: Path) -> ProjectConfig:
    raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    split = raw_config.get("split", {})
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
        browser=BrowserConfig(
            profile_dir=Path(browser.get("profile_dir", "browser/profile")),
            headless=bool(browser.get("headless", False)),
        ),
        runninghub=RunningHubConfig(
            workflow_url=runninghub.get("workflow_url", ""),
        ),
        actors=actors,
    )
