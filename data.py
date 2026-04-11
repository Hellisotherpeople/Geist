"""Static game data: level themes, monster tables, item tables, traps, identification, procgen tables."""

import random

# ── Level Themes ──────────────────────────────────────────────

LEVEL_THEMES: dict[int, dict] = {
    1: {
        "name": "The Deep Shadows",
        "floor_fg_base": (120, 0, 200),
        "floor_fg_amp": (90, 0, 82),
        "wall_fg": (180, 0, 255),
        "wall_bg_base": (20, 0, 40),
        "wall_bg_amp": (20, 0, 26),
        "explored_fg": (100, 50, 130),
        "explored_bg": (10, 5, 15),
        "shimmer_speed": 1.0,
    },
    2: {
        "name": "The Flickering Flames",
        "floor_fg_base": (220, 140, 20),
        "floor_fg_amp": (52, 90, 0),
        "wall_fg": (255, 160, 30),
        "wall_bg_base": (40, 15, 0),
        "wall_bg_amp": (32, 13, 0),
        "explored_fg": (160, 100, 40),
        "explored_bg": (15, 8, 5),
        "shimmer_speed": 1.1,
    },
    3: {
        "name": "The Shadow Gallery",
        "floor_fg_base": (100, 120, 150),
        "floor_fg_amp": (60, 60, 75),
        "wall_fg": (140, 160, 190),
        "wall_bg_base": (15, 18, 25),
        "wall_bg_amp": (13, 16, 20),
        "explored_fg": (80, 90, 110),
        "explored_bg": (8, 10, 14),
        "shimmer_speed": 1.2,
    },
    4: {
        "name": "The Narrow Passage",
        "floor_fg_base": (160, 120, 70),
        "floor_fg_amp": (75, 52, 22),
        "wall_fg": (180, 140, 80),
        "wall_bg_base": (30, 20, 10),
        "wall_bg_amp": (20, 13, 7),
        "explored_fg": (120, 90, 60),
        "explored_bg": (12, 9, 6),
        "shimmer_speed": 1.3,
    },
    5: {
        "name": "The Blinding Light",
        "floor_fg_base": (230, 220, 80),
        "floor_fg_amp": (38, 52, 90),
        "wall_fg": (255, 245, 120),
        "wall_bg_base": (40, 38, 10),
        "wall_bg_amp": (26, 23, 10),
        "explored_fg": (170, 160, 70),
        "explored_bg": (15, 14, 8),
        "shimmer_speed": 1.5,
    },
    6: {
        "name": "The World of Forms",
        "floor_fg_base": (180, 100, 200),
        "floor_fg_amp": (112, 120, 82),
        "wall_fg": (200, 120, 255),
        "wall_bg_base": (25, 15, 35),
        "wall_bg_amp": (26, 20, 20),
        "explored_fg": (140, 100, 160),
        "explored_bg": (12, 8, 16),
        "shimmer_speed": 1.6,
    },
    7: {
        "name": "The Noumenon",
        "floor_fg_base": (230, 210, 140),
        "floor_fg_amp": (38, 45, 90),
        "wall_fg": (255, 240, 180),
        "wall_bg_base": (40, 35, 15),
        "wall_bg_amp": (26, 23, 13),
        "explored_fg": (190, 170, 110),
        "explored_bg": (18, 15, 8),
        "shimmer_speed": 1.8,
    },
}


def get_theme(depth: int, ascending: bool) -> dict:
    theme = LEVEL_THEMES[max(1, min(7, depth))].copy()
    if not ascending:
        theme["name"] = "Corrupted " + theme["name"]
        for key in ("floor_fg_base", "floor_fg_amp", "wall_fg", "wall_bg_base",
                     "wall_bg_amp", "explored_fg", "explored_bg"):
            r, g, b = theme[key]
            theme[key] = (int(r * 0.7), int(g * 0.7), int(b * 0.7))
    return theme


# ── Elements & Resistances ───────────────────────────────────

ELEMENTS = ("fire", "cold", "poison", "lightning")

# ── Monster Tables ────────────────────────────────────────────
# ability: None, "ranged", "poison_touch", "drain", "teleport", "summon",
#          "split", "heal_allies", "steal", "explode", "invisible", "paralyze_gaze"

