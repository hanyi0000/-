def choose_resize_action(
    clip_width: int,
    clip_height: int,
    ref_width: int,
    ref_height: int,
    target_width: int,
    target_height: int,
) -> str:
    clip_ratio = clip_width / clip_height
    ref_ratio = ref_width / ref_height
    target_ratio = target_width / target_height

    if round(clip_ratio, 4) == round(ref_ratio, 4) == round(target_ratio, 4):
        return "none"

    return "pad"
