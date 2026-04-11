"""Dungeon generation: layout dispatch + entity placement + connectivity guarantee."""

import random

import numpy as np
import tcod.path

from data import (
    get_monsters, get_items, pick_weighted,
    ENEMY_PREFIXES, CHAMPION_TINT, ITEM_PREFIXES, ITEM_SUFFIXES,
    generate_random_wand, generate_random_scroll,
    generate_random_potion, generate_random_ring,
    generate_random_amulet, generate_random_food,
    generate_random_trap, TRAP_TYPES,
)

MONSTER_CHANCE = 0.002
ITEM_CHANCE = 0.0008
TRAP_CHANCE = 0.0015
DOOR_CHANCE = 0.30


class Rect:
    """A rectangular room."""

    __slots__ = ("x1", "y1", "x2", "y2")

    def __init__(self, x: int, y: int, w: int, h: int):
        self.x1, self.y1 = x, y
        self.x2, self.y2 = x + w, y + h

    def center(self) -> tuple[int, int]:
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    def intersects(self, other: "Rect") -> bool:
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )

    def inner_tiles(self) -> list[tuple[int, int]]:
        """Return all inner floor tiles of this room."""
        tiles = []
        for x in range(self.x1 + 1, self.x2):
            for y in range(self.y1 + 1, self.y2):
                tiles.append((x, y))
        return tiles


def _prune_unreachable(walkable: np.ndarray, transparent: np.ndarray, origin_x: int, origin_y: int):
    """Remove any walkable tiles not reachable from (origin_x, origin_y)."""
    w, h = walkable.shape
    cost = walkable.astype(np.int32, order="F")
    dist = tcod.path.maxarray((w, h), dtype=np.int32, order="F")
    dist[origin_x, origin_y] = 0
    tcod.path.dijkstra2d(dist, cost, 1, 1, out=dist)
    unreachable = walkable & (dist > w * h)
    walkable[unreachable] = False
    transparent[unreachable] = False


def _farthest_room(rooms: list[Rect], origin: tuple[int, int]) -> Rect:
    """Return the room whose center is farthest from origin."""
    best = rooms[0]
    best_dist = 0
    ox, oy = origin
    for room in rooms:
        cx, cy = room.center()
        d = abs(cx - ox) + abs(cy - oy)
        if d > best_dist:
            best_dist = d
            best = room
    return best


def _clamp_color(r: int, g: int, b: int) -> tuple[int, int, int]:
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def apply_enemy_prefix(entity, template: dict) -> None:
    """Maybe apply a random prefix (25%) or champion status (5%) to a monster."""
    roll = random.random()
    if roll < 0.05:
        # Champion: gold tint, +30% all stats
        entity.name = f"Champion {entity.name}"
        entity.hp = int(entity.hp * 1.3)
        entity.max_hp = entity.hp
        entity.power = int(entity.power * 1.3)
        entity.defense = int(entity.defense * 1.3)
        entity.xp_value = int(entity.xp_value * 2.0)
        r, g, b = entity.fg
        tr, tg, tb = CHAMPION_TINT
        entity.fg = _clamp_color(r + tr, g + tg, b + tb)
    elif roll < 0.30:
        # Random prefix
        prefix = random.choice(ENEMY_PREFIXES)
        entity.name = f"{prefix['name']} {entity.name}"
        entity.hp = max(1, entity.hp + prefix["hp"])
        entity.max_hp = entity.hp
        entity.power = max(0, entity.power + prefix["power"])
        entity.defense = max(0, entity.defense + prefix["defense"])
        if prefix["ai"]:
            entity.ai = prefix["ai"]
        r, g, b = entity.fg
        tr, tg, tb = prefix["tint"]
        entity.fg = _clamp_color(r + tr, g + tg, b + tb)
        # Giant: uppercase char
        if prefix["name"] == "Giant":
            ch = chr(entity.char)
            if ch.islower():
                entity.char = ord(ch.upper())
        # grant_ability from prefix
        if "grant_ability" in prefix:
            entity.ability = prefix["grant_ability"]
            entity.ability_params = prefix.get("grant_ability_params")


