"""Geist - A roguelike game."""

import os
os.environ["SDL_RENDER_SCALE_QUALITY"] = "0"

import tcod.console
import tcod.context
import tcod.event

from engine import Game, GameState

MAP_WIDTH = 100
MAP_HEIGHT = 100
UI_WIDTH = 30

MOVE_KEYS: dict[int, tuple[int, int]] = {
    # Arrow keys
    tcod.event.KeySym.UP: (0, -1),
    tcod.event.KeySym.DOWN: (0, 1),
    tcod.event.KeySym.LEFT: (-1, 0),
    tcod.event.KeySym.RIGHT: (1, 0),
    # Numpad
    tcod.event.KeySym.KP_1: (-1, 1),
    tcod.event.KeySym.KP_2: (0, 1),
    tcod.event.KeySym.KP_3: (1, 1),
    tcod.event.KeySym.KP_4: (-1, 0),
    tcod.event.KeySym.KP_6: (1, 0),
    tcod.event.KeySym.KP_7: (-1, -1),
    tcod.event.KeySym.KP_8: (0, -1),
    tcod.event.KeySym.KP_9: (1, -1),
}

# Vi-keys mapped separately so they can be disabled when inventory is open
VI_MOVE_KEYS: dict[int, tuple[int, int]] = {
    tcod.event.KeySym.h: (-1, 0),
    tcod.event.KeySym.j: (0, 1),
    tcod.event.KeySym.k: (0, -1),
    tcod.event.KeySym.l: (1, 0),
    tcod.event.KeySym.y: (-1, -1),
    tcod.event.KeySym.u: (1, -1),
    tcod.event.KeySym.b: (-1, 1),
    tcod.event.KeySym.n: (1, 1),
}

# Combined for targeting and look mode (where letters don't conflict)
ALL_MOVE_KEYS = {**MOVE_KEYS, **VI_MOVE_KEYS}

WAIT_KEYS = {tcod.event.KeySym.KP_5, tcod.event.KeySym.N5}


