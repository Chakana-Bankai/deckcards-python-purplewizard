from __future__ import annotations

import pygame


class IconGenerator:
    """Generate unified symbolic icons for UI semantics."""

    def render(self, icon_name: str, size: tuple[int, int], color: tuple[int, int, int] | None = None) -> pygame.Surface:
        w, h = max(12, int(size[0])), max(12, int(size[1]))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        c = tuple(int(v) for v in (color or (220, 210, 240)))
        px = max(1, w // 16)
        cx, cy = w // 2, h // 2
        k = str(icon_name or 'unknown').lower()

        if k in {'damage', 'sword'}:
            pygame.draw.line(s, c, (int(w*0.2), int(h*0.8)), (int(w*0.8), int(h*0.2)), max(1, px+1))
            pygame.draw.polygon(s, c, [(int(w*0.72), int(h*0.2)), (int(w*0.86), int(h*0.14)), (int(w*0.80), int(h*0.30))])
        elif k in {'block', 'shield'}:
            pygame.draw.polygon(s, c, [(cx, int(h*0.1)), (int(w*0.82), int(h*0.3)), (int(w*0.72), int(h*0.82)), (cx, int(h*0.94)), (int(w*0.28), int(h*0.82)), (int(w*0.18), int(h*0.3))], max(1, px+1))
        elif k in {'energy', 'bolt'}:
            pygame.draw.polygon(s, c, [(int(w*0.58), int(h*0.08)), (int(w*0.32), int(h*0.52)), (int(w*0.55), int(h*0.52)), (int(w*0.42), int(h*0.92)), (int(w*0.72), int(h*0.45)), (int(w*0.50), int(h*0.45))])
        elif k in {'harmony', 'ritual', 'star'}:
            pygame.draw.polygon(s, c, [(cx, int(h*0.08)), (int(w*0.66), int(h*0.34)), (int(w*0.92), cy), (int(w*0.66), int(h*0.66)), (cx, int(h*0.92)), (int(w*0.34), int(h*0.66)), (int(w*0.08), cy), (int(w*0.34), int(h*0.34))], max(1, px))
        elif k in {'rupture', 'crack'}:
            pygame.draw.lines(s, c, False, [(int(w*0.22), int(h*0.12)), (int(w*0.48), int(h*0.44)), (int(w*0.34), int(h*0.56)), (int(w*0.76), int(h*0.90))], max(1, px+1))
        elif k in {'scry', 'eye'}:
            pygame.draw.ellipse(s, c, (int(w*0.1), int(h*0.28), int(w*0.8), int(h*0.44)), max(1, px))
            pygame.draw.circle(s, c, (cx, cy), max(1, int(w*0.12)))
        elif k in {'draw', 'scroll'}:
            pygame.draw.rect(s, c, (int(w*0.22), int(h*0.16), int(w*0.56), int(h*0.68)), max(1, px), border_radius=max(1, px))
            pygame.draw.line(s, c, (int(w*0.34), int(h*0.34)), (int(w*0.66), int(h*0.34)), max(1, px))
            pygame.draw.line(s, c, (int(w*0.34), int(h*0.50)), (int(w*0.62), int(h*0.50)), max(1, px))
        elif k in {'gold'}:
            pygame.draw.circle(s, c, (cx, cy), int(min(w,h)*0.36), max(1, px))
            pygame.draw.circle(s, c, (cx, cy), max(1, px), 0)
        elif k in {'xp', 'level'}:
            pygame.draw.circle(s, c, (cx, cy), int(min(w,h)*0.34), max(1, px))
            pygame.draw.line(s, c, (cx, int(h*0.22)), (cx, int(h*0.78)), max(1, px))
            pygame.draw.line(s, c, (int(w*0.22), cy), (int(w*0.78), cy), max(1, px))
        elif k in {'relic'}:
            pygame.draw.polygon(s, c, [(cx, int(h*0.1)), (int(w*0.76), int(h*0.42)), (int(w*0.64), int(h*0.88)), (int(w*0.36), int(h*0.88)), (int(w*0.24), int(h*0.42))], max(1, px))
        elif k in {'event'}:
            pygame.draw.circle(s, c, (cx, cy), int(min(w,h)*0.32), max(1, px))
            pygame.draw.polygon(s, c, [(cx, int(h*0.18)), (int(w*0.62), int(h*0.52)), (int(w*0.34), int(h*0.52))])
        elif k in {'shop'}:
            pygame.draw.rect(s, c, (int(w*0.22), int(h*0.3), int(w*0.56), int(h*0.46)), max(1, px), border_radius=max(1, px))
            pygame.draw.arc(s, c, (int(w*0.30), int(h*0.16), int(w*0.40), int(h*0.28)), 3.14, 6.20, max(1, px))
        elif k in {'boss'}:
            pygame.draw.polygon(s, c, [(cx, int(h*0.08)), (int(w*0.88), int(h*0.30)), (int(w*0.74), int(h*0.90)), (int(w*0.26), int(h*0.90)), (int(w*0.12), int(h*0.30))], max(1, px+1))
        elif k in {'pack'}:
            pygame.draw.rect(s, c, (int(w*0.2), int(h*0.2), int(w*0.6), int(h*0.6)), max(1, px), border_radius=max(1, px))
            pygame.draw.line(s, c, (cx, int(h*0.2)), (cx, int(h*0.8)), max(1, px))
            pygame.draw.line(s, c, (int(w*0.2), cy), (int(w*0.8), cy), max(1, px))
        else:
            pygame.draw.circle(s, c, (cx, cy), int(min(w,h)*0.28), max(1, px))
        return s