def apply_item_affixes(template: dict) -> dict:
    """Maybe apply prefix (~30%) and/or suffix (~15%) to an item template."""
    # Skip affixes for scrolls
    if template.get("type") == "scroll":
        return template

    name = template["name"]
    itype = template.get("type", "")

    # Prefix
    if random.random() < 0.30:
        prefix = random.choice(ITEM_PREFIXES)
        name = f"{prefix['name']} {name}"
        if itype == "weapon":
            template["power_bonus"] = template.get("power_bonus", 0) + prefix["power_bonus"]
        elif itype == "armor":
            template["defense_bonus"] = template.get("defense_bonus", 0) + prefix["defense_bonus"]
        elif itype == "potion":
            template["heal"] = int(template.get("heal", 0) * prefix["heal_mult"])
        elif itype == "wand":
            template["charges"] = template.get("charges", 0) + prefix["charges"]

    # Suffix
    if random.random() < 0.15:
        suffix = random.choice(ITEM_SUFFIXES)
        name = f"{name} {suffix['name']}"
        if itype == "weapon":
            template["power_bonus"] = template.get("power_bonus", 0) + suffix["power_bonus"]
        elif itype == "armor":
            template["defense_bonus"] = template.get("defense_bonus", 0) + suffix["defense_bonus"]
        elif itype == "potion":
            template["heal"] = template.get("heal", 0) + suffix["heal_bonus"]
        elif itype == "wand":
            template["charges"] = template.get("charges", 0) + suffix["charges"]

    template["name"] = name
    return template


def _resolve_wand(template: dict, depth: int) -> dict:
    """Replace generic wand template with a specific wand type."""
    wand_info = generate_random_wand(depth)
    template["name"] = wand_info["name"]
    template["fg"] = wand_info["fg"]
    template["wand_id"] = wand_info["wand_id"]
    template["bolt_fg"] = wand_info["bolt_fg"]
    template["bolt_char"] = wand_info["bolt_char"]
    return template


def _resolve_scroll(template: dict) -> dict:
    """Replace generic scroll template with a specific scroll type."""
    scroll_info = generate_random_scroll()
    template["name"] = scroll_info["name"]
    template["fg"] = scroll_info["fg"]
    template["scroll_id"] = scroll_info["scroll_id"]
    return template


def _resolve_potion(template: dict) -> dict:
    """Replace generic potion template with a specific potion type."""
    info = generate_random_potion()
    template["potion_id"] = info["potion_id"]
    template["name"] = info["name"]
    template["fg"] = info["fg"]
    # Copy all effect data
    for key in ("effect", "value", "status", "duration", "buff_power", "buff_defense"):
        if key in info:
            template[key] = info[key]
    return template


def _resolve_ring(template: dict) -> dict:
    """Replace generic ring template with a specific ring type."""
    info = generate_random_ring()
    template["ring_id"] = info["ring_id"]
    template["name"] = info["name"]
    template["fg"] = info["fg"]
    for k, v in info.items():
        if k not in ("ring_id", "name", "fg"):
            template[k] = v
    return template


def _resolve_amulet(template: dict) -> dict:
    """Replace generic amulet template with a specific amulet type."""
    info = generate_random_amulet()
    template["amulet_id"] = info["amulet_id"]
    template["name"] = info["name"]
    template["fg"] = info["fg"]
    for k, v in info.items():
        if k not in ("amulet_id", "name", "fg"):
            template[k] = v
    return template


def _resolve_food(template: dict) -> dict:
    """Replace generic food template with a specific food type."""
    info = generate_random_food()
    template["food_id"] = info["food_id"]
    template["name"] = info["name"]
    template["fg"] = info["fg"]
    for k, v in info.items():
        if k not in ("food_id", "name", "fg"):
            template[k] = v
    return template


