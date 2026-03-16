from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ActorConfig:
    character: str
    reference_image: Path


@dataclass(frozen=True)
class ProjectConfig:
    source_video: Path
    actors: dict[str, ActorConfig]


def load_project_config(config_path: Path) -> ProjectConfig:
    raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    actors = {
        name: ActorConfig(
            character=actor["character"],
            reference_image=Path(actor["reference_image"]),
        )
        for name, actor in raw_config["actors"].items()
    }

    return ProjectConfig(
        source_video=Path(raw_config["source_video"]),
        actors=actors,
    )
