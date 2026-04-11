"""Dungeon generation: layout dispatch + entity placement + connectivity guarantee."""

import random

import numpy as np
import tcod.path

from data import (
    get_monsters, get_items, pick_weighted,
    ENEMY_PREFIXES, CHAMPION_TINT, ITEM_PREFIXES, ITEM_SUFFIXES,
    generate_random_wand, generate_random_scroll,
)

MONSTER_CHANCE = 0.002
ITEM_CHANCE = 0.0008


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


def generate_dungeon(width: int, height: int, depth: int = 1, ascending: bool = True):
    """Generate dungeon. Returns (walkable, transparent, entities, special_rooms, shrine_locations, layout_name)."""
    from engine import Entity, RenderOrder

    walkable = np.zeros((width, height), dtype=bool, order="F")
    transparent = np.zeros((width, height), dtype=bool, order="F")
    entities: list = []

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

    # 4. Designate special rooms (~15% of non-first rooms)
    special_rooms: dict[int, str] = {}  # room index -> type
    shrine_locations: set[tuple[int, int]] = set()
    for i in range(1, len(rooms)):
        if random.random() < 0.15:
            rtype = random.choice(["vault", "arena", "shrine"])
            special_rooms[i] = rtype

    # 5. Place player
    entities.append(
        Entity(px, py, "@", "Player", fg=(255, 255, 255), blocks=True, hp=100, power=2)
    )

    # 6. Scatter monsters using data tables (skip special vault/shrine rooms)
    monster_table = get_monsters(depth, ascending)
    monster_counts: dict[str, int] = {}

    # Build set of tiles belonging to vault/shrine rooms (no monsters there)
    no_monster_tiles: set[tuple[int, int]] = set()
    arena_tiles: set[tuple[int, int]] = set()
    for ri, rtype in special_rooms.items():
        room = rooms[ri]
        tiles = room.inner_tiles()
        if rtype in ("vault", "shrine"):
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
            # Resolve generic wands/scrolls to specific types
            if template.get("type") == "wand":
                template = _resolve_wand(template, depth)
            elif template.get("type") == "scroll":
                template = _resolve_scroll(template)
            template = apply_item_affixes(template)
            entities.append(
                Entity(
                    x, y, template["char"], template["name"],
                    fg=template["fg"], blocks=False,
                    render_order=RenderOrder.ITEM,
                    item=template,
                )
            )

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
                if template.get("type") == "wand":
                    template = _resolve_wand(template, depth)
                elif template.get("type") == "scroll":
                    template = _resolve_scroll(template)
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
            if template.get("type") == "wand":
                template = _resolve_wand(template, depth)
            elif template.get("type") == "scroll":
                template = _resolve_scroll(template)
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

    return walkable, transparent, entities, special_rooms, shrine_locations, layout_name