MONSTER_TABLE: dict[int, list[tuple[int, dict]]] = {
    1: [
        (30, {"char": "s", "name": "Shadow", "fg": (130, 80, 200), "hp": 4, "power": 1, "defense": 0, "xp": 5,
              "ability": None, "corpse_nutrition": 50, "corpse_effect": None}),
        (15, {"char": "S", "name": "Shackled One", "fg": (160, 100, 255), "hp": 6, "power": 2, "defense": 1, "xp": 8,
              "ability": None, "corpse_nutrition": 80, "corpse_effect": None}),
        (25, {"char": "b", "name": "Cave Bat", "fg": (140, 100, 80), "hp": 3, "power": 1, "defense": 0, "xp": 3,
              "ability": None, "corpse_nutrition": 30, "corpse_effect": None}),
        (15, {"char": "d", "name": "Flickering Doubt", "fg": (150, 80, 180), "hp": 5, "power": 2, "defense": 0, "xp": 7,
              "ability": "invisible", "corpse_nutrition": 40, "corpse_effect": "see_invisible"}),
        (10, {"char": "e", "name": "Phantom Echo", "fg": (100, 100, 180), "hp": 4, "power": 1, "defense": 1, "xp": 6,
              "ability": "teleport", "ability_params": {"range": 5}, "corpse_nutrition": 30, "corpse_effect": None}),
        (5, {"char": "W", "name": "Umbral Watcher", "fg": (80, 60, 160), "hp": 8, "power": 2, "defense": 1, "xp": 12,
             "ability": "paralyze_gaze", "ability_params": {"chance": 0.08, "duration": 2},
             "corpse_nutrition": 100, "corpse_effect": None}),
    ],
    2: [
        (25, {"char": "f", "name": "Fire Phantasm", "fg": (255, 120, 20), "hp": 6, "power": 2, "defense": 0, "xp": 10,
              "ability": "ranged", "ability_params": {"range": 6, "damage": 3, "element": "fire"},
              "corpse_nutrition": 60, "corpse_effect": "fire"}),
        (20, {"char": "W", "name": "Smoke Wraith", "fg": (180, 160, 140), "hp": 8, "power": 2, "defense": 1, "xp": 12,
              "ability": "invisible", "corpse_nutrition": 0, "corpse_effect": None}),
        (25, {"char": "w", "name": "Ember Wisp", "fg": (255, 180, 50), "hp": 4, "power": 3, "defense": 0, "xp": 8,
              "ability": "explode", "ability_params": {"radius": 2, "damage": 8},
              "corpse_nutrition": 20, "corpse_effect": None}),
        (15, {"char": "p", "name": "Pyrrhic Spirit", "fg": (200, 80, 30), "hp": 7, "power": 2, "defense": 0, "xp": 11,
              "ability": "split", "ability_params": {"chance": 0.25},
              "corpse_nutrition": 40, "corpse_effect": None}),
        (10, {"char": "g", "name": "Ash Golem", "fg": (120, 110, 100), "hp": 12, "power": 3, "defense": 2, "xp": 16,
              "ability": None, "corpse_nutrition": 0, "corpse_effect": None}),
        (5, {"char": "F", "name": "Flame Sylph", "fg": (255, 200, 100), "hp": 5, "power": 4, "defense": 0, "xp": 14,
             "ability": "ranged", "ability_params": {"range": 8, "damage": 5, "element": "fire"},
             "corpse_nutrition": 30, "corpse_effect": "fire"}),
    ],
    3: [
        (25, {"char": "p", "name": "Puppet Master", "fg": (120, 140, 170), "hp": 8, "power": 3, "defense": 1, "xp": 18,
              "ability": "summon", "ability_params": {"template_name": "Gallery Shade", "cooldown": 8},
              "corpse_nutrition": 80, "corpse_effect": None}),
        (20, {"char": "I", "name": "False Idol", "fg": (200, 200, 220), "hp": 10, "power": 2, "defense": 2, "xp": 20,
              "ability": "paralyze_gaze", "ability_params": {"chance": 0.10, "duration": 2},
              "corpse_nutrition": 0, "corpse_effect": None}),
        (25, {"char": "s", "name": "Gallery Shade", "fg": (90, 100, 130), "hp": 5, "power": 2, "defense": 0, "xp": 10,
              "ability": None, "corpse_nutrition": 40, "corpse_effect": None}),
        (15, {"char": "m", "name": "Mimetic Phantom", "fg": (180, 180, 200), "hp": 7, "power": 3, "defense": 1, "xp": 16,
              "ability": "steal", "corpse_nutrition": 50, "corpse_effect": None}),
        (15, {"char": "t", "name": "Echo Thief", "fg": (130, 160, 190), "hp": 6, "power": 4, "defense": 0, "xp": 15,
              "ability": "drain", "ability_params": {"stat": "random"},
              "corpse_nutrition": 60, "corpse_effect": None}),
    ],
    4: [
        (25, {"char": "c", "name": "Cave Crawler", "fg": (180, 130, 60), "hp": 10, "power": 3, "defense": 2, "xp": 25,
              "ability": "poison_touch", "ability_params": {"duration": 5, "dps": 1},
              "corpse_nutrition": 100, "corpse_effect": "poison"}),
        (20, {"char": "w", "name": "Doubt Worm", "fg": (140, 100, 70), "hp": 12, "power": 4, "defense": 1, "xp": 28,
              "ability": "split", "ability_params": {"chance": 0.20},
              "corpse_nutrition": 80, "corpse_effect": None}),
        (20, {"char": "v", "name": "Tunnel Viper", "fg": (100, 160, 60), "hp": 8, "power": 5, "defense": 0, "xp": 22,
              "ability": "poison_touch", "ability_params": {"duration": 8, "dps": 2},
              "corpse_nutrition": 60, "corpse_effect": "poison"}),
        (20, {"char": "l", "name": "Passage Lurker", "fg": (150, 120, 80), "hp": 14, "power": 3, "defense": 3, "xp": 30,
              "ability": "invisible", "corpse_nutrition": 120, "corpse_effect": "see_invisible"}),
        (15, {"char": "M", "name": "Narrow Mind", "fg": (170, 140, 100), "hp": 10, "power": 4, "defense": 1, "xp": 26,
              "ability": "drain", "ability_params": {"stat": "random"},
              "corpse_nutrition": 70, "corpse_effect": None}),
    ],
    5: [
        (25, {"char": "L", "name": "Light Warden", "fg": (255, 240, 100), "hp": 14, "power": 4, "defense": 2, "xp": 35,
              "ability": "heal_allies", "ability_params": {"heal": 6, "cooldown": 4},
              "corpse_nutrition": 120, "corpse_effect": None}),
        (20, {"char": "d", "name": "Dazzle Sprite", "fg": (255, 255, 180), "hp": 10, "power": 5, "defense": 1, "xp": 32,
              "ability": "ranged", "ability_params": {"range": 7, "damage": 6, "element": "lightning"},
              "corpse_nutrition": 40, "corpse_effect": "lightning"}),
        (20, {"char": "A", "name": "Blinding Seraph", "fg": (255, 255, 220), "hp": 16, "power": 5, "defense": 2, "xp": 40,
              "ability": "paralyze_gaze", "ability_params": {"chance": 0.12, "duration": 3},
              "corpse_nutrition": 80, "corpse_effect": None}),
        (20, {"char": "E", "name": "Radiant Elemental", "fg": (255, 220, 80), "hp": 18, "power": 4, "defense": 3, "xp": 38,
              "ability": "explode", "ability_params": {"radius": 3, "damage": 12},
              "corpse_nutrition": 0, "corpse_effect": "fire"}),
        (15, {"char": "T", "name": "Truth Scorcher", "fg": (255, 200, 60), "hp": 12, "power": 6, "defense": 1, "xp": 36,
              "ability": "ranged", "ability_params": {"range": 10, "damage": 8, "element": "fire"},
              "corpse_nutrition": 60, "corpse_effect": "fire"}),
    ],
    6: [
        (20, {"char": "G", "name": "Ideal Guardian", "fg": (200, 100, 255), "hp": 16, "power": 5, "defense": 3, "xp": 45,
              "ability": "heal_allies", "ability_params": {"heal": 8, "cooldown": 3},
              "corpse_nutrition": 140, "corpse_effect": None}),
        (20, {"char": "F", "name": "Form Sentinel", "fg": (100, 220, 255), "hp": 18, "power": 4, "defense": 3, "xp": 48,
              "ability": "summon", "ability_params": {"template_name": "Platonic Shade", "cooldown": 10},
              "corpse_nutrition": 120, "corpse_effect": "cold"}),
        (20, {"char": "D", "name": "Abstract Devourer", "fg": (180, 60, 200), "hp": 14, "power": 6, "defense": 2, "xp": 50,
              "ability": "drain", "ability_params": {"stat": "random"},
              "corpse_nutrition": 100, "corpse_effect": None}),
        (20, {"char": "s", "name": "Platonic Shade", "fg": (160, 140, 220), "hp": 10, "power": 4, "defense": 2, "xp": 30,
              "ability": "teleport", "ability_params": {"range": 8},
              "corpse_nutrition": 60, "corpse_effect": None}),
        (20, {"char": "H", "name": "Archetype Hunter", "fg": (220, 150, 255), "hp": 20, "power": 5, "defense": 2, "xp": 52,
              "ability": "steal", "corpse_nutrition": 130, "corpse_effect": None}),
    ],
    7: [
        (20, {"char": "N", "name": "Noumenal Watcher", "fg": (255, 230, 150), "hp": 20, "power": 6, "defense": 3, "xp": 55,
              "ability": "paralyze_gaze", "ability_params": {"chance": 0.15, "duration": 3},
              "corpse_nutrition": 150, "corpse_effect": None}),
        (15, {"char": "K", "name": "Transcendent Keeper", "fg": (255, 255, 220), "hp": 22, "power": 5, "defense": 4, "xp": 58,
              "ability": "heal_allies", "ability_params": {"heal": 10, "cooldown": 3},
              "corpse_nutrition": 160, "corpse_effect": None}),
        (15, {"char": "H", "name": "Kantian Horror", "fg": (200, 180, 255), "hp": 18, "power": 7, "defense": 3, "xp": 60,
              "ability": "drain", "ability_params": {"stat": "random"},
              "corpse_nutrition": 130, "corpse_effect": "cold"}),
        (15, {"char": "*", "name": "Ding-an-sich", "fg": (255, 255, 180), "hp": 25, "power": 6, "defense": 5, "xp": 70,
              "ability": "teleport", "ability_params": {"range": 12},
              "corpse_nutrition": 200, "corpse_effect": "lightning"}),
        (15, {"char": "B", "name": "Categorical Beast", "fg": (240, 200, 140), "hp": 24, "power": 8, "defense": 2, "xp": 65,
              "ability": "explode", "ability_params": {"radius": 3, "damage": 18},
              "corpse_nutrition": 140, "corpse_effect": "fire"}),
        (20, {"char": "S", "name": "The Sublime", "fg": (255, 240, 255), "hp": 30, "power": 7, "defense": 4, "xp": 80,
              "ability": "summon", "ability_params": {"template_name": "Noumenal Watcher", "cooldown": 12},
              "corpse_nutrition": 200, "corpse_effect": None}),
    ],
}


