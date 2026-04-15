"""Geist - A roguelike game."""

import os
os.environ["SDL_RENDER_SCALE_QUALITY"] = "0"

import tcod.console
import tcod.context
import tcod.event
import tcod.tileset

from engine import Game, GameState
from tiles import register_sprites

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

# Combined for targeting, throwing, and look mode (where letters don't conflict)
ALL_MOVE_KEYS = {**MOVE_KEYS, **VI_MOVE_KEYS}

WAIT_KEYS = {tcod.event.KeySym.KP_5, tcod.event.KeySym.N5}


TILE_SIZES = [8, 10, 12, 14, 16, 20, 24]
DEFAULT_TILE_IDX = 4  # 16px


def _load_tileset(tile_size: int) -> tcod.tileset.Tileset | None:
    """Generate a font tilesheet at the given size, load it, register sprites."""
    out = os.path.join(os.path.dirname(__file__), "assets", f"tileset_{tile_size}.png")
    base = os.path.join(os.path.dirname(__file__), "assets", "tileset.png")
    # Use the pre-generated 16px sheet if it matches, otherwise generate on the fly
    if tile_size == 16 and os.path.exists(base):
        path = base
    elif os.path.exists(out):
        path = out
    else:
        try:
            from generate_tileset import generate_tileset
            generate_tileset(tile_size=tile_size, output=out)
            path = out
        except Exception:
            if os.path.exists(base):
                path = base
            else:
                return None
    ts = tcod.tileset.load_tilesheet(path, 16, 16, tcod.tileset.CHARMAP_CP437)
    register_sprites(ts)
    return ts


