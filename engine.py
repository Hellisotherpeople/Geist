"""Game engine: state, entities, logic, and rendering."""

import math
import random
import time
from collections import deque
from enum import Enum, auto

import numpy as np
import tcod.console
import tcod.map
import tcod.path

FOV_RADIUS = 20
UI_WIDTH = 30
INV_W = 28
INV_H = 28
MAX_MESSAGES = 50


class RenderOrder(Enum):
    CORPSE = 1
    ITEM = 2
    ACTOR = 3


class GameState(Enum):
    PLAYING = auto()
    TARGETING = auto()
    DEAD = auto()
    VICTORY = auto()
    ANIMATING = auto()
    LOOKING = auto()
    CHARACTER = auto()


class Entity:
    """A game object: player, monster, item, etc."""

    def __init__(
        self, x: int, y: int, char: str | int, name: str, *,
        fg: tuple[int, int, int] = (255, 255, 255),
        blocks: bool = False, ai: str | None = None,
        hp: int = 0, power: int = 0, defense: int = 0,
        render_order: RenderOrder = RenderOrder.ACTOR,
        item: dict | None = None,
        xp_value: int = 0,
    ):
        self.x = x
        self.y = y
        self.char = ord(char) if isinstance(char, str) else char
        self.name = name
        self.fg = fg
        self.blocks = blocks
        self.ai = ai
        self.hp = hp
        self.max_hp = hp
        self.power = power
        self.defense = defense
        self.render_order = render_order
        self.item = item
        self.confused_turns: int = 0
        self.xp_value: int = xp_value

    @property
    def alive(self) -> bool:
        return self.hp > 0


