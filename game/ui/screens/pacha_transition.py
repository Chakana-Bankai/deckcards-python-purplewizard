from __future__ import annotations

from game.ui.screens.scene_fusion import SceneFusionScreen


class PachaTransitionScreen:
    """Compatibility wrapper that routes legacy transition calls through SceneFusionScreen."""

    def __init__(self, app, title, next_fn, lore_line="Era una vez... la Trama susurro un cambio.", hint="Pulsa cualquier tecla", min_seconds=0.9, auto_seconds=6.0):
        self._scene = SceneFusionScreen(
            app,
            title=str(title or "Transicion"),
            dialogue=str(lore_line or "La Trama cambia de forma."),
            lore_line=str(hint or "Pulsa cualquier tecla"),
            next_fn=next_fn,
            background="Ruinas Chakana",
            biome_layer=None,
            portrait_key="chakana_mage_portrait",
            portrait_group="avatar",
            speaker_label="CHAKANA",
            set_label="TRANSICION RITUAL",
            min_seconds=float(min_seconds),
            auto_seconds=float(auto_seconds),
        )

    def on_enter(self):
        self._scene.on_enter()

    def handle_event(self, event):
        self._scene.handle_event(event)

    def update(self, dt):
        self._scene.update(dt)

    def render(self, s):
        self._scene.render(s)
