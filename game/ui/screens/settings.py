import pygame

from game.ui.theme import UI_THEME


class SettingsScreen:
    SECTIONS = ["General", "Audio", "Visual", "Combate", "Accesibilidad", "Diagnostico"]

    def __init__(self, app, return_screen=None):
        self.app = app
        self.return_screen = return_screen
        self.section_idx = 0
        self.progress = ""

        self.left_nav_rect = pygame.Rect(58, 124, 280, 820)
        self.content_rect = pygame.Rect(356, 124, 1506, 820)
        self.back_rect = pygame.Rect(58, 964, 220, 52)
        self.apply_rect = pygame.Rect(1642, 964, 220, 52)

        self.row_actions = []
        self.section_actions = []
        self.active_preview = None
        self.preview_saved_context = None

        self._ensure_defaults()

    def _ensure_defaults(self):
        s = self.app.user_settings
        s.setdefault("ui_scale", 1.0)
        s.setdefault("resolution", "1920x1080")
        s.setdefault("master_volume", 1.0)
        s.setdefault("stinger_volume", 0.8)
        s.setdefault("music_muted", False)
        s.setdefault("sfx_muted", False)

        s.setdefault("hologram_intensity", 0.7)
        s.setdefault("enemy_rgb_intensity", 0.6)
        s.setdefault("ui_glow_intensity", 0.7)
        s.setdefault("hover_anim_intensity", 0.7)
        s.setdefault("contrast_mode", False)
        s.setdefault("particles_quality", "high")

        s.setdefault("animation_speed", 1.0)
        s.setdefault("tooltip_visibility", True)
        s.setdefault("icon_legend_visibility", False)
        s.setdefault("confirm_end_turn", False)
        s.setdefault("card_hover_scale_preset", "medium")

        s.setdefault("text_scale", 1.0)
        s.setdefault("icon_scale", 1.0)
        s.setdefault("high_contrast", False)
        s.setdefault("reduced_fx", False)

    def _audio_engine(self):
        return getattr(self.app.music, "engine", None)

    def _audio_entries(self):
        eng = self._audio_engine()
        if eng is None:
            return []

        music_entries = [
            ("menu", "menu", "a"),
            ("map", "map_kay", "a"),
            ("shop", "shop", "a"),
            ("combat", "combat", "a"),
            ("boss", "combat_boss", "a"),
            ("studio_logo", "studio_intro", "stinger"),
        ]
        stingers = [
            ("combat_start", "combat_start"),
            ("boss_reveal", "boss_reveal"),
            ("reward", "relic_gain"),
            ("victory", "victory"),
            ("defeat", "defeat"),
            ("relic_gain", "relic_gain"),
            ("civilization_reveal", "relic_gain"),
        ]

        items = eng._manifest.get("items", {}) if isinstance(eng._manifest, dict) else {}
        out = []
        for label, ctx, var in music_entries:
            if var == "stinger":
                item_id = f"stinger_{ctx}"
                row = items.get(item_id, {}) if isinstance(items, dict) else {}
                path = str((row or {}).get("file_path", ""))
                out.append({"kind": "stinger", "label": label, "id": ctx, "path": path})
            else:
                item_id = f"{ctx}_{var}"
                row = items.get(item_id, {}) if isinstance(items, dict) else {}
                path = str((row or {}).get("file_path", ""))
                out.append({"kind": "music", "label": label, "id": ctx, "variant": var, "path": path})

        for label, sid in stingers:
            item_id = f"stinger_{sid}"
            row = items.get(item_id, {}) if isinstance(items, dict) else {}
            path = str((row or {}).get("file_path", ""))
            out.append({"kind": "stinger", "label": label, "id": sid, "path": path})
        return out

    def _path_source(self, path: str) -> str:
        p = str(path or "").lower()
        if not p:
            return "missing"
        if "/curated/" in p or "\\curated\\" in p:
            return "curated"
        if "/generated/" in p or "\\generated\\" in p:
            return "generated"
        return "fallback"

    def _toggle(self, key: str):
        self.app.user_settings[key] = not bool(self.app.user_settings.get(key, False))
        if key == "fullscreen":
            wanted = bool(self.app.user_settings.get("fullscreen", False))
            if bool(self.app.renderer.fullscreen) != wanted:
                self.app.renderer.toggle_fullscreen()
        elif key == "music_muted":
            muted = bool(self.app.user_settings.get("music_muted", False))
            self.app.user_settings["music_mute"] = muted
            self.app.music.set_muted(muted)
        elif key == "sfx_muted":
            muted = bool(self.app.user_settings.get("sfx_muted", False))
            has_master = hasattr(self.app.sfx, "engine") and hasattr(self.app.sfx.engine, "set_master_volume")
            if has_master:
                sv = 0.0 if muted else self._slider_value("sfx_volume", 0.7)
                stv = 0.0 if muted else self._slider_value("stinger_volume", 0.8)
            else:
                mv = self._slider_value("master_volume", 1.0)
                sv = 0.0 if muted else self._slider_value("sfx_volume", 0.7) * mv
                stv = 0.0 if muted else self._slider_value("stinger_volume", 0.8) * mv
            self.app.sfx.set_volume(sv)
            self.app.sfx.set_stinger_volume(stv)

    def _cycle(self, key: str, values: list[str]):
        if key == "language":
            self.app.toggle_language()
            self.app.user_settings["language"] = self.app.loc.current_lang
            return
        cur = str(self.app.user_settings.get(key, values[0]))
        try:
            idx = values.index(cur)
        except Exception:
            idx = 0
        self.app.user_settings[key] = values[(idx + 1) % len(values)]

    def _set_slider(self, x: int, rect: pygame.Rect, key: str, min_v: float = 0.0, max_v: float = 1.0):
        t = max(0.0, min(1.0, (x - rect.x) / max(1, rect.w)))
        self.app.user_settings[key] = float(min_v + (max_v - min_v) * t)

    def _slider_value(self, key: str, fallback: float = 1.0) -> float:
        return float(self.app.user_settings.get(key, fallback) or fallback)

    def _go_back(self):
        self._stop_preview(restore=True)
        self.app.save_user_settings()
        if self.return_screen is not None:
            self.app.sm.set(self.return_screen)
            self.app.settings_return_screen = None
            return
        self.app.settings_return_screen = None
        self.app.goto_menu()

    def _play_music_preview(self, context_key: str):
        if self.preview_saved_context is None:
            self.preview_saved_context = getattr(self.app.music, "current_key", None)
        self._stop_preview(restore=False)
        self.app.music.play_for(context_key)
        self.active_preview = ("music", context_key)
        print(f"[options][audio] preview music context={context_key}")

    def _play_stinger_preview(self, stinger_name: str):
        self._stop_preview(restore=False)
        self.app.sfx.play(stinger_name)
        self.active_preview = ("stinger", stinger_name)
        print(f"[options][audio] preview stinger={stinger_name}")

    def _stop_preview(self, restore: bool):
        eng = self._audio_engine()
        if eng is not None and getattr(eng, "_stinger_channel", None) is not None:
            try:
                eng._stinger_channel.stop()
            except Exception:
                pass

        if restore:
            restore_key = self.preview_saved_context
            self.preview_saved_context = None
            if restore_key:
                self.app.music.play_for(restore_key)
            elif self.app.sm.current is not None:
                self.app.music.play_for(self.app.get_bgm_track("menu"))
        self.active_preview = None

    def _regen_audio_item(self, item: dict):
        eng = self._audio_engine()
        if eng is None:
            return
        if item.get("kind") == "music":
            ctx = str(item.get("id", "menu"))
            var = str(item.get("variant", "a"))
            path = eng._ensure_bgm_variant(ctx, var, force=True)
            print(f"[options][audio] regenerated context={ctx} variant={var} file={path}")
        else:
            sid = str(item.get("id", "victory"))
            path = eng._ensure_stinger(sid, force=True)
            print(f"[options][audio] regenerated stinger={sid} file={path}")

    def _debug_action(self, action: str):
        eng = self._audio_engine()
        try:
            if action == "reload_assets":
                self.app.assets._cache.clear()
                self.app.visual_engine._surface_cache.clear()
                self.progress = "Assets recargados"
                print("[options][debug] reload_assets=ok")
            elif action == "clear_audio_cache" and eng is not None:
                eng._sound_cache.clear()
                self.progress = "Cache de audio limpiada"
                print("[options][debug] clear_audio_cache=ok")
            elif action == "clear_visual_cache":
                self.app.assets._cache.clear()
                self.app.visual_engine._surface_cache.clear()
                self.progress = "Cache visual limpiada"
                print("[options][debug] clear_visual_cache=ok")
            elif action == "rebuild_manifests":
                self.app.user_settings["update_manifests"] = True
                self.app.audio_pipeline.ensure_music_assets(self.app.user_settings)
                self.app.user_settings["update_manifests"] = False
                self.progress = "Manifests reconstruidos"
                print("[options][debug] rebuild_manifests=ok")
            elif action == "print_active_asset_report":
                if eng is not None:
                    print(f"[options][debug] audio_state {eng.debug_state()}")
                print(f"[options][debug] visual_cache={len(self.app.visual_engine._surface_cache)}")
                self.progress = "Reporte impreso en consola"
        except Exception as exc:
            self.progress = f"Debug error: {exc}"
            print(f"[options][debug] action_failed action={action} err={exc}")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
                return
            if event.key == pygame.K_TAB:
                self.section_idx = (self.section_idx + 1) % len(self.SECTIONS)
                return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        pos = self.app.renderer.map_mouse(event.pos)

        if self.back_rect.collidepoint(pos):
            self._go_back()
            return

        if self.apply_rect.collidepoint(pos):
            self.app.save_user_settings()
            self.progress = "Opciones guardadas"
            return

        for i, sec in enumerate(self.SECTIONS):
            r = pygame.Rect(self.left_nav_rect.x + 12, self.left_nav_rect.y + 12 + i * 64, self.left_nav_rect.w - 24, 50)
            if r.collidepoint(pos):
                self.section_idx = i
                return

        # Section interactions.
        for rect, action in self.section_actions:
            if rect.collidepoint(pos):
                kind = action.get("kind")
                if kind == "toggle":
                    self._toggle(action["key"])
                    return
                if kind == "cycle":
                    self._cycle(action["key"], action["values"])
                    return
                if kind == "back":
                    self._go_back()
                    return
                if kind == "slider":
                    self._set_slider(pos[0], rect, action["key"], action.get("min", 0.0), action.get("max", 1.0))
                    if action["key"] == "master_volume":
                        mv = self._slider_value("master_volume", 1.0)
                        has_master = hasattr(self.app.sfx, "engine") and hasattr(self.app.sfx.engine, "set_master_volume")
                        if has_master:
                            self.app.sfx.engine.set_master_volume(mv)
                            self.app.music.set_volume(self._slider_value("music_volume", 0.5))
                            sfx_val = self._slider_value("sfx_volume", 0.7)
                            self.app.sfx.set_volume(0.0 if self.app.user_settings.get("sfx_muted", False) else sfx_val)
                            st_val = self._slider_value("stinger_volume", 0.8)
                            self.app.sfx.set_stinger_volume(0.0 if self.app.user_settings.get("sfx_muted", False) else st_val)
                        else:
                            self.app.music.set_volume(self._slider_value("music_volume", 0.5) * mv)
                            sfx_val = self._slider_value("sfx_volume", 0.7) * mv
                            self.app.sfx.set_volume(0.0 if self.app.user_settings.get("sfx_muted", False) else sfx_val)
                    elif action["key"] == "music_volume":
                        mv = self._slider_value("master_volume", 1.0)
                        has_master = hasattr(self.app.sfx, "engine") and hasattr(self.app.sfx.engine, "set_master_volume")
                        mv_eff = 1.0 if has_master else mv
                        self.app.music.set_volume(self._slider_value("music_volume", 0.5) * mv_eff)
                    elif action["key"] in {"sfx_volume", "stinger_volume"}:
                        mv = self._slider_value("master_volume", 1.0)
                        has_master = hasattr(self.app.sfx, "engine") and hasattr(self.app.sfx.engine, "set_master_volume")
                        mv_eff = 1.0 if has_master else mv
                        sfx_val = self._slider_value("sfx_volume", 0.7) * mv_eff
                        self.app.sfx.set_volume(0.0 if self.app.user_settings.get("sfx_muted", False) else sfx_val)
                        st_val = self._slider_value("stinger_volume", 0.8) * mv_eff
                        self.app.sfx.set_stinger_volume(0.0 if self.app.user_settings.get("sfx_muted", False) else st_val)
                    return
                if kind == "debug":
                    self._debug_action(action["action"])
                    return

        for row in self.row_actions:
            if row["play"].collidepoint(pos):
                if row["item"]["kind"] == "music":
                    self._play_music_preview(row["item"]["id"])
                else:
                    self._play_stinger_preview(row["item"]["id"])
                return
            if row["stop"].collidepoint(pos):
                self._stop_preview(restore=True)
                print("[options][audio] preview stopped")
                return
            if row["regen"].collidepoint(pos):
                self._regen_audio_item(row["item"])
                return

    def update(self, dt):
        pass

    def _draw_btn(self, s, rect, label, active=False):
        fill = UI_THEME["panel_2"] if active else UI_THEME["panel"]
        pygame.draw.rect(s, fill, rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"] if not active else UI_THEME["gold"], rect, 2, border_radius=10)
        s.blit(self.app.small_font.render(label, True, UI_THEME["text"]), (rect.x + 12, rect.y + 13))

    def _draw_slider(self, surface, rect, value):
        pygame.draw.rect(surface, UI_THEME["panel_2"], rect, border_radius=7)
        kx = rect.x + int(rect.w * max(0.0, min(1.0, float(value))))
        pygame.draw.circle(surface, UI_THEME["gold"], (kx, rect.y + rect.h // 2), 10)

    def _add_toggle_row(self, s, x, y, w, label, key):
        rect = pygame.Rect(x, y, w, 48)
        pygame.draw.rect(s, UI_THEME["panel"], rect, border_radius=10)
        state = "ON" if bool(self.app.user_settings.get(key, False)) else "OFF"
        s.blit(self.app.small_font.render(f"{label}: {state}", True, UI_THEME["text"]), (rect.x + 14, rect.y + 12))
        self.section_actions.append((rect, {"kind": "toggle", "key": key}))

    def _add_cycle_row(self, s, x, y, w, label, key, values):
        rect = pygame.Rect(x, y, w, 48)
        pygame.draw.rect(s, UI_THEME["panel"], rect, border_radius=10)
        cur = str(self.app.user_settings.get(key, values[0]))
        s.blit(self.app.small_font.render(f"{label}: {cur}", True, UI_THEME["text"]), (rect.x + 14, rect.y + 12))
        self.section_actions.append((rect, {"kind": "cycle", "key": key, "values": values}))

    def _add_slider_row(self, s, x, y, w, label, key, min_v=0.0, max_v=1.0):
        line = pygame.Rect(x, y, w, 56)
        pygame.draw.rect(s, UI_THEME["panel"], line, border_radius=10)
        sval = self._slider_value(key, min_v)
        shown = f"{sval:.2f}" if max_v <= 3.0 else f"{sval:.0f}"
        s.blit(self.app.small_font.render(f"{label}: {shown}", True, UI_THEME["text"]), (line.x + 14, line.y + 8))
        slider = pygame.Rect(line.x + 14, line.y + 32, line.w - 28, 12)
        norm = (sval - min_v) / max(0.001, (max_v - min_v))
        self._draw_slider(s, slider, norm)
        self.section_actions.append((slider.inflate(0, 14), {"kind": "slider", "key": key, "min": min_v, "max": max_v}))

    def _render_general(self, s, panel):
        x = panel.x + 20
        y = panel.y + 20
        w = panel.w - 40
        self._add_toggle_row(s, x, y, w, "Pantalla completa", "fullscreen")
        y += 58
        self._add_cycle_row(s, x, y, w, "Resolucion", "resolution", ["1920x1080", "1600x900", "1280x720"])
        y += 58
        self._add_slider_row(s, x, y, w, "Escala UI", "ui_scale", 0.8, 1.4)
        y += 66
        lang = "es" if self.app.loc.current_lang == "es" else "en"
        lr = pygame.Rect(x, y, w, 48)
        pygame.draw.rect(s, UI_THEME["panel"], lr, border_radius=10)
        s.blit(self.app.small_font.render(f"Idioma: {lang} (click para cambiar)", True, UI_THEME["text"]), (lr.x + 14, lr.y + 12))
        self.section_actions.append((lr, {"kind": "cycle", "key": "language", "values": ["es", "en"]}))
        # override language cycle via app localization
        if self.app.user_settings.get("language") != self.app.loc.current_lang:
            self.app.user_settings["language"] = self.app.loc.current_lang

        y += 58
        br = pygame.Rect(x, y, 260, 48)
        self._draw_btn(s, br, "Volver")
        self.section_actions.append((br, {"kind": "back"}))

    def _render_audio(self, s, panel):
        x = panel.x + 16
        y = panel.y + 18
        w = panel.w - 32

        self._add_slider_row(s, x, y, w, "Master", "master_volume", 0.0, 1.0)
        y += 64
        self._add_slider_row(s, x, y, w, "Musica", "music_volume", 0.0, 1.0)
        y += 64
        self._add_slider_row(s, x, y, w, "SFX", "sfx_volume", 0.0, 1.0)
        y += 64
        self._add_slider_row(s, x, y, w, "Stinger", "stinger_volume", 0.0, 1.0)
        y += 68

        self._add_toggle_row(s, x, y, (w // 2) - 8, "Mute musica", "music_muted")
        self._add_toggle_row(s, x + (w // 2) + 8, y, (w // 2) - 8, "Mute sfx", "sfx_muted")
        y += 62

        hdr = self.app.small_font.render("Contexto / archivo activo / fuente", True, UI_THEME["gold"])
        s.blit(hdr, (x, y))
        y += 28

        entries = self._audio_entries()
        self.row_actions = []
        for item in entries:
            row = pygame.Rect(x, y, w, 38)
            pygame.draw.rect(s, UI_THEME["panel"], row, border_radius=8)
            path = str(item.get("path", ""))
            src = self._path_source(path)
            short_path = path.replace("\\", "/")
            if len(short_path) > 54:
                short_path = "..." + short_path[-54:]
            txt = f"{item['label']}  [{item['kind']}]  {short_path or 'missing'}  ({src})"
            s.blit(self.app.tiny_font.render(txt, True, UI_THEME["text"]), (row.x + 10, row.y + 12))

            b_play = pygame.Rect(row.right - 270, row.y + 6, 82, 26)
            b_stop = pygame.Rect(row.right - 180, row.y + 6, 82, 26)
            b_reg = pygame.Rect(row.right - 90, row.y + 6, 82, 26)
            self._draw_btn(s, b_play, "Reproducir")
            self._draw_btn(s, b_stop, "Detener")
            self._draw_btn(s, b_reg, "Regenerar")
            self.row_actions.append({"item": item, "play": b_play, "stop": b_stop, "regen": b_reg})
            y += 42
            if y > panel.bottom - 46:
                break

    def _render_visual(self, s, panel):
        x = panel.x + 20
        y = panel.y + 20
        w = panel.w - 40
        self._add_slider_row(s, x, y, w, "Intensidad holograma", "hologram_intensity", 0.0, 1.0)
        y += 64
        self._add_slider_row(s, x, y, w, "Intensidad RGB enemigo", "enemy_rgb_intensity", 0.0, 1.0)
        y += 64
        self._add_cycle_row(s, x, y, w, "Particulas", "particles_quality", ["low", "medium", "high"])
        y += 58
        self._add_slider_row(s, x, y, w, "Glow UI", "ui_glow_intensity", 0.0, 1.0)
        y += 64
        self._add_slider_row(s, x, y, w, "Hover anim", "hover_anim_intensity", 0.0, 1.0)
        y += 64
        self._add_toggle_row(s, x, y, w, "Modo contraste", "contrast_mode")

    def _render_combat(self, s, panel):
        x = panel.x + 20
        y = panel.y + 20
        w = panel.w - 40
        self._add_slider_row(s, x, y, w, "Velocidad animacion", "animation_speed", 0.7, 1.4)
        y += 64
        self._add_toggle_row(s, x, y, w, "Tooltips", "tooltip_visibility")
        y += 58
        self._add_toggle_row(s, x, y, w, "Leyenda de iconos", "icon_legend_visibility")
        y += 58
        self._add_toggle_row(s, x, y, w, "Confirmar fin de turno", "confirm_end_turn")
        y += 58
        self._add_cycle_row(s, x, y, w, "Escala hover cartas", "card_hover_scale_preset", ["small", "medium", "large"])

    def _render_accessibility(self, s, panel):
        x = panel.x + 20
        y = panel.y + 20
        w = panel.w - 40
        self._add_slider_row(s, x, y, w, "Escala texto", "text_scale", 0.9, 1.4)
        y += 64
        self._add_slider_row(s, x, y, w, "Escala iconos", "icon_scale", 0.9, 1.6)
        y += 64
        self._add_toggle_row(s, x, y, w, "Alto contraste", "high_contrast")
        y += 58
        self._add_toggle_row(s, x, y, w, "Reducir FX", "reduced_fx")

    def _render_debug(self, s, panel):
        x = panel.x + 20
        y = panel.y + 20
        w = panel.w - 40
        actions = [
            ("Recargar assets", "reload_assets"),
            ("Limpiar cache audio", "clear_audio_cache"),
            ("Limpiar cache visual", "clear_visual_cache"),
            ("Reconstruir manifests", "rebuild_manifests"),
            ("Imprimir reporte activo", "print_active_asset_report"),
        ]
        for label, aid in actions:
            r = pygame.Rect(x, y, w, 50)
            self._draw_btn(s, r, label)
            self.section_actions.append((r, {"kind": "debug", "action": aid}))
            y += 58

        eng = self._audio_engine()
        dbg = eng.debug_state() if eng is not None else "audio_engine=missing"
        s.blit(self.app.tiny_font.render(dbg, True, UI_THEME["muted"]), (x, panel.bottom - 32))

    def render(self, surface):
        surface.fill(UI_THEME["bg"])
        title = self.app.big_font.render("Opciones", True, UI_THEME["text"])
        surface.blit(title, (72, 62))

        pygame.draw.rect(surface, UI_THEME["panel"], self.left_nav_rect, border_radius=12)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], self.left_nav_rect, 2, border_radius=12)
        for i, sec in enumerate(self.SECTIONS):
            r = pygame.Rect(self.left_nav_rect.x + 12, self.left_nav_rect.y + 12 + i * 64, self.left_nav_rect.w - 24, 50)
            self._draw_btn(surface, r, sec, active=(i == self.section_idx))

        pygame.draw.rect(surface, UI_THEME["panel"], self.content_rect, border_radius=12)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], self.content_rect, 2, border_radius=12)

        self.section_actions = []
        self.row_actions = []
        section = self.SECTIONS[self.section_idx]
        hdr = self.app.font.render(section, True, UI_THEME["gold"])
        surface.blit(hdr, (self.content_rect.x + 18, self.content_rect.y + 10))
        panel = pygame.Rect(self.content_rect.x + 12, self.content_rect.y + 44, self.content_rect.w - 24, self.content_rect.h - 56)

        if section == "General":
            self._render_general(surface, panel)
        elif section == "Audio":
            self._render_audio(surface, panel)
        elif section == "Visual":
            self._render_visual(surface, panel)
        elif section == "Combate":
            self._render_combat(surface, panel)
        elif section == "Accesibilidad":
            self._render_accessibility(surface, panel)
        else:
            self._render_debug(surface, panel)

        self._draw_btn(surface, self.back_rect, "Volver")
        self._draw_btn(surface, self.apply_rect, "Aplicar")

        if self.progress:
            surface.blit(self.app.small_font.render(self.progress, True, UI_THEME["gold"]), (self.content_rect.x + 20, self.content_rect.bottom - 30))