def main() -> None:
    game = Game(MAP_WIDTH, MAP_HEIGHT)
    total_w = MAP_WIDTH + UI_WIDTH
    console = tcod.console.Console(total_w, MAP_HEIGHT, order="F")
    drop_mode = False   # When True in inventory, next letter drops instead of uses
    throw_mode = False  # When True in inventory, next letter throws instead of uses

    tile_idx = DEFAULT_TILE_IDX
    tileset = _load_tileset(TILE_SIZES[tile_idx])

    with tcod.context.new(
        columns=total_w, rows=MAP_HEIGHT, title="Geist",
        sdl_window_flags=0x2020,
        tileset=tileset,
    ) as context:
        while game.running:
            console.clear()
            game.render(console)
            context.present(console)

            # During animation, don't block on events -- poll and keep rendering
            if game.state == GameState.ANIMATING:
                for event in tcod.event.get():
                    if isinstance(event, tcod.event.Quit):
                        game.running = False
                continue

            # Auto-explore: non-blocking poll so we keep stepping each frame
            if game.auto_exploring and game.state == GameState.PLAYING:
                interrupted = False
                for event in tcod.event.get():
                    context.convert_event(event)
                    if isinstance(event, tcod.event.Quit):
                        game.running = False
                        interrupted = True
                        break
                    elif isinstance(event, (tcod.event.KeyDown, tcod.event.MouseButtonDown)):
                        # Any key or click interrupts auto-explore
                        game.auto_exploring = False
                        game.log("Auto-explore interrupted.", (200, 200, 150))
                        interrupted = True
                        break
                if not interrupted and game.auto_exploring:
                    game.auto_explore()
                continue

            for event in tcod.event.get():
                # Convert event for mouse tile coordinates
                context.convert_event(event)

                if isinstance(event, tcod.event.Quit):
                    game.running = False

                # -- Mouse Motion: track hover position --
                elif isinstance(event, tcod.event.MouseMotion):
                    tx, ty = int(event.tile.x), int(event.tile.y)
                    game.mouse_x = tx
                    game.mouse_y = ty
                    game.mouse_in_map = (0 <= tx < MAP_WIDTH and 0 <= ty < MAP_HEIGHT)

                # -- Mouse Button --
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
                            # Fire wand or throw in direction toward clicked tile
                            dx = tx - game.player.x
                            dy = ty - game.player.y
                            ndx = (1 if dx > 0 else -1 if dx < 0 else 0)
                            ndy = (1 if dy > 0 else -1 if dy < 0 else 0)
                            if ndx != 0 or ndy != 0:
                                if game.throwing_item is not None:
                                    game.fire_throw(ndx, ndy)
                                else:
                                    game.fire_wand(ndx, ndy)

                        elif game.state == GameState.THROWING and in_map:
                            dx = tx - game.player.x
                            dy = ty - game.player.y
                            ndx = (1 if dx > 0 else -1 if dx < 0 else 0)
                            ndy = (1 if dy > 0 else -1 if dy < 0 else 0)
                            if ndx != 0 or ndy != 0:
                                game.fire_throw(ndx, ndy)

                    elif event.button == tcod.event.MouseButton.RIGHT:
                        if game.state == GameState.PLAYING and in_map:
                            game.start_look(tx, ty)
                        elif game.state == GameState.TARGETING:
                            game.cancel_targeting()
                        elif game.state == GameState.THROWING:
                            game.cancel_throwing()

                elif isinstance(event, tcod.event.KeyDown):
                    sym = event.sym

                    # -- ZOOM: Ctrl+= zoom in, Ctrl+- zoom out --
                    if event.mod & tcod.event.Modifier.CTRL:
                        if sym in (tcod.event.KeySym.EQUALS, tcod.event.KeySym.PLUS, tcod.event.KeySym.KP_PLUS):
                            if tile_idx < len(TILE_SIZES) - 1:
                                tile_idx += 1
                                new_ts = _load_tileset(TILE_SIZES[tile_idx])
                                if new_ts:
                                    context.change_tileset(new_ts)
                            continue
                        elif sym in (tcod.event.KeySym.MINUS, tcod.event.KeySym.KP_MINUS):
                            if tile_idx > 0:
                                tile_idx -= 1
                                new_ts = _load_tileset(TILE_SIZES[tile_idx])
                                if new_ts:
                                    context.change_tileset(new_ts)
                            continue

                    # -- DEAD / VICTORY: any key exits --
                    if game.state in (GameState.DEAD, GameState.VICTORY):
                        game.running = False
                        continue

                    # -- LOOKING: movement moves cursor, ESC exits --
                    if game.state == GameState.LOOKING:
                        if sym == tcod.event.KeySym.ESCAPE:
                            game.cancel_look()
                        elif sym in ALL_MOVE_KEYS:
                            dx, dy = ALL_MOVE_KEYS[sym]
                            game.move_look_cursor(dx, dy)
                        continue

                    # -- CHARACTER: ESC or c exits --
                    if game.state == GameState.CHARACTER:
                        if sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.c):
                            game.toggle_character_screen()
                        continue

                    # -- TARGETING: direction fires wand, ESC cancels --
                    if game.state == GameState.TARGETING:
                        if sym == tcod.event.KeySym.ESCAPE:
                            game.cancel_targeting()
                        elif sym in ALL_MOVE_KEYS:
                            dx, dy = ALL_MOVE_KEYS[sym]
                            if game.throwing_item is not None:
                                game.fire_throw(dx, dy)
                            else:
                                game.fire_wand(dx, dy)
                        continue

                    # -- THROWING: direction fires throw, ESC cancels --
                    if game.state == GameState.THROWING:
                        if sym == tcod.event.KeySym.ESCAPE:
                            game.cancel_throwing()
                        elif sym in ALL_MOVE_KEYS:
                            dx, dy = ALL_MOVE_KEYS[sym]
                            game.fire_throw(dx, dy)
                        continue

                    # -- INVENTORY open: letter keys select items --
                    if game.inventory_open:
                        if sym == tcod.event.KeySym.ESCAPE or sym == tcod.event.KeySym.i:
                            game.inventory_open = False
                            drop_mode = False
                            throw_mode = False
                        elif sym == tcod.event.KeySym.d:
                            # Toggle drop mode (disable throw mode)
                            throw_mode = False
                            drop_mode = not drop_mode
                            if drop_mode:
                                game.log("Drop mode: press letter to drop.", (180, 180, 150))
                            else:
                                game.log("Use mode.", (150, 150, 180))
                        elif sym == tcod.event.KeySym.t:
                            # Toggle throw mode (disable drop mode)
                            drop_mode = False
                            throw_mode = not throw_mode
                            if throw_mode:
                                game.log("Throw mode: press letter to throw.", (200, 180, 100))
                            else:
                                game.log("Use mode.", (150, 150, 180))
                        elif ord("a") <= sym.value <= ord("z"):
                            index = sym.value - ord("a")
                            if drop_mode:
                                game.drop_item(index)
                                drop_mode = False
                            elif throw_mode:
                                game.start_throw(index)
                                throw_mode = False
                                # start_throw closes inventory and enters THROWING state
                            else:
                                game.use_item(index)
                        continue

                    # -- PLAYING: normal input --

                    # Paralysis check: if paralyzed, skip action and let enemies act
                    if "paralyzed" in game.player.effects:
                        if sym in MOVE_KEYS or sym in VI_MOVE_KEYS or sym in WAIT_KEYS:
                            game.log("You are paralyzed!", (200, 200, 100))
                            game.process_enemies()
                            continue

                    if sym == tcod.event.KeySym.ESCAPE:
                        game.running = False
                    elif sym == tcod.event.KeySym.i:
                        game.inventory_open = not game.inventory_open
                        drop_mode = False
                        throw_mode = False
                    elif sym == tcod.event.KeySym.g:
                        game.player_pickup()
                    elif sym == tcod.event.KeySym.x:
                        game.start_look()
                    elif sym == tcod.event.KeySym.c:
                        game.toggle_character_screen()
                    elif sym == tcod.event.KeySym.e:
                        # Eat: check for corpse at feet first, then inventory food
                        corpses = [
                            e for e in game.entities
                            if e.x == game.player.x and e.y == game.player.y
                            and e.char == ord("%") and not e.blocks
                        ]
                        if corpses:
                            game.eat_corpse()
                            game.process_enemies()
                        else:
                            # Find first food item in inventory
                            food_index = None
                            for idx, item_entity in enumerate(game.inventory):
                                if item_entity.item and item_entity.item.get("type") == "food":
                                    food_index = idx
                                    break
                            if food_index is not None:
                                game.eat_food(food_index)
                                game.process_enemies()
                            else:
                                game.log("Nothing to eat.", (150, 150, 150))
                    elif sym == tcod.event.KeySym.t:
                        # Throw: open inventory in throw mode
                        game.inventory_open = True
                        drop_mode = False
                        throw_mode = True
                        game.log("Throw mode: press letter to throw.", (200, 180, 100))
                    elif sym == tcod.event.KeySym.s:
                        # Search: reveal adjacent traps
                        game.search()
                        game.process_enemies()
                    elif sym == tcod.event.KeySym.o:
                        # Open door: auto-detect adjacent closed door
                        opened = False
                        for ddx in range(-1, 2):
                            for ddy in range(-1, 2):
                                if ddx == 0 and ddy == 0:
                                    continue
                                pos = (game.player.x + ddx, game.player.y + ddy)
                                if pos in game.doors and game.doors[pos] == "closed":
                                    game.open_door(ddx, ddy)
                                    opened = True
                                    break
                            if opened:
                                break
                        if opened:
                            game.process_enemies()
                        else:
                            game.log("No adjacent door to open.", (150, 150, 150))
                    elif sym == tcod.event.KeySym.a:
                        # Auto-explore
                        game.auto_exploring = True
                        game.auto_explore()
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
