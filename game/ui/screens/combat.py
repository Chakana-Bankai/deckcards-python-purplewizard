import math
import pygame

from game.settings import INTERNAL_WIDTH
from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME


def wrap_text(font, text, width):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        nxt = (cur + " " + w).strip()
        if font.size(nxt)[0] <= width:
            cur = nxt
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def generate_chakana_polygon(center, size, step=0.35):
    cx, cy = center
    s = size
    k = int(s * step)
    pts = [
        (cx-k, cy-s),(cx+k, cy-s),(cx+k, cy-k),(cx+s, cy-k),(cx+s, cy+k),
        (cx+k, cy+k),(cx+k, cy+s),(cx-k, cy+s),(cx-k, cy+k),(cx-s, cy+k),
        (cx-s, cy-k),(cx-k, cy-k),(cx-k, cy-s),(cx, cy-s),(cx, cy-k),
        (cx+s, cy),(cx, cy+k),(cx, cy+s),(cx-k, cy),(cx-s, cy)
    ]
    return pts


class CombatScreen:
    TOPBAR = pygame.Rect(0, 0, 1920, 100)
    ENEMY_PANEL = pygame.Rect(40, 110, 1840, 340)
    DIALOGUE_PANEL = pygame.Rect(220, 460, 1480, 140)
    CARD_AREA = pygame.Rect(40, 620, 1160, 250)
    PLAYER_HUD = pygame.Rect(1220, 620, 660, 250)
    ACTION_BAR = pygame.Rect(40, 890, 1840, 170)
    PLAYFIELD = pygame.Rect(0, 0, 1920, 610)

    def __init__(self, app, combat_state, is_boss=False):
        self.app = app
        self.c = combat_state
        self.is_boss = is_boss
        self.selected_card_index = None
        self.scry_selected = None
        self.tooltip = None
        self.log_lines = []
        self.banner = TypewriterBanner()
        self.dialog_enemy = TypewriterBanner()
        self.dialog_hero = TypewriterBanner()
        self.dialog_cd = 0.0
        self.enemy_line_fx = 0.0
        self.hero_line_fx = 0.0
        self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
        self.ui_state = "IDLE"
        self.resolving_t = 0.0
        self.last_turn = self.c.turn
        self.selected_biome = self.app.rng.choice(self.app.bg_gen.BIOMES)
        self.bg_seed = abs(hash(f"{self.selected_biome}:{self.c.turn}:{self.c.enemies[0].id if self.c.enemies else 'none'}")) % 100000
        self.end_turn_rect = pygame.Rect(self.ACTION_BAR.right - 330, self.ACTION_BAR.y + 52, 300, 78)
        self.status_rect = pygame.Rect(self.ACTION_BAR.right - 670, self.ACTION_BAR.y + 52, 300, 78)
        self.scry_confirm_rect = pygame.Rect(1920 // 2 - 140, 680, 280, 66)
        self._trigger_dialog("start")

    def draw_panel(self, s, rect, title):
        pygame.draw.rect(s, UI_THEME["panel"], rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], rect, 2, border_radius=12)
        s.blit(self.app.small_font.render(title, True, UI_THEME["gold"]), (rect.x + 12, rect.y + 8))

    def _zone_titles(self):
        return [
            (self.TOPBAR, "Trama"), (self.ENEMY_PANEL, "Enemigo"), (self.DIALOGUE_PANEL, "Voces"),
            (self.PLAYER_HUD, "Chakana"), (self.CARD_AREA, "Mano"), (self.ACTION_BAR, "Acciones")
        ]

    def _enemy_rect(self, idx):
        return pygame.Rect(self.ENEMY_PANEL.x + 24 + idx * 600, self.ENEMY_PANEL.y + 36, 560, 286)

    def _card_rect(self, i, total, hovered=False):
        w,h,g=180,250,14
        tw=total*w+max(0,total-1)*g
        x=self.CARD_AREA.x+(self.CARD_AREA.w-tw)//2+i*(w+g)
        r=pygame.Rect(x,self.CARD_AREA.y+8,w,h)
        return r.inflate(20,10) if hovered else r

    def _update_ui_state(self):
        if self.resolving_t > 0:
            self.ui_state = "RESOLVING"; return
        if self.selected_card_index is None or self.selected_card_index >= len(self.c.hand):
            self.ui_state = "IDLE"; return
        card=self.c.hand[self.selected_card_index]
        self.ui_state = "SELECTED_PLAYABLE" if card.cost <= self.c.player["energy"] else "SELECTED_NOT_PLAYABLE"

    def _dialog_pick(self, side, trigger, enemy_id):
        dc = self.app.content.dialogues_combat if hasattr(self.app, "content") else {}
        item = dc.get(enemy_id, dc.get("default", {})) if isinstance(dc, dict) else {}
        trig = item.get(trigger, {}) if isinstance(item, dict) else {}
        return trig.get(side, "...") if isinstance(trig, dict) else "..."

    def _trigger_dialog(self, trigger):
        if self.dialog_cd > 0:
            return
        enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
        self.dialog_enemy.set(self._dialog_pick("enemy", trigger, enemy_id), 2.1)
        self.dialog_hero.set(self._dialog_pick("chakana", trigger, enemy_id), 2.1)
        self.enemy_line_fx = 0.24
        self.hero_line_fx = 0.22
        self.dialog_cd = 2.8
        self.app.sfx.play("whisper"); self.app.sfx.play("chime")

    def _execute_selected(self):
        self._update_ui_state()
        if self.ui_state != "SELECTED_PLAYABLE":
            return
        self.resolving_t = 0.15
        target_idx = next((i for i,e in enumerate(self.c.enemies) if e.alive), None)
        self.c.play_card(self.selected_card_index, target_idx)
        self.selected_card_index = None
        self._update_ui_state()

    def _handle_scry_event(self, event):
        cards=self.c.scry_pending
        rects=[pygame.Rect(360+i*250,320,220,320) for i in range(len(cards))]
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            pos=self.app.renderer.map_mouse(event.pos)
            for i,r in enumerate(rects):
                if r.collidepoint(pos): self.scry_selected=i; return True
            if self.scry_confirm_rect.collidepoint(pos) and self.scry_selected is not None:
                self.c.apply_scry_order(cards); self.scry_selected=None; return True
        return True

    def handle_event(self, event):
        if self.c.scry_pending and self._handle_scry_event(event): return
        if self.ui_state == "RESOLVING": return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos=self.app.renderer.map_mouse(event.pos)
            if self.end_turn_rect.collidepoint(pos):
                if self.ui_state == "IDLE":
                    self.c.end_turn(); self.selected_card_index=None
                elif self.ui_state == "SELECTED_PLAYABLE":
                    self._execute_selected()
                self._update_ui_state(); return
            for i,_ in enumerate(self.c.hand[:6]):
                if self._card_rect(i,min(6,len(self.c.hand))).collidepoint(pos):
                    self.selected_card_index=i; self._update_ui_state(); self.app.sfx.play("card_pick"); return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            self._execute_selected()

    def update(self, dt):
        self.c.update(dt)
        self.resolving_t=max(0,self.resolving_t-dt)
        self.dialog_cd=max(0,self.dialog_cd-dt)
        self.enemy_line_fx=max(0,self.enemy_line_fx-dt)
        self.hero_line_fx=max(0,self.hero_line_fx-dt)
        if self.last_turn != self.c.turn:
            self.last_turn=self.c.turn; self.selected_card_index=None
        for ev in self.c.pop_events():
            if ev.get("type") == "damage":
                self.log_lines.insert(0,f"{ev['target']}: -{ev['amount']} Vida")
                if ev.get("target")!="player" and ev.get("amount",0)>=10: self._trigger_dialog("enemy_big_attack")
            if ev.get("type") == "block": self.log_lines.insert(0,f"{ev['target']}: +{ev['amount']} Guardia")
        if self.c.player["hp"] <= max(10, self.c.player["max_hp"]*0.3): self._trigger_dialog("player_low_hp")
        if any(e.alive and e.hp <= e.max_hp*0.25 for e in self.c.enemies): self._trigger_dialog("enemy_low_hp")
        if self.is_boss and self.c.turn % 4 == 0: self._trigger_dialog("boss_phase")
        self.log_lines=self.log_lines[:8]
        self._update_ui_state()
        if self.c.result == "victory": self._trigger_dialog("victory"); self.app.on_combat_victory()
        elif self.c.result == "defeat": self.app.goto_menu()

    def _draw_chakana_avatar(self, s):
        t=pygame.time.get_ticks()/1000.0
        sc=1.0+0.06*(0.5+0.5*math.sin(t*2*math.pi/1.6))
        center=(self.PLAYER_HUD.x+545,self.PLAYER_HUD.y+88)
        pts=generate_chakana_polygon(center,int(42*sc),step=0.35)
        pygame.draw.polygon(s,(182,154,240),pts,2)
        pygame.draw.circle(s,(180,120,240,80),center,int(58*sc),1)
        stars=[(center[0]+32,center[1]-40),(center[0]+50,center[1]-54),(center[0]+66,center[1]-42),(center[0]+56,center[1]-28)]
        for i,st in enumerate(stars):
            rr=2+int((math.sin(t*4+i)+1)*1.2)
            pygame.draw.circle(s,(230,230,255),st,rr)

    def _draw_harmony(self,s):
        r=pygame.Rect(self.PLAYER_HUD.x+420,self.PLAYER_HUD.y+146,220,90)
        pygame.draw.rect(s,UI_THEME["panel_2"],r,border_radius=10)
        s.blit(self.app.tiny_font.render("Harmony",True,UI_THEME["gold"]),(r.x+8,r.y+6))
        dirs=["ESTE","SUR","NORTE","OESTE"]; sym={"ESTE":"E","SUR":"S","NORTE":"N","OESTE":"O"}
        for i,d in enumerate(dirs):
            col=UI_THEME["accent_violet"] if d in self.c.harmony_last3 else (90,90,110)
            pygame.draw.circle(s,col,(r.x+24+i*46,r.y+34),8)
        for i,d in enumerate(self.c.harmony_last3[-3:]):
            s.blit(self.app.small_font.render(sym.get(d,"?"),True,UI_THEME["text"]),(r.x+20+i*40,r.y+52))

    def _draw_card(self,s,rect,card,selected=False):
        pygame.draw.rect(s,UI_THEME["card_bg"],rect,border_radius=12)
        pygame.draw.rect(s,UI_THEME["card_border"],rect,2,border_radius=12)
        art=self.app.assets.sprite("cards",card.definition.id,(rect.w-14,int(rect.h*0.56)),fallback=(70,44,105)); s.blit(art,(rect.x+7,rect.y+30))
        s.blit(self.app.tiny_font.render(str(card.definition.name_key),True,UI_THEME["text"]),(rect.x+8,rect.y+6))
        lines=wrap_text(self.app.tiny_font,str(card.definition.text_key),rect.w-14)[:2]
        for i,l in enumerate(lines): s.blit(self.app.tiny_font.render(l,True,UI_THEME["muted"]),(rect.x+8,rect.y+int(rect.h*0.72)+i*18))
        pygame.draw.circle(s,UI_THEME["energy"],(rect.right-16,rect.y+16),12)
        s.blit(self.app.tiny_font.render(str(card.cost),True,UI_THEME["text_dark"]),(rect.right-20,rect.y+9))
        if selected: pygame.draw.rect(s,UI_THEME["gold"],rect.inflate(8,8),3,border_radius=14)

    def render(self, s):
        t=pygame.time.get_ticks()*0.02
        self.app.bg_gen.render_parallax(s,self.selected_biome,self.bg_seed,t,clip_rect=self.PLAYFIELD,particles_on=self.app.user_settings.get("fx_particles",True))
        if self.app.user_settings.get("fx_vignette",True):
            ov=pygame.Surface((1920,1080),pygame.SRCALPHA); pygame.draw.rect(ov,(0,0,0,90),ov.get_rect(),120); s.blit(ov,(0,0))
        mouse=self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.tooltip=None

        for rect,title in self._zone_titles(): self.draw_panel(s,rect,title)
        s.blit(self.app.big_font.render("Chakana Purple Wizard",True,UI_THEME["gold"]),(54,26))

        ejit = int(math.sin(pygame.time.get_ticks()*0.04)) if self.enemy_line_fx>0 else 0
        esc = 1.03 if self.hero_line_fx>0 else 1.0
        e_line=self.dialog_enemy.current; h_line=self.dialog_hero.current
        s.blit(self.app.font.render(e_line,True,UI_THEME["bad"]),(self.DIALOGUE_PANEL.centerx-self.app.font.size(e_line)[0]//2+ejit,self.DIALOGUE_PANEL.y+30))
        hf=self.app.font.render(h_line,True,UI_THEME["good"]); hf=pygame.transform.rotozoom(hf,0,esc)
        s.blit(hf,(self.DIALOGUE_PANEL.centerx-hf.get_width()//2,self.DIALOGUE_PANEL.y+80))

        p=self.c.player
        s.blit(self.app.font.render(f"Vida {p['hp']}/{p['max_hp']}",True,UI_THEME["text"]),(self.PLAYER_HUD.x+22,self.PLAYER_HUD.y+38))
        s.blit(self.app.font.render(f"Guardia {p['block']}",True,UI_THEME["block"]),(self.PLAYER_HUD.x+22,self.PLAYER_HUD.y+78))
        s.blit(self.app.font.render(f"Quiebre {p['rupture']}",True,UI_THEME["rupture"]),(self.PLAYER_HUD.x+260,self.PLAYER_HUD.y+38))
        s.blit(self.app.font.render("Maná",True,UI_THEME["text"]),(self.PLAYER_HUD.x+260,self.PLAYER_HUD.y+78))
        for i in range(6): pygame.draw.circle(s,UI_THEME["energy"] if i<p["energy"] else (65,68,90),(self.PLAYER_HUD.x+350+i*30,self.PLAYER_HUD.y+90),10)
        self._draw_chakana_avatar(s); self._draw_harmony(s)

        for i,e in enumerate(self.c.enemies):
            er=self._enemy_rect(i); pygame.draw.rect(s,UI_THEME["deep_purple"],er,border_radius=12)
            portrait=230 if self.is_boss or 'senor' in e.id or 'guardian' in e.id or 'oraculo' in e.id else 180
            s.blit(self.app.assets.sprite("enemies",e.id,(portrait,portrait),fallback=(100,60,90)),(er.x+18,er.y+28))
            intent=e.current_intent().get("label","Preparando")
            s.blit(self.app.small_font.render(str(e.name_key),True,UI_THEME["text"]),(er.x+260,er.y+46))
            s.blit(self.app.small_font.render(intent,True,UI_THEME["gold"]),(er.x+260,er.y+86))
            ratio=max(0,e.hp)/max(1,e.max_hp)
            pygame.draw.rect(s,(35,24,50),(er.x+260,er.y+188,280,18),border_radius=7)
            pygame.draw.rect(s,UI_THEME["hp"],(er.x+260,er.y+188,int(280*ratio),18),border_radius=7)
            s.blit(self.app.tiny_font.render(f"Vida {e.hp}/{e.max_hp}",True,UI_THEME["text"]),(er.x+260,er.y+212))

        hand=self.c.hand[:6]; hover=None
        for i in range(len(hand)):
            if self._card_rect(i,len(hand)).collidepoint(mouse): hover=i
        for i,card in enumerate(hand):
            rr=self._card_rect(i,len(hand),hovered=(i==hover)); self._draw_card(s,rr,card,selected=(i==self.selected_card_index))
            if rr.collidepoint(mouse): self.tooltip=str(card.definition.text_key)

        pygame.draw.rect(s,UI_THEME["panel"],self.status_rect,border_radius=10)
        s.blit(self.app.small_font.render("Registro",True,UI_THEME["text"]),(self.status_rect.x+105,self.status_rect.y+24))

        label,disabled="Fin de Turno",False
        if self.ui_state=="SELECTED_PLAYABLE": label="Ejecutar"
        elif self.ui_state=="SELECTED_NOT_PLAYABLE": label="Sin Maná"; disabled=True
        elif self.ui_state=="RESOLVING": label="..."; disabled=True
        pygame.draw.rect(s, UI_THEME["violet"] if not disabled else (88,84,102), self.end_turn_rect, border_radius=12)
        s.blit(self.app.font.render(label,True,UI_THEME["text"]),(self.end_turn_rect.x+82,self.end_turn_rect.y+24))

        log_rect=pygame.Rect(self.ACTION_BAR.x+12,self.ACTION_BAR.y+28,860,108)
        pygame.draw.rect(s,UI_THEME["panel_2"],log_rect,border_radius=10)
        for i,line in enumerate(self.log_lines[:3]):
            col=UI_THEME["bad"] if "-" in line else UI_THEME["block"] if "+" in line else UI_THEME["muted"]
            s.blit(self.app.small_font.render(line,True,col),(log_rect.x+14,log_rect.y+12+i*30))

        if self.c.scry_pending:
            ov=pygame.Surface((1920,1080),pygame.SRCALPHA); ov.fill((0,0,0,170)); s.blit(ov,(0,0))
            modal=pygame.Rect(300,240,1320,560); self.draw_panel(s,modal,"Scry")
            for i,card in enumerate(self.c.scry_pending):
                r=pygame.Rect(360+i*250,320,220,320)
                if r.collidepoint(mouse): pygame.draw.rect(s,(200,170,255),r.inflate(12,12),2,border_radius=14)
                self._draw_card(s,r,card,selected=(i==self.scry_selected))
                if i==self.scry_selected:
                    pygame.draw.rect(s,UI_THEME["gold"],r.inflate(16,16),4,border_radius=16)
                    s.blit(self.app.small_font.render("SELECCIONADA",True,UI_THEME["gold"]),(r.x+24,r.y-28))
            en=self.scry_selected is not None
            pygame.draw.rect(s,UI_THEME["violet"] if en else (76,72,94),self.scry_confirm_rect,border_radius=10)
            s.blit(self.app.font.render("Confirmar",True,UI_THEME["text"]),(self.scry_confirm_rect.x+86,self.scry_confirm_rect.y+18))


        if self.app.user_settings.get("fx_glow", True):
            g = pygame.transform.smoothscale(s, (960, 540))
            g = pygame.transform.smoothscale(g, (1920, 1080))
            g.set_alpha(18)
            s.blit(g, (0, 0))
        if self.app.user_settings.get("fx_scanlines", False):
            for yy in range(0, 1080, 4):
                pygame.draw.line(s, (8, 8, 12), (0, yy), (1920, yy))
        if self.tooltip and not self.c.scry_pending:
            tr=pygame.Rect(self.ACTION_BAR.x+12,self.ACTION_BAR.y-56,720,46)
            pygame.draw.rect(s,(18,18,26),tr,border_radius=8)
            s.blit(self.app.tiny_font.render(self.tooltip,True,UI_THEME["text"]),(tr.x+10,tr.y+14))
