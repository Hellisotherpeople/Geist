import tcod
import tcod.event
import tcod.map
import tcod.noise
import numpy as np
import random 
from enum import Enum
import time
import sys

class GameStates(Enum):
    PLAYERS_TURN = 1
    ENEMY_TURN = 2
    PLAYER_DEAD = 3

class RenderOrder(Enum):
    CORPSE = 1
    ITEM = 2 
    ACTOR = 3


room_max_size = 15
room_min_size = 2
max_rooms = 300

gm_width = 100
gm_height = 100

screen_width = gm_width + 50
screen_height = gm_height

tcod.default_fg = [1, 3, 1]


### ~~~~~ Entity ~~~~~ ### 

class Entity:
    #this is a generic Entity: the player, a monster, an item, the stairs...
    #it's always represented by a character on screen.
    #IDEAS 
    # - Make color of character be denoted by its HP
    # - Make items have random buffs or debuffs each playthrough (or even special abilities)
    # - Make a "Varient" system for items and monsters
    # - Include special unique items and monsters
    # - All entities will be potentiall turned sentient
    def __init__(self, x, y, char, name, fg_color = [0,0,0], bg_color = [0,0,0], blocks = False, 
    fighter = True, ai = None, hp = [0,0,0,0,0], attack_power = 0, render_order = RenderOrder.ACTOR):
        self.x = x
        self.y = y
        self.char = char
        self.fg_color = fg_color # Tuple of rgb
        self.bg_color = bg_color
        self.blocks = blocks
        self.name = name
        self.fighter = True ## Can you fight people?
        self.ai = ai ## Can be a string indicating what type of AI this will have
        ### I intend for all AI to be potentially sentient (vicious potion running at you!) 
        self.hp = hp
        self.attack_power = attack_power ## should be 0 unless its now alive
        self.render_order = render_order

    def move(self, dx, dy):
        #move by the given amount
        self.x += dx
        self.y += dy
    
    def move_to_position(self, new_x, new_y):
        self.x = new_x
        self.y = new_y
 
    def draw(self):
        if 0 <= self.y < gm_width:
            if 0 <= self.x < gm_height:
                is_visable = game_map.fov[self.x][self.y]
                if is_visable:
                    ##Color based on health left? 
                    rand_red_char_fg = random.randint(self.fg_color[0], 255)
                    modified_red_color = self.fg_color[0] + rand_red_char_fg
                    mod_color = [modified_red_color, self.fg_color[1], self.fg_color[2]]
                    root_console.tiles_rgb[self.x, self.y] = self.char, mod_color, self.bg_color
 
    def clear(self):
        #erase the character that represents this Entity
        root_console.put_char(self.x, self.y, ch = 0, bg_blend = 5)

    def kill_entity(self):
        if self.name == "Player":
            self.char = ord("D")
            print("You died!")
            time.sleep(2)
            quit()
        else:
            print('{0} has died!'.format(self.name))
            self.char = ord("%")
            self.blocks = False
            self.fighter = None
            self.ai = None
            self.name = 'remains of ' + self.name
            self.render_order = RenderOrder.CORPSE
            return None

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.kill_entity()

    def attack(self, target):
        damage = self.attack_power
        target.take_damage(damage)
        print('{0} attacks {1} for {2} hit points.'.format(self.name, target.name, str(damage)))
        

    def take_turn(self, d_map):
        if self.ai == "Basic":
            print('The ' + self.name + ' wonders when it will get to move.')

        elif self.ai == "Dijkstra": ### DIJKSTRA MAPS :D 
            path = tcod.path.hillclimb2d(d_map, (self.x, self.y), True, True) ## Climb the hill
            #print("My current position: " + str(self.x) + " " + str(self.y))
            if len(path) > 1:
                can_x = path[1][0]
                can_y = path[1][1]
                #print(path)
                if 0 <= can_x < gm_width:
                    if 0 <= can_y < gm_height:
                        is_walkable = game_map.walkable[can_x][can_y]
                        is_visable = game_map.fov[can_x][can_y]
                        if is_visable:
                            if is_walkable:
                                possible_entity = get_blocking_entities_at_location(Entitys, can_x, can_y)
                                if possible_entity: ##Are we gonna hit anything?
                                    #self.move_to_position(can_x, can_y)
                                    self.attack(possible_entity)
                                else:
                                    self.move_to_position(can_x, can_y)
                            else:
                                pass
                                #print("The " + self.name + " can't move towards you!")
                        else:
                            pass
                            #print("The " + self.name + " can't see me!")



def get_blocking_entities_at_location(entities, destination_x, destination_y):
    for entity in entities:
        if entity.blocks and entity.x == destination_x and entity.y == destination_y:
            return entity
    return None


### ~~~~~~~~~ Initialize Entities ~~~~~~ ##### 



ai_dist = []

### ~~~~~ Event dispatch ~~~~~~ 

