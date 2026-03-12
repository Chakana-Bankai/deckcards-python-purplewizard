from __future__ import annotations


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    ratio = _clamp(ratio, 0.0, 1.0)
    return (
        int(a[0] * (1.0 - ratio) + b[0] * ratio),
        int(a[1] * (1.0 - ratio) + b[1] * ratio),
        int(a[2] * (1.0 - ratio) + b[2] * ratio),
    )


def build_material_tones(palette, archetype: str, shape_profile: dict[str, float | str]) -> dict[str, tuple[int, int, int, int]]:
    top, mid, low, acc = palette
    detail_density = float(shape_profile.get('detail_density', 0.55))
    angularity = float(shape_profile.get('angularity', 0.5))
    curve_bias = float(shape_profile.get('curve_bias', 0.5))

    if archetype == 'archon':
        cloth = _mix(top, mid, 0.26)
        cloth_dark = _mix(top, (0, 0, 0), 0.42)
        trim = _mix(acc, mid, 0.18)
        metal = _mix(acc, (255, 255, 255), 0.22)
        wood = _mix(low, top, 0.32)
        rune = _mix(acc, (255, 255, 255), 0.16)
    elif archetype == 'guide_mage':
        cloth = _mix(mid, low, 0.34)
        cloth_dark = _mix(top, low, 0.28)
        trim = _mix(acc, (255, 255, 255), 0.12)
        metal = _mix(acc, mid, 0.28)
        wood = _mix(low, top, 0.20)
        rune = _mix(acc, (255, 255, 255), 0.24)
    else:
        cloth = _mix(mid, top, 0.24)
        cloth_dark = _mix(top, (0, 0, 0), 0.28)
        trim = _mix(acc, (255, 255, 255), 0.18)
        metal = _mix(acc, (255, 255, 255), 0.32)
        wood = _mix(low, top, 0.18)
        rune = _mix(acc, mid, 0.14)

    shadow = _mix(top, (0, 0, 0), 0.38 + angularity * 0.08)
    skin = _mix(mid, (255, 255, 255), 0.08 + curve_bias * 0.06)
    glow = _mix(acc, (255, 255, 255), 0.10 + detail_density * 0.08)

    return {
        'cloth': (*cloth, 255),
        'cloth_dark': (*cloth_dark, 255),
        'trim': (*trim, 255),
        'metal': (*metal, 255),
        'wood': (*wood, 255),
        'rune': (*rune, 255),
        'shadow': (*shadow, 255),
        'skin': (*skin, 255),
        'glow': (*glow, 255),
    }
