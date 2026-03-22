from scripts.browser_video_remix.prompts import render_chatgpt_prompt


def test_render_chatgpt_prompt_includes_all_actor_mappings() -> None:
    prompt = render_chatgpt_prompt(
        scene_description="cinematic indoor dialogue scene",
        mappings={"actor_a": "jett", "actor_b": "sage"},
    )

    assert "actor_a" in prompt
    assert "jett" in prompt
    assert "actor_b" in prompt
    assert "sage" in prompt