def _resolve_item(template: dict, depth: int) -> dict:
    """Resolve any generic item template to its specific type."""
    itype = template.get("type")
    if itype == "wand":
        template = _resolve_wand(template, depth)
    elif itype == "scroll":
        template = _resolve_scroll(template)
    elif itype == "potion":
        template = _resolve_potion(template)
    elif itype == "ring":
        template = _resolve_ring(template)
    elif itype == "amulet":
        template = _resolve_amulet(template)
    elif itype == "food":
        template = _resolve_food(template)
    return template


def _find_door_chokepoints(walkable: np.ndarray) -> list[tuple[int, int]]:
    """Find 1-wide corridor chokepoints suitable for door placement.

    A chokepoint is a walkable tile with exactly 2 walkable orthogonal
    neighbors that are on opposite sides (horizontal or vertical).
    """
    w, h = walkable.shape
    chokepoints = []
    for x in range(1, w - 1):
        for y in range(1, h - 1):
            if not walkable[x, y]:
                continue
            n = walkable[x, y - 1]
            s = walkable[x, y + 1]
            e = walkable[x + 1, y]
            ww = walkable[x - 1, y]
            neighbors = int(n) + int(s) + int(e) + int(ww)
            if neighbors != 2:
                continue
            # Opposite sides: north-south or east-west
            if (n and s and not e and not ww) or (e and ww and not n and not s):
                chokepoints.append((x, y))
    return chokepoints


