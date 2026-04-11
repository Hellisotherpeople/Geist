"""Static game data: level themes, monster tables, item tables, procgen tables."""

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
    """Return the theme for a given depth. Darkened variant when descending."""
    theme = LEVEL_THEMES[max(1, min(7, depth))].copy()
    if not ascending:
        theme["name"] = "Corrupted " + theme["name"]
        for key in ("floor_fg_base", "floor_fg_amp", "wall_fg", "wall_bg_base",
                     "wall_bg_amp", "explored_fg", "explored_bg"):
            r, g, b = theme[key]
            theme[key] = (int(r * 0.7), int(g * 0.7), int(b * 0.7))
    return theme


# ── Monster Tables ────────────────────────────────────────────

MONSTER_TABLE: dict[int, list[tuple[int, dict]]] = {
    1: [
        (70, {"char": "s", "name": "Shadow", "fg": (130, 80, 200), "hp": 4, "power": 1, "defense": 0, "xp": 5}),
        (30, {"char": "S", "name": "Shackled One", "fg": (160, 100, 255), "hp": 6, "power": 2, "defense": 1, "xp": 8}),
    ],
    2: [
        (65, {"char": "f", "name": "Fire Phantasm", "fg": (255, 120, 20), "hp": 6, "power": 2, "defense": 0, "xp": 10}),
        (35, {"char": "W", "name": "Smoke Wraith", "fg": (180, 160, 140), "hp": 8, "power": 2, "defense": 1, "xp": 12}),
    ],
    3: [
        (60, {"char": "p", "name": "Puppet Master", "fg": (120, 140, 170), "hp": 8, "power": 3, "defense": 1, "xp": 18}),
        (40, {"char": "I", "name": "False Idol", "fg": (200, 200, 220), "hp": 10, "power": 2, "defense": 2, "xp": 20}),
    ],
    4: [
        (60, {"char": "c", "name": "Cave Crawler", "fg": (180, 130, 60), "hp": 10, "power": 3, "defense": 2, "xp": 25}),
        (40, {"char": "w", "name": "Doubt Worm", "fg": (140, 100, 70), "hp": 12, "power": 4, "defense": 1, "xp": 28}),
    ],
    5: [
        (55, {"char": "L", "name": "Light Warden", "fg": (255, 240, 100), "hp": 14, "power": 4, "defense": 2, "xp": 35}),
        (45, {"char": "d", "name": "Dazzle Sprite", "fg": (255, 255, 180), "hp": 10, "power": 5, "defense": 1, "xp": 32}),
    ],
    6: [
        (55, {"char": "G", "name": "Ideal Guardian", "fg": (200, 100, 255), "hp": 16, "power": 5, "defense": 3, "xp": 45}),
        (45, {"char": "F", "name": "Form Sentinel", "fg": (100, 220, 255), "hp": 18, "power": 4, "defense": 3, "xp": 48}),
    ],
    7: [
        (50, {"char": "N", "name": "Noumenal Watcher", "fg": (255, 230, 150), "hp": 20, "power": 6, "defense": 3, "xp": 55}),
        (50, {"char": "K", "name": "Transcendent Keeper", "fg": (255, 255, 220), "hp": 22, "power": 5, "defense": 4, "xp": 58}),
    ],
}


def get_monsters(depth: int, ascending: bool) -> list[tuple[int, dict]]:
    """Return monster table for depth. Corrupted variants on descent."""
    depth = max(1, min(7, depth))
    table = [(w, t.copy()) for w, t in MONSTER_TABLE[depth]]
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


# ── Item Tables ───────────────────────────────────────────────

