import tcod
import g
import numpy as np
import random
import rect
from entity import Entity, RenderOrder

def dungeon_generate(game_map, entities, number_of_monsters, noise = None):

    
    noise = tcod.noise.Noise(dimensions=2, algorithm=tcod.NOISE_SIMPLEX, implementation=tcod.noise.TURBULENCE, 
    hurst=0.5, lacunarity=2.0, octaves=4, seed=None)

    ogrid = [np.arange(game_map.width, dtype=np.float32),
         np.arange(game_map.height, dtype=np.float32)]

    samples = noise.sample_ogrid(ogrid)

    troll_number = 0
    goblin_number = 0

    first_room = rect.Rect(10, 10, 5, 5)
    rooms = [first_room]
    num_rooms = 0

    for i in range(g.max_rooms):
        w = random.randint(g.room_min_size, g.room_max_size)
        h = random.randint(g.room_min_size, g.room_max_size)
        x = random.randint(0, g.game_map.width - w - 1)
        y = random.randint(0, g.game_map.height - h - 1)
        new_room = rect.Rect(x, y, w, h)
        for other_room in rooms:
            if new_room.intersect(other_room):
                break
            else:
                rect.create_room(new_room)
                (new_x, new_y) = new_room.center()
                if num_rooms == 0:
                    num_rooms += 1
                    player_str_x = new_x
                    player_str_y = new_y
                    # this is the first room, where the player starts at
                    player = Entity(new_x, new_y, ord("@"), name = "Player", fighter = True, blocks = True, hp = 100, attack_power=1, render_order = RenderOrder.ACTOR)
                    entities.append(player)
    if noise:
        for y in range(g.game_map.height):
            for x in range(g.game_map.width):
                walkable = g.game_map.walkable[x][y]
                if samples[x][y] < 0.40 and walkable == False:
                    g.game_map.walkable[x][y] = True
                    g.game_map.transparent[x][y] = True
                if y != player_str_y and x != player_str_x:
                    if random.randint(0, 10000) >= 9980 and walkable: ## do we place a monster?
                        if random.randint(0, 100) <= 80:
                            troll_number += 1
                            t_name = "Troll " + str(troll_number)
                            monster = Entity(x, y, ord("T"), name = t_name, blocks = True, fighter = True, fg_color = [0, 100, 200], ai = "Dijkstra", attack_power = 1, hp = 1, render_order = RenderOrder.ACTOR)
                        else:
                            goblin_number += 1
                            g_name = "Goblin " + str(goblin_number)
                            monster = Entity(x, y, ord("G"), name = g_name, blocks = True, fighter = True, fg_color = [10, 200, 0], ai = "Dijkstra", attack_power = 2, hp = 2, render_order = RenderOrder.ACTOR)
                        entities.append(monster)