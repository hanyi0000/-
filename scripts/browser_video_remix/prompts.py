def render_chatgpt_prompt(scene_description: str, mappings: dict[str, str]) -> str:
    lines = [
        "Replace the people in this frame while preserving composition, lighting, and camera angle.",
        f"Scene: {scene_description}",
    ]

    for actor_name, character_name in mappings.items():
        lines.append(f"Replace {actor_name} with {character_name}.")

    return "\n".join(lines)