class State(tcod.event.EventDispatch):


    def __init__(self):
        self.Entitys_list = Entitys 
        self.player_Entity = Entitys[0]
        self.turn = GameStates.PLAYERS_TURN 

    def ev_quit(self, event):
        raise SystemExit()

    def compute_move(self, dx, dy):
        if self.turn == GameStates.PLAYERS_TURN:
            player_x_pos = self.player_Entity.x
            player_y_pos = self.player_Entity.y 
            ch_x = player_x_pos + dx
            ch_y = player_y_pos + dy
            if 0 <= ch_x < gm_width:
                if 0 <= ch_y < gm_height:
                    is_walkable = game_map.walkable[ch_x][ch_y]
                    if is_walkable:
                        target = get_blocking_entities_at_location(Entitys, ch_x, ch_y) ### check if there is an enemy
                        if target:
                            self.player_Entity.attack(target)
                        else: ### No entity that blocks, move
                            self.player_Entity.move(dx, dy)
                            player_x_pos = self.player_Entity.x
                            player_y_pos = self.player_Entity.y 
                            ## TODO: Write a function which put_chars the numbers of the distances to visualize 
                            game_map.compute_fov(player_x_pos,  player_y_pos, light_walls = True, radius = 20, algorithm= 12)
                            #dist = tcod.path.maxarray((gm_width, gm_height), dtype = np.int32, order = "F") ## every type of movement should cost the same 
                            #dist[player_y_pos, player_x_pos] = 0 
                            #tcod.path.dijkstra2d(dist, cost_map, 1, 1)
                            #print(dist) ## Good print 
                            #print("player_x_pos" + str(player_x_pos))
                            #print("player_y_pos" + str(player_y_pos))
            self.turn = GameStates.ENEMY_TURN
        

    def ev_keydown(self, event):

        if event.sym == tcod.event.K_UP or event.sym == tcod.event.K_KP_8: ## up key
            dx = 0
            dy = -1
            self.compute_move(dx, dy)
        elif event.sym == tcod.event.K_DOWN or event.sym == tcod.event.K_KP_2: ## down key 
            dx = 0
            dy = 1
            self.compute_move(dx, dy)
        elif event.sym == tcod.event.K_LEFT or event.sym == tcod.event.K_KP_4: ## left key 
            dx = -1
            dy = 0
            self.compute_move(dx, dy)
        elif event.sym == tcod.event.K_RIGHT or event.sym == tcod.event.K_KP_6: ## right key
            dx = 1
            dy = 0
            self.compute_move(dx, dy)
        elif event.sym == tcod.event.K_KP_1: 
            dx = -1
            dy = 1
            self.compute_move(dx, dy)
        elif event.sym == tcod.event.K_KP_3:
            dx = 1
            dy = 1
            self.compute_move(dx, dy)
        elif event.sym == tcod.event.K_KP_7:
            dx = -1
            dy = -1
            self.compute_move(dx, dy)
        elif event.sym == tcod.event.K_KP_9:
            dx = 1
            dy = -1
            self.compute_move(dx, dy)

    def ev_mousebuttondown(self, event):
        pass
        #print(event)

    def ev_mousemotion(self, event):
        pass
        #print(event)


#### ~~~~ Dungeon Generation and placement of enemies ~~~~~~~~ #####

class Rect:
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
    
    def center(self):
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)
        return (center_x, center_y)

    def intersect(self, other):
        # returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

def create_room(room):
    # go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            game_map.walkable[x][y] = True
            game_map.transparent[x][y] = True

