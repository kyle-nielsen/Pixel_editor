"""The interactive editor: rendering, input handling, and the main loop."""

import os

import pygame
import pygame._freetype as _freetype  # raw C ext; the .py shims have a
                                      # circular-import bug on this build

from . import constants as K

_FONT_FILE = os.path.join(os.path.dirname(pygame.__file__), "freesansbold.ttf")
from .model import Project, UndoStack, new_frame, flood_fill, idx, in_bounds
from .export import export_spritesheet, export_frames

PROJECT_FILE = "project.json"
EXPORT_DIR = "export"

TOOLS = ["pencil", "eraser", "fill", "picker"]


class _Font:
    """Thin adapter so call sites can use a pygame.font-style ``render``.

    This build of pygame lacks the SDL_ttf ``font`` module and its Python
    ``font``/``freetype`` shims fail to import (a circular import with
    ``sysfont``).  The underlying ``_freetype`` C extension is fine, so we
    drive it directly with the bundled font file.
    """

    def __init__(self, size, bold=False):
        self._f = _freetype.Font(_FONT_FILE, size)
        self._f.strong = bold  # freetype's bold emulation

    def render(self, text, _antialias, colour):
        surf, _rect = self._f.render(text, colour)
        return surf


class Button:
    """A tiny clickable rect with a label and an on-click callback."""

    def __init__(self, rect, label, on_click):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click

    def hit(self, pos):
        return self.rect.collidepoint(pos)


