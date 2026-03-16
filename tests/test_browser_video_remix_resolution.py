from scripts.browser_video_remix.resolution import choose_resize_action


def test_choose_resize_action_returns_none_for_matching_ratio() -> None:
    action = choose_resize_action(
        clip_width=1920,
        clip_height=1080,
        ref_width=1024,
        ref_height=576,
        target_width=1920,
        target_height=1080,
    )

    assert action == "none"
