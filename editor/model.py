"""Data model for the editor: frames, sprites, the project, and persistence.

A *frame* is a flat list of RGBA tuples, length GRID_W * GRID_H, indexed by
``y * GRID_W + x``.  Empty pixels use the TRANSPARENT sentinel.  Tuples are
immutable, so a frame copy is just ``list(frame)`` — handy for undo snapshots.
"""

from __future__ import annotations

import json
import os
from collections import deque

from .constants import GRID_W, GRID_H, TRANSPARENT


def new_frame():
    """Return a blank (fully transparent) frame."""
    return [TRANSPARENT] * (GRID_W * GRID_H)


def idx(x, y):
    return y * GRID_W + x


def in_bounds(x, y):
    return 0 <= x < GRID_W and 0 <= y < GRID_H


def flood_fill(frame, x, y, colour):
    """4-connected flood fill starting at (x, y). Mutates ``frame``."""
    if not in_bounds(x, y):
        return
    target = frame[idx(x, y)]
    if target == colour:
        return
    stack = [(x, y)]
    while stack:
        cx, cy = stack.pop()
        if not in_bounds(cx, cy):
            continue
        if frame[idx(cx, cy)] != target:
            continue
        frame[idx(cx, cy)] = colour
        stack.extend(((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)))


class Sprite:
    """A named sprite: an ordered list of animation frames plus a playback fps."""

    def __init__(self, name, frames=None, fps=8):
        self.name = name
        self.frames = frames if frames else [new_frame()]
        self.fps = fps

    def to_dict(self):
        return {
            "name": self.name,
            "fps": self.fps,
            # Store each pixel as a compact [r,g,b,a] list.
            "frames": [[list(px) for px in frame] for frame in self.frames],
        }

    @classmethod
    def from_dict(cls, d):
        frames = [[tuple(px) for px in frame] for frame in d["frames"]]
        return cls(d["name"], frames, d.get("fps", 8))


class Project:
    """The whole document: a list of sprites and the editing selection."""

    def __init__(self, sprites=None):
        self.sprites = sprites if sprites else [
            Sprite("char1"), Sprite("char2"), Sprite("char3"), Sprite("props"),
        ]
        self.sprite_index = 0
        self.frame_index = 0

    # -- selection helpers ---------------------------------------------------
    @property
    def sprite(self) -> Sprite:
        return self.sprites[self.sprite_index]

    @property
    def frame(self):
        return self.sprite.frames[self.frame_index]

    def set_frame(self, frame):
        self.sprite.frames[self.frame_index] = frame

    def clamp(self):
        self.sprite_index = max(0, min(self.sprite_index, len(self.sprites) - 1))
        s = self.sprite
        self.frame_index = max(0, min(self.frame_index, len(s.frames) - 1))

    # -- persistence ---------------------------------------------------------
    def save(self, path):
        data = {"version": 1, "sprites": [s.to_dict() for s in self.sprites]}
        with open(path, "w") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path):
        with open(path) as f:
            data = json.load(f)
        sprites = [Sprite.from_dict(s) for s in data["sprites"]]
        return cls(sprites)


class UndoStack:
    """Bounded undo/redo of (sprite_index, frame_index, frame_snapshot)."""

    def __init__(self, limit=120):
        self._undo = deque(maxlen=limit)
        self._redo = deque(maxlen=limit)

    def push(self, sprite_index, frame_index, snapshot):
        self._undo.append((sprite_index, frame_index, snapshot))
        self._redo.clear()

    def can_undo(self):
        return bool(self._undo)

    def can_redo(self):
        return bool(self._redo)

    def undo(self, project: Project):
        if not self._undo:
            return
        si, fi, snap = self._undo.pop()
        self._redo.append((si, fi, list(project.sprites[si].frames[fi])))
        project.sprites[si].frames[fi] = snap
        project.sprite_index, project.frame_index = si, fi
        project.clamp()

    def redo(self, project: Project):
        if not self._redo:
            return
        si, fi, snap = self._redo.pop()
        self._undo.append((si, fi, list(project.sprites[si].frames[fi])))
        project.sprites[si].frames[fi] = snap
        project.sprite_index, project.frame_index = si, fi
        project.clamp()
