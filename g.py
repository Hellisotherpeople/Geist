### Initalize global variables used by the game
from enum import Enum


class GameStates(Enum):
    PLAYERS_TURN = 1
    ENEMY_TURN = 2
    PLAYER_DEAD = 3

root_console = None

game_map = []

Entitys = [] 

room_max_size = 15
room_min_size = 2
max_rooms = 300

gm_width = 100
gm_height = 100

screen_width = gm_width + 50
screen_height = gm_height

dist = [] ## Dijkstra Distance Maps