def get_monsters(depth: int, ascending: bool) -> list[tuple[int, dict]]:
    depth = max(1, min(7, depth))
    table = [(w, {k: v for k, v in t.items()}) for w, t in MONSTER_TABLE[depth]]
    if not ascending:
        for _w, t in table:
            t["name"] = "Corrupted " + t["name"]
            t["hp"] = int(t["hp"] * 1.4)
            t["power"] = t["power"] + 2
            t["defense"] = t["defense"] + 1
            t["xp"] = int(t.get("xp", 0) * 1.5)
            r, g, b = t["fg"]
            t["fg"] = (min(255, r + 60), max(0, g - 40), max(0, b - 40))
    return table


# ── Potion Types (with identification) ───────────────────────

POTION_TYPES: list[dict] = [
    {"potion_id": "healing", "name": "Potion of Healing", "fg": (200, 50, 50),
     "effect": "heal", "value": 15},
    {"potion_id": "greater_healing", "name": "Potion of Greater Healing", "fg": (255, 80, 80),
     "effect": "heal", "value": 35},
    {"potion_id": "poison", "name": "Potion of Poison", "fg": (80, 200, 40),
     "effect": "status", "status": "poison", "duration": 10},
    {"potion_id": "speed", "name": "Potion of Speed", "fg": (100, 200, 255),
     "effect": "status", "status": "haste", "duration": 15},
    {"potion_id": "might", "name": "Potion of Might", "fg": (255, 160, 60),
     "effect": "buff", "buff_power": 3, "buff_defense": 0, "duration": 20},
    {"potion_id": "resistance", "name": "Potion of Resistance", "fg": (200, 200, 200),
     "effect": "buff", "buff_power": 0, "buff_defense": 3, "duration": 20},
    {"potion_id": "invisibility", "name": "Potion of Invisibility", "fg": (200, 200, 255),
     "effect": "status", "status": "invisible", "duration": 20},
    {"potion_id": "blindness", "name": "Potion of Blindness", "fg": (40, 40, 40),
     "effect": "status", "status": "blind", "duration": 15},
    {"potion_id": "confusion", "name": "Potion of Confusion", "fg": (200, 100, 200),
     "effect": "status", "status": "confused", "duration": 10},
    {"potion_id": "paralysis", "name": "Potion of Paralysis", "fg": (160, 160, 60),
     "effect": "status", "status": "paralyzed", "duration": 5},
    {"potion_id": "levitation", "name": "Potion of Levitation", "fg": (180, 220, 255),
     "effect": "status", "status": "levitating", "duration": 20},
    {"potion_id": "regeneration", "name": "Potion of Regeneration", "fg": (100, 255, 100),
     "effect": "status", "status": "regenerating", "duration": 25},
    {"potion_id": "experience", "name": "Potion of Experience", "fg": (255, 255, 100),
     "effect": "xp", "value": 50},
    {"potion_id": "see_invisible", "name": "Potion of True Sight", "fg": (255, 200, 255),
     "effect": "status", "status": "see_invisible", "duration": 50},
]

