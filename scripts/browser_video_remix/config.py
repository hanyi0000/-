from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ActorConfig:
    character: str
    reference_image: Path


@dataclass(frozen=True)
class SegmentationConfig:
    mode: str
    min_seconds: float
    threshold: float


@dataclass(frozen=True)
class SourceIdentityConfig:
    sample_images: list[Path]


@dataclass(frozen=True)
class LoraConfig:
    name: str
    weight: float


@dataclass(frozen=True)
class TargetRoleConfig:
    strategy: str
    prompt: str
    reference_images: list[Path]
    lora: LoraConfig | None


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
    executable_path: Path | None
    proxy_server: str | None


@dataclass(frozen=True)
class RunningHubConfig:
    workflow_url: str
    poll_interval_seconds: int


@dataclass(frozen=True)
class QualityAuditConfig:
    max_background_delta: float


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int


@dataclass(frozen=True)
class ProjectConfig:
    source_video: Path
    split: SplitConfig
    segmentation: SegmentationConfig
    chatgpt: ChatGptConfig
    browser: BrowserConfig
    runninghub: RunningHubConfig
    actors: dict[str, ActorConfig]
    source_identities: dict[str, SourceIdentityConfig]
    target_roles: dict[str, TargetRoleConfig]
    identity_mapping: dict[str, str]
    quality_audit: QualityAuditConfig
    retry: RetryConfig


def load_project_config(config_path: Path) -> ProjectConfig:
    raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    split = raw_config.get("split", {})
    segmentation = raw_config.get("segmentation", {})
    chatgpt = raw_config.get("chatgpt", {})
    browser = raw_config.get("browser", {})
    runninghub = raw_config.get("runninghub", {})
    quality_audit = raw_config.get("quality_audit", {})
    retry = raw_config.get("retry", {})
    actors = {
        name: ActorConfig(
            character=actor["character"],
            reference_image=Path(actor["reference_image"]),
        )
        for name, actor in raw_config["actors"].items()
    }
    source_identities = {
        name: SourceIdentityConfig(
            sample_images=[Path(image) for image in identity.get("sample_images", [])],
        )
        for name, identity in raw_config.get("source_identities", {}).items()
    }
    target_roles = {}
    for name, role in raw_config.get("target_roles", {}).items():
        lora = role.get("lora")
        target_roles[name] = TargetRoleConfig(
            strategy=role.get("strategy", "prompt_only"),
            prompt=role.get("prompt", ""),
            reference_images=[Path(image) for image in role.get("reference_images", [])],
            lora=(
                LoraConfig(
                    name=lora["name"],
                    weight=float(lora["weight"]),
                )
                if lora
                else None
            ),
        )

    return ProjectConfig(
        source_video=Path(raw_config["source_video"]),
        split=SplitConfig(
            mode=split.get("mode", "fixed_duration"),
            seconds=int(split.get("seconds", 0)),
        ),
        segmentation=SegmentationConfig(
            mode=segmentation.get("mode", split.get("mode", "fixed_duration")),
            min_seconds=float(segmentation.get("min_seconds", split.get("seconds", 0))),
            threshold=float(segmentation.get("threshold", 30.0)),
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
            executable_path=(
                Path(browser["executable_path"])
                if browser.get("executable_path")
                else None
            ),
            proxy_server=browser.get("proxy_server"),
        ),
        runninghub=RunningHubConfig(
            workflow_url=runninghub.get("workflow_url", ""),
            poll_interval_seconds=int(runninghub.get("poll_interval_seconds", 5)),
        ),
        actors=actors,
        source_identities=source_identities,
        target_roles=target_roles,
        identity_mapping={
            source_person_id: str(target_role_id)
            for source_person_id, target_role_id in raw_config.get("identity_mapping", {}).items()
        },
        quality_audit=QualityAuditConfig(
            max_background_delta=float(quality_audit.get("max_background_delta", 0.2)),
        ),
        retry=RetryConfig(
            max_attempts=int(retry.get("max_attempts", 3)),
        ),
    )