ITEM_TABLE: dict[int, list[tuple[int, dict]]] = {
    1: [
        (55, {"char": "!", "name": "Minor Potion", "fg": (200, 50, 50), "type": "potion", "heal": 8}),
        (25, {"char": "/", "name": "Rusty Dagger", "fg": (180, 160, 140), "type": "weapon", "power_bonus": 1}),
        (10, {"char": "[", "name": "Tattered Robe", "fg": (100, 80, 140), "type": "armor", "defense_bonus": 1}),
        (5, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (5, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
    ],
    2: [
        (50, {"char": "!", "name": "Light Potion", "fg": (220, 80, 60), "type": "potion", "heal": 12}),
        (25, {"char": "/", "name": "Bronze Sword", "fg": (200, 160, 60), "type": "weapon", "power_bonus": 2}),
        (13, {"char": "[", "name": "Leather Armor", "fg": (140, 100, 60), "type": "armor", "defense_bonus": 1}),
        (5, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (7, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
    ],
    3: [
        (45, {"char": "!", "name": "Potion", "fg": (230, 100, 80), "type": "potion", "heal": 16}),
        (23, {"char": "/", "name": "Iron Blade", "fg": (190, 190, 200), "type": "weapon", "power_bonus": 3}),
        (17, {"char": "[", "name": "Chain Mail", "fg": (170, 170, 180), "type": "armor", "defense_bonus": 2}),
        (7, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (8, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
    ],
    4: [
        (42, {"char": "!", "name": "Strong Potion", "fg": (240, 120, 100), "type": "potion", "heal": 22}),
        (22, {"char": "/", "name": "Steel Sword", "fg": (200, 200, 220), "type": "weapon", "power_bonus": 4}),
        (17, {"char": "[", "name": "Plate Armor", "fg": (180, 180, 200), "type": "armor", "defense_bonus": 3}),
        (9, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (10, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
    ],
    5: [
        (40, {"char": "!", "name": "Greater Potion", "fg": (255, 140, 120), "type": "potion", "heal": 28}),
        (22, {"char": "/", "name": "Radiant Blade", "fg": (255, 240, 140), "type": "weapon", "power_bonus": 5}),
        (17, {"char": "[", "name": "Light Ward Armor", "fg": (240, 230, 140), "type": "armor", "defense_bonus": 3}),
        (10, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (11, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
    ],
    6: [
        (35, {"char": "!", "name": "Superior Potion", "fg": (255, 160, 200), "type": "potion", "heal": 35}),
        (20, {"char": "/", "name": "Form Slicer", "fg": (180, 100, 255), "type": "weapon", "power_bonus": 6}),
        (20, {"char": "[", "name": "Ideal Shield Armor", "fg": (120, 200, 255), "type": "armor", "defense_bonus": 4}),
        (12, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (13, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
    ],
    7: [
        (33, {"char": "!", "name": "Noumenal Elixir", "fg": (255, 220, 180), "type": "potion", "heal": 45}),
        (20, {"char": "/", "name": "Truth Seeker Blade", "fg": (255, 240, 200), "type": "weapon", "power_bonus": 7}),
        (20, {"char": "[", "name": "Transcendent Plate", "fg": (255, 255, 220), "type": "armor", "defense_bonus": 5}),
        (13, {"char": "~", "name": "Wand", "fg": (100, 255, 255), "type": "wand", "charges": 3}),
        (14, {"char": "?", "name": "Scroll", "fg": (200, 200, 150), "type": "scroll"}),
    ],
}


def get_items(depth: int) -> list[tuple[int, dict]]:
    """Return item table for a given depth."""
    depth = max(1, min(7, depth))
    return [(w, t.copy()) for w, t in ITEM_TABLE[depth]]


def pick_weighted(table: list[tuple[int, dict]]) -> dict:
    """Pick a random entry from a weighted table, returning a copy of the template."""
    weights = [w for w, _ in table]
    templates = [t for _, t in table]
    chosen = random.choices(templates, weights=weights, k=1)[0]
    return chosen.copy()


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
]

CHAMPION_TINT = (40, 30, -20)  # gold tint


# ── Item Affixes ──────────────────────────────────────────────

ITEM_PREFIXES: list[dict] = [
    {"name": "Gleaming", "power_bonus": 1, "defense_bonus": 0, "heal_mult": 1.0, "charges": 0},
    {"name": "Sturdy", "power_bonus": 0, "defense_bonus": 1, "heal_mult": 1.0, "charges": 0},
    {"name": "Ancient", "power_bonus": 2, "defense_bonus": 0, "heal_mult": 1.0, "charges": 0},
    {"name": "Cursed", "power_bonus": 3, "defense_bonus": -1, "heal_mult": 1.0, "charges": 0},
    {"name": "Blessed", "power_bonus": 0, "defense_bonus": 0, "heal_mult": 1.5, "charges": 0},
    {"name": "Volatile", "power_bonus": 0, "defense_bonus": 0, "heal_mult": 1.0, "charges": 1},
]

ITEM_SUFFIXES: list[dict] = [
    {"name": "of Wrath", "power_bonus": 2, "defense_bonus": 0, "heal_bonus": 0, "charges": 0},
    {"name": "of the Guardian", "power_bonus": 0, "defense_bonus": 2, "heal_bonus": 0, "charges": 0},
    {"name": "of Vitality", "power_bonus": 0, "defense_bonus": 0, "heal_bonus": 5, "charges": 0},
    {"name": "of the Phoenix", "power_bonus": 0, "defense_bonus": 0, "heal_bonus": 10, "charges": 0},
    {"name": "of Thorns", "power_bonus": 0, "defense_bonus": 0, "heal_bonus": 0, "charges": 0},
    {"name": "of Animation", "power_bonus": 0, "defense_bonus": 0, "heal_bonus": 0, "charges": 1},
]


# ── Player Traits ─────────────────────────────────────────────

PLAYER_TRAITS: list[dict] = [
    {"name": "Scholar", "max_hp": 20, "power": 0, "defense": 0, "wand_charges": 0, "extra_item": False},
    {"name": "Warrior", "max_hp": 0, "power": 2, "defense": 0, "wand_charges": 0, "extra_item": False},
    {"name": "Sentinel", "max_hp": 0, "power": 0, "defense": 2, "wand_charges": 0, "extra_item": False},
    {"name": "Mystic", "max_hp": 0, "power": 0, "defense": 0, "wand_charges": 2, "extra_item": False},
    {"name": "Scavenger", "max_hp": 0, "power": 0, "defense": 0, "wand_charges": 0, "extra_item": True},
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
    """Return a random wand type for the given depth. Deeper = more variety."""
    depth = max(1, min(7, depth))
    available = min(1 + depth, len(WAND_TYPES))
    wand = random.choice(WAND_TYPES[:available])
    return wand.copy()


# ── Scroll Types ──────────────────────────────────────────────

SCROLL_TYPES: list[dict] = [
    {"scroll_id": "mapping", "name": "Scroll of Mapping", "fg": (200, 220, 150)},
    {"scroll_id": "teleportation", "name": "Scroll of Teleportation", "fg": (100, 200, 255)},
    {"scroll_id": "fear", "name": "Scroll of Fear", "fg": (255, 180, 100)},
    {"scroll_id": "mending", "name": "Scroll of Mending", "fg": (100, 255, 150)},
    {"scroll_id": "imperative", "name": "Scroll of Imperative", "fg": (255, 150, 150)},
    {"scroll_id": "transcendence", "name": "Scroll of Transcendence", "fg": (220, 180, 255)},
]


def generate_random_scroll() -> dict:
    """Return a random scroll type."""
    scroll = random.choice(SCROLL_TYPES)
    return scroll.copy()


# ── XP & Leveling ────────────────────────────────────────────

XP_THRESHOLDS: list[int] = [0, 0, 30, 80, 160, 280, 440, 650, 920, 1250, 1650]


# ── Flavor Text ──────────────────────────────────────────────

ATMOSPHERE_MESSAGES: dict[int, list[str]] = {
    1: [
        "The shadows whisper of things beyond perception.",
        "A cold draft carries the scent of forgotten knowledge.",
        "The darkness here feels almost purposeful.",
        "You sense the boundary between appearance and reality.",
        "Something stirs in the phenomenal depths.",
        "The cave breathes with an intelligence you cannot name.",
    ],
    2: [
        "Flames dance without fuel, pure form without substance.",
        "The heat here is more concept than sensation.",
        "Smoke traces patterns that almost resolve into meaning.",
        "Fire illuminates only to deepen the surrounding mystery.",
        "The flickering light reveals and conceals in equal measure.",
        "Embers drift upward as if seeking their own first cause.",
    ],
    3: [
        "Echoes of your steps return changed, distorted.",
        "The gallery walls seem to observe your passage.",
        "Shadows here move with deliberate intent.",
        "You feel the weight of unasked questions.",
        "The silence between sounds carries its own meaning.",
        "Something watches from beyond the veil of sense.",
    ],
    4: [
        "The passage narrows like a closing argument.",
        "Stone presses close, whispering of necessary limits.",
        "Each step forward is a small act of pure reason.",
        "The walls channel your will toward a single direction.",
        "Dust motes hang suspended, indifferent to time.",
        "The earth groans with the weight of hidden truths.",
    ],
    5: [
        "The light here burns with the intensity of pure reason.",
        "Brightness scours away comfortable illusions.",
        "You squint against truths too brilliant to face directly.",
        "The radiance strips bare every comfortable deception.",
        "Light and understanding merge into a single blinding force.",
    ],
    6: [
        "Reality here feels more real than the surface world.",
        "Perfect geometric forms shimmer at the edge of vision.",
        "The ideal presses against the merely actual.",
        "You walk among archetypes, not their pale copies.",
        "Each form here is a universal made particular.",
        "The boundary between thought and thing dissolves.",
    ],
    7: [
        "You stand at the threshold of the thing-in-itself.",
        "The noumenal realm resists comprehension by design.",
        "Categories of understanding strain and buckle here.",
        "What lies beyond phenomena cannot be spoken, only approached.",
        "The ground of all being hums beneath your feet.",
        "You sense the unconditioned condition of all that is.",
    ],
}

ATTACK_VERBS_PLAYER: list[str] = [
    "strike", "slash", "smash", "cut", "cleave", "rend",
]

ATTACK_VERBS_MONSTER: list[str] = [
    "claws at", "bites", "strikes", "lunges at", "tears at", "slashes",
]

DEATH_MESSAGES_MONSTER: list[str] = [
    "{name} dissolves into shadow.",
    "{name} collapses into nothing.",
    "{name} shatters like a broken idea.",
    "{name} fades from existence.",
    "{name} crumbles to phenomenal dust.",
]

DEATH_MESSAGES_PLAYER: list[str] = [
    "The shadows claim you.",
    "You dissolve into the noumenal void.",
    "Consciousness fades beyond the veil.",
    "The cave swallows your understanding.",
]

TRAIT_DESCRIPTIONS: dict[str, str] = {
    "Scholar": "A keen mind grants resilience against the unknown. +20 max HP.",
    "Warrior": "Combat mastery born of disciplined will. +2 ATK.",
    "Sentinel": "Unyielding defense, immovable as the categorical. +2 DEF.",
    "Mystic": "Deep arcane affinity channels wand energies. +2 wand charges.",
    "Scavenger": "Resourceful pragmatism finds use in all things. Extra starting item.",
}