def main() -> None:
    game = Game(MAP_WIDTH, MAP_HEIGHT)
    total_w = MAP_WIDTH + UI_WIDTH
    console = tcod.console.Console(total_w, MAP_HEIGHT, order="F")
    drop_mode = False  # When True in inventory, next letter drops instead of uses

    with tcod.context.new(
        columns=total_w, rows=MAP_HEIGHT, title="Geist",
        sdl_window_flags=0x2020,
    ) as context:
        while game.running:
            console.clear()
            game.render(console)
            context.present(console)

            # During animation, don't block on events — poll and keep rendering
            if game.state == GameState.ANIMATING:
                for event in tcod.event.get():
                    if isinstance(event, tcod.event.Quit):
                        game.running = False
                continue

            for event in tcod.event.get():
                # Convert event for mouse tile coordinates
                context.convert_event(event)

                if isinstance(event, tcod.event.Quit):
                    game.running = False

                # ── Mouse Motion: track hover position ──
                elif isinstance(event, tcod.event.MouseMotion):
                    tx, ty = int(event.tile.x), int(event.tile.y)
                    game.mouse_x = tx
                    game.mouse_y = ty
                    game.mouse_in_map = (0 <= tx < MAP_WIDTH and 0 <= ty < MAP_HEIGHT)

                # ── Mouse Button ──
                elif isinstance(event, tcod.event.MouseButtonDown):
                    tx, ty = int(event.tile.x), int(event.tile.y)
                    in_map = (0 <= tx < MAP_WIDTH and 0 <= ty < MAP_HEIGHT)

                    if event.button == tcod.event.MouseButton.LEFT:
                        if game.state == GameState.PLAYING and in_map:
                            # Adjacent: direct move/attack
                            dx = tx - game.player.x
                            dy = ty - game.player.y
                            if abs(dx) <= 1 and abs(dy) <= 1 and (dx != 0 or dy != 0):
                                game.player_move(dx, dy)
                                game.process_enemies()
                            else:
                                # Distant: pathfind one step toward target
                                if game.player_move_toward(tx, ty):
                                    game.process_enemies()
                        elif game.state == GameState.TARGETING and in_map:
                            # Fire wand in direction toward clicked tile
                            dx = tx - game.player.x
                            dy = ty - game.player.y
                            # Normalize to -1/0/1
                            ndx = (1 if dx > 0 else -1 if dx < 0 else 0)
                            ndy = (1 if dy > 0 else -1 if dy < 0 else 0)
                            if ndx != 0 or ndy != 0:
                                game.fire_wand(ndx, ndy)

                    elif event.button == tcod.event.MouseButton.RIGHT:
                        if game.state == GameState.PLAYING and in_map:
                            game.start_look(tx, ty)
                        elif game.state == GameState.TARGETING:
                            game.cancel_targeting()

                elif isinstance(event, tcod.event.KeyDown):
                    sym = event.sym

                    # ── DEAD / VICTORY: any key exits ──
                    if game.state in (GameState.DEAD, GameState.VICTORY):
                        game.running = False
                        continue

                    # ── LOOKING: movement moves cursor, ESC exits ──
                    if game.state == GameState.LOOKING:
                        if sym == tcod.event.KeySym.ESCAPE:
                            game.cancel_look()
                        elif sym in ALL_MOVE_KEYS:
                            dx, dy = ALL_MOVE_KEYS[sym]
                            game.move_look_cursor(dx, dy)
                        continue

                    # ── CHARACTER: ESC or c exits ──
                    if game.state == GameState.CHARACTER:
                        if sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.c):
                            game.toggle_character_screen()
                        continue

                    # ── TARGETING: direction fires, ESC cancels ──
                    if game.state == GameState.TARGETING:
                        if sym == tcod.event.KeySym.ESCAPE:
                            game.cancel_targeting()
                        elif sym in ALL_MOVE_KEYS:
                            dx, dy = ALL_MOVE_KEYS[sym]
                            game.fire_wand(dx, dy)
                        continue

                    # ── INVENTORY open: letter keys select items ──
                    if game.inventory_open:
                        if sym == tcod.event.KeySym.ESCAPE or sym == tcod.event.KeySym.i:
                            game.inventory_open = False
                            drop_mode = False
                        elif sym == tcod.event.KeySym.d:
                            drop_mode = not drop_mode
                            if drop_mode:
                                game.log("Drop mode: press letter to drop.", (180, 180, 150))
                            else:
                                game.log("Use mode.", (150, 150, 180))
                        elif ord("a") <= sym.value <= ord("z"):
                            index = sym.value - ord("a")
                            if drop_mode:
                                game.drop_item(index)
                                drop_mode = False
                            else:
                                game.use_item(index)
                        continue

                    # ── PLAYING: normal input ──
                    if sym == tcod.event.KeySym.ESCAPE:
                        game.running = False
                    elif sym == tcod.event.KeySym.i:
                        game.inventory_open = not game.inventory_open
                        drop_mode = False
                    elif sym == tcod.event.KeySym.g:
                        game.player_pickup()
                    elif sym == tcod.event.KeySym.x:
                        game.start_look()
                    elif sym == tcod.event.KeySym.c:
                        game.toggle_character_screen()
                    elif sym in WAIT_KEYS:
                        game.player_wait()
                    elif sym in (tcod.event.KeySym.LESS, tcod.event.KeySym.GREATER,
                                 tcod.event.KeySym.PERIOD):
                        game.use_stairs()
                    elif sym == tcod.event.KeySym.EQUALS:
                        game.debug_change_level(+1)
                    elif sym == tcod.event.KeySym.MINUS:
                        game.debug_change_level(-1)
                    elif sym in MOVE_KEYS:
                        game.player_move(*MOVE_KEYS[sym])
                        game.process_enemies()
                    elif sym in VI_MOVE_KEYS:
                        game.player_move(*VI_MOVE_KEYS[sym])
                        game.process_enemies()


if __name__ == "__main__":
    main()
