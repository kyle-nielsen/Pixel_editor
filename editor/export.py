"""PNG export helpers built on pygame surfaces.

Exports an individual frame, a horizontal spritesheet, and per-frame PNGs.
Kept separate from the model so the data layer stays free of pygame.
"""

import os

import pygame

from .constants import GRID_W, GRID_H
from .model import idx


def frame_to_surface(frame, scale=1):
    """Render a frame to a per-pixel-alpha Surface, optionally scaled up."""
    surf = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
    for y in range(GRID_H):
        for x in range(GRID_W):
            surf.set_at((x, y), frame[idx(x, y)])
    if scale != 1:
        surf = pygame.transform.scale(surf, (GRID_W * scale, GRID_H * scale))
    return surf


def export_spritesheet(sprite, out_dir, scale=1):
    """Write a horizontal spritesheet PNG. Returns the file path."""
    os.makedirs(out_dir, exist_ok=True)
    n = len(sprite.frames)
    sheet = pygame.Surface((GRID_W * scale * n, GRID_H * scale), pygame.SRCALPHA)
    for i, frame in enumerate(sprite.frames):
        sheet.blit(frame_to_surface(frame, scale), (i * GRID_W * scale, 0))
    path = os.path.join(out_dir, f"{sprite.name}_sheet.png")
    pygame.image.save(sheet, path)
    return path


def export_frames(sprite, out_dir, scale=1):
    """Write one PNG per frame into ``out_dir/<sprite>/``. Returns the dir."""
    sprite_dir = os.path.join(out_dir, sprite.name)
    os.makedirs(sprite_dir, exist_ok=True)
    for i, frame in enumerate(sprite.frames):
        path = os.path.join(sprite_dir, f"{sprite.name}_{i:02d}.png")
        pygame.image.save(frame_to_surface(frame, scale), path)
    return sprite_dir
