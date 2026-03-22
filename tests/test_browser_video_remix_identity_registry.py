from pathlib import Path

from scripts.browser_video_remix.config import (
    LoraConfig,
    SourceIdentityConfig,
    TargetRoleConfig,
)
from scripts.browser_video_remix.identity_registry import build_identity_registry


def test_build_role_execution_plan_prefers_hybrid_when_assets_exist() -> None:
    registry = build_identity_registry(
        source_identities={"actor_a": SourceIdentityConfig(sample_images=[Path("a.png")])},
        target_roles={
            "jett": TargetRoleConfig(
                strategy="hybrid",
                prompt="valorant jett",
                reference_images=[Path("jett.png")],
                lora=LoraConfig(name="jett_v1", weight=0.8),
            )
        },
        identity_mapping={"actor_a": "jett"},
    )

    plan = registry.role_plan_for("actor_a")

    assert plan.target_role_id == "jett"
    assert plan.strategy == "hybrid"
    assert plan.lora_name == "jett_v1"