UNID_POTION_NAMES: list[str] = [
    "murky potion", "bubbling elixir", "glowing draught", "viscous tincture",
    "shimmering potion", "fuming vial", "crystalline potion", "opalescent elixir",
    "smoky potion", "phosphorescent draught", "swirling vial", "brackish potion",
    "luminous elixir", "effervescent potion", "cloudy tincture", "prismatic vial",
]

# ── Scroll Types (with identification) ───────────────────────

SCROLL_TYPES: list[dict] = [
    {"scroll_id": "mapping", "name": "Scroll of Mapping", "fg": (200, 220, 150)},
    {"scroll_id": "teleportation", "name": "Scroll of Teleportation", "fg": (100, 200, 255)},
    {"scroll_id": "fear", "name": "Scroll of Fear", "fg": (255, 180, 100)},
    {"scroll_id": "mending", "name": "Scroll of Mending", "fg": (100, 255, 150)},
    {"scroll_id": "imperative", "name": "Scroll of Imperative", "fg": (255, 150, 150)},
    {"scroll_id": "transcendence", "name": "Scroll of Transcendence", "fg": (220, 180, 255)},
    {"scroll_id": "enchant_weapon", "name": "Scroll of Enchant Weapon", "fg": (255, 220, 100)},
    {"scroll_id": "enchant_armor", "name": "Scroll of Enchant Armor", "fg": (100, 200, 255)},
    {"scroll_id": "identify", "name": "Scroll of Identify", "fg": (255, 255, 200)},
    {"scroll_id": "remove_curse", "name": "Scroll of Remove Curse", "fg": (255, 255, 255)},
    {"scroll_id": "summon", "name": "Scroll of Summoning", "fg": (200, 100, 100)},
    {"scroll_id": "fire", "name": "Scroll of Fire", "fg": (255, 100, 30)},
    {"scroll_id": "protection", "name": "Scroll of Protection", "fg": (100, 150, 255)},
    {"scroll_id": "amnesia", "name": "Scroll of Amnesia", "fg": (150, 150, 150)},
]

UNID_SCROLL_LABELS: list[str] = [
    "ELBERETH", "XYZZY", "NIHIL", "COGITO", "ERGO SUM", "DASEIN",
    "TABULA RASA", "LOGOS", "PRAGMA", "NOESIS", "EPOCHÉ", "APORIA",
    "PHRONESIS", "ALETHEIA", "NOUS", "ENTELECHY",
]

# ── Ring Types ────────────────────────────────────────────────

RING_TYPES: list[dict] = [
    {"ring_id": "protection", "name": "Ring of Protection", "fg": (150, 180, 255),
     "defense_bonus": 2, "cursed": False},
    {"ring_id": "strength", "name": "Ring of Strength", "fg": (255, 180, 100),
     "power_bonus": 2, "cursed": False},
    {"ring_id": "regeneration", "name": "Ring of Regeneration", "fg": (100, 255, 150),
     "regen_rate": 5, "cursed": False},
    {"ring_id": "fire_resist", "name": "Ring of Fire Resistance", "fg": (255, 100, 50),
     "resist": "fire", "cursed": False},
    {"ring_id": "cold_resist", "name": "Ring of Cold Resistance", "fg": (100, 180, 255),
     "resist": "cold", "cursed": False},
    {"ring_id": "poison_resist", "name": "Ring of Poison Resistance", "fg": (80, 200, 80),
     "resist": "poison", "cursed": False},
    {"ring_id": "see_invisible", "name": "Ring of True Sight", "fg": (220, 180, 255),
     "see_invisible": True, "cursed": False},
    {"ring_id": "stealth", "name": "Ring of Stealth", "fg": (100, 100, 120),
     "stealth": True, "cursed": False},
    {"ring_id": "hunger", "name": "Ring of Hunger", "fg": (180, 140, 80),
     "hunger_mult": 2, "cursed": True},
    {"ring_id": "teleportation", "name": "Ring of Teleportation", "fg": (200, 100, 255),
     "teleport_chance": 0.02, "cursed": True},
]

UNID_RING_NAMES: list[str] = [
    "jade ring", "iron ring", "obsidian ring", "copper ring", "silver ring",
    "amber ring", "bone ring", "crystal ring", "opal ring", "garnet ring",
    "sapphire ring", "ruby ring",
]

# ── Amulet Types ──────────────────────────────────────────────

AMULET_TYPES: list[dict] = [
    {"amulet_id": "life_saving", "name": "Amulet of Life Saving", "fg": (255, 255, 200),
     "cursed": False},
    {"amulet_id": "esp", "name": "Amulet of ESP", "fg": (200, 150, 255),
     "cursed": False},
    {"amulet_id": "reflection", "name": "Amulet of Reflection", "fg": (200, 200, 220),
     "cursed": False},
    {"amulet_id": "vitality", "name": "Amulet of Vitality", "fg": (100, 255, 100),
     "max_hp_bonus": 20, "cursed": False},
    {"amulet_id": "strangulation", "name": "Amulet of Strangulation", "fg": (180, 80, 80),
     "cursed": True},
    {"amulet_id": "restful_sleep", "name": "Amulet of Restful Sleep", "fg": (100, 100, 180),
     "cursed": True},
    {"amulet_id": "wisdom", "name": "Amulet of Wisdom", "fg": (255, 220, 150),
     "xp_mult": 1.5, "cursed": False},
]

