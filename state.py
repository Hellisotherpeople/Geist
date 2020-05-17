from enum import Enum
import g
import random
import tcod
import time
import entity


#### This is where we handle key presses


class State(tcod.event.EventDispatch):
    def __init__(self):
        self.Entitys_list = g.Entitys 
        self.player_Entity = g.Entitys[0]
        self.turn = g.GameStates.PLAYERS_TURN 

    def ev_quit(self, event):
        raise SystemExit()

    def compute_move(self, dx, dy):
        if self.turn == g.GameStates.PLAYERS_TURN:
            player_x_pos = self.player_Entity.x
            player_y_pos = self.player_Entity.y 
            ch_x = player_x_pos + dx
            ch_y = player_y_pos + dy
            if 0 <= ch_x < g.gm_width:
                if 0 <= ch_y < g.gm_height:
                    is_walkable = g.game_map.walkable[ch_x][ch_y]
                    if is_walkable:
                        target = entity.get_blocking_entities_at_location(g.Entitys, ch_x, ch_y) ### check if there is an enemy
                        if target:
                            self.player_Entity.attack(target)
                        else: ### No entity that blocks, move
                            self.player_Entity.move(dx, dy)
                            player_x_pos = self.player_Entity.x
                            player_y_pos = self.player_Entity.y 
                            g.game_map.compute_fov(player_x_pos,  player_y_pos, light_walls = True, radius = 20, algorithm= 12)
                            #dist = tcod.path.maxarray((gm_width, gm_height), dtype = np.int32, order = "F") ## every type of movement should cost the same 
                            #dist[player_y_pos, player_x_pos] = 0 
                            #tcod.path.dijkstra2d(dist, cost_map, 1, 1)
                            #print(dist) ## Good print 
                            #print("player_x_pos" + str(player_x_pos))
                            #print("player_y_pos" + str(player_y_pos))
            self.turn = g.GameStates.ENEMY_TURN
        

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


