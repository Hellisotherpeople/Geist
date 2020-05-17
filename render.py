import g
import random

def render_all(entities, screen_width, screen_height):

    v_dijksta = False ## This only works when there is only one distance value
    for x in range(g.game_map.width):
        for y in range(g.game_map.height):
            is_walkable = g.game_map.walkable[x][y]
            is_visable = g.game_map.fov[x][y]
            explored = g.game_map.explored[x][y]

            if is_visable:
                rand_red = random.randint(100, 255)
                rand_red_wall = random.randint(0,50)
                g.game_map.explored[x][y] = True
                if is_walkable:
                    if v_dijksta:
                        dijkstra_dist_int = g.dist[x][y]
                        if dijkstra_dist_int < 10:
                            ord_char = ord(dijkstra_dist_int.astype(str))
                        else:
                            ord_char = ord("_")
                        g.root_console.tiles_rgb[x, y] = ord_char, (rand_red, 0, 255), (0, 0, 0)
                    else:
                        g.root_console.tiles_rgb[x, y] = ord("_"), (rand_red, 0, 255), (0, 0, 0) ## Floors 
                else:
                    g.root_console.tiles_rgb[x, y] = ord("#"), (255, 0, 40), (rand_red_wall, 0, 0)

            elif explored:
                if is_walkable:
                    g.root_console.tiles_rgb[x, y] = ord("_"), (200, 100, 100), (10, 10, 10)
                else:
                    g.root_console.tiles_rgb[x, y] = ord("#"), (200, 100, 100), (10, 10, 10)
            else:
                if is_walkable:
                    g.root_console.tiles_rgb[x, y] = ord(" "), (0, 0, 0), (0, 0, 0)
                else:
                    g.root_console.tiles_rgb[x, y] = ord(" "), (0, 0, 0), (0, 0, 0)
                #pass

    # Draw all entities in the list

    entities_in_render_order = sorted(entities, key = lambda x: x.render_order.value)
    for entity in entities_in_render_order:
        entity.draw()

    #root_console.print_ex

    g.root_console.blit(g.root_console, 0, 0, screen_width, screen_height, 0, 0, 0)


def clear_all(entities):
    for entity in entities:
        entity.clear()