UNID_AMULET_NAMES: list[str] = [
    "golden amulet", "tarnished amulet", "glowing amulet", "bone amulet",
    "crystal amulet", "iron amulet", "silver amulet", "obsidian amulet",
]

# ── Food Types ────────────────────────────────────────────────

FOOD_TYPES: list[dict] = [
    {"food_id": "ration", "name": "Ration", "fg": (180, 140, 80), "nutrition": 800},
    {"food_id": "bread", "name": "Stale Bread", "fg": (200, 170, 100), "nutrition": 400},
    {"food_id": "dried_meat", "name": "Dried Meat", "fg": (160, 80, 60), "nutrition": 500},
    {"food_id": "mushroom", "name": "Cave Mushroom", "fg": (180, 200, 160), "nutrition": 300,
     "random_effect": True},
    {"food_id": "text", "name": "Philosophical Text", "fg": (200, 200, 150), "nutrition": 200,
     "xp_bonus": 15},
]

# ── Trap Types ────────────────────────────────────────────────

TRAP_TYPES: list[dict] = [
    {"trap_id": "bear_trap", "name": "bear trap", "fg": (180, 120, 60),
     "effect": "immobilize", "duration": 3, "damage": 3},
    {"trap_id": "pit", "name": "pit", "fg": (100, 80, 60),
     "effect": "damage", "damage": 10},
    {"trap_id": "spiked_pit", "name": "spiked pit", "fg": (150, 60, 60),
     "effect": "damage", "damage": 20},
    {"trap_id": "teleport", "name": "teleport trap", "fg": (100, 200, 255),
     "effect": "teleport"},
    {"trap_id": "arrow", "name": "arrow trap", "fg": (200, 180, 100),
     "effect": "damage", "damage": 15},
    {"trap_id": "poison_dart", "name": "poison dart trap", "fg": (80, 200, 80),
     "effect": "poison", "damage": 5, "duration": 8},
    {"trap_id": "fire", "name": "fire trap", "fg": (255, 100, 30),
     "effect": "fire_damage", "damage": 12},
    {"trap_id": "alarm", "name": "alarm trap", "fg": (255, 255, 100),
     "effect": "alarm"},
    {"trap_id": "confusion_gas", "name": "confusion gas trap", "fg": (200, 100, 200),
     "effect": "confuse", "duration": 8},
    {"trap_id": "sleep_gas", "name": "sleep gas trap", "fg": (100, 100, 200),
     "effect": "paralyze", "duration": 5},
]

# ── Item Tables (expanded per depth) ─────────────────────────

