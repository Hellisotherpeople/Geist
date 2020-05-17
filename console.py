import tcod
import tcod.event
import tcod.map
import tcod.noise
import numpy as np
import random 
from enum import Enum
import time
import sys
from entity import Entity
from state import State
import g 
import rect
import render
import dungeon_gen

tcod.default_fg = [1, 3, 1]

ai_dist = []

#### ~~~~ Dungeon Generation and placement of enemies ~~~~~~~~ #####


game_map = tcod.map.Map(width = g.gm_width, height = g.gm_height, order="F")
game_map.walkable[:] = False
game_map.transparent[:] = False
game_map.explored = game_map.walkable[:].copy() ## initialize explroed tiles to be false

g.game_map = game_map 

player = None        

Entitys = []
dungeon_gen.dungeon_generate(game_map = game_map, entities = Entitys, number_of_monsters = 5, noise = True)

g.Entitys = Entitys

cost_map = game_map.walkable.astype(int, order= "F") ## just convert walls to be impassable for now 
dist = tcod.path.maxarray((g.gm_width, g.gm_height), dtype = np.int32, order = "F") ## every type of movement should cost the same 
g.dist = dist

tcod.path.dijkstra2d(g.dist, cost_map, 1, 1)

state = State()


# The main game loop, doing console stuff 
with tcod.console_init_root(g.screen_width, g.screen_height, order="F") as root_console:
    g.root_console = root_console
    root_console.draw_frame(x = 1, y = 0, width = g.gm_width, height = g.gm_height, bg = (200, 20, 20)) ## Seperater
    root_console.print_box(x = 103, y = 5, width = 40, height = 1, string = ("UI under construction"), bg = (200, 20, 20) )
    #root_console.draw_rect(x = 101, y= 50, width = 10, height = 1, ch = ord("n"))
    while True:
        render.render_all(g.Entitys, g.gm_width, g.gm_height)
        tcod.console_flush()  # Show the console. 
        render.clear_all(g.Entitys)
        for event in tcod.event.wait():
            the_ev = state.dispatch(event)
            if event.type == "QUIT":
                raise SystemExit()
        if state.turn == g.GameStates.ENEMY_TURN:
            player_ent = g.Entitys[0]
            player_x = player_ent.x
            player_y = player_ent.y 
            ### Compute the Dijkstra Map
            g.dist = tcod.path.maxarray((g.gm_width, g.gm_height), dtype = np.int32, order = "F")  ##Compute distance array, modified in place
            g.dist[player_x, player_y] = 0  ## For now, monster just wants to hunt the player 
            g.dist[50, 50] = 1 ## Testing the desire driven AI part of this, it works! 
            tcod.path.dijkstra2d(g.dist, cost_map, 1, 1) ## Compute the map 
            for entity in g.Entitys:
                if entity != player:
                    entity.take_turn(d_map = g.dist)
            state.turn = g.GameStates.PLAYERS_TURN



    # The libtcod window will be closed at the end of this with-block.