def create_h_tunnel(x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        game_map.walkable[x][y] = True
        game_map.transparent[x][y] = True

def create_v_tunnel(y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        game_map.walkable[x][y] = True
        game_map.transparent[x][y] = True


game_map = tcod.map.Map(width = gm_width, height = gm_height, order="F")
game_map.walkable[:] = False
game_map.transparent[:] = False
game_map.explored = game_map.walkable[:].copy() ## initialize explroed tiles to be false
print(game_map.explored)

print(game_map.explored)

player = None

def dungeon_generate(game_map, entities, number_of_monsters, noise = None):

    
    noise = tcod.noise.Noise(
    dimensions=2,
    algorithm=tcod.NOISE_SIMPLEX,
    implementation=tcod.noise.TURBULENCE,
    hurst=0.5,
    lacunarity=2.0,
    octaves=4,
    seed=None,
    )

    ogrid = [np.arange(game_map.width, dtype=np.float32),
         np.arange(game_map.height, dtype=np.float32)]

    samples = noise.sample_ogrid(ogrid)

    troll_number = 0
    goblin_number = 0

    first_room = Rect(10, 10, 5, 5)
    rooms = [first_room]
    num_rooms = 0

    for i in range(max_rooms):
        w = random.randint(room_min_size, room_max_size)
        h = random.randint(room_min_size, room_max_size)
        x = random.randint(0, game_map.width - w - 1)
        y = random.randint(0, game_map.height - h - 1)
        new_room = Rect(x, y, w, h)
        for other_room in rooms:
            if new_room.intersect(other_room):
                break
            else:
                create_room(new_room)
                (new_x, new_y) = new_room.center()
                if num_rooms == 0:
                    num_rooms += 1
                    player_str_x = new_x
                    player_str_y = new_y
                    # this is the first room, where the player starts at
                    player = Entity(new_x, new_y, ord("@"), name = "Player", fighter = True, blocks = True, hp = 100, attack_power=1, render_order = RenderOrder.ACTOR)
                    entities.append(player)
    if noise:
        for y in range(game_map.height):
            for x in range(game_map.width):
                walkable = game_map.walkable[x][y]
                if samples[x][y] < 0.40 and walkable == False:
                    game_map.walkable[x][y] = True
                    game_map.transparent[x][y] = True
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
        

Entitys = []
dungeon_generate(game_map = game_map, entities = Entitys, number_of_monsters = 5, noise = True)

print(Entitys)

cost_map = game_map.walkable.astype(int, order= "F") ## just convert walls to be impassable for now 
dist = tcod.path.maxarray((gm_width, gm_height), dtype = np.int32, order = "F") ## every type of movement should cost the same 
tcod.path.dijkstra2d(dist, cost_map, 1, 1)

state = State()


#### ~~~~ Render Functions ~~~~~~~~~ ########

def render_all(entities, screen_width, screen_height):

    v_dijksta = False ## This only works when there is only one distance value
    for x in range(game_map.width):
        for y in range(game_map.height):
            is_walkable = game_map.walkable[x][y]
            is_visable = game_map.fov[x][y]
            explored = game_map.explored[x][y]

            if is_visable:
                rand_red = random.randint(100, 255)
                rand_red_wall = random.randint(0,50)
                game_map.explored[x][y] = True
                if is_walkable:
                    if v_dijksta:
                        dijkstra_dist_int = dist[x][y]
                        if dijkstra_dist_int < 10:
                            ord_char = ord(dijkstra_dist_int.astype(str))
                        else:
                            ord_char = ord("_")
                        root_console.tiles_rgb[x, y] = ord_char, (rand_red, 0, 255), (0, 0, 0)
                    else:
                        root_console.tiles_rgb[x, y] = ord("_"), (rand_red, 0, 255), (0, 0, 0) ## Floors 
                else:
                    root_console.tiles_rgb[x, y] = ord("#"), (255, 0, 40), (rand_red_wall, 0, 0)

            elif explored:
                if is_walkable:
                    root_console.tiles_rgb[x, y] = ord("_"), (200, 100, 100), (10, 10, 10)
                else:
                    root_console.tiles_rgb[x, y] = ord("#"), (200, 100, 100), (10, 10, 10)
            else:
                if is_walkable:
                    root_console.tiles_rgb[x, y] = ord(" "), (0, 0, 0), (0, 0, 0)
                else:
                    root_console.tiles_rgb[x, y] = ord(" "), (0, 0, 0), (0, 0, 0)
                #pass

    # Draw all entities in the list

    entities_in_render_order = sorted(entities, key = lambda x: x.render_order.value)
    for entity in entities_in_render_order:
        entity.draw()

    #root_console.print_ex

    root_console.blit(root_console, 0, 0, screen_width, screen_height, 0, 0, 0)


def clear_all(entities):
    for entity in entities:
        entity.clear()


print(Entitys[0])
# The main game loop, doing console stuff 
with tcod.console_init_root(screen_width, screen_height, order="F") as root_console:
    root_console.draw_frame(x = 1, y = 0, width = gm_width, height = gm_height, bg = (200, 20, 20)) ## Seperater
    root_console.print_box(x = 103, y = 5, width = 40, height = 1, string = ("UI under construction"), bg = (200, 20, 20) )
    #root_console.draw_rect(x = 101, y= 50, width = 10, height = 1, ch = ord("n"))
    while True:
        render_all(Entitys, gm_width, gm_height)
        tcod.console_flush()  # Show the console. 
        clear_all(Entitys)
        for event in tcod.event.wait():
            the_ev = state.dispatch(event)
            if event.type == "QUIT":
                raise SystemExit()
        if state.turn == GameStates.ENEMY_TURN:
            player_ent = Entitys[0]
            player_x = player_ent.x
            player_y = player_ent.y 
            ### Compute the Dijkstra Map
            dist = tcod.path.maxarray((gm_width, gm_height), dtype = np.int32, order = "F")  ##Compute distance array, modified in place
            dist[player_x, player_y] = 0  ## For now, monster just wants to hunt the player 
            dist[50, 50] = 1 ## Testing the desire driven AI part of this, it works! 
            tcod.path.dijkstra2d(dist, cost_map, 1, 1) ## Compute the map 
            for entity in Entitys:
                if entity != player:

                    entity.take_turn(d_map = dist)
            state.turn = GameStates.PLAYERS_TURN



    # The libtcod window will be closed at the end of this with-block.