ITEM_TABLE: dict[int, list[tuple[int, dict]]] = {
    1: [
        (30, {"char": "!", "name": "Potion", "fg": (200, 50, 50), "type": "potion"}),
        (20, {"char": "/", "name": "Rusty Dagger", "fg": (180, 160, 140), "type": "weapon", "power_bonus": 1}),
        (10, {"char": "[", "name": "Tattered Robe", "fg": (100, 80, 140), "type": "armor", "defense_bonus": 1}),
        (5, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (5, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
        (10, {"char": "=", "name": "Ring", "fg": (200, 200, 200), "type": "ring"}),
        (5, {"char": '"', "name": "Amulet", "fg": (200, 200, 150), "type": "amulet"}),
        (15, {"char": "%", "name": "Food", "fg": (180, 140, 80), "type": "food"}),
    ],
    2: [
        (28, {"char": "!", "name": "Potion", "fg": (220, 80, 60), "type": "potion"}),
        (18, {"char": "/", "name": "Bronze Sword", "fg": (200, 160, 60), "type": "weapon", "power_bonus": 2}),
        (10, {"char": "[", "name": "Leather Armor", "fg": (140, 100, 60), "type": "armor", "defense_bonus": 1}),
        (5, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (7, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
        (8, {"char": "=", "name": "Ring", "fg": (200, 200, 200), "type": "ring"}),
        (5, {"char": '"', "name": "Amulet", "fg": (200, 200, 150), "type": "amulet"}),
        (12, {"char": "%", "name": "Food", "fg": (180, 140, 80), "type": "food"}),
        (7, {"char": "!", "name": "Potion", "fg": (255, 80, 80), "type": "potion"}),
    ],
    3: [
        (25, {"char": "!", "name": "Potion", "fg": (230, 100, 80), "type": "potion"}),
        (16, {"char": "/", "name": "Iron Blade", "fg": (190, 190, 200), "type": "weapon", "power_bonus": 3}),
        (12, {"char": "[", "name": "Chain Mail", "fg": (170, 170, 180), "type": "armor", "defense_bonus": 2}),
        (7, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (8, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
        (8, {"char": "=", "name": "Ring", "fg": (200, 200, 200), "type": "ring"}),
        (5, {"char": '"', "name": "Amulet", "fg": (200, 200, 150), "type": "amulet"}),
        (10, {"char": "%", "name": "Food", "fg": (180, 140, 80), "type": "food"}),
        (9, {"char": "!", "name": "Potion", "fg": (255, 80, 80), "type": "potion"}),
    ],
    4: [
        (22, {"char": "!", "name": "Potion", "fg": (240, 120, 100), "type": "potion"}),
        (15, {"char": "/", "name": "Steel Sword", "fg": (200, 200, 220), "type": "weapon", "power_bonus": 4}),
        (12, {"char": "[", "name": "Plate Armor", "fg": (180, 180, 200), "type": "armor", "defense_bonus": 3}),
        (9, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (10, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
        (8, {"char": "=", "name": "Ring", "fg": (200, 200, 200), "type": "ring"}),
        (6, {"char": '"', "name": "Amulet", "fg": (200, 200, 150), "type": "amulet"}),
        (10, {"char": "%", "name": "Food", "fg": (180, 140, 80), "type": "food"}),
        (8, {"char": "!", "name": "Potion", "fg": (255, 80, 80), "type": "potion"}),
    ],
    5: [
        (20, {"char": "!", "name": "Potion", "fg": (255, 140, 120), "type": "potion"}),
        (14, {"char": "/", "name": "Radiant Blade", "fg": (255, 240, 140), "type": "weapon", "power_bonus": 5}),
        (12, {"char": "[", "name": "Light Ward Armor", "fg": (240, 230, 140), "type": "armor", "defense_bonus": 3}),
        (10, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (11, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
        (9, {"char": "=", "name": "Ring", "fg": (200, 200, 200), "type": "ring"}),
        (7, {"char": '"', "name": "Amulet", "fg": (200, 200, 150), "type": "amulet"}),
        (9, {"char": "%", "name": "Food", "fg": (180, 140, 80), "type": "food"}),
        (8, {"char": "!", "name": "Potion", "fg": (255, 80, 80), "type": "potion"}),
    ],
    6: [
        (18, {"char": "!", "name": "Potion", "fg": (255, 160, 200), "type": "potion"}),
        (13, {"char": "/", "name": "Form Slicer", "fg": (180, 100, 255), "type": "weapon", "power_bonus": 6}),
        (13, {"char": "[", "name": "Ideal Shield Armor", "fg": (120, 200, 255), "type": "armor", "defense_bonus": 4}),
        (12, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (13, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
        (9, {"char": "=", "name": "Ring", "fg": (200, 200, 200), "type": "ring"}),
        (7, {"char": '"', "name": "Amulet", "fg": (200, 200, 150), "type": "amulet"}),
        (8, {"char": "%", "name": "Food", "fg": (180, 140, 80), "type": "food"}),
        (7, {"char": "!", "name": "Potion", "fg": (255, 80, 80), "type": "potion"}),
    ],
    7: [
        (16, {"char": "!", "name": "Potion", "fg": (255, 220, 180), "type": "potion"}),
        (12, {"char": "/", "name": "Truth Seeker Blade", "fg": (255, 240, 200), "type": "weapon", "power_bonus": 7}),
        (12, {"char": "[", "name": "Transcendent Plate", "fg": (255, 255, 220), "type": "armor", "defense_bonus": 5}),
        (13, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (14, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
        (9, {"char": "=", "name": "Ring", "fg": (200, 200, 200), "type": "ring"}),
        (8, {"char": '"', "name": "Amulet", "fg": (200, 200, 150), "type": "amulet"}),
        (8, {"char": "%", "name": "Food", "fg": (180, 140, 80), "type": "food"}),
        (8, {"char": "!", "name": "Potion", "fg": (255, 80, 80), "type": "potion"}),
    ],
}


def get_items(depth: int) -> list[tuple[int, dict]]:
    depth = max(1, min(7, depth))
    return [(w, {k: v for k, v in t.items()}) for w, t in ITEM_TABLE[depth]]


def pick_weighted(table: list[tuple[int, dict]]) -> dict:
    weights = [w for w, _ in table]
    templates = [t for _, t in table]
    chosen = random.choices(templates, weights=weights, k=1)[0]
    return {k: v for k, v in chosen.items()}


# ── Enemy Prefixes ────────────────────────────────────────────

ENEMY_PREFIXES: list[dict] = [
    {"name": "Frenzied", "ai": "berserker", "power": 1, "hp": 0, "defense": 0,
     "tint": (60, -30, -30)},
    {"name": "Spectral", "ai": None, "power": 0, "hp": 0, "defense": 2,
     "tint": (-40, -20, 40)},
    {"name": "Armored", "ai": None, "power": 0, "hp": 4, "defense": 3,
     "tint": (-30, -30, -30)},
    {"name": "Stalking", "ai": "stalker", "power": 0, "hp": 0, "defense": 0,
     "tint": (-40, -40, -20)},
    {"name": "Cowardly", "ai": "coward", "power": -1, "hp": 2, "defense": 0,
     "tint": (-20, 20, -20)},
    {"name": "Swarming", "ai": "swarm", "power": 0, "hp": -1, "defense": 0,
     "tint": (-20, 40, -20)},
    {"name": "Giant", "ai": None, "power": 2, "hp": 6, "defense": 0,
     "tint": (20, 20, 20)},
    {"name": "Quick", "ai": None, "power": 2, "hp": 0, "defense": 0,
     "tint": (30, 30, 40)},
    {"name": "Venomous", "ai": None, "power": 0, "hp": 0, "defense": 0,
     "tint": (-20, 50, -30), "grant_ability": "poison_touch",
     "grant_ability_params": {"duration": 5, "dps": 1}},
    {"name": "Blinking", "ai": None, "power": 0, "hp": 0, "defense": 0,
     "tint": (30, -20, 50), "grant_ability": "teleport",
     "grant_ability_params": {"range": 6}},
    {"name": "Invisible", "ai": None, "power": 0, "hp": 0, "defense": 0,
     "tint": (-30, -30, -30), "grant_ability": "invisible"},
    {"name": "Splitting", "ai": None, "power": 0, "hp": 2, "defense": 0,
     "tint": (20, 20, -20), "grant_ability": "split",
     "grant_ability_params": {"chance": 0.25}},
]

CHAMPION_TINT = (40, 30, -20)


# ── Item Affixes ──────────────────────────────────────────────

ITEM_PREFIXES: list[dict] = [
    {"name": "Gleaming", "power_bonus": 1, "defense_bonus": 0, "heal_mult": 1.0, "charges": 0},
    {"name": "Sturdy", "power_bonus": 0, "defense_bonus": 1, "heal_mult": 1.0, "charges": 0},
    {"name": "Ancient", "power_bonus": 2, "defense_bonus": 0, "heal_mult": 1.0, "charges": 0},
    {"name": "Cursed", "power_bonus": 3, "defense_bonus": -1, "heal_mult": 1.0, "charges": 0},
    {"name": "Blessed", "power_bonus": 0, "defense_bonus": 0, "heal_mult": 1.5, "charges": 0},
    {"name": "Volatile", "power_bonus": 0, "defense_bonus": 0, "heal_mult": 1.0, "charges": 1},
    {"name": "Flaming", "power_bonus": 1, "defense_bonus": 0, "heal_mult": 1.0, "charges": 0,
     "element": "fire"},
    {"name": "Frozen", "power_bonus": 1, "defense_bonus": 0, "heal_mult": 1.0, "charges": 0,
     "element": "cold"},
    {"name": "Venomous", "power_bonus": 0, "defense_bonus": 0, "heal_mult": 1.0, "charges": 0,
     "element": "poison"},
    {"name": "Thundering", "power_bonus": 1, "defense_bonus": 0, "heal_mult": 1.0, "charges": 0,
     "element": "lightning"},
]

ITEM_SUFFIXES: list[dict] = [
    {"name": "of Wrath", "power_bonus": 2, "defense_bonus": 0, "heal_bonus": 0, "charges": 0},
    {"name": "of the Guardian", "power_bonus": 0, "defense_bonus": 2, "heal_bonus": 0, "charges": 0},
    {"name": "of Vitality", "power_bonus": 0, "defense_bonus": 0, "heal_bonus": 5, "charges": 0},
    {"name": "of the Phoenix", "power_bonus": 0, "defense_bonus": 0, "heal_bonus": 10, "charges": 0},
    {"name": "of Thorns", "power_bonus": 0, "defense_bonus": 0, "heal_bonus": 0, "charges": 0},
    {"name": "of Animation", "power_bonus": 0, "defense_bonus": 0, "heal_bonus": 0, "charges": 1},
    {"name": "of Sustenance", "power_bonus": 0, "defense_bonus": 0, "heal_bonus": 0, "charges": 0,
     "hunger_reduction": 0.5},
    {"name": "of the Philosopher", "power_bonus": 0, "defense_bonus": 0, "heal_bonus": 0, "charges": 0,
     "xp_mult": 1.2},
]


# ── Player Traits ─────────────────────────────────────────────

PLAYER_TRAITS: list[dict] = [
    {"name": "Scholar", "max_hp": 20, "power": 0, "defense": 0, "wand_charges": 0, "extra_item": False,
     "hunger_rate": 1.0},
    {"name": "Warrior", "max_hp": 0, "power": 2, "defense": 0, "wand_charges": 0, "extra_item": False,
     "hunger_rate": 1.2},
    {"name": "Sentinel", "max_hp": 0, "power": 0, "defense": 2, "wand_charges": 0, "extra_item": False,
     "hunger_rate": 1.0},
    {"name": "Mystic", "max_hp": 0, "power": 0, "defense": 0, "wand_charges": 2, "extra_item": False,
     "hunger_rate": 0.8},
    {"name": "Scavenger", "max_hp": 0, "power": 0, "defense": 0, "wand_charges": 0, "extra_item": True,
     "hunger_rate": 0.7},
    {"name": "Ascetic", "max_hp": 10, "power": 1, "defense": 1, "wand_charges": 0, "extra_item": False,
     "hunger_rate": 0.5},
]


# ── Wand Types ────────────────────────────────────────────────

WAND_TYPES: list[dict] = [
    {"wand_id": "animation", "name": "Wand of Animation", "fg": (100, 255, 255),
     "bolt_fg": (100, 255, 255), "bolt_char": "*"},
    {"wand_id": "negation", "name": "Wand of Negation", "fg": (255, 80, 80),
     "bolt_fg": (255, 80, 80), "bolt_char": "-"},
    {"wand_id": "transposition", "name": "Wand of Transposition", "fg": (80, 130, 255),
     "bolt_fg": (80, 130, 255), "bolt_char": "~"},
    {"wand_id": "petrification", "name": "Wand of Petrification", "fg": (160, 160, 160),
     "bolt_fg": (160, 160, 160), "bolt_char": "#"},
    {"wand_id": "revelation", "name": "Wand of Revelation", "fg": (255, 255, 100),
     "bolt_fg": (255, 255, 100), "bolt_char": "!"},
    {"wand_id": "sundering", "name": "Wand of Sundering", "fg": (255, 160, 50),
     "bolt_fg": (255, 160, 50), "bolt_char": "/"},
    {"wand_id": "communion", "name": "Wand of Communion", "fg": (180, 80, 255),
     "bolt_fg": (180, 80, 255), "bolt_char": "+"},
    {"wand_id": "entropy", "name": "Wand of Entropy", "fg": (160, 160, 160),
     "bolt_fg": (160, 160, 160), "bolt_char": "?"},
]


def generate_random_wand(depth: int) -> dict:
    depth = max(1, min(7, depth))
    available = min(1 + depth, len(WAND_TYPES))
    wand = random.choice(WAND_TYPES[:available])
    return {k: v for k, v in wand.items()}


def generate_random_scroll() -> dict:
    scroll = random.choice(SCROLL_TYPES)
    return {k: v for k, v in scroll.items()}


def generate_random_potion() -> dict:
    potion = random.choice(POTION_TYPES)
    return {k: v for k, v in potion.items()}


def generate_random_ring() -> dict:
    ring = random.choice(RING_TYPES)
    return {k: v for k, v in ring.items()}


def generate_random_amulet() -> dict:
    amulet = random.choice(AMULET_TYPES)
    return {k: v for k, v in amulet.items()}


def generate_random_food() -> dict:
    food = random.choice(FOOD_TYPES)
    return {k: v for k, v in food.items()}


def generate_random_trap() -> dict:
    trap = random.choice(TRAP_TYPES)
    return {k: v for k, v in trap.items()}


# ── Identification Shuffle ────────────────────────────────────

def shuffle_identification() -> dict:
    """Generate randomized unidentified names for a new game run.
    Returns dict with potion_map, scroll_map, ring_map, amulet_map.
    Each maps true_id -> unidentified_appearance_name."""
    potion_names = UNID_POTION_NAMES[:]
    random.shuffle(potion_names)
    potion_map = {}
    for i, pt in enumerate(POTION_TYPES):
        potion_map[pt["potion_id"]] = potion_names[i % len(potion_names)]

    scroll_labels = UNID_SCROLL_LABELS[:]
    random.shuffle(scroll_labels)
    scroll_map = {}
    for i, st in enumerate(SCROLL_TYPES):
        scroll_map[st["scroll_id"]] = f"scroll labeled {scroll_labels[i % len(scroll_labels)]}"

    ring_names = UNID_RING_NAMES[:]
    random.shuffle(ring_names)
    ring_map = {}
    for i, rt in enumerate(RING_TYPES):
        ring_map[rt["ring_id"]] = ring_names[i % len(ring_names)]

    amulet_names = UNID_AMULET_NAMES[:]
    random.shuffle(amulet_names)
    amulet_map = {}
    for i, at in enumerate(AMULET_TYPES):
        amulet_map[at["amulet_id"]] = amulet_names[i % len(amulet_names)]

    return {
        "potion": potion_map,
        "scroll": scroll_map,
        "ring": ring_map,
        "amulet": amulet_map,
    }


# ── XP & Leveling ────────────────────────────────────────────

XP_THRESHOLDS: list[int] = [0, 0, 30, 80, 160, 280, 440, 650, 920, 1250, 1650, 2100, 2600, 3200, 3900]


# ── Flavor Text ──────────────────────────────────────────────

ATMOSPHERE_MESSAGES: dict[int, list[str]] = {
    1: [
        "The shadows whisper of things beyond perception.",
        "A cold draft carries the scent of forgotten knowledge.",
        "The darkness here feels almost purposeful.",
        "You sense the boundary between appearance and reality.",
        "Something stirs in the phenomenal depths.",
        "The cave breathes with an intelligence you cannot name.",
        "Chains rattle somewhere in the dark.",
        "You hear dripping water echo from impossible distances.",
    ],
    2: [
        "Flames dance without fuel, pure form without substance.",
        "The heat here is more concept than sensation.",
        "Smoke traces patterns that almost resolve into meaning.",
        "Fire illuminates only to deepen the surrounding mystery.",
        "The flickering light reveals and conceals in equal measure.",
        "Embers drift upward as if seeking their own first cause.",
        "The air shimmers with potential energy.",
        "Something crackles and pops in the walls.",
    ],
    3: [
        "Echoes of your steps return changed, distorted.",
        "The gallery walls seem to observe your passage.",
        "Shadows here move with deliberate intent.",
        "You feel the weight of unasked questions.",
        "The silence between sounds carries its own meaning.",
        "Something watches from beyond the veil of sense.",
        "A painting you don't remember seeing seems to follow you.",
        "The floor creaks beneath unseen weight.",
    ],
    4: [
        "The passage narrows like a closing argument.",
        "Stone presses close, whispering of necessary limits.",
        "Each step forward is a small act of pure reason.",
        "The walls channel your will toward a single direction.",
        "Dust motes hang suspended, indifferent to time.",
        "The earth groans with the weight of hidden truths.",
        "Roots push through cracks in the ancient stone.",
        "Something skitters in the darkness ahead.",
    ],
    5: [
        "The light here burns with the intensity of pure reason.",
        "Brightness scours away comfortable illusions.",
        "You squint against truths too brilliant to face directly.",
        "The radiance strips bare every comfortable deception.",
        "Light and understanding merge into a single blinding force.",
        "Your shadow stretches impossibly long behind you.",
        "The air hums with barely contained energy.",
    ],
    6: [
        "Reality here feels more real than the surface world.",
        "Perfect geometric forms shimmer at the edge of vision.",
        "The ideal presses against the merely actual.",
        "You walk among archetypes, not their pale copies.",
        "Each form here is a universal made particular.",
        "The boundary between thought and thing dissolves.",
        "Mathematics and matter become one.",
        "You sense the eternal forms underlying all appearance.",
    ],
    7: [
        "You stand at the threshold of the thing-in-itself.",
        "The noumenal realm resists comprehension by design.",
        "Categories of understanding strain and buckle here.",
        "What lies beyond phenomena cannot be spoken, only approached.",
        "The ground of all being hums beneath your feet.",
        "You sense the unconditioned condition of all that is.",
        "Time and space feel like mere suggestions here.",
        "The boundary of knowledge presses against your mind.",
    ],
}

ATTACK_VERBS_PLAYER: list[str] = [
    "strike", "slash", "smash", "cut", "cleave", "rend", "jab", "thrust",
]

ATTACK_VERBS_MONSTER: list[str] = [
    "claws at", "bites", "strikes", "lunges at", "tears at", "slashes",
    "snaps at", "rakes", "hammers",
]

DEATH_MESSAGES_MONSTER: list[str] = [
    "{name} dissolves into shadow.",
    "{name} collapses into nothing.",
    "{name} shatters like a broken idea.",
    "{name} fades from existence.",
    "{name} crumbles to phenomenal dust.",
    "{name} evaporates into the void.",
    "{name} unravels into nothingness.",
]

DEATH_MESSAGES_PLAYER: list[str] = [
    "The shadows claim you.",
    "You dissolve into the noumenal void.",
    "Consciousness fades beyond the veil.",
    "The cave swallows your understanding.",
    "Your phenomenal existence ceases.",
]

HUNGER_MESSAGES: dict[str, tuple[str, tuple[int, int, int]]] = {
    "satiated": ("You feel satiated.", (100, 200, 100)),
    "normal": ("You feel normal.", (180, 180, 180)),
    "hungry": ("You are getting hungry.", (220, 200, 100)),
    "weak": ("You feel weak from hunger!", (255, 150, 50)),
    "fainting": ("You are fainting from hunger!!", (255, 80, 80)),
}

TRAIT_DESCRIPTIONS: dict[str, str] = {
    "Scholar": "Keen mind grants resilience. +20 HP.",
    "Warrior": "Combat mastery. +2 ATK. Hungers fast.",
    "Sentinel": "Immovable as the categorical. +2 DEF.",
    "Mystic": "Arcane affinity. +2 wand charges. Low hunger.",
    "Scavenger": "Pragmatic. Extra item. Very low hunger.",
    "Ascetic": "Balanced discipline. +10 HP, +1/+1. Half hunger.",
}