class Game:
    """Core game state and logic."""

    def __init__(self, width: int, height: int):
        from dungeon import generate_dungeon
        from data import get_theme, PLAYER_TRAITS, get_items, pick_weighted

        self.width = width
        self.height = height
        self.running = True
        self.inventory_open = False
        self.inventory: list[Entity] = []
        self.messages: deque[tuple[str, tuple[int, int, int]]] = deque(maxlen=MAX_MESSAGES)

        # Game progression
        self.depth = 1
        self.ascending = True
        self.has_thing = False
        self.kills = 0
        self.turn_count = 0

        # XP & Leveling
        self.player_xp = 0
        self.player_level = 1

        # Buff system
        self.buffs: list[dict] = []

        # Equipment
        self.equipped_weapon: Entity | None = None
        self.equipped_armor: Entity | None = None

        # State machine
        self.state = GameState.PLAYING
        self.targeting_wand: Entity | None = None

        # Look mode
        self.look_x = 0
        self.look_y = 0

        # Mouse state
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_in_map = False

        # VFX system
        self.vfx: list[dict] = []

        # Shrine tracking
        self.used_shrines: set[tuple[int, int]] = set()

        # Player trait
        self.player_trait = random.choice(PLAYER_TRAITS)

        # Theme
        self.current_theme = get_theme(self.depth, self.ascending)

        # Generate first level
        result = generate_dungeon(width, height, self.depth, self.ascending)
        self.walkable, self.transparent, self.entities = result[0], result[1], result[2]
        self.special_rooms = result[3]
        self.shrine_locations = result[4]
        self.layout_name = result[5]
        self.explored = np.zeros((width, height), dtype=bool, order="F")
        self.fov = np.zeros((width, height), dtype=bool, order="F")
        self.player = self.entities[0]
        self.cost = self.walkable.astype(np.int32, order="F")
        self._recompute_fov()

        # Apply player trait
        trait = self.player_trait
        self.player.max_hp += trait["max_hp"]
        self.player.hp = self.player.max_hp
        self.player.power += trait["power"]
        self.player.defense += trait["defense"]

        # Start with a Wand of Animation
        wand_charges = 3 + trait["wand_charges"]
        wand_item = {
            "char": "~", "name": "Wand of Animation", "fg": (100, 255, 255),
            "type": "wand", "charges": wand_charges,
            "wand_id": "animation", "bolt_fg": (100, 255, 255), "bolt_char": "*",
        }
        wand_entity = Entity(0, 0, "~", "Wand of Animation", fg=(100, 255, 255), item=wand_item)
        self.inventory.append(wand_entity)

        # Scavenger: extra starting item
        if trait["extra_item"]:
            item_table = get_items(self.depth)
            template = pick_weighted(item_table)
            from dungeon import apply_item_affixes, _resolve_wand, _resolve_scroll
            if template.get("type") == "wand":
                template = _resolve_wand(template, self.depth)
            elif template.get("type") == "scroll":
                template = _resolve_scroll(template)
            template = apply_item_affixes(template)
            extra = Entity(0, 0, template["char"], template["name"], fg=template["fg"], item=template)
            self.inventory.append(extra)

        self.log(f"Welcome to Geist \u2014 {self.current_theme['name']}.", (200, 200, 255))
        self.log(f"You are a {trait['name']}.", (220, 200, 255))
        self.log("Escape the cave. Find the Truth.", (180, 180, 220))
        self.log("Mv:arrows X:look C:char I:inv", (150, 150, 180))

    def log(self, text: str, color: tuple[int, int, int] = (200, 200, 200)):
        self.messages.append((text, color))

    def _recompute_fov(self):
        self.fov = tcod.map.compute_fov(
            self.transparent, (self.player.x, self.player.y), radius=FOV_RADIUS,
        )
        self.explored |= self.fov

    def _blocker_at(self, x: int, y: int) -> Entity | None:
        return next((e for e in self.entities if e.blocks and e.x == x and e.y == y), None)

    def _items_at(self, x: int, y: int) -> list[Entity]:
        return [e for e in self.entities if e.item and e.x == x and e.y == y and not e.blocks]

    def _stairs_at(self, x: int, y: int) -> Entity | None:
        return next(
            (e for e in self.entities
             if e.x == x and e.y == y and e.char in (ord("<"), ord(">"), ord("*"))),
            None,
        )

    # ── Buff System ────────────────────────────────────────────

    def _tick_buffs(self):
        expired = []
        for buff in self.buffs:
            buff["turns"] -= 1
            if buff["turns"] <= 0:
                expired.append(buff)
        for buff in expired:
            self.buffs.remove(buff)
            hp_bonus = buff.get("max_hp", 0)
            if hp_bonus > 0:
                self.player.max_hp -= hp_bonus
                self.player.hp = min(self.player.hp, self.player.max_hp)
            self.log(f"{buff['name']} fades.", (180, 180, 150))

    def _get_buff_power(self) -> int:
        return sum(b.get("power", 0) for b in self.buffs)

    def _get_buff_defense(self) -> int:
        return sum(b.get("defense", 0) for b in self.buffs)

    # ── XP & Leveling ─────────────────────────────────────────

    def _check_level_up(self):
        from data import XP_THRESHOLDS
        while (self.player_level < len(XP_THRESHOLDS) - 1
               and self.player_xp >= XP_THRESHOLDS[self.player_level + 1]):
            self.player_level += 1
            cycle = (self.player_level - 2) % 3
            if cycle == 0:
                self.player.max_hp += 10
                self.player.hp += 10
                self.log(f"Level {self.player_level}! +10 max HP.", (255, 255, 100))
            elif cycle == 1:
                self.player.power += 1
                self.log(f"Level {self.player_level}! +1 ATK.", (255, 220, 100))
            else:
                self.player.defense += 1
                self.log(f"Level {self.player_level}! +1 DEF.", (100, 200, 255))

    # ── Player Actions ────────────────────────────────────────

    def player_move(self, dx: int, dy: int):
        if self.state != GameState.PLAYING:
            return
        if not self.player.alive:
            return
        nx, ny = self.player.x + dx, self.player.y + dy
        if not (0 <= nx < self.width and 0 <= ny < self.height and self.walkable[nx, ny]):
            return
        target = self._blocker_at(nx, ny)
        if target and target is not self.player:
            self._attack(self.player, target)
        else:
            self.player.x, self.player.y = nx, ny
            self._recompute_fov()
            self._check_shrine()
            # Atmosphere
            from data import ATMOSPHERE_MESSAGES
            if random.random() < 0.03:
                depth = max(1, min(7, self.depth))
                msgs = ATMOSPHERE_MESSAGES.get(depth, [])
                if msgs:
                    self.log(random.choice(msgs), (120, 120, 160))

    def player_wait(self):
        """Skip turn, regen 1 HP."""
        if self.state != GameState.PLAYING:
            return
        if not self.player.alive:
            return
        if self.player.hp < self.player.max_hp:
            self.player.hp += 1
        self.process_enemies()

    def player_move_toward(self, tx: int, ty: int) -> bool:
        """Move one step toward target via pathfinding. Returns True if moved."""
        if self.state != GameState.PLAYING:
            return False
        dist = tcod.path.maxarray((self.width, self.height), dtype=np.int32, order="F")
        dist[tx, ty] = 0
        tcod.path.dijkstra2d(dist, self.cost, 1, 1, out=dist)
        path = tcod.path.hillclimb2d(dist, (self.player.x, self.player.y), True, True)
        if len(path) > 1:
            nx, ny = int(path[1][0]), int(path[1][1])
            dx = nx - self.player.x
            dy = ny - self.player.y
            self.player_move(dx, dy)
            return True
        return False

    def _check_shrine(self):
        """If player steps on a shrine, grant +1 random stat."""
        pos = (self.player.x, self.player.y)
        if pos in self.used_shrines:
            return
        items = self._items_at(self.player.x, self.player.y)
        for item_e in items:
            if item_e.item and item_e.item.get("type") == "shrine":
                self.used_shrines.add(pos)
                stat = random.choice(["hp", "power", "defense"])
                if stat == "hp":
                    self.player.max_hp += 5
                    self.player.hp += 5
                    self.log("The shrine glows! +5 Max HP.", (255, 255, 200))
                elif stat == "power":
                    self.player.power += 1
                    self.log("The shrine glows! +1 ATK.", (255, 200, 200))
                else:
                    self.player.defense += 1
                    self.log("The shrine glows! +1 DEF.", (200, 200, 255))
                self.entities.remove(item_e)
                return

    def player_pickup(self):
        if self.state != GameState.PLAYING:
            return
        items = self._items_at(self.player.x, self.player.y)
        if not items:
            self.log("Nothing to pick up here.", (150, 150, 150))
            return
        item_entity = items[0]
        # Special: Thing-in-Itself
        if item_entity.char == ord("*"):
            self.has_thing = True
            self.entities.remove(item_entity)
            self.log("You grasp the Thing-in-Itself!", (255, 255, 100))
            self.log("The cave shudders. Descend to escape!", (255, 200, 100))
            self.ascending = False
            return
        # Skip shrines — they activate on step
        if item_entity.item and item_entity.item.get("type") == "shrine":
            self.log("The shrine pulses with energy.", (255, 255, 200))
            return
        if len(self.inventory) >= 26:
            self.log("Inventory full!", (255, 100, 100))
            return
        self.entities.remove(item_entity)
        self.inventory.append(item_entity)
        self.log(f"Picked up {item_entity.name}.", (150, 200, 255))

    def use_item(self, index: int):
        """Use/equip item at inventory index."""
        if index < 0 or index >= len(self.inventory):
            return
        item_entity = self.inventory[index]
        item = item_entity.item
        if not item:
            return

        if item["type"] == "potion":
            heal = item["heal"]
            healed = min(heal, self.player.max_hp - self.player.hp)
            self.player.hp += healed
            self.log(f"Healed {healed} HP.", (100, 255, 100))
            self.inventory.pop(index)

        elif item["type"] == "weapon":
            if self.equipped_weapon is item_entity:
                self.equipped_weapon = None
                self.log(f"Unequipped {item_entity.name}.", (200, 200, 150))
            else:
                self.equipped_weapon = item_entity
                self.log(f"Equipped {item_entity.name} (+{item['power_bonus']} ATK).", (255, 220, 100))

        elif item["type"] == "armor":
            if self.equipped_armor is item_entity:
                self.equipped_armor = None
                self.log(f"Unequipped {item_entity.name}.", (200, 200, 150))
            else:
                self.equipped_armor = item_entity
                self.log(f"Equipped {item_entity.name} (+{item['defense_bonus']} DEF).", (100, 200, 255))

        elif item["type"] == "wand":
            self.targeting_wand = item_entity
            self.state = GameState.TARGETING
            self.inventory_open = False
            self.log("Aim the wand: direction key to fire, ESC to cancel.", (100, 255, 255))

        elif item["type"] == "scroll":
            self._use_scroll(item)
            self.inventory.pop(index)

    def _use_scroll(self, item: dict):
        """Apply scroll effect."""
        scroll_id = item.get("scroll_id", "")

        if scroll_id == "mapping":
            self.explored[:] = self.walkable
            self.log("The map reveals itself!", (255, 255, 200))

        elif scroll_id == "teleportation":
            candidates = []
            for x in range(self.width):
                for y in range(self.height):
                    if self.walkable[x, y] and self.explored[x, y]:
                        if not self._blocker_at(x, y):
                            candidates.append((x, y))
            if candidates:
                tx, ty = random.choice(candidates)
                self.player.x, self.player.y = tx, ty
                self._recompute_fov()
                self.log("You blink to a new location!", (100, 200, 255))
            else:
                self.log("The scroll fizzles.", (150, 150, 150))

        elif scroll_id == "fear":
            count = 0
            for e in self.entities:
                if e is self.player or not e.alive or not e.ai:
                    continue
                if e.ai == "allied":
                    continue
                if self.fov[e.x, e.y]:
                    e.confused_turns = max(e.confused_turns, 5)
                    count += 1
            self.log(f"A wave of terror! {count} enemies confused.", (255, 200, 100))

        elif scroll_id == "mending":
            heal = self.player.max_hp // 2
            healed = min(heal, self.player.max_hp - self.player.hp)
            self.player.hp += healed
            self.log(f"Warm light mends your wounds. +{healed} HP.", (100, 255, 100))

        elif scroll_id == "imperative":
            count = 0
            for e in list(self.entities):
                if e is self.player or not e.alive or not e.ai:
                    continue
                if e.ai == "allied":
                    continue
                if self.fov[e.x, e.y]:
                    e.hp -= 10
                    count += 1
                    if e.hp <= 0:
                        self._kill(e)
            self.log(f"Categorical force! {count} enemies struck.", (255, 150, 100))

        elif scroll_id == "transcendence":
            self.buffs.append({
                "name": "Transcendence",
                "turns": 20,
                "power": 2,
                "defense": 2,
                "max_hp": 10,
            })
            self.player.max_hp += 10
            self.player.hp += 10
            self.log("You transcend! +2 ATK/DEF, +10 HP for 20 turns.", (255, 220, 255))

        else:
            self.log("The scroll crumbles to dust.", (150, 150, 100))

    def drop_item(self, index: int):
        """Drop item at inventory index at player's feet."""
        if index < 0 or index >= len(self.inventory):
            return
        item_entity = self.inventory.pop(index)
        if self.equipped_weapon is item_entity:
            self.equipped_weapon = None
        if self.equipped_armor is item_entity:
            self.equipped_armor = None
        item_entity.x = self.player.x
        item_entity.y = self.player.y
        self.entities.append(item_entity)
        self.log(f"Dropped {item_entity.name}.", (180, 180, 150))

    def use_stairs(self):
        """Attempt to use stairs at player position."""
        if self.state != GameState.PLAYING:
            return
        stairs = self._stairs_at(self.player.x, self.player.y)
        if not stairs:
            self.log("No stairs here.", (150, 150, 150))
            return
        if stairs.char == ord("*"):
            self.player_pickup()
            return

        from dungeon import generate_dungeon
        from data import get_theme

        # Save player state
        p_hp = self.player.hp
        p_max_hp = self.player.max_hp
        p_power = self.player.power
        p_defense = self.player.defense

        if self.ascending:
            self.depth += 1
            if self.depth > 7:
                self.depth = 7
        else:
            self.depth -= 1
            if self.depth <= 0:
                self.depth = 0
                self.state = GameState.VICTORY
                self.log("You escaped with the Truth!", (255, 255, 100))
                return

        self.current_theme = get_theme(self.depth, self.ascending)
        result = generate_dungeon(self.width, self.height, self.depth, self.ascending)
        self.walkable, self.transparent, self.entities = result[0], result[1], result[2]
        self.special_rooms = result[3]
        self.shrine_locations = result[4]
        self.layout_name = result[5]
        self.explored = np.zeros((self.width, self.height), dtype=bool, order="F")
        self.fov = np.zeros((self.width, self.height), dtype=bool, order="F")
        self.player = self.entities[0]

        # Restore player stats
        self.player.hp = p_hp
        self.player.max_hp = p_max_hp
        self.player.power = p_power
        self.player.defense = p_defense

        self.cost = self.walkable.astype(np.int32, order="F")
        self._recompute_fov()

        direction = "ascending" if self.ascending else "descending"
        self.log(f"Level {self.depth}: {self.current_theme['name']} ({direction}).", (200, 200, 255))
        self.log(f"Layout: {self.layout_name}", (150, 150, 180))

    # ── Look Mode ─────────────────────────────────────────────

    def start_look(self, x: int | None = None, y: int | None = None):
        self.look_x = x if x is not None else self.player.x
        self.look_y = y if y is not None else self.player.y
        self.state = GameState.LOOKING

    def move_look_cursor(self, dx: int, dy: int):
        nx = self.look_x + dx
        ny = self.look_y + dy
        if 0 <= nx < self.width and 0 <= ny < self.height:
            self.look_x = nx
            self.look_y = ny

    def cancel_look(self):
        self.state = GameState.PLAYING

    # ── Character Screen ──────────────────────────────────────

    def toggle_character_screen(self):
        if self.state == GameState.CHARACTER:
            self.state = GameState.PLAYING
        else:
            self.state = GameState.CHARACTER

    # ── Debug ─────────────────────────────────────────────────

    def debug_change_level(self, delta: int):
        """Force travel up (delta=+1) or down (delta=-1), ignoring stairs."""
        if self.state != GameState.PLAYING:
            return
        from dungeon import generate_dungeon
        from data import get_theme

        new_depth = self.depth + delta
        if new_depth < 1 or new_depth > 7:
            self.log(f"No level {new_depth}.", (150, 150, 150))
            return

        p_hp = self.player.hp
        p_max_hp = self.player.max_hp
        p_power = self.player.power
        p_defense = self.player.defense

        self.depth = new_depth
        self.current_theme = get_theme(self.depth, self.ascending)
        result = generate_dungeon(self.width, self.height, self.depth, self.ascending)
        self.walkable, self.transparent, self.entities = result[0], result[1], result[2]
        self.special_rooms = result[3]
        self.shrine_locations = result[4]
        self.layout_name = result[5]
        self.explored = np.zeros((self.width, self.height), dtype=bool, order="F")
        self.fov = np.zeros((self.width, self.height), dtype=bool, order="F")
        self.player = self.entities[0]

        self.player.hp = p_hp
        self.player.max_hp = p_max_hp
        self.player.power = p_power
        self.player.defense = p_defense

        self.cost = self.walkable.astype(np.int32, order="F")
        self._recompute_fov()

        direction = "ascending" if self.ascending else "descending"
        self.log(f"[DEBUG] Warped to level {self.depth}: {self.current_theme['name']} ({direction}).", (255, 255, 0))
        self.log(f"Layout: {self.layout_name}", (255, 255, 0))

    # ── Wand System ───────────────────────────────────────────

    def fire_wand(self, dx: int, dy: int):
        """Fire the wand in direction (dx, dy). Trace path, create bolt VFX."""
        if not self.targeting_wand:
            self.state = GameState.PLAYING
            return

        wand_item = self.targeting_wand.item
        wand_entity = self.targeting_wand
        self.targeting_wand = None

        if not wand_item:
            self.state = GameState.PLAYING
            return

        bolt_fg = tuple(wand_item.get("bolt_fg", (100, 255, 255)))
        bolt_char = wand_item.get("bolt_char", "*")
        bolt_char_ord = ord(bolt_char) if isinstance(bolt_char, str) else bolt_char

        # Trace the bolt path and compute result
        path: list[tuple[int, int]] = []
        result: dict = {"type": "empty", "wand_item": wand_item, "wand_entity": wand_entity}
        x, y = self.player.x, self.player.y
        for _ in range(FOV_RADIUS):
            x += dx
            y += dy
            if not (0 <= x < self.width and 0 <= y < self.height):
                break
            path.append((x, y))

            blocker = self._blocker_at(x, y)
            if blocker:
                if blocker.alive:
                    result = {"type": "living", "target": blocker,
                              "wand_item": wand_item, "wand_entity": wand_entity}
                else:
                    result = {"type": "corpse", "target": blocker,
                              "wand_item": wand_item, "wand_entity": wand_entity,
                              "x": x, "y": y}
                break

            items = self._items_at(x, y)
            if items:
                result = {"type": "item", "target": items[0], "x": x, "y": y,
                          "wand_item": wand_item, "wand_entity": wand_entity}
                break

            if not self.walkable[x, y]:
                result = {"type": "wall", "x": x, "y": y,
                          "wand_item": wand_item, "wand_entity": wand_entity}
                break

        if not path:
            self._apply_wand_result(result)
            self.state = GameState.PLAYING
            return

        # Create bolt VFX
        self.vfx.append({
            "type": "bolt",
            "path": path,
            "start": time.monotonic(),
            "speed": 30,
            "char": bolt_char_ord,
            "fg": bolt_fg,
            "trail_len": 4,
            "result": result,
            "impact_time": None,
        })
        self.state = GameState.ANIMATING

    def _apply_wand_result(self, result: dict):
        """Apply the stored wand result after animation completes."""
        wand_item = result["wand_item"]
        wand_id = wand_item.get("wand_id", "animation")
        hit_type = result["type"]

        # Dispatch to specific handler
        method_name = f"_wand_{wand_id}_{hit_type}"
        method = getattr(self, method_name, None)
        if method:
            method(result)
        else:
            self.log("The wand bolt fizzles into nothing.", (100, 100, 150))

        wand_item["charges"] -= 1
        self._check_wand_charges(wand_item)

    # ── Wand: Animation ───────────────────────────────────────

    def _wand_animation_living(self, result: dict):
        target = result["target"]
        target.hp = min(target.hp + 5, target.max_hp + 5)
        target.max_hp = max(target.max_hp, target.hp)
        target.confused_turns = 5
        self.log(f"The wand zaps {target.name}! It looks confused.", (100, 255, 255))

    def _wand_animation_corpse(self, result: dict):
        target = result["target"]
        target.ai = "allied"
        target.blocks = True
        target.hp = 8
        target.max_hp = 8
        target.power = 2
        target.char = ord("a")
        old_name = target.name.replace("remains of ", "")
        target.name = f"Animated {old_name}"
        target.fg = (100, 255, 200)
        target.render_order = RenderOrder.ACTOR
        self.log(f"{target.name} rises as your ally!", (100, 255, 200))

    def _wand_animation_wall(self, result: dict):
        x, y = result["x"], result["y"]
        self.walkable[x, y] = True
        self.transparent[x, y] = True
        self.cost = self.walkable.astype(np.int32, order="F")
        animated = Entity(
            x, y, "A", "Animated Wall",
            fg=(100, 255, 200), blocks=True, ai="allied",
            hp=15, power=3, defense=3,
        )
        self.entities.append(animated)
        self.log("The wall crumbles and animates as your ally!", (100, 255, 200))
        self._recompute_fov()

    def _wand_animation_item(self, result: dict):
        target = result["target"]
        x, y = result["x"], result["y"]
        # Check if it's stairs
        if target.char in (ord("<"), ord(">"), ord("*")):
            self.entities.remove(target)
            animated = Entity(
                x, y, "A", "Animated Staircase",
                fg=(100, 255, 200), blocks=True, ai="allied",
                hp=25, power=5, defense=2,
            )
            self.entities.append(animated)
            self.log("The staircase animates as your ally! (Exit removed!)", (255, 200, 100))
        else:
            self.entities.remove(target)
            animated = Entity(
                x, y, "a", f"Animated {target.name}",
                fg=(100, 255, 200), blocks=True, ai="allied",
                hp=10, power=3, defense=1,
            )
            self.entities.append(animated)
            self.log(f"The {target.name} animates as your ally!", (100, 255, 200))

    def _wand_animation_empty(self, result: dict):
        self.log("The wand bolt fizzles into nothing.", (100, 100, 150))

    # ── Wand: Negation ────────────────────────────────────────

    def _wand_negation_living(self, result: dict):
        target = result["target"]
        target.hp -= 15
        self.log(f"The bolt of negation strikes {target.name} for 15 damage!", (255, 80, 80))
        if target.hp <= 0:
            self._kill(target)

    def _wand_negation_corpse(self, result: dict):
        target = result["target"]
        self.entities.remove(target)
        self.log(f"The remains of {target.name.replace('remains of ', '')} are annihilated.", (255, 80, 80))

    def _wand_negation_wall(self, result: dict):
        self.log("The bolt of negation dissipates against the wall.", (100, 100, 150))

    def _wand_negation_item(self, result: dict):
        target = result["target"]
        self.entities.remove(target)
        self.log(f"The {target.name} is annihilated!", (255, 80, 80))

    def _wand_negation_empty(self, result: dict):
        self.log("The bolt of negation fizzles.", (100, 100, 150))

    # ── Wand: Transposition ───────────────────────────────────

    def _wand_transposition_living(self, result: dict):
        target = result["target"]
        px, py = self.player.x, self.player.y
        self.player.x, self.player.y = target.x, target.y
        target.x, target.y = px, py
        self._recompute_fov()
        self.log(f"You swap positions with {target.name}!", (80, 130, 255))

    def _wand_transposition_corpse(self, result: dict):
        target = result["target"]
        target.x, target.y = self.player.x, self.player.y
        self.log(f"The remains are pulled to your position.", (80, 130, 255))

    def _wand_transposition_wall(self, result: dict):
        self.log("The bolt of transposition fizzles against the wall.", (100, 100, 150))

    def _wand_transposition_item(self, result: dict):
        target = result["target"]
        target.x, target.y = self.player.x, self.player.y
        self.log(f"The {target.name} is pulled to you!", (80, 130, 255))

    def _wand_transposition_empty(self, result: dict):
        # Teleport self to the empty tile
        path = result.get("wand_entity", None)
        # Find last tile in bolt path from VFX
        for vfx in self.vfx:
            if vfx.get("result") is result:
                if vfx["path"]:
                    tx, ty = vfx["path"][-1]
                    if self.walkable[tx, ty]:
                        self.player.x, self.player.y = tx, ty
                        self._recompute_fov()
                        self.log("You teleport forward!", (80, 130, 255))
                        return
        self.log("The bolt of transposition fizzles.", (100, 100, 150))

    # ── Wand: Petrification ───────────────────────────────────

    def _wand_petrification_living(self, result: dict):
        target = result["target"]
        target.confused_turns = max(target.confused_turns, 8)
        self.log(f"{target.name} is petrified! Frozen for 8 turns.", (160, 160, 160))

    def _wand_petrification_corpse(self, result: dict):
        target = result["target"]
        x, y = result.get("x", target.x), result.get("y", target.y)
        self.entities.remove(target)
        self.walkable[x, y] = False
        self.transparent[x, y] = False
        self.cost = self.walkable.astype(np.int32, order="F")
        self._recompute_fov()
        self.log("The remains solidify into stone.", (160, 160, 160))

    def _wand_petrification_wall(self, result: dict):
        self.log("The bolt of petrification fizzles against the wall.", (100, 100, 150))

    def _wand_petrification_item(self, result: dict):
        target = result["target"]
        x, y = result["x"], result["y"]
        self.entities.remove(target)
        self.walkable[x, y] = False
        self.transparent[x, y] = False
        self.cost = self.walkable.astype(np.int32, order="F")
        self._recompute_fov()
        self.log(f"The {target.name} turns to stone!", (160, 160, 160))

    def _wand_petrification_empty(self, result: dict):
        # Create a wall at the end of the bolt path
        for vfx in self.vfx:
            if vfx.get("result") is result and vfx["path"]:
                tx, ty = vfx["path"][-1]
                if self.walkable[tx, ty] and not self._blocker_at(tx, ty):
                    self.walkable[tx, ty] = False
                    self.transparent[tx, ty] = False
                    self.cost = self.walkable.astype(np.int32, order="F")
                    self._recompute_fov()
                    self.log("Stone materializes from nothing!", (160, 160, 160))
                    return
        self.log("The bolt of petrification fizzles.", (100, 100, 150))

    # ── Wand: Revelation ──────────────────────────────────────

    def _wand_revelation_living(self, result: dict):
        target = result["target"]
        target.confused_turns = max(target.confused_turns, 3)
        self.log(f"{target.name}: HP {target.hp}/{target.max_hp}, ATK {target.power}, DEF {target.defense}", (255, 255, 100))

    def _wand_revelation_corpse(self, result: dict):
        target = result["target"]
        self.log(f"Identified: {target.name}", (255, 255, 100))

    def _wand_revelation_wall(self, result: dict):
        x, y = result["x"], result["y"]
        for rx in range(max(0, x - 10), min(self.width, x + 11)):
            for ry in range(max(0, y - 10), min(self.height, y + 11)):
                self.explored[rx, ry] = True
        self.log("The wall reveals its surroundings!", (255, 255, 100))

    def _wand_revelation_item(self, result: dict):
        target = result["target"]
        item = target.item
        if item:
            itype = item.get("type", "unknown")
            details = ""
            if itype == "weapon":
                details = f" (+{item.get('power_bonus', 0)} ATK)"
            elif itype == "armor":
                details = f" (+{item.get('defense_bonus', 0)} DEF)"
            elif itype == "potion":
                details = f" (heals {item.get('heal', 0)})"
            elif itype == "wand":
                details = f" ({item.get('charges', 0)} charges)"
            self.log(f"Identified: {target.name}{details}", (255, 255, 100))
        else:
            self.log(f"Identified: {target.name}", (255, 255, 100))

    def _wand_revelation_empty(self, result: dict):
        # Reveal all FOV
        self.explored |= self.fov
        for rx in range(self.width):
            for ry in range(self.height):
                dist = abs(rx - self.player.x) + abs(ry - self.player.y)
                if dist <= FOV_RADIUS:
                    self.explored[rx, ry] = True
        self.log("Light reveals the surrounding area!", (255, 255, 100))

    # ── Wand: Sundering ───────────────────────────────────────

    def _wand_sundering_living(self, result: dict):
        target = result["target"]
        target.defense = target.defense // 2
        target.hp -= 8
        self.log(f"{target.name}'s defenses shatter! DEF halved, 8 damage!", (255, 160, 50))
        if target.hp <= 0:
            self._kill(target)

    def _wand_sundering_corpse(self, result: dict):
        target = result["target"]
        x, y = result.get("x", target.x), result.get("y", target.y)
        self.entities.remove(target)
        # Scatter shrapnel: damage nearby enemies
        count = 0
        for e in list(self.entities):
            if e is self.player or not e.alive or not e.ai:
                continue
            if abs(e.x - x) <= 2 and abs(e.y - y) <= 2:
                e.hp -= 5
                count += 1
                if e.hp <= 0:
                    self._kill(e)
        self.log(f"The remains explode! Shrapnel hits {count} nearby.", (255, 160, 50))

    def _wand_sundering_wall(self, result: dict):
        x, y = result["x"], result["y"]
        self.walkable[x, y] = True
        self.transparent[x, y] = True
        self.cost = self.walkable.astype(np.int32, order="F")
        self._recompute_fov()
        self.log("The wall is sundered!", (255, 160, 50))

    def _wand_sundering_item(self, result: dict):
        target = result["target"]
        x, y = result["x"], result["y"]
        self.entities.remove(target)
        # Explode in radius
        count = 0
        for e in list(self.entities):
            if e is self.player or not e.alive or not e.ai:
                continue
            if abs(e.x - x) <= 3 and abs(e.y - y) <= 3:
                e.hp -= 8
                count += 1
                if e.hp <= 0:
                    self._kill(e)
        self.log(f"The {target.name} explodes! {count} caught in blast.", (255, 160, 50))

    def _wand_sundering_empty(self, result: dict):
        self.log("The bolt of sundering fizzles.", (100, 100, 150))

    # ── Wand: Communion ───────────────────────────────────────

    def _wand_communion_living(self, result: dict):
        target = result["target"]
        target.ai = "allied"
        target.confused_turns = 0
        target.fg = (100, 255, 200)
        self.log(f"{target.name} is charmed! It fights for you.", (180, 80, 255))

    def _wand_communion_corpse(self, result: dict):
        target = result["target"]
        target.ai = "allied"
        target.blocks = True
        target.hp = 5
        target.max_hp = 5
        target.power = 1
        target.char = ord("a")
        old_name = target.name.replace("remains of ", "")
        target.name = f"Weak {old_name}"
        target.fg = (140, 100, 200)
        target.render_order = RenderOrder.ACTOR
        self.log(f"{target.name} stirs weakly as your ally.", (180, 80, 255))

    def _wand_communion_wall(self, result: dict):
        self.log("The bolt of communion fizzles against the wall.", (100, 100, 150))

    def _wand_communion_item(self, result: dict):
        target = result["target"]
        item = target.item
        if item:
            if item.get("type") == "weapon":
                item["power_bonus"] = item.get("power_bonus", 0) + 1
                self.log(f"The {target.name} is imbued! +1 ATK.", (180, 80, 255))
            elif item.get("type") == "armor":
                item["defense_bonus"] = item.get("defense_bonus", 0) + 1
                self.log(f"The {target.name} is imbued! +1 DEF.", (180, 80, 255))
            else:
                self.log("The bolt of communion fizzles.", (100, 100, 150))
        else:
            self.log("The bolt of communion fizzles.", (100, 100, 150))

    def _wand_communion_empty(self, result: dict):
        self.log("The bolt of communion fizzles.", (100, 100, 150))

    # ── Wand: Entropy ─────────────────────────────────────────

    def _entropy_dispatch(self, hit_type: str, result: dict):
        from data import WAND_TYPES
        other_ids = [w["wand_id"] for w in WAND_TYPES if w["wand_id"] != "entropy"]
        chosen_id = random.choice(other_ids)
        method = getattr(self, f"_wand_{chosen_id}_{hit_type}", None)
        if method:
            self.log(f"The entropy wand channels {chosen_id}!", (160, 160, 160))
            method(result)
        else:
            self.log("The wand bolt fizzles chaotically.", (100, 100, 150))

    def _wand_entropy_living(self, result: dict):
        self._entropy_dispatch("living", result)

    def _wand_entropy_corpse(self, result: dict):
        self._entropy_dispatch("corpse", result)

    def _wand_entropy_wall(self, result: dict):
        self._entropy_dispatch("wall", result)

    def _wand_entropy_item(self, result: dict):
        self._entropy_dispatch("item", result)

    def _wand_entropy_empty(self, result: dict):
        self._entropy_dispatch("empty", result)

    # ── Wand Charges ──────────────────────────────────────────

    def _check_wand_charges(self, wand_item: dict):
        if wand_item["charges"] <= 0:
            for i, e in enumerate(self.inventory):
                if e.item is wand_item:
                    self.inventory.pop(i)
                    self.log("The wand crumbles to dust.", (150, 150, 100))
                    break

    def cancel_targeting(self):
        self.targeting_wand = None
        self.state = GameState.PLAYING
        self.log("Targeting cancelled.", (150, 150, 150))

    # ── Combat ────────────────────────────────────────────────

    def _attack(self, attacker: Entity, target: Entity):
        if attacker.ai == "allied" and target.ai == "allied":
            return
        if attacker is self.player and target.ai == "allied":
            return

        atk_power = attacker.power
        tgt_defense = target.defense

        if attacker is self.player:
            if self.equipped_weapon and self.equipped_weapon.item:
                atk_power += self.equipped_weapon.item.get("power_bonus", 0)
            atk_power += self._get_buff_power()
        if target is self.player:
            if self.equipped_armor and self.equipped_armor.item:
                tgt_defense += self.equipped_armor.item.get("defense_bonus", 0)
            tgt_defense += self._get_buff_defense()

        # Berserker rage: below 50% HP -> 2x power
        if attacker.ai == "berserker" and attacker.hp <= attacker.max_hp * 0.5:
            atk_power *= 2

        damage = max(1, atk_power - tgt_defense)
        target.hp -= damage

        from data import ATTACK_VERBS_PLAYER, ATTACK_VERBS_MONSTER

        if attacker is self.player:
            verb = random.choice(ATTACK_VERBS_PLAYER)
            color = (255, 200, 200)
            self.log(f"You {verb} {target.name} for {damage}!", color)
        elif target is self.player:
            verb = random.choice(ATTACK_VERBS_MONSTER)
            color = (255, 100, 100)
            self.log(f"{attacker.name} {verb} you for {damage}!", color)
        else:
            color = (200, 200, 150)
            self.log(f"{attacker.name} hits {target.name} for {damage}!", color)

        if target.hp <= 0:
            self._kill(target)

    def _kill(self, entity: Entity):
        from data import DEATH_MESSAGES_MONSTER, DEATH_MESSAGES_PLAYER

        if entity is self.player:
            msg = random.choice(DEATH_MESSAGES_PLAYER)
            self.log(msg, (255, 0, 0))
            self.state = GameState.DEAD
        else:
            msg = random.choice(DEATH_MESSAGES_MONSTER).format(name=entity.name)
            self.log(msg, (255, 150, 50))
            self.kills += 1
            # Award XP
            xp = getattr(entity, 'xp_value', 0)
            if xp > 0:
                self.player_xp += xp
                self._check_level_up()
        entity.blocks = False
        entity.ai = None
        entity.char = ord("%")
        entity.name = f"remains of {entity.name}"
        entity.render_order = RenderOrder.CORPSE

    # ── Enemy AI ──────────────────────────────────────────────

    def process_enemies(self):
        if not self.player.alive:
            return

        self.turn_count += 1
        self._tick_buffs()

        # Dijkstra map toward player
        dist_player = tcod.path.maxarray((self.width, self.height), dtype=np.int32, order="F")
        dist_player[self.player.x, self.player.y] = 0
        tcod.path.dijkstra2d(dist_player, self.cost, 1, 1, out=dist_player)

        for e in self.entities:
            if e is self.player or not e.ai:
                continue

            # Confused: random movement
            if e.confused_turns > 0:
                e.confused_turns -= 1
                dx, dy = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)])
                nx, ny = e.x + dx, e.y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height and self.walkable[nx, ny]:
                    blocker = self._blocker_at(nx, ny)
                    if not blocker:
                        e.x, e.y = nx, ny
                continue

            if e.ai == "dijkstra":
                self._ai_dijkstra(e, dist_player)
            elif e.ai == "berserker":
                self._ai_berserker(e, dist_player)
            elif e.ai == "stalker":
                self._ai_stalker(e, dist_player)
            elif e.ai == "coward":
                self._ai_coward(e, dist_player)
            elif e.ai == "swarm":
                self._ai_swarm(e, dist_player)
            elif e.ai == "allied":
                self._ai_allied(e)

    def _ai_dijkstra(self, e: Entity, dist_player: np.ndarray):
        """Standard hostile: path toward player when visible."""
        path = tcod.path.hillclimb2d(dist_player, (e.x, e.y), True, True)
        if len(path) <= 1:
            return
        nx, ny = int(path[1][0]), int(path[1][1])
        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return
        if not self.walkable[nx, ny] or not self.fov[nx, ny]:
            return
        blocker = self._blocker_at(nx, ny)
        if blocker is self.player:
            self._attack(e, self.player)
        elif not blocker:
            e.x, e.y = nx, ny

    def _ai_berserker(self, e: Entity, dist_player: np.ndarray):
        """Dijkstra pursuit; below 50% HP -> fg tints red (handled in render + combat)."""
        path = tcod.path.hillclimb2d(dist_player, (e.x, e.y), True, True)
        if len(path) <= 1:
            return
        nx, ny = int(path[1][0]), int(path[1][1])
        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return
        if not self.walkable[nx, ny]:
            return
        dist = abs(e.x - self.player.x) + abs(e.y - self.player.y)
        if not self.fov[e.x, e.y] and dist > 10:
            return
        blocker = self._blocker_at(nx, ny)
        if blocker is self.player:
            self._attack(e, self.player)
        elif not blocker:
            e.x, e.y = nx, ny

    def _ai_stalker(self, e: Entity, dist_player: np.ndarray):
        """Moves only when OUT of player FOV. Freezes when visible."""
        if self.fov[e.x, e.y]:
            return
        path = tcod.path.hillclimb2d(dist_player, (e.x, e.y), True, True)
        if len(path) <= 1:
            return
        nx, ny = int(path[1][0]), int(path[1][1])
        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return
        if not self.walkable[nx, ny]:
            return
        blocker = self._blocker_at(nx, ny)
        if blocker is self.player:
            self._attack(e, self.player)
        elif not blocker:
            e.x, e.y = nx, ny

    def _ai_coward(self, e: Entity, dist_player: np.ndarray):
        """Pursues normally; below 30% HP -> flees."""
        if e.hp <= e.max_hp * 0.3:
            best_pos = None
            best_dist = dist_player[e.x, e.y]
            for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
                nx, ny = e.x + ddx, e.y + ddy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                if not self.walkable[nx, ny]:
                    continue
                if self._blocker_at(nx, ny):
                    continue
                if dist_player[nx, ny] > best_dist:
                    best_dist = dist_player[nx, ny]
                    best_pos = (nx, ny)
            if best_pos:
                e.x, e.y = best_pos
        else:
            self._ai_dijkstra(e, dist_player)

    def _ai_swarm(self, e: Entity, dist_player: np.ndarray):
        """Seeks nearest same-name ally; when 2+ allies within 5 tiles, rush player."""
        base_name = e.name.split(" ")[0] if " " in e.name else e.name
        nearby_allies = 0
        nearest_ally = None
        nearest_ally_dist = 999
        for other in self.entities:
            if other is e or not other.alive or other is self.player:
                continue
            if not other.ai or other.ai == "allied":
                continue
            other_base = other.name.split(" ")[0] if " " in other.name else other.name
            if other_base != base_name:
                continue
            d = abs(other.x - e.x) + abs(other.y - e.y)
            if d <= 5:
                nearby_allies += 1
            if d < nearest_ally_dist:
                nearest_ally_dist = d
                nearest_ally = other

        if nearby_allies >= 2:
            self._ai_dijkstra(e, dist_player)
        elif nearest_ally:
            dist_ally = tcod.path.maxarray((self.width, self.height), dtype=np.int32, order="F")
            dist_ally[nearest_ally.x, nearest_ally.y] = 0
            tcod.path.dijkstra2d(dist_ally, self.cost, 1, 1, out=dist_ally)
            path = tcod.path.hillclimb2d(dist_ally, (e.x, e.y), True, True)
            if len(path) <= 1:
                return
            nx, ny = int(path[1][0]), int(path[1][1])
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                return
            if not self.walkable[nx, ny]:
                return
            blocker = self._blocker_at(nx, ny)
            if blocker is self.player:
                self._attack(e, self.player)
            elif not blocker:
                e.x, e.y = nx, ny
        else:
            self._ai_dijkstra(e, dist_player)

    def _ai_allied(self, e: Entity):
        """Allied: path toward nearest hostile."""
        nearest = None
        nearest_dist = 999999
        hostile_ais = ("dijkstra", "berserker", "stalker", "coward", "swarm")
        for other in self.entities:
            if other is e or other is self.player or not other.alive:
                continue
            if other.ai not in hostile_ais:
                continue
            d = abs(other.x - e.x) + abs(other.y - e.y)
            if d < nearest_dist:
                nearest_dist = d
                nearest = other
        if not nearest:
            return
        dist_target = tcod.path.maxarray((self.width, self.height), dtype=np.int32, order="F")
        dist_target[nearest.x, nearest.y] = 0
        tcod.path.dijkstra2d(dist_target, self.cost, 1, 1, out=dist_target)
        path = tcod.path.hillclimb2d(dist_target, (e.x, e.y), True, True)
        if len(path) <= 1:
            return
        nx, ny = int(path[1][0]), int(path[1][1])
        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return
        if not self.walkable[nx, ny]:
            return
        blocker = self._blocker_at(nx, ny)
        if blocker and blocker is not self.player and blocker.ai in hostile_ais:
            self._attack(e, blocker)
        elif not blocker:
            e.x, e.y = nx, ny

    # ── VFX Update ────────────────────────────────────────────

    def _update_vfx(self):
        """Update VFX and complete any finished animations."""
        now = time.monotonic()
        finished = []
        for vfx in self.vfx:
            if vfx["type"] == "bolt":
                elapsed = now - vfx["start"]
                head_idx = int(elapsed * vfx["speed"])
                path_len = len(vfx["path"])

                if vfx["impact_time"] is not None:
                    if now - vfx["impact_time"] > 0.15:
                        finished.append(vfx)
                elif head_idx >= path_len:
                    vfx["impact_time"] = now
                    self._apply_wand_result(vfx["result"])

        for vfx in finished:
            self.vfx.remove(vfx)

        if not self.vfx and self.state == GameState.ANIMATING:
            self.state = GameState.PLAYING
            self.process_enemies()

    # ── Rendering ─────────────────────────────────────────────

    def render(self, console: tcod.console.Console):
        if self.state == GameState.ANIMATING:
            self._update_vfx()

        if self.state == GameState.DEAD:
            self._render_map(console)
            self._render_entities(console)
            self._render_ui(console)
            self._render_death_screen(console)
            return
        if self.state == GameState.VICTORY:
            self._render_map(console)
            self._render_entities(console)
            self._render_ui(console)
            self._render_victory_screen(console)
            return

        self._render_map(console)
        self._render_entities(console)
        if self.vfx:
            self._render_vfx(console)
        self._render_ui(console)
        if self.state == GameState.TARGETING:
            self._render_targeting(console)
        if self.state == GameState.LOOKING:
            self._render_look_panel(console)
        if self.state == GameState.CHARACTER:
            self._render_character_screen(console)
        if self.inventory_open:
            self._render_inventory(console)
        if self.mouse_in_map and self.state == GameState.PLAYING:
            self._render_mouse_tooltip(console)

    def _render_map(self, console: tcod.console.Console):
        t = time.monotonic()
        theme = self.current_theme
        fb = theme["floor_fg_base"]
        fa = theme["floor_fg_amp"]
        wfg = theme["wall_fg"]
        wbb = theme["wall_bg_base"]
        wba = theme["wall_bg_amp"]
        efg = theme["explored_fg"]
        ebg = theme["explored_bg"]
        spd = theme.get("shimmer_speed", 1.0)

        ts = t * spd

        for x in range(self.width):
            for y in range(self.height):
                if self.fov[x, y]:
                    if self.walkable[x, y]:
                        s_r = (0.5 * math.sin(ts * 2.0 + x * 0.3 + y * 0.5)
                               + 0.3 * math.sin(ts * 3.4 + x * 0.7 - y * 0.4)
                               + 0.2 * math.sin(ts * 1.2 - x * 0.5 + y * 0.9))
                        s_g = (0.5 * math.sin(ts * 2.0 + x * 0.3 + y * 0.5 + 1.0)
                               + 0.3 * math.sin(ts * 3.4 + x * 0.7 - y * 0.4 + 0.7)
                               + 0.2 * math.sin(ts * 1.2 - x * 0.5 + y * 0.9 + 1.5))
                        s_b = (0.5 * math.sin(ts * 2.0 + x * 0.3 + y * 0.5 + 2.1)
                               + 0.3 * math.sin(ts * 3.4 + x * 0.7 - y * 0.4 + 1.4)
                               + 0.2 * math.sin(ts * 1.2 - x * 0.5 + y * 0.9 + 0.5))

                        r = max(0, min(255, int(fb[0] + fa[0] * s_r)))
                        g = max(0, min(255, int(fb[1] + fa[1] * s_g)))
                        b = max(0, min(255, int(fb[2] + fa[2] * s_b)))

                        sparkle = (x * 374761 + y * 668265 + int(t * 4)) % 200
                        if sparkle == 0:
                            r = min(255, r + 80)
                            g = min(255, g + 80)
                            b = min(255, b + 80)

                        floor_ch = ord("_")
                        console.rgb[x, y] = floor_ch, (r, g, b), (0, 0, 0)
                    else:
                        s_bg = (0.5 * math.sin(ts * 1.5 + x * 0.2 + y * 0.3)
                                + 0.3 * math.sin(ts * 2.5 + x * 0.5 - y * 0.2)
                                + 0.2 * math.sin(ts * 0.8 - x * 0.3 + y * 0.6))
                        br = max(0, min(255, int(wbb[0] + wba[0] * s_bg)))
                        bg = max(0, min(255, int(wbb[1] + wba[1] * s_bg)))
                        bb = max(0, min(255, int(wbb[2] + wba[2] * s_bg)))

                        s_wf = 0.15 * math.sin(ts * 1.0 + x * 0.4 + y * 0.6)
                        wfr = max(0, min(255, int(wfg[0] + 30 * s_wf)))
                        wfg_ = max(0, min(255, int(wfg[1] + 30 * s_wf)))
                        wfb = max(0, min(255, int(wfg[2] + 30 * s_wf)))

                        console.rgb[x, y] = ord("#"), (wfr, wfg_, wfb), (br, bg, bb)
                elif self.explored[x, y]:
                    ch = ord("_") if self.walkable[x, y] else ord("#")
                    pulse = 0.07 * math.sin(t * 0.5 + x * 0.1 + y * 0.1)
                    er = max(0, min(255, int(efg[0] + efg[0] * pulse)))
                    eg = max(0, min(255, int(efg[1] + efg[1] * pulse)))
                    eb = max(0, min(255, int(efg[2] + efg[2] * pulse)))
                    console.rgb[x, y] = ch, (er, eg, eb), ebg

    def _render_entities(self, console: tcod.console.Console):
        t = time.monotonic()
        for e in sorted(self.entities, key=lambda e: e.render_order.value):
            if not self.fov[e.x, e.y]:
                continue
            fg = e.fg
            if e.alive:
                if e.ai == "allied":
                    s = math.sin(t * 3.0 + e.x + e.y)
                    r = max(0, min(255, int(fg[0] + 15 * s)))
                    g = max(0, min(255, int(fg[1] + 30 + 30 * s)))
                    b = max(0, min(255, int(fg[2] + 15 * s)))
                    fg = (r, g, b)
                elif e.confused_turns > 0:
                    flicker = random.random() * 0.6 + 0.4
                    fg = (
                        max(0, min(255, int(fg[0] * flicker))),
                        max(0, min(255, int(fg[1] * flicker))),
                        max(0, min(255, int(fg[2] * flicker))),
                    )
                elif e.ai == "berserker" and e.hp <= e.max_hp * 0.5:
                    s = math.sin(t * 6.0 + e.x + e.y)
                    fg = (min(255, fg[0] + 60 + int(40 * s)), max(0, fg[1] - 30), max(0, fg[2] - 30))
                else:
                    s = math.sin(t * 3.0 + e.x + e.y)
                    r = max(0, min(255, int(fg[0] + 25 * s)))
                    g = max(0, min(255, int(fg[1] + 20 * s)))
                    b = max(0, min(255, int(fg[2] + 15 * s)))
                    fg = (r, g, b)
            console.rgb[e.x, e.y] = e.char, fg, (0, 0, 0)

    def _render_vfx(self, console: tcod.console.Console):
        """Render active VFX (bolt travel + impact flash)."""
        now = time.monotonic()
        for vfx in self.vfx:
            if vfx["type"] == "bolt":
                path = vfx["path"]
                elapsed = now - vfx["start"]
                head_idx = int(elapsed * vfx["speed"])
                trail_len = vfx["trail_len"]
                bolt_fg = vfx["fg"]

                if vfx["impact_time"] is not None:
                    flash_elapsed = now - vfx["impact_time"]
                    brightness = max(0.0, 1.0 - flash_elapsed / 0.15)
                    ix, iy = path[-1]
                    if 0 <= ix < self.width and 0 <= iy < self.height:
                        c = int(255 * brightness)
                        console.rgb[ix, iy] = ord("*"), (c, c, c), (int(c * 0.3), int(c * 0.3), int(c * 0.2))
                else:
                    for i in range(max(0, head_idx - trail_len), min(head_idx + 1, len(path))):
                        px, py = path[i]
                        if not (0 <= px < self.width and 0 <= py < self.height):
                            continue
                        dist_from_head = head_idx - i
                        fade = max(0.2, 1.0 - dist_from_head / (trail_len + 1))
                        r = int(bolt_fg[0] * fade)
                        g = int(bolt_fg[1] * fade)
                        b = int(bolt_fg[2] * fade)
                        ch = vfx["char"] if dist_from_head == 0 else ord(".")
                        console.rgb[px, py] = ch, (r, g, b), (0, int(20 * fade), int(20 * fade))

    def _render_ui(self, console: tcod.console.Console):
        ux = self.width
        uh = self.height

        console.draw_frame(ux, 0, UI_WIDTH, uh, title=" Geist ",
                           fg=(200, 150, 255), bg=(10, 5, 15))

        # Level info
        direction = "\u2191" if self.ascending else "\u2193"
        console.print(ux + 2, 2, f"Depth: {self.depth} {direction}  {self.layout_name}", fg=(200, 200, 255))
        console.print(ux + 2, 3, self.current_theme["name"][:UI_WIDTH - 4], fg=(180, 180, 220))

        # Player level + trait
        from data import TRAIT_DESCRIPTIONS
        console.print(ux + 2, 4, f"Lv{self.player_level} {self.player_trait['name']}", fg=(220, 200, 255))

        # HP bar
        hp, max_hp = self.player.hp, self.player.max_hp
        hp_ratio = max(0.0, hp / max_hp) if max_hp > 0 else 0.0
        bar_w = UI_WIDTH - 4
        filled = int(bar_w * hp_ratio)
        console.print(ux + 2, 6, f"HP: {hp}/{max_hp}", fg=(255, 255, 255))
        for bx in range(bar_w):
            color = (200, 30, 30) if bx < filled else (50, 10, 10)
            console.rgb[ux + 2 + bx, 7] = ord("\u2588"), color, (10, 5, 15)

        # XP bar
        from data import XP_THRESHOLDS
        if self.player_level < len(XP_THRESHOLDS) - 1:
            xp_cur = self.player_xp - XP_THRESHOLDS[self.player_level]
            xp_need = XP_THRESHOLDS[self.player_level + 1] - XP_THRESHOLDS[self.player_level]
            xp_ratio = max(0.0, min(1.0, xp_cur / xp_need)) if xp_need > 0 else 1.0
        else:
            xp_ratio = 1.0
        xp_filled = int(bar_w * xp_ratio)
        console.print(ux + 2, 8, f"XP: {self.player_xp}", fg=(200, 200, 100))
        for bx in range(bar_w):
            color = (180, 180, 50) if bx < xp_filled else (40, 40, 10)
            console.rgb[ux + 2 + bx, 9] = ord("\u2588"), color, (10, 5, 15)

        # Stats with breakdown
        weapon_bonus = 0
        armor_bonus = 0
        if self.equipped_weapon and self.equipped_weapon.item:
            weapon_bonus = self.equipped_weapon.item.get("power_bonus", 0)
        if self.equipped_armor and self.equipped_armor.item:
            armor_bonus = self.equipped_armor.item.get("defense_bonus", 0)

        buff_atk = self._get_buff_power()
        buff_def = self._get_buff_defense()
        base_atk = self.player.power
        base_def = self.player.defense

        atk_total = base_atk + weapon_bonus + buff_atk
        def_total = base_def + armor_bonus + buff_def

        atk_parts = [str(base_atk)]
        if weapon_bonus:
            atk_parts.append(f"+{weapon_bonus}")
        if buff_atk:
            atk_parts.append(f"+{buff_atk}")
        atk_str = f"ATK: {atk_total}"
        if len(atk_parts) > 1:
            atk_str += f" ({'+'.join(str(p) for p in [base_atk, weapon_bonus, buff_atk] if p)})"

        def_parts = [str(base_def)]
        if armor_bonus:
            def_parts.append(f"+{armor_bonus}")
        if buff_def:
            def_parts.append(f"+{buff_def}")
        def_str = f"DEF: {def_total}"
        if len(def_parts) > 1:
            def_str += f" ({'+'.join(str(p) for p in [base_def, armor_bonus, buff_def] if p)})"

        console.print(ux + 2, 11, atk_str[:UI_WIDTH - 4], fg=(200, 180, 150))
        console.print(ux + 2, 12, def_str[:UI_WIDTH - 4], fg=(150, 180, 200))
        console.print(ux + 2, 13, f"Kills: {self.kills}  T:{self.turn_count}", fg=(200, 150, 150))

        # Equipment
        y = 15
        if self.equipped_weapon:
            w_name = self.equipped_weapon.name[:UI_WIDTH - 7]
            console.print(ux + 2, y, f"W: {w_name}", fg=(255, 220, 100))
            y += 1
        if self.equipped_armor:
            a_name = self.equipped_armor.name[:UI_WIDTH - 7]
            console.print(ux + 2, y, f"A: {a_name}", fg=(100, 200, 255))
            y += 1

        # Active buffs
        if self.buffs:
            y += 1
            for buff in self.buffs:
                buff_text = f"{buff['name']} ({buff['turns']}t)"
                console.print(ux + 2, y, buff_text[:UI_WIDTH - 4], fg=(220, 180, 255))
                y += 1

        # The Truth indicator
        if self.has_thing:
            y += 1
            console.print(ux + 2, y, "* The Truth *", fg=(255, 255, 100))

        # Help text
        y += 1
        console.print(ux + 2, y, "Mv:arrows X:look C:char", fg=(100, 100, 130))
        y += 1
        console.print(ux + 2, y, "I:inv G:grab </>:stairs", fg=(100, 100, 130))

        # Separator + message log
        log_top = max(y + 2, 22)
        console.print(ux + 2, log_top, "\u2500\u2500 Log \u2500\u2500", fg=(150, 120, 200))
        log_start = log_top + 1
        log_space = uh - log_start - 1
        msgs = list(self.messages)[-log_space:]
        for i, (text, color) in enumerate(msgs):
            console.print(ux + 2, log_start + i, text[:UI_WIDTH - 4], fg=color)

    def _render_inventory(self, console: tcod.console.Console):
        px, py = self.player.x, self.player.y

        inv_h = max(INV_H, len(self.inventory) + 5)
        inv_h = min(inv_h, self.height - 2)

        ix = px + 2
        if ix + INV_W > self.width:
            ix = px - INV_W - 1
        ix = max(0, ix)

        iy = max(0, min(py - inv_h // 2, self.height - inv_h))

        # Connector
        conn_y = py
        box_left = ix
        box_right = ix + INV_W - 1
        connector_fg = (180, 170, 220)
        connector_bg = (15, 10, 30)

        if ix > px:
            for cx in range(px + 1, ix):
                if 0 <= cx < self.width:
                    console.rgb[cx, conn_y] = ord("\u2500"), connector_fg, connector_bg
            if iy < conn_y < iy + inv_h - 1:
                console.rgb[box_left, conn_y] = ord("\u251c"), connector_fg, connector_bg
        else:
            for cx in range(box_right + 1, px):
                if 0 <= cx < self.width:
                    console.rgb[cx, conn_y] = ord("\u2500"), connector_fg, connector_bg
            if iy < conn_y < iy + inv_h - 1:
                console.rgb[box_right, conn_y] = ord("\u2524"), connector_fg, connector_bg

        console.draw_frame(ix, iy, INV_W, inv_h, title=" Inventory ",
                           fg=(220, 220, 255), bg=(15, 10, 30))

        if iy < conn_y < iy + inv_h - 1:
            if ix > px:
                console.rgb[box_left, conn_y] = ord("\u251c"), connector_fg, connector_bg
            else:
                console.rgb[box_right, conn_y] = ord("\u2524"), connector_fg, connector_bg

        if not self.inventory:
            console.print(ix + 2, iy + 2, "(empty)", fg=(120, 120, 150))
            console.print(ix + 2, iy + 4, "No items yet.", fg=(80, 80, 100))
        else:
            for i, item_entity in enumerate(self.inventory[:inv_h - 4]):
                label = chr(ord("a") + i)
                equipped = ""
                if item_entity is self.equipped_weapon or item_entity is self.equipped_armor:
                    equipped = " (E)"
                max_name_len = INV_W - 6 - len(equipped)
                name = item_entity.name[:max_name_len] + equipped
                console.print(ix + 2, iy + 1 + i, f"{label}) {name}", fg=item_entity.fg)

            # Usage hints at bottom
            hint_y = iy + inv_h - 2
            console.print(ix + 2, hint_y, "a-z:use d:drop ESC:close", fg=(100, 100, 130))

    def _render_look_panel(self, console: tcod.console.Console):
        lx, ly = self.look_x, self.look_y

        # Draw cursor
        t = time.monotonic()
        alpha = 0.5 + 0.5 * math.sin(t * 5.0)
        c = int(150 + 105 * alpha)
        if 0 <= lx < self.width and 0 <= ly < self.height:
            console.rgb[lx, ly] = ord("X"), (c, c, 255), (0, 0, 30)

        # Build info lines
        lines: list[tuple[str, tuple[int, int, int]]] = []
        if not (0 <= lx < self.width and 0 <= ly < self.height):
            lines.append(("Out of bounds", (150, 150, 150)))
        elif not self.explored[lx, ly]:
            lines.append(("Unexplored", (100, 100, 100)))
        else:
            entities_here = [e for e in self.entities if e.x == lx and e.y == ly]
            entities_here.sort(key=lambda e: e.render_order.value, reverse=True)

            if entities_here:
                for e in entities_here:
                    lines.append((e.name, e.fg))
                    if e.alive and e.hp > 0:
                        lines.append((f"  HP: {e.hp}/{e.max_hp}", (255, 200, 200)))
                        lines.append((f"  ATK: {e.power} DEF: {e.defense}", (200, 200, 200)))
                        if e.ai and e.ai != "allied":
                            lines.append((f"  Behavior: {e.ai}", (150, 150, 180)))
                        elif e.ai == "allied":
                            lines.append(("  Allied", (100, 255, 200)))
                    elif e.item:
                        item = e.item
                        itype = item.get("type", "")
                        if itype == "weapon":
                            lines.append((f"  +{item.get('power_bonus', 0)} ATK", (255, 220, 100)))
                        elif itype == "armor":
                            lines.append((f"  +{item.get('defense_bonus', 0)} DEF", (100, 200, 255)))
                        elif itype == "potion":
                            lines.append((f"  Heals {item.get('heal', 0)} HP", (100, 255, 100)))
                        elif itype == "wand":
                            wid = item.get("wand_id", "unknown")
                            lines.append((f"  {wid}, {item.get('charges', 0)} charges", (100, 255, 255)))
                        elif itype == "scroll":
                            sid = item.get("scroll_id", "unknown")
                            lines.append((f"  {sid}", (200, 200, 150)))
            else:
                if self.walkable[lx, ly]:
                    lines.append(("Empty floor", (100, 100, 100)))
                else:
                    lines.append(("Solid wall", (150, 150, 150)))

        if not lines:
            return

        # Draw panel
        panel_w = max(len(text) for text, _ in lines) + 4
        panel_h = len(lines) + 2
        panel_w = max(panel_w, 12)
        panel_w = min(panel_w, 30)

        px = lx + 2
        if px + panel_w > self.width:
            px = lx - panel_w - 1
        px = max(0, px)
        py_panel = max(0, min(ly - panel_h // 2, self.height - panel_h))

        # Connector
        conn_y = ly
        box_left = px
        box_right = px + panel_w - 1
        connector_fg = (180, 170, 220)
        connector_bg = (15, 10, 30)

        if px > lx:
            for cx in range(lx + 1, px):
                if 0 <= cx < self.width:
                    console.rgb[cx, conn_y] = ord("\u2500"), connector_fg, connector_bg
            if py_panel < conn_y < py_panel + panel_h - 1:
                console.rgb[box_left, conn_y] = ord("\u251c"), connector_fg, connector_bg
        elif box_right < lx:
            for cx in range(box_right + 1, lx):
                if 0 <= cx < self.width:
                    console.rgb[cx, conn_y] = ord("\u2500"), connector_fg, connector_bg
            if py_panel < conn_y < py_panel + panel_h - 1:
                console.rgb[box_right, conn_y] = ord("\u2524"), connector_fg, connector_bg

        console.draw_frame(px, py_panel, panel_w, panel_h, title=" Look ",
                           fg=(200, 200, 220), bg=(15, 10, 30))

        if py_panel < conn_y < py_panel + panel_h - 1:
            if px > lx:
                console.rgb[box_left, conn_y] = ord("\u251c"), connector_fg, connector_bg
            elif box_right < lx:
                console.rgb[box_right, conn_y] = ord("\u2524"), connector_fg, connector_bg

        for i, (text, color) in enumerate(lines):
            console.print(px + 2, py_panel + 1 + i, text[:panel_w - 4], fg=color)

    def _render_character_screen(self, console: tcod.console.Console):
        from data import TRAIT_DESCRIPTIONS

        px, py = self.player.x, self.player.y

        lines: list[tuple[str, tuple[int, int, int]]] = []
        lines.append((f"Level {self.player_level} {self.player_trait['name']}", (220, 220, 255)))

        trait_desc = TRAIT_DESCRIPTIONS.get(self.player_trait['name'], "")
        if trait_desc:
            lines.append((trait_desc[:26], (180, 180, 200)))

        lines.append((f"HP: {self.player.hp}/{self.player.max_hp}", (255, 200, 200)))

        # ATK breakdown
        base_atk = self.player.power
        weapon_bonus = 0
        if self.equipped_weapon and self.equipped_weapon.item:
            weapon_bonus = self.equipped_weapon.item.get("power_bonus", 0)
        buff_atk = self._get_buff_power()
        total_atk = base_atk + weapon_bonus + buff_atk
        parts = [str(base_atk)]
        if weapon_bonus:
            parts.append(str(weapon_bonus))
        if buff_atk:
            parts.append(str(buff_atk))
        breakdown = "+".join(parts)
        atk_line = f"ATK: {total_atk} ({breakdown})" if len(parts) > 1 else f"ATK: {total_atk}"
        lines.append((atk_line, (200, 180, 150)))

        # DEF breakdown
        base_def = self.player.defense
        armor_bonus = 0
        if self.equipped_armor and self.equipped_armor.item:
            armor_bonus = self.equipped_armor.item.get("defense_bonus", 0)
        buff_def = self._get_buff_defense()
        total_def = base_def + armor_bonus + buff_def
        parts = [str(base_def)]
        if armor_bonus:
            parts.append(str(armor_bonus))
        if buff_def:
            parts.append(str(buff_def))
        breakdown = "+".join(parts)
        def_line = f"DEF: {total_def} ({breakdown})" if len(parts) > 1 else f"DEF: {total_def}"
        lines.append((def_line, (150, 180, 200)))

        lines.append((f"XP: {self.player_xp}", (200, 200, 100)))
        lines.append((f"Kills: {self.kills}", (200, 150, 150)))
        lines.append((f"Turns: {self.turn_count}", (180, 180, 180)))
        lines.append((f"Depth: {self.depth}", (200, 200, 255)))

        if self.buffs:
            lines.append(("", (0, 0, 0)))
            lines.append(("Active Buffs:", (220, 200, 255)))
            for buff in self.buffs:
                lines.append((f"  {buff['name']} ({buff['turns']}t)", (200, 200, 150)))

        panel_w = max((len(text) for text, _ in lines if text), default=10) + 4
        panel_h = len(lines) + 2
        panel_w = max(panel_w, 16)
        panel_w = min(panel_w, 32)

        ix = px + 2
        if ix + panel_w > self.width:
            ix = px - panel_w - 1
        ix = max(0, ix)

        iy = max(0, min(py - panel_h // 2, self.height - panel_h))

        conn_y = py
        box_left = ix
        box_right = ix + panel_w - 1
        connector_fg = (180, 170, 220)
        connector_bg = (15, 10, 30)

        if ix > px:
            for cx in range(px + 1, ix):
                if 0 <= cx < self.width:
                    console.rgb[cx, conn_y] = ord("\u2500"), connector_fg, connector_bg
            if iy < conn_y < iy + panel_h - 1:
                console.rgb[box_left, conn_y] = ord("\u251c"), connector_fg, connector_bg
        elif box_right < px:
            for cx in range(box_right + 1, px):
                if 0 <= cx < self.width:
                    console.rgb[cx, conn_y] = ord("\u2500"), connector_fg, connector_bg
            if iy < conn_y < iy + panel_h - 1:
                console.rgb[box_right, conn_y] = ord("\u2524"), connector_fg, connector_bg

        console.draw_frame(ix, iy, panel_w, panel_h, title=" Character ",
                           fg=(220, 200, 255), bg=(15, 10, 30))

        if iy < conn_y < iy + panel_h - 1:
            if ix > px:
                console.rgb[box_left, conn_y] = ord("\u251c"), connector_fg, connector_bg
            elif box_right < px:
                console.rgb[box_right, conn_y] = ord("\u2524"), connector_fg, connector_bg

        for i, (text, color) in enumerate(lines):
            if text:
                console.print(ix + 2, iy + 1 + i, text[:panel_w - 4], fg=color)

    def _render_mouse_tooltip(self, console: tcod.console.Console):
        mx, my = int(self.mouse_x), int(self.mouse_y)
        if not (0 <= mx < self.width and 0 <= my < self.height):
            return
        if not self.fov[mx, my]:
            return

        entities_here = [e for e in self.entities if e.x == mx and e.y == my]
        if not entities_here:
            return

        entities_here.sort(key=lambda e: e.render_order.value, reverse=True)
        name = entities_here[0].name

        tw = len(name) + 2
        tx = mx + 1
        ty = my - 1
        if tx + tw > self.width:
            tx = mx - tw
        tx = max(0, tx)
        ty = max(0, ty)

        console.print(tx, ty, f" {name} ", fg=(255, 255, 255), bg=(30, 20, 40))

    def _render_death_screen(self, console: tcod.console.Console):
        map_w = self.width
        map_h = self.height
        for x in range(map_w):
            for y in range(map_h):
                fg = console.rgb["fg"][x, y]
                console.rgb["fg"][x, y] = (fg[0] // 4, fg[1] // 4, fg[2] // 4)
                bg = console.rgb["bg"][x, y]
                console.rgb["bg"][x, y] = (bg[0] // 4, bg[1] // 4, bg[2] // 4)

        cx = map_w // 2
        cy = map_h // 2
        bw, bh = 40, 12
        bx = cx - bw // 2
        by = cy - bh // 2
        console.draw_frame(bx, by, bw, bh, title=" DEATH ",
                           fg=(255, 50, 50), bg=(20, 0, 0))
        console.print(bx + 2, by + 2, "Consumed by shadows...", fg=(255, 80, 80))
        console.print(bx + 2, by + 4, f"Level: {self.player_level}", fg=(200, 150, 150))
        console.print(bx + 2, by + 5, f"Depth reached: {self.depth}", fg=(200, 150, 150))
        console.print(bx + 2, by + 6, f"Kills: {self.kills}", fg=(200, 150, 150))
        console.print(bx + 2, by + 7, f"XP: {self.player_xp}  Turns: {self.turn_count}", fg=(200, 150, 150))
        if self.has_thing:
            console.print(bx + 2, by + 8, "The Truth is lost.", fg=(255, 200, 100))
        console.print(bx + 2, by + bh - 2, "Press any key to exit.", fg=(150, 100, 100))

    def _render_victory_screen(self, console: tcod.console.Console):
        map_w = self.width
        map_h = self.height
        for x in range(map_w):
            for y in range(map_h):
                fg = console.rgb["fg"][x, y]
                console.rgb["fg"][x, y] = (
                    min(255, fg[0] + 40),
                    min(255, fg[1] + 40),
                    min(255, fg[2] + 20),
                )

        cx = map_w // 2
        cy = map_h // 2
        bw, bh = 44, 12
        bx = cx - bw // 2
        by = cy - bh // 2
        console.draw_frame(bx, by, bw, bh, title=" VICTORY ",
                           fg=(255, 255, 100), bg=(10, 10, 0))
        console.print(bx + 2, by + 2, "You escaped with the Truth!", fg=(255, 255, 180))
        console.print(bx + 2, by + 3, "Kant's Ding an sich is yours.", fg=(220, 220, 150))
        console.print(bx + 2, by + 5, f"Level: {self.player_level}", fg=(200, 200, 150))
        console.print(bx + 2, by + 6, f"Kills: {self.kills}", fg=(200, 200, 150))
        console.print(bx + 2, by + 7, f"XP: {self.player_xp}  Turns: {self.turn_count}", fg=(200, 200, 150))
        console.print(bx + 2, by + 8, f"Items: {len(self.inventory)}", fg=(200, 200, 150))
        console.print(bx + 2, by + bh - 2, "Press any key to exit.", fg=(180, 180, 100))

    def _render_targeting(self, console: tcod.console.Console):
        t = time.monotonic()
        alpha = 0.5 + 0.5 * math.sin(t * 5.0)
        c = int(150 + 105 * alpha)
        console.print(1, 1, " Aim: direction key | ESC: cancel ", fg=(c, 255, 255), bg=(0, 20, 20))