class Editor:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Pixel Art Editor")
        self.screen = pygame.display.set_mode((K.WINDOW_W, K.WINDOW_H))
        self.clock = pygame.time.Clock()
        _freetype.init()
        self.font = _Font(14)
        self.font_sm = _Font(12)
        self.font_lg = _Font(18, bold=True)

        self.project = Project()
        if os.path.exists(PROJECT_FILE):
            try:
                self.project = Project.load(PROJECT_FILE)
            except Exception as e:  # corrupt file shouldn't block startup
                print("Could not load project:", e)
        self.undo = UndoStack()

        self.tool = "pencil"
        self.colour = K.PALETTE[21]  # white
        self.show_grid = True
        self.onion = False

        self.playing = False
        self._play_acc = 0.0

        self.status = "Ready. Press H for help in the console."
        self._stroke_snapshot = None  # frame state captured at mouse-down
        self._painting = False

        # Pre-render a transparency checkerboard for the canvas background.
        self._checker = self._make_checker()

        self.buttons = []
        self._build_buttons()

    # ------------------------------------------------------------------ setup
    def _make_checker(self):
        surf = pygame.Surface((K.CANVAS_W, K.CANVAS_H))
        sq = K.CELL
        for gy in range(K.GRID_H):
            for gx in range(K.GRID_W):
                c = K.C_CHECKER_A if (gx + gy) % 2 == 0 else K.C_CHECKER_B
                surf.fill(c, (gx * sq, gy * sq, sq, sq))
        return surf

    def _build_buttons(self):
        self.buttons.clear()
        # Frame/playback controls under the timeline.
        y = K.TIMELINE_Y + K.THUMB + 12
        defs = [
            ("+ Frame", self.add_frame), ("Duplicate", self.duplicate_frame),
            ("Delete", self.delete_frame), ("Clear", self.clear_frame),
        ]
        x = K.TIMELINE_X
        for label, cb in defs:
            w = 92
            self.buttons.append(Button((x, y, w, 26), label, cb))
            x += w + 8

        # Right-column action buttons.
        rx, ry = K.RIGHT_X, 300
        racts = [
            ("Play / Pause", self.toggle_play), ("FPS -", lambda: self.change_fps(-1)),
            ("FPS +", lambda: self.change_fps(1)), ("Onion skin", self.toggle_onion),
            ("Toggle grid", self.toggle_grid), ("Save  (Ctrl+S)", self.save),
            ("Load  (Ctrl+O)", self.load), ("Export (Ctrl+E)", self.export),
        ]
        for label, cb in racts:
            self.buttons.append(Button((rx, ry, 150, 26), label, cb))
            ry += 32

    # ------------------------------------------------------------- frame ops
    def _begin_stroke(self):
        self._stroke_snapshot = list(self.project.frame)

    def _commit_stroke(self):
        if self._stroke_snapshot is not None and \
                self._stroke_snapshot != self.project.frame:
            self.undo.push(self.project.sprite_index,
                           self.project.frame_index, self._stroke_snapshot)
        self._stroke_snapshot = None

    def add_frame(self):
        self._begin_stroke_meta()
        s = self.project.sprite
        s.frames.insert(self.project.frame_index + 1, new_frame())
        self.project.frame_index += 1
        self.status = f"Added frame {self.project.frame_index + 1}/{len(s.frames)}"

    def duplicate_frame(self):
        self._begin_stroke_meta()
        s = self.project.sprite
        s.frames.insert(self.project.frame_index + 1, list(self.project.frame))
        self.project.frame_index += 1
        self.status = f"Duplicated -> frame {self.project.frame_index + 1}"

    def delete_frame(self):
        s = self.project.sprite
        if len(s.frames) <= 1:
            self.status = "Can't delete the last frame."
            return
        self._begin_stroke_meta()
        del s.frames[self.project.frame_index]
        self.project.clamp()
        self.status = f"Deleted frame. {len(s.frames)} left."

    def clear_frame(self):
        self._begin_stroke()
        self.project.set_frame(new_frame())
        self._commit_stroke()
        self.status = "Cleared frame."

    def _begin_stroke_meta(self):
        """Frame add/remove changes structure; just note it (no per-pixel undo)."""
        self._stroke_snapshot = None

    def next_frame(self, step=1):
        s = self.project.sprite
        self.project.frame_index = (self.project.frame_index + step) % len(s.frames)

    def select_sprite(self, i):
        if 0 <= i < len(self.project.sprites):
            self.project.sprite_index = i
            self.project.frame_index = 0
            self.status = f"Sprite: {self.project.sprite.name}"

    # ----------------------------------------------------------- toggles/etc
    def toggle_play(self):
        self.playing = not self.playing
        self._play_acc = 0.0

    def toggle_onion(self):
        self.onion = not self.onion

    def toggle_grid(self):
        self.show_grid = not self.show_grid

    def change_fps(self, d):
        s = self.project.sprite
        s.fps = max(1, min(60, s.fps + d))
        self.status = f"{s.name} fps = {s.fps}"

    # -------------------------------------------------------------- file ops
    def save(self):
        try:
            self.project.save(PROJECT_FILE)
            self.status = f"Saved -> {PROJECT_FILE}"
        except Exception as e:
            self.status = f"Save failed: {e}"

    def load(self):
        if not os.path.exists(PROJECT_FILE):
            self.status = "No project.json to load."
            return
        try:
            self.project = Project.load(PROJECT_FILE)
            self.undo = UndoStack()
            self.status = f"Loaded {PROJECT_FILE}"
        except Exception as e:
            self.status = f"Load failed: {e}"

    def export(self):
        try:
            sheet = export_spritesheet(self.project.sprite, EXPORT_DIR, scale=1)
            export_frames(self.project.sprite, EXPORT_DIR, scale=1)
            self.status = f"Exported -> {sheet}"
        except Exception as e:
            self.status = f"Export failed: {e}"

    # ---------------------------------------------------------------- canvas
    def _canvas_cell(self, pos):
        """Map a screen position to a grid cell, or None if outside the canvas."""
        mx, my = pos
        if not (K.CANVAS_X <= mx < K.CANVAS_X + K.CANVAS_W and
                K.CANVAS_Y <= my < K.CANVAS_Y + K.CANVAS_H):
            return None
        gx = (mx - K.CANVAS_X) // K.CELL
        gy = (my - K.CANVAS_Y) // K.CELL
        return (gx, gy) if in_bounds(gx, gy) else None

    def _apply_tool(self, cell):
        gx, gy = cell
        frame = self.project.frame
        if self.tool == "pencil":
            frame[idx(gx, gy)] = self.colour
        elif self.tool == "eraser":
            frame[idx(gx, gy)] = K.TRANSPARENT
        elif self.tool == "fill":
            flood_fill(frame, gx, gy, self.colour)
        elif self.tool == "picker":
            px = frame[idx(gx, gy)]
            if px[3] != 0:
                self.colour = px
            self.tool = "pencil"

    # ----------------------------------------------------------------- input
    def handle_mouse_down(self, pos):
        # Palette swatches.
        for i, sw in enumerate(self._palette_rects()):
            if sw.collidepoint(pos):
                self.colour = K.PALETTE[i]
                return
        # Tool buttons.
        for name, rect in self._tool_rects():
            if rect.collidepoint(pos):
                self.tool = name
                return
        # Sprite tabs.
        for i, rect in self._tab_rects():
            if rect.collidepoint(pos):
                self.select_sprite(i)
                return
        # Timeline thumbnails.
        for i, rect in enumerate(self._thumb_rects()):
            if rect.collidepoint(pos):
                self.project.frame_index = i
                return
        # Generic buttons.
        for b in self.buttons:
            if b.hit(pos):
                b.on_click()
                return
        # Canvas painting.
        cell = self._canvas_cell(pos)
        if cell:
            self._begin_stroke()
            self._painting = self.tool in ("pencil", "eraser")
            self._apply_tool(cell)
            if not self._painting:  # fill / picker are one-shot
                self._commit_stroke()

    def handle_mouse_up(self):
        if self._painting:
            self._commit_stroke()
        self._painting = False

    def handle_drag(self, pos):
        if self._painting:
            cell = self._canvas_cell(pos)
            if cell:
                self._apply_tool(cell)

    def handle_key(self, e):
        ctrl = e.mod & pygame.KMOD_CTRL
        shift = e.mod & pygame.KMOD_SHIFT
        k = e.key
        if ctrl and k == pygame.K_z:
            (self.undo.redo if shift else self.undo.undo)(self.project)
        elif ctrl and k == pygame.K_y:
            self.undo.redo(self.project)
        elif ctrl and k == pygame.K_s:
            self.save()
        elif ctrl and k == pygame.K_o:
            self.load()
        elif ctrl and k == pygame.K_e:
            self.export()
        elif k == pygame.K_p:
            self.tool = "pencil"
        elif k == pygame.K_e:
            self.tool = "eraser"
        elif k == pygame.K_f:
            self.tool = "fill"
        elif k == pygame.K_i:
            self.tool = "picker"
        elif k == pygame.K_n:
            self.add_frame()
        elif k == pygame.K_d:
            self.duplicate_frame()
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self.delete_frame()
        elif k == pygame.K_c:
            self.clear_frame()
        elif k == pygame.K_COMMA:
            self.next_frame(-1)
        elif k == pygame.K_PERIOD:
            self.next_frame(1)
        elif k == pygame.K_SPACE:
            self.toggle_play()
        elif k == pygame.K_g:
            self.toggle_grid()
        elif k == pygame.K_o:
            self.toggle_onion()
        elif k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            self.select_sprite(k - pygame.K_1)
        elif k == pygame.K_h:
            print(HELP_TEXT)

    # --------------------------------------------------------------- regions
    def _palette_rects(self):
        rects = []
        cols, sw, gap = 8, 16, 2
        x0, y0 = K.LEFT_X, 250
        for i in range(len(K.PALETTE)):
            r, c = divmod(i, cols)
            rects.append(pygame.Rect(x0 + c * (sw + gap), y0 + r * (sw + gap), sw, sw))
        return rects

    def _tool_rects(self):
        out = []
        y0 = 90
        for i, name in enumerate(TOOLS):
            out.append((name, pygame.Rect(K.LEFT_X, y0 + i * 32, K.LEFT_W, 26)))
        return out

    def _tab_rects(self):
        out = []
        x = K.CANVAS_X
        for i, s in enumerate(self.project.sprites):
            w = 96
            out.append((i, pygame.Rect(x, 16, w, 28)))
            x += w + 6
        return out

    def _thumb_rects(self):
        out = []
        x = K.TIMELINE_X
        for i in range(len(self.project.sprite.frames)):
            out.append(pygame.Rect(x, K.TIMELINE_Y, K.THUMB, K.THUMB))
            x += K.THUMB + 6
        return out

    # --------------------------------------------------------------- drawing
    def _text(self, s, pos, font=None, colour=K.C_TEXT):
        self.screen.blit((font or self.font).render(s, True, colour), pos)

    def _panel(self, rect, hi=False):
        pygame.draw.rect(self.screen, K.C_PANEL_HI if hi else K.C_PANEL, rect, border_radius=4)

    def draw(self):
        self.screen.fill(K.C_BG)
        self._draw_tabs()
        self._draw_tools_palette()
        self._draw_canvas()
        self._draw_right_panel()
        self._draw_timeline()
        self._draw_buttons()
        self._draw_status()
        pygame.display.flip()

    def _draw_tabs(self):
        for i, rect in self._tab_rects():
            active = i == self.project.sprite_index
            self._panel(rect, hi=active)
            if active:
                pygame.draw.rect(self.screen, K.C_ACCENT, rect, 2, border_radius=4)
            name = self.project.sprites[i].name
            self._text(name, (rect.x + 8, rect.y + 6),
                       colour=K.C_TEXT if active else K.C_TEXT_DIM)

    def _draw_tools_palette(self):
        self._text("TOOLS", (K.LEFT_X, 66), self.font_sm, K.C_TEXT_DIM)
        for name, rect in self._tool_rects():
            active = name == self.tool
            self._panel(rect, hi=active)
            if active:
                pygame.draw.rect(self.screen, K.C_ACCENT, rect, 2, border_radius=4)
            self._text(name.capitalize(), (rect.x + 8, rect.y + 5),
                       colour=K.C_TEXT if active else K.C_TEXT_DIM)

        self._text("PALETTE", (K.LEFT_X, 230), self.font_sm, K.C_TEXT_DIM)
        for i, sw in enumerate(self._palette_rects()):
            pygame.draw.rect(self.screen, K.PALETTE[i][:3], sw)
            if K.PALETTE[i] == self.colour:
                pygame.draw.rect(self.screen, K.C_ACCENT, sw.inflate(4, 4), 2)

        # Current colour swatch.
        cy = 250 + 4 * (16 + 2) + 12
        self._text("COLOUR", (K.LEFT_X, cy), self.font_sm, K.C_TEXT_DIM)
        sw = pygame.Rect(K.LEFT_X, cy + 16, 40, 40)
        pygame.draw.rect(self.screen, self.colour[:3], sw)
        pygame.draw.rect(self.screen, K.C_BORDER, sw, 1)
        self._text("#%02X%02X%02X" % self.colour[:3],
                   (K.LEFT_X + 48, cy + 28), self.font_sm)

    def _draw_canvas(self):
        self.screen.blit(self._checker, (K.CANVAS_X, K.CANVAS_Y))

        # Onion skin: previous frame, faint.
        if self.onion and len(self.project.sprite.frames) > 1:
            prev = self.project.sprite.frames[self.project.frame_index - 1]
            self._blit_frame(prev, alpha=70)

        self._blit_frame(self.project.frame)

        if self.show_grid:
            for gx in range(K.GRID_W + 1):
                x = K.CANVAS_X + gx * K.CELL
                pygame.draw.line(self.screen, K.C_GRID,
                                 (x, K.CANVAS_Y), (x, K.CANVAS_Y + K.CANVAS_H))
            for gy in range(K.GRID_H + 1):
                y = K.CANVAS_Y + gy * K.CELL
                pygame.draw.line(self.screen, K.C_GRID,
                                 (K.CANVAS_X, y), (K.CANVAS_X + K.CANVAS_W, y))
        pygame.draw.rect(self.screen, K.C_BORDER,
                         (K.CANVAS_X, K.CANVAS_Y, K.CANVAS_W, K.CANVAS_H), 2)

        # Hovered-cell highlight.
        cell = self._canvas_cell(pygame.mouse.get_pos())
        if cell:
            gx, gy = cell
            r = pygame.Rect(K.CANVAS_X + gx * K.CELL, K.CANVAS_Y + gy * K.CELL,
                            K.CELL, K.CELL)
            pygame.draw.rect(self.screen, K.C_ACCENT, r, 1)

    def _blit_frame(self, frame, alpha=255):
        sq = K.CELL
        for gy in range(K.GRID_H):
            for gx in range(K.GRID_W):
                px = frame[idx(gx, gy)]
                if px[3] == 0:
                    continue
                rect = (K.CANVAS_X + gx * sq, K.CANVAS_Y + gy * sq, sq, sq)
                if alpha < 255:
                    s = pygame.Surface((sq, sq), pygame.SRCALPHA)
                    s.fill((*px[:3], alpha))
                    self.screen.blit(s, rect[:2])
                else:
                    self.screen.fill(px[:3], rect)

    def _draw_right_panel(self):
        x = K.RIGHT_X
        s = self.project.sprite
        self._text("INFO", (x, 60), self.font_sm, K.C_TEXT_DIM)
        lines = [
            f"sprite : {s.name}",
            f"frame  : {self.project.frame_index + 1}/{len(s.frames)}",
            f"fps    : {s.fps}",
            f"tool   : {self.tool}",
            f"onion  : {'on' if self.onion else 'off'}",
            f"play   : {'>' if self.playing else 'paused'}",
        ]
        for i, ln in enumerate(lines):
            self._text(ln, (x, 82 + i * 20), self.font_sm)

        # Live animation preview (4x).
        self._text("PREVIEW", (x, 210), self.font_sm, K.C_TEXT_DIM)
        scale = 4
        pr = pygame.Rect(x, 226, K.GRID_W * scale, K.GRID_H * scale)
        pygame.draw.rect(self.screen, K.C_PANEL, pr)
        frame = self.project.frame
        for gy in range(K.GRID_H):
            for gx in range(K.GRID_W):
                px = frame[idx(gx, gy)]
                if px[3]:
                    self.screen.fill(px[:3], (pr.x + gx * scale, pr.y + gy * scale,
                                              scale, scale))
        pygame.draw.rect(self.screen, K.C_BORDER, pr, 1)

    def _draw_timeline(self):
        self._text("FRAMES", (K.TIMELINE_X, K.TIMELINE_Y - 18),
                   self.font_sm, K.C_TEXT_DIM)
        for i, rect in enumerate(self._thumb_rects()):
            pygame.draw.rect(self.screen, K.C_PANEL, rect)
            frame = self.project.sprite.frames[i]
            sc = K.THUMB / K.GRID_W
            for gy in range(K.GRID_H):
                for gx in range(K.GRID_W):
                    px = frame[idx(gx, gy)]
                    if px[3]:
                        self.screen.fill(
                            px[:3],
                            (rect.x + int(gx * sc), rect.y + int(gy * sc),
                             max(1, int(sc)), max(1, int(sc))))
            border = K.C_ACCENT if i == self.project.frame_index else K.C_BORDER
            pygame.draw.rect(self.screen, border, rect, 2)
            self._text(str(i + 1), (rect.x + 2, rect.bottom - 14), self.font_sm)

    def _draw_buttons(self):
        for b in self.buttons:
            self._panel(b.rect)
            self._text(b.label, (b.rect.x + 8, b.rect.y + 5), self.font_sm)

    def _draw_status(self):
        bar = pygame.Rect(0, K.WINDOW_H - 24, K.WINDOW_W, 24)
        pygame.draw.rect(self.screen, K.C_PANEL, bar)
        self._text(self.status, (10, K.WINDOW_H - 20), self.font_sm, K.C_TEXT_DIM)

    # ------------------------------------------------------------------- loop
    def update(self, dt):
        if self.playing:
            s = self.project.sprite
            self._play_acc += dt
            spf = 1.0 / max(1, s.fps)
            while self._play_acc >= spf:
                self._play_acc -= spf
                self.next_frame(1)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(K.FPS) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.handle_mouse_down(e.pos)
                elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                    self.handle_mouse_up()
                elif e.type == pygame.MOUSEMOTION:
                    self.handle_drag(e.pos)
                elif e.type == pygame.KEYDOWN:
                    self.handle_key(e)
            self.update(dt)
            self.draw()
        pygame.quit()


HELP_TEXT = """
Pixel Art Editor — shortcuts
  Tools     P pencil  E eraser  F fill  I picker
  Frames    N new  D duplicate  Del delete  C clear  , / . prev/next
  Sprites   1-4 select character/props tab
  Playback  Space play/pause   (FPS +/- buttons on the right)
  View      G grid   O onion skin
  Edit      Ctrl+Z undo  Ctrl+Shift+Z / Ctrl+Y redo
  File      Ctrl+S save  Ctrl+O load  Ctrl+E export PNGs
"""
