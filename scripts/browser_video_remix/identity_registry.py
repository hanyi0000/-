from dataclasses import dataclass
from pathlib import Path

from .config import SourceIdentityConfig, TargetRoleConfig


@dataclass(frozen=True)
class RoleExecutionPlan:
    source_person_id: str
    target_role_id: str
    strategy: str
    prompt: str
    reference_images: list[Path]
    lora_name: str | None
    lora_weight: float | None


class IdentityRegistry:
    def __init__(
        self,
        *,
        source_identities: dict[str, SourceIdentityConfig],
        target_roles: dict[str, TargetRoleConfig],
        identity_mapping: dict[str, str],
    ) -> None:
        self._source_identities = source_identities
        self._target_roles = target_roles
        self._identity_mapping = identity_mapping

    def role_plan_for(self, source_person_id: str) -> RoleExecutionPlan:
        if source_person_id not in self._source_identities:
            raise KeyError(source_person_id)
        target_role_id = self._identity_mapping[source_person_id]
        target_role = self._target_roles[target_role_id]
        return RoleExecutionPlan(
            source_person_id=source_person_id,
            target_role_id=target_role_id,
            strategy=target_role.strategy,
            prompt=target_role.prompt,
            reference_images=list(target_role.reference_images),
            lora_name=None if target_role.lora is None else target_role.lora.name,
            lora_weight=None if target_role.lora is None else target_role.lora.weight,
        )


def build_identity_registry(
    *,
    source_identities: dict[str, SourceIdentityConfig],
    target_roles: dict[str, TargetRoleConfig],
    identity_mapping: dict[str, str],
) -> IdentityRegistry:
    return IdentityRegistry(
        source_identities=source_identities,
        target_roles=target_roles,
        identity_mapping=identity_mapping,
    )