def generate_dungeon(width: int, height: int, depth: int = 1, ascending: bool = True):
    """Generate dungeon.

    Returns (walkable, transparent, entities, special_rooms,
             shrine_locations, layout_name, traps, doors).
    """
    from engine import Entity, RenderOrder

    walkable = np.zeros((width, height), dtype=bool, order="F")
    transparent = np.zeros((width, height), dtype=bool, order="F")
    entities: list = []
    traps: list[dict] = []
    doors: dict[tuple[int, int], str] = {}

    # 1. Pick and run layout generator
    from generators import pick_layout
    layout_fn, layout_name = pick_layout(depth, ascending)
    rooms = layout_fn(width, height, walkable, transparent, random.Random())

    # Corrupted variant: randomly wall-off 3-5% of walkable tiles
    if not ascending:
        wall_pct = random.uniform(0.03, 0.05)
        walkable_coords = list(zip(*np.where(walkable)))
        num_wall = int(len(walkable_coords) * wall_pct)
        for wx, wy in random.sample(walkable_coords, min(num_wall, len(walkable_coords))):
            walkable[wx, wy] = False
            transparent[wx, wy] = False

    # 2. Player start position
    px, py = rooms[0].center() if rooms else (width // 2, height // 2)

    # 3. Prune any tiles unreachable from the player
    _prune_unreachable(walkable, transparent, px, py)

    # 3b. Door placement at chokepoints (before entity placement)
    chokepoints = _find_door_chokepoints(walkable)
    for cx, cy in chokepoints:
        if cx == px and cy == py:
            continue  # never block player start
        if random.random() < DOOR_CHANCE:
            doors[(cx, cy)] = "closed"
            walkable[cx, cy] = False
            transparent[cx, cy] = False

    # 4. Designate special rooms (~15% of non-first rooms)
    special_rooms: dict[int, str] = {}  # room index -> type
    shrine_locations: set[tuple[int, int]] = set()
    room_types = ["vault", "arena", "shrine", "library", "armory", "garden"]
    for i in range(1, len(rooms)):
        if random.random() < 0.15:
            rtype = random.choice(room_types)
            special_rooms[i] = rtype

    # 5. Place player
    entities.append(
        Entity(px, py, "@", "Player", fg=(255, 255, 255), blocks=True, hp=100, power=2)
    )

    # 6. Scatter monsters using data tables (skip special vault/shrine/library/armory/garden rooms)
    monster_table = get_monsters(depth, ascending)
    monster_counts: dict[str, int] = {}

    # Build set of tiles belonging to no-monster and arena rooms
    no_monster_tiles: set[tuple[int, int]] = set()
    arena_tiles: set[tuple[int, int]] = set()
    for ri, rtype in special_rooms.items():
        room = rooms[ri]
        tiles = room.inner_tiles()
        if rtype in ("vault", "shrine", "library", "armory", "garden"):
            no_monster_tiles.update(tiles)
        elif rtype == "arena":
            arena_tiles.update(tiles)

    for x in range(width):
        for y in range(height):
            if (x == px and y == py) or not walkable[x, y]:
                continue
            if (x, y) in no_monster_tiles:
                continue
            chance = MONSTER_CHANCE
            if (x, y) in arena_tiles:
                chance *= 2  # double monsters in arena
            if random.random() > chance:
                continue
            template = pick_weighted(monster_table)
            base_name = template["name"]
            monster_counts[base_name] = monster_counts.get(base_name, 0) + 1
            xp_value = template.get("xp", 0)
            e = Entity(
                x, y, template["char"], f"{base_name} {monster_counts[base_name]}",
                fg=template["fg"], blocks=True, ai="dijkstra",
                hp=template["hp"], power=template["power"], defense=template["defense"],
                xp_value=xp_value,
                ability=template.get("ability"),
                ability_params=template.get("ability_params"),
                corpse_nutrition=template.get("corpse_nutrition", 0),
                corpse_effect=template.get("corpse_effect"),
            )
            apply_enemy_prefix(e, template)
            entities.append(e)

    # 7. Scatter items using data tables (skip special arena rooms for normal scatter)
    item_table = get_items(depth)
    for x in range(width):
        for y in range(height):
            if (x == px and y == py) or not walkable[x, y]:
                continue
            if random.random() > ITEM_CHANCE:
                continue
            if any(e.blocks and e.x == x and e.y == y for e in entities):
                continue
            template = pick_weighted(item_table)
            template = _resolve_item(template, depth)
            template = apply_item_affixes(template)
            entities.append(
                Entity(
                    x, y, template["char"], template["name"],
                    fg=template["fg"], blocks=False,
                    render_order=RenderOrder.ITEM,
                    item=template,
                )
            )

    # 7b. Scatter traps
    # Build set of entity positions and shrine room tiles for exclusion
    entity_positions: set[tuple[int, int]] = {(e.x, e.y) for e in entities}
    shrine_tiles: set[tuple[int, int]] = set()
    for ri, rtype in special_rooms.items():
        if rtype == "shrine":
            shrine_tiles.update(rooms[ri].inner_tiles())

    for x in range(width):
        for y in range(height):
            if not walkable[x, y]:
                continue
            if x == px and y == py:
                continue
            if (x, y) in entity_positions:
                continue
            if (x, y) in shrine_tiles:
                continue
            if random.random() > TRAP_CHANCE:
                continue
            trap_info = generate_random_trap()
            trap_entry = {
                "x": x,
                "y": y,
                "revealed": False,
            }
            # Copy all fields from trap type
            for k, v in trap_info.items():
                trap_entry[k] = v
            traps.append(trap_entry)

    # 8. Populate special rooms
    for ri, rtype in special_rooms.items():
        room = rooms[ri]
        tiles = room.inner_tiles()
        if not tiles:
            continue
        cx, cy = room.center()

        if rtype == "vault":
            # 3-5 items, no monsters (already excluded above)
            num_items = random.randint(3, 5)
            chosen_tiles = random.sample(tiles, min(num_items, len(tiles)))
            for tx, ty in chosen_tiles:
                if any(e.x == tx and e.y == ty for e in entities):
                    continue
                template = pick_weighted(item_table)
                template = _resolve_item(template, depth)
                template = apply_item_affixes(template)
                entities.append(
                    Entity(
                        tx, ty, template["char"], template["name"],
                        fg=template["fg"], blocks=False,
                        render_order=RenderOrder.ITEM,
                        item=template,
                    )
                )

        elif rtype == "arena":
            # One guaranteed good item at center
            template = pick_weighted(item_table)
            template = _resolve_item(template, depth)
            template = apply_item_affixes(template)
            if not any(e.x == cx and e.y == cy and e.blocks for e in entities):
                entities.append(
                    Entity(
                        cx, cy, template["char"], template["name"],
                        fg=template["fg"], blocks=False,
                        render_order=RenderOrder.ITEM,
                        item=template,
                    )
                )

        elif rtype == "shrine":
            # No monsters (already excluded), center tile grants +1 random stat
            shrine_locations.add((cx, cy))
            entities.append(
                Entity(
                    cx, cy, "+", "Shrine",
                    fg=(255, 255, 200), blocks=False,
                    render_order=RenderOrder.ITEM,
                    item={"type": "shrine"},
                )
            )

        elif rtype == "library":
            # 2-4 scrolls only
            num_scrolls = random.randint(2, 4)
            chosen_tiles = random.sample(tiles, min(num_scrolls, len(tiles)))
            for tx, ty in chosen_tiles:
                if any(e.x == tx and e.y == ty for e in entities):
                    continue
                template = {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}
                template = _resolve_scroll(template)
                # No affixes on scrolls (apply_item_affixes skips them anyway)
                template = apply_item_affixes(template)
                entities.append(
                    Entity(
                        tx, ty, template["char"], template["name"],
                        fg=template["fg"], blocks=False,
                        render_order=RenderOrder.ITEM,
                        item=template,
                    )
                )

        elif rtype == "armory":
            # 2-3 weapons/armor only
            num_gear = random.randint(2, 3)
            chosen_tiles = random.sample(tiles, min(num_gear, len(tiles)))
            for tx, ty in chosen_tiles:
                if any(e.x == tx and e.y == ty for e in entities):
                    continue
                # Pick weapon or armor from the item table for this depth
                gear_items = [
                    (w, t) for w, t in item_table
                    if t.get("type") in ("weapon", "armor")
                ]
                if not gear_items:
                    continue
                template = pick_weighted(gear_items)
                template = _resolve_item(template, depth)
                template = apply_item_affixes(template)
                entities.append(
                    Entity(
                        tx, ty, template["char"], template["name"],
                        fg=template["fg"], blocks=False,
                        render_order=RenderOrder.ITEM,
                        item=template,
                    )
                )

        elif rtype == "garden":
            # 2-4 food/potions only
            num_garden = random.randint(2, 4)
            chosen_tiles = random.sample(tiles, min(num_garden, len(tiles)))
            for tx, ty in chosen_tiles:
                if any(e.x == tx and e.y == ty for e in entities):
                    continue
                # Randomly choose food or potion
                if random.random() < 0.5:
                    template = {"char": "%", "name": "Food", "fg": (180, 140, 80), "type": "food"}
                    template = _resolve_food(template)
                else:
                    template = {"char": "!", "name": "Potion", "fg": (200, 50, 50), "type": "potion"}
                    template = _resolve_potion(template)
                template = apply_item_affixes(template)
                entities.append(
                    Entity(
                        tx, ty, template["char"], template["name"],
                        fg=template["fg"], blocks=False,
                        render_order=RenderOrder.ITEM,
                        item=template,
                    )
                )

    # 9. Place stairs or Thing-in-Itself
    if len(rooms) >= 2:
        far_room = _farthest_room(rooms, (px, py))
        sx, sy = far_room.center()
    else:
        sx, sy = width // 2, height // 2

    if ascending and depth == 7:
        entities.append(
            Entity(
                sx, sy, "*", "The Thing-in-Itself",
                fg=(255, 255, 100), blocks=False,
                render_order=RenderOrder.ITEM,
                item={"type": "thing"},
            )
        )
    elif ascending:
        entities.append(
            Entity(
                sx, sy, "<", "stairs (ascending)",
                fg=(255, 255, 255), blocks=False,
                render_order=RenderOrder.ITEM,
            )
        )
    else:
        entities.append(
            Entity(
                sx, sy, ">", "stairs (descending)",
                fg=(255, 255, 255), blocks=False,
                render_order=RenderOrder.ITEM,
            )
        )

    return walkable, transparent, entities, special_rooms, shrine_locations, layout_name, traps, doors
