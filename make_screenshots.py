#!/usr/bin/env python3
"""Generate screenshots and an animated GIF of Geist gameplay.

Run with:  uv run --with pillow python make_screenshots.py
"""

import os
import random
import shutil
import time

os.environ["SDL_RENDER_SCALE_QUALITY"] = "0"

import numpy as np
import tcod.console
import tcod.tileset
import tcod.context
import tcod.path
from PIL import Image

from engine import Game, GameState

MAP_WIDTH = 100
MAP_HEIGHT = 100
UI_WIDTH = 30
TOTAL_W = MAP_WIDTH + UI_WIDTH

GIF_FRAMES = 90
FRAME_DELAY_MS = 140
SCREENSHOT_DIR = "_frames"


def find_exploration_target(game: Game) -> tuple[int, int] | None:
    """Find an unexplored walkable tile at the FOV boundary."""
    candidates: list[tuple[int, int]] = []
    for x in range(game.width):
        for y in range(game.height):
            if game.walkable[x, y] and not game.explored[x, y]:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < game.width and 0 <= ny < game.height and game.explored[nx, ny]:
                        candidates.append((x, y))
                        break
    if not candidates:
        return None
    px, py = game.player.x, game.player.y
    candidates.sort(key=lambda c: abs(c[0] - px) + abs(c[1] - py))
    # Pick one of the nearest few for variety
    idx = random.randint(0, min(4, len(candidates) - 1))
    return candidates[idx]


def simulate_step(game: Game) -> bool:
    """Simulate one gameplay step. Returns True if an action was taken."""
    if game.state == GameState.ANIMATING:
        game.vfx.clear()
        game.state = GameState.PLAYING
    if game.state != GameState.PLAYING or not game.player.alive:
        return False

    target = find_exploration_target(game)
    if target:
        moved = game.player_move_toward(target[0], target[1])
        if moved:
            game.process_enemies()
            return True

    # Fallback: random valid move
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]
    random.shuffle(dirs)
    for dx, dy in dirs:
        nx, ny = game.player.x + dx, game.player.y + dy
        if 0 <= nx < game.width and 0 <= ny < game.height and game.walkable[nx, ny]:
            game.player_move(dx, dy)
            game.process_enemies()
            return True
    return False


def render_frame(game: Game, console: tcod.console.Console, context: tcod.context.Context):
    """Render one frame to the SDL window."""
    # Clear any lingering VFX to avoid stuck animation states
    if game.state == GameState.ANIMATING:
        game.vfx.clear()
        game.state = GameState.PLAYING
    console.clear()
    game.render(console)
    context.present(console)


def main() -> None:
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    random.seed(42)  # Reproducible dungeons

    game = Game(MAP_WIDTH, MAP_HEIGHT)
    console = tcod.console.Console(TOTAL_W, MAP_HEIGHT, order="F")

    print(f"Player starts at ({game.player.x}, {game.player.y})")
    print(f"Theme: {game.current_theme['name']}")
    print(f"Capturing {GIF_FRAMES} frames...")

    tileset_path = os.path.join(os.path.dirname(__file__), "assets", "tileset.png")
    if os.path.exists(tileset_path):
        tileset = tcod.tileset.load_tilesheet(
            tileset_path, 16, 16, tcod.tileset.CHARMAP_CP437,
        )
    else:
        tileset = None

    with tcod.context.new(
        columns=TOTAL_W, rows=MAP_HEIGHT, title="Geist - Screenshot Mode",
        sdl_window_flags=0x2020,
        tileset=tileset,
    ) as context:
        # Let the window initialise and render a couple of warm-up frames
        for _ in range(3):
            render_frame(game, console, context)
            time.sleep(0.05)

        for i in range(GIF_FRAMES):
            # Simulate 1-2 steps per frame for faster exploration
            simulate_step(game)
            if game.state in (GameState.DEAD, GameState.VICTORY):
                print(f"Game ended at frame {i} ({game.state.name})")
                break

            # Small real-time gap so the shimmer animation advances
            time.sleep(0.06)

            render_frame(game, console, context)

            path = os.path.join(SCREENSHOT_DIR, f"frame_{i:04d}.png")
            context.save_screenshot(path)

            if (i + 1) % 20 == 0:
                print(f"  frame {i + 1}/{GIF_FRAMES}")

        # Save a standalone hero screenshot (mid-exploration)
        render_frame(game, console, context)
        context.save_screenshot("screenshot.png")
        print("Saved screenshot.png")

    # ── Build GIF ──────────────────────────────────────────────
    print("Assembling GIF...")
    images: list[Image.Image] = []
    frame_paths = sorted(
        f for f in os.listdir(SCREENSHOT_DIR) if f.endswith(".png")
    )
    for fname in frame_paths:
        img = Image.open(os.path.join(SCREENSHOT_DIR, fname)).convert("RGB")
        # Keep full resolution for crispness — GitHub scales it anyway
        images.append(img)

    if not images:
        print("No frames captured!")
        return

    # Quantize to 256 colours per-frame for smaller file
    quantized = [img.quantize(colors=256, method=Image.Quantize.MEDIANCUT) for img in images]

    quantized[0].save(
        "gameplay.gif",
        save_all=True,
        append_images=quantized[1:],
        duration=FRAME_DELAY_MS,
        loop=0,
        optimize=True,
    )
    gif_size = os.path.getsize("gameplay.gif") / (1024 * 1024)
    print(f"Saved gameplay.gif  ({len(images)} frames, {gif_size:.1f} MB)")

    # If GIF is too large for GitHub (>10 MB), resize and rebuild
    if gif_size > 10:
        print("GIF too large — resizing to 50% ...")
        resized = []
        for img in images:
            small = img.resize((img.width // 2, img.height // 2), Image.NEAREST)
            resized.append(small.quantize(colors=256, method=Image.Quantize.MEDIANCUT))
        resized[0].save(
            "gameplay.gif",
            save_all=True,
            append_images=resized[1:],
            duration=FRAME_DELAY_MS,
            loop=0,
            optimize=True,
        )
        gif_size = os.path.getsize("gameplay.gif") / (1024 * 1024)
        print(f"Resized gameplay.gif  ({gif_size:.1f} MB)")

    # Clean up frames
    shutil.rmtree(SCREENSHOT_DIR)
    print("Done!")


if __name__ == "__main__":
    main()
