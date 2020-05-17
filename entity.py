from enum import Enum
import g
import random
import tcod
import time

class RenderOrder(Enum):
    CORPSE = 1
    ITEM = 2 
    ACTOR = 3

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
        if 0 <= self.y < g.gm_width:
            if 0 <= self.x < g.gm_height:
                is_visable = g.game_map.fov[self.x][self.y]
                if is_visable:
                    ##Color based on health left? 
                    rand_red_char_fg = random.randint(self.fg_color[0], 255)
                    modified_red_color = self.fg_color[0] + rand_red_char_fg
                    mod_color = [modified_red_color, self.fg_color[1], self.fg_color[2]]
                    g.root_console.tiles_rgb[self.x, self.y] = self.char, mod_color, self.bg_color
 
    def clear(self):
        #erase the character that represents this Entity
        g.root_console.put_char(self.x, self.y, ch = 0, bg_blend = 5)

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
                if 0 <= can_x < g.gm_width:
                    if 0 <= can_y < g.gm_height:
                        is_walkable = g.game_map.walkable[can_x][can_y]
                        is_visable = g.game_map.fov[can_x][can_y]
                        if is_visable:
                            if is_walkable:
                                possible_entity = get_blocking_entities_at_location(g.Entitys, can_x, can_y)
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