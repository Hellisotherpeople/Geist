"""Layout generators for dungeon variety. Each generator carves into pre-zeroed
walkable/transparent arrays and returns a list of Rect rooms."""

import math
import random

import numpy as np
import tcod.bsp
import tcod.noise
from tcod import libtcodpy

from dungeon import Rect

# ── Helpers ───────────────────────────────────────────────────

def _carve(walkable, transparent, x, y):
    if 0 <= x < walkable.shape[0] and 0 <= y < walkable.shape[1]:
        walkable[x, y] = True
        transparent[x, y] = True


def _carve_rect(walkable, transparent, rect):
    """Carve the inner tiles of a Rect."""
    walkable[rect.x1 + 1:rect.x2, rect.y1 + 1:rect.y2] = True
    transparent[rect.x1 + 1:rect.x2, rect.y1 + 1:rect.y2] = True


def _carve_h_tunnel(walkable, transparent, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        _carve(walkable, transparent, x, y)


def _carve_v_tunnel(walkable, transparent, y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        _carve(walkable, transparent, x, y)


def _l_tunnel(walkable, transparent, x1, y1, x2, y2, rng):
    """Carve an L-shaped tunnel between two points."""
    if rng.random() < 0.5:
        _carve_h_tunnel(walkable, transparent, x1, x2, y1)
        _carve_v_tunnel(walkable, transparent, y1, y2, x2)
    else:
        _carve_v_tunnel(walkable, transparent, y1, y2, x1)
        _carve_h_tunnel(walkable, transparent, x1, x2, y2)


def _find_virtual_rooms(walkable, width, height):
    """Scan walkable area in ~12x12 grid chunks and find the largest
    axis-aligned rectangle fully within walkable area per chunk.
    Returns list of Rect, sorted so closest-to-center is first."""
    rooms = []
    cx, cy = width // 2, height // 2
    step = 12

    for gx in range(1, width - 1, step):
        for gy in range(1, height - 1, step):
            best_area = 0
            best_rect = None
            ex = min(gx + step, width - 1)
            ey = min(gy + step, height - 1)
            # Try all possible rectangles in this chunk (brute force small area)
            for rx in range(gx, ex):
                for ry in range(gy, ey):
                    if not walkable[rx, ry]:
                        continue
                    # Expand right and down from (rx, ry)
                    max_w = 0
                    for tx in range(rx, ex):
                        if not walkable[tx, ry]:
                            break
                        max_w = tx - rx + 1
                    # Now try expanding height
                    for rh in range(1, ey - ry + 1):
                        # Check full row at ry + rh - 1
                        row_ok = True
                        cur_w = max_w
                        for tx in range(rx, rx + cur_w):
                            if not walkable[tx, ry + rh - 1]:
                                cur_w = tx - rx
                                break
                        if cur_w < 2:
                            break
                        max_w = cur_w
                        area = max_w * rh
                        if area > best_area and max_w >= 2 and rh >= 2:
                            best_area = area
                            # Store as Rect (x, y, w, h) where inner = (x1+1..x2, y1+1..y2)
                            # We want inner_tiles to match walkable, so set coords such that
                            # inner = rx..rx+max_w-1, ry..ry+rh-1
                            best_rect = Rect(rx - 1, ry - 1, max_w + 1, rh + 1)
            if best_rect and best_area >= 4:
                rooms.append(best_rect)

    if not rooms:
        # Fallback: find any walkable tile and make a tiny room
        for x in range(1, width - 1):
            for y in range(1, height - 1):
                if walkable[x, y]:
                    rooms.append(Rect(x - 1, y - 1, 3, 3))
                    if len(rooms) >= 8:
                        break
            if len(rooms) >= 8:
                break

    # Sort so closest-to-center is rooms[0]
    rooms.sort(key=lambda r: abs(r.center()[0] - cx) + abs(r.center()[1] - cy))

    # Ensure minimum ~8 rooms by splitting large ones
    attempts = 0
    while len(rooms) < 8 and attempts < 20:
        attempts += 1
        # Duplicate the largest room as two halves
        if rooms:
            r = rooms[0]
            w = r.x2 - r.x1
            h = r.y2 - r.y1
            if w > 3:
                mid = r.x1 + w // 2
                rooms.append(Rect(r.x1, r.y1, w // 2, h))
                rooms.append(Rect(mid, r.y1, w - w // 2, h))
            elif h > 3:
                mid = r.y1 + h // 2
                rooms.append(Rect(r.x1, r.y1, w, h // 2))
                rooms.append(Rect(r.x1, mid, w, h - h // 2))
            else:
                # Can't split, just duplicate
                rooms.append(Rect(r.x1, r.y1, r.x2 - r.x1, r.y2 - r.y1))
        else:
            break

    # Re-sort after potential splits
    rooms.sort(key=lambda r: abs(r.center()[0] - cx) + abs(r.center()[1] - cy))
    return rooms


# ── Generator 1: Classic ──────────────────────────────────────

def generate_classic(width, height, walkable, transparent, rng):
    """Current code: random rooms + L-tunnels + simplex noise caves."""
    rooms = []
    for _ in range(300):
        w = rng.randint(3, 15)
        h = rng.randint(3, 15)
        x = rng.randint(0, width - w - 1)
        y = rng.randint(0, height - h - 1)
        room = Rect(x, y, w, h)
        if any(room.intersects(r) for r in rooms):
            continue
        _carve_rect(walkable, transparent, room)
        rooms.append(room)

    for i in range(1, len(rooms)):
        x1, y1 = rooms[i - 1].center()
        x2, y2 = rooms[i].center()
        _l_tunnel(walkable, transparent, x1, y1, x2, y2, rng)

    noise = tcod.noise.Noise(
        2, algorithm=libtcodpy.NOISE_SIMPLEX,
        implementation=tcod.noise.Implementation.TURBULENCE,
        hurst=0.5, lacunarity=2.0, octaves=4,
    )
    samples = noise.sample_ogrid(
        [np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32)]
    )
    cave = (samples < 0.40) & ~walkable
    walkable[cave] = True
    transparent[cave] = True

    return rooms


# ── Generator 2: BSP ─────────────────────────────────────────

def generate_bsp(width, height, walkable, transparent, rng):
    """BSP recursive partition, rooms in leaves, sibling corridors."""
    bsp = tcod.bsp.BSP(x=1, y=1, width=width - 2, height=height - 2)
    bsp.split_recursive(depth=5, min_width=8, min_height=8,
                        max_horizontal_ratio=1.8, max_vertical_ratio=1.8)

    rooms = []
    node_rooms = {}  # map node id -> Rect

    # Place rooms in leaf nodes
    for node in bsp.inverted_level_order():
        if not node.children:
            # Leaf: place a room
            pad = 2
            rw = rng.randint(max(3, node.width // 3), max(3, node.width - pad))
            rh = rng.randint(max(3, node.height // 3), max(3, node.height - pad))
            rx = rng.randint(node.x, max(node.x, node.x + node.width - rw - 1))
            ry = rng.randint(node.y, max(node.y, node.y + node.height - rh - 1))
            room = Rect(rx, ry, rw, rh)
            _carve_rect(walkable, transparent, room)
            rooms.append(room)
            node_rooms[id(node)] = room
        else:
            # Internal: connect children
            left, right = node.children
            lr = node_rooms.get(id(left))
            rr = node_rooms.get(id(right))
            if lr and rr:
                x1, y1 = lr.center()
                x2, y2 = rr.center()
                _l_tunnel(walkable, transparent, x1, y1, x2, y2, rng)
            # Propagate a room reference up
            node_rooms[id(node)] = lr or rr

    return rooms


# ── Generator 3: Cavern ───────────────────────────────────────

def generate_cavern(width, height, walkable, transparent, rng):
    """Cellular automata cave: 45% fill, 5 iterations, keep largest blob."""
    grid = np.zeros((width, height), dtype=bool)
    # Initial random fill
    for x in range(1, width - 1):
        for y in range(1, height - 1):
            if rng.random() < 0.45:
                grid[x, y] = True

    # Cellular automata iterations
    for _ in range(5):
        new_grid = np.zeros_like(grid)
        for x in range(1, width - 1):
            for y in range(1, height - 1):
                neighbors = 0
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height and grid[nx, ny]:
                            neighbors += 1
                # Birth: 5+ neighbors. Survival: 4+ neighbors
                if grid[x, y]:
                    new_grid[x, y] = neighbors >= 4
                else:
                    new_grid[x, y] = neighbors >= 5
        grid = new_grid

    # Keep largest connected blob via flood fill
    visited = np.zeros_like(grid)
    blobs = []

    def flood_fill(sx, sy):
        stack = [(sx, sy)]
        cells = []
        while stack:
            cx, cy = stack.pop()
            if visited[cx, cy] or not grid[cx, cy]:
                continue
            visited[cx, cy] = True
            cells.append((cx, cy))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    stack.append((nx, ny))
        return cells

    for x in range(width):
        for y in range(height):
            if grid[x, y] and not visited[x, y]:
                blob = flood_fill(x, y)
                if blob:
                    blobs.append(blob)

    if not blobs:
        # Fallback to classic
        return generate_classic(width, height, walkable, transparent, rng)

    largest = max(blobs, key=len)
    for x, y in largest:
        walkable[x, y] = True
        transparent[x, y] = True

    return _find_virtual_rooms(walkable, width, height)


# ── Generator 4: Drunkard ─────────────────────────────────────

def generate_drunkard(width, height, walkable, transparent, rng):
    """3-5 random walkers carving ~38% of map, occasional 3x3 pockets."""
    target = int(width * height * 0.38)
    carved = 0
    num_walkers = rng.randint(3, 5)

    for _ in range(num_walkers):
        wx = rng.randint(width // 4, 3 * width // 4)
        wy = rng.randint(height // 4, 3 * height // 4)
        steps = target // num_walkers

        for _ in range(steps):
            if carved >= target:
                break
            if not walkable[wx, wy]:
                walkable[wx, wy] = True
                transparent[wx, wy] = True
                carved += 1

            # Occasional 3x3 pocket
            if rng.random() < 0.08:
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        nx, ny = wx + dx, wy + dy
                        if 1 <= nx < width - 1 and 1 <= ny < height - 1:
                            if not walkable[nx, ny]:
                                walkable[nx, ny] = True
                                transparent[nx, ny] = True
                                carved += 1

            # Random walk
            dx, dy = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
            nx, ny = wx + dx, wy + dy
            if 1 <= nx < width - 1 and 1 <= ny < height - 1:
                wx, wy = nx, ny

    return _find_virtual_rooms(walkable, width, height)


# ── Generator 5: Arena ────────────────────────────────────────

def generate_arena(width, height, walkable, transparent, rng):
    """One huge central room with pillar grid + 6-10 satellite rooms."""
    # Central arena
    aw = rng.randint(30, 40)
    ah = rng.randint(20, 30)
    ax = (width - aw) // 2
    ay = (height - ah) // 2
    arena = Rect(ax, ay, aw, ah)
    _carve_rect(walkable, transparent, arena)

    # Pillar grid inside arena (every 4 tiles)
    for px in range(arena.x1 + 3, arena.x2 - 1, 4):
        for py in range(arena.y1 + 3, arena.y2 - 1, 4):
            if 0 <= px < width and 0 <= py < height:
                walkable[px, py] = False
                transparent[px, py] = False

    rooms = [arena]

    # Satellite rooms
    num_satellites = rng.randint(8, 12)
    for _ in range(num_satellites):
        sw = rng.randint(4, 8)
        sh = rng.randint(4, 8)
        # Place around the arena
        side = rng.randint(0, 3)
        if side == 0:  # top
            sx = rng.randint(ax - sw, ax + aw)
            sy = rng.randint(max(1, ay - sh - 10), max(1, ay - sh - 1))
        elif side == 1:  # bottom
            sx = rng.randint(ax - sw, ax + aw)
            sy = rng.randint(ay + ah + 1, min(height - sh - 1, ay + ah + 10))
        elif side == 2:  # left
            sx = rng.randint(max(1, ax - sw - 10), max(1, ax - sw - 1))
            sy = rng.randint(ay - sh, ay + ah)
        else:  # right
            sx = rng.randint(ax + aw + 1, min(width - sw - 1, ax + aw + 10))
            sy = rng.randint(ay - sh, ay + ah)

        sx = max(1, min(sx, width - sw - 2))
        sy = max(1, min(sy, height - sh - 2))
        sat = Rect(sx, sy, sw, sh)
        _carve_rect(walkable, transparent, sat)
        rooms.append(sat)

        # Connect to arena
        x1, y1 = sat.center()
        x2, y2 = arena.center()
        _l_tunnel(walkable, transparent, x1, y1, x2, y2, rng)

    return rooms


# ── Generator 6: Maze ─────────────────────────────────────────

def generate_maze(width, height, walkable, transparent, rng):
    """Recursive backtracker on 3x3 cell grid, 8% wall removal for loops,
    merge clusters into rooms."""
    cell_w = 3
    cols = (width - 2) // cell_w
    rows = (height - 2) // cell_w
    if cols < 3 or rows < 3:
        return generate_classic(width, height, walkable, transparent, rng)

    visited = [[False] * rows for _ in range(cols)]
    stack = []

    # Start from center-ish cell
    sc, sr = cols // 2, rows // 2
    visited[sc][sr] = True
    stack.append((sc, sr))

    def cell_to_map(c, r):
        return 1 + c * cell_w + cell_w // 2, 1 + r * cell_w + cell_w // 2

    def carve_cell(c, r):
        mx, my = cell_to_map(c, r)
        for dx in range(-(cell_w // 2), cell_w // 2 + 1):
            for dy in range(-(cell_w // 2), cell_w // 2 + 1):
                nx, ny = mx + dx, my + dy
                if 1 <= nx < width - 1 and 1 <= ny < height - 1:
                    _carve(walkable, transparent, nx, ny)

    def carve_between(c1, r1, c2, r2):
        mx1, my1 = cell_to_map(c1, r1)
        mx2, my2 = cell_to_map(c2, r2)
        if c1 == c2:
            x = mx1
            for y in range(min(my1, my2), max(my1, my2) + 1):
                for dx in range(-(cell_w // 2), cell_w // 2 + 1):
                    _carve(walkable, transparent, x + dx, y)
        else:
            y = my1
            for x in range(min(mx1, mx2), max(mx1, mx2) + 1):
                for dy in range(-(cell_w // 2), cell_w // 2 + 1):
                    _carve(walkable, transparent, x, y + dy)

    carve_cell(sc, sr)

    while stack:
        c, r = stack[-1]
        neighbors = []
        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nc, nr = c + dc, r + dr
            if 0 <= nc < cols and 0 <= nr < rows and not visited[nc][nr]:
                neighbors.append((nc, nr))
        if neighbors:
            nc, nr = rng.choice(neighbors)
            visited[nc][nr] = True
            carve_between(c, r, nc, nr)
            carve_cell(nc, nr)
            stack.append((nc, nr))
        else:
            stack.pop()

    # 8% wall removal for loops
    for x in range(2, width - 2):
        for y in range(2, height - 2):
            if not walkable[x, y] and rng.random() < 0.08:
                # Only remove if it connects two walkable areas
                adj_walk = sum(1 for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                               if walkable[x + dx, y + dy])
                if adj_walk >= 2:
                    _carve(walkable, transparent, x, y)

    # Build rooms from cell clusters
    rooms = []
    for c in range(0, cols, 3):
        for r in range(0, rows, 3):
            mx, my = cell_to_map(c, r)
            # Make a room spanning a few cells
            rw = min(cell_w * 3, width - mx - 1)
            rh = min(cell_w * 3, height - my - 1)
            if rw >= 3 and rh >= 3:
                room = Rect(mx - 1, my - 1, rw, rh)
                rooms.append(room)

    if len(rooms) < 8:
        rooms = _find_virtual_rooms(walkable, width, height)
    else:
        cx, cy = width // 2, height // 2
        rooms.sort(key=lambda r: abs(r.center()[0] - cx) + abs(r.center()[1] - cy))

    return rooms


# ── Generator 7: Rings ────────────────────────────────────────

def generate_rings(width, height, walkable, transparent, rng):
    """3-5 concentric rectangular corridors + 8 radial spokes + sector rooms."""
    cx, cy = width // 2, height // 2
    num_rings = rng.randint(3, 5)
    rooms = []

    ring_gap = min(width, height) // (num_rings * 2 + 2)
    ring_gap = max(ring_gap, 4)

    for i in range(1, num_rings + 1):
        rx = ring_gap * i
        ry = ring_gap * i
        # Draw rectangular ring
        x1 = max(1, cx - rx)
        y1 = max(1, cy - ry)
        x2 = min(width - 2, cx + rx)
        y2 = min(height - 2, cy + ry)

        # Top and bottom edges
        for x in range(x1, x2 + 1):
            _carve(walkable, transparent, x, y1)
            _carve(walkable, transparent, x, y2)
        # Left and right edges
        for y in range(y1, y2 + 1):
            _carve(walkable, transparent, x1, y)
            _carve(walkable, transparent, x2, y)

    # 8 radial spokes from center
    for angle_idx in range(8):
        angle = angle_idx * math.pi / 4
        for dist in range(2, min(width, height) // 2 - 2):
            sx = int(cx + dist * math.cos(angle))
            sy = int(cy + dist * math.sin(angle))
            if 1 <= sx < width - 1 and 1 <= sy < height - 1:
                _carve(walkable, transparent, sx, sy)

    # Sector rooms between rings
    for i in range(1, num_rings + 1):
        rx = ring_gap * i
        ry = ring_gap * i
        # Place rooms in 4 quadrants at this ring level
        for qx, qy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
            room_cx = cx + qx * rx * 2 // 3
            room_cy = cy + qy * ry * 2 // 3
            rw = rng.randint(4, 7)
            rh = rng.randint(4, 7)
            room_x = max(1, room_cx - rw // 2)
            room_y = max(1, room_cy - rh // 2)
            room_x = min(room_x, width - rw - 2)
            room_y = min(room_y, height - rh - 2)
            if room_x > 0 and room_y > 0:
                room = Rect(room_x, room_y, rw, rh)
                _carve_rect(walkable, transparent, room)
                rooms.append(room)
                # Connect to nearest ring point
                _l_tunnel(walkable, transparent,
                          room_cx, room_cy, room.center()[0], room.center()[1], rng)

    # Center room
    center_room = Rect(cx - 3, cy - 3, 7, 7)
    _carve_rect(walkable, transparent, center_room)
    rooms.insert(0, center_room)

    return rooms


# ── Generator 8: Islands ──────────────────────────────────────

def generate_islands(width, height, walkable, transparent, rng):
    """15-25 circular platforms connected by MST + extra bridges."""
    num_islands = rng.randint(15, 25)
    centers = []
    radii = []
    rooms = []

    for _ in range(num_islands * 5):
        if len(centers) >= num_islands:
            break
        ix = rng.randint(8, width - 9)
        iy = rng.randint(8, height - 9)
        ir = rng.randint(3, 7)
        # Check no overlap with existing
        too_close = False
        for (ox, oy), orr in zip(centers, radii):
            if abs(ix - ox) + abs(iy - oy) < ir + orr + 3:
                too_close = True
                break
        if too_close:
            continue
        centers.append((ix, iy))
        radii.append(ir)

        # Carve circle
        for dx in range(-ir, ir + 1):
            for dy in range(-ir, ir + 1):
                if dx * dx + dy * dy <= ir * ir:
                    nx, ny = ix + dx, iy + dy
                    if 1 <= nx < width - 1 and 1 <= ny < height - 1:
                        _carve(walkable, transparent, nx, ny)

        # Create room rect inscribed in circle
        side = max(2, int(ir * 0.7))
        room = Rect(ix - side, iy - side, side * 2, side * 2)
        rooms.append(room)

    if len(centers) < 2:
        return generate_classic(width, height, walkable, transparent, rng)

    # MST via Prim's algorithm
    connected = {0}
    edges = []

    while len(connected) < len(centers):
        best_edge = None
        best_dist = float("inf")
        for ci in connected:
            for cj in range(len(centers)):
                if cj in connected:
                    continue
                dx = centers[ci][0] - centers[cj][0]
                dy = centers[ci][1] - centers[cj][1]
                d = dx * dx + dy * dy
                if d < best_dist:
                    best_dist = d
                    best_edge = (ci, cj)
        if best_edge is None:
            break
        edges.append(best_edge)
        connected.add(best_edge[1])

    # Extra bridges (~30% of MST edges)
    num_extra = max(1, len(edges) // 3)
    for _ in range(num_extra):
        ci = rng.randint(0, len(centers) - 1)
        cj = rng.randint(0, len(centers) - 1)
        if ci != cj:
            edges.append((ci, cj))

    # Carve bridges
    for ci, cj in edges:
        x1, y1 = centers[ci]
        x2, y2 = centers[cj]
        _l_tunnel(walkable, transparent, x1, y1, x2, y2, rng)

    # Sort rooms: closest to center first
    cx, cy = width // 2, height // 2
    rooms.sort(key=lambda r: abs(r.center()[0] - cx) + abs(r.center()[1] - cy))
    return rooms


# ── Generator 9: Worms ────────────────────────────────────────

def generate_worms(width, height, walkable, transparent, rng):
    """5-8 angle-drifting wide tunnels (r=2-4, 200-500 steps each)."""
    num_worms = rng.randint(5, 8)

    for _ in range(num_worms):
        wx = rng.randint(width // 4, 3 * width // 4)
        wy = rng.randint(height // 4, 3 * height // 4)
        angle = rng.random() * 2 * math.pi
        radius = rng.randint(2, 4)
        steps = rng.randint(200, 500)

        for _ in range(steps):
            # Carve a circle at current position
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if dx * dx + dy * dy <= radius * radius:
                        nx, ny = int(wx) + dx, int(wy) + dy
                        if 1 <= nx < width - 1 and 1 <= ny < height - 1:
                            _carve(walkable, transparent, nx, ny)

            # Drift angle
            angle += rng.uniform(-0.5, 0.5)
            wx += math.cos(angle) * 1.5
            wy += math.sin(angle) * 1.5

            # Keep in bounds
            wx = max(radius + 1, min(width - radius - 2, wx))
            wy = max(radius + 1, min(height - radius - 2, wy))

    return _find_virtual_rooms(walkable, width, height)


# ── Generator 10: Cathedral ──────────────────────────────────

def generate_cathedral(width, height, walkable, transparent, rng):
    """Symmetric: long nave + transept cross + side chapel pairs + apse."""
    cx, cy = width // 2, height // 2
    rooms = []

    # Nave: long vertical corridor
    nave_w = rng.randint(8, 12)
    nave_h = rng.randint(40, min(60, height - 10))
    nave = Rect(cx - nave_w // 2, cy - nave_h // 2, nave_w, nave_h)
    _carve_rect(walkable, transparent, nave)
    rooms.append(nave)

    # Transept: horizontal cross
    trans_w = rng.randint(35, min(50, width - 10))
    trans_h = rng.randint(6, 10)
    trans_y = cy - trans_h // 2
    transept = Rect(cx - trans_w // 2, trans_y, trans_w, trans_h)
    _carve_rect(walkable, transparent, transept)
    rooms.append(transept)

    # Apse: semicircular end at top of nave
    apse_r = nave_w // 2 + 2
    apse_cy = cy - nave_h // 2
    for dx in range(-apse_r, apse_r + 1):
        for dy in range(-apse_r, 1):
            if dx * dx + dy * dy <= apse_r * apse_r:
                nx, ny = cx + dx, apse_cy + dy
                if 1 <= nx < width - 1 and 1 <= ny < height - 1:
                    _carve(walkable, transparent, nx, ny)
    apse = Rect(cx - apse_r, apse_cy - apse_r, apse_r * 2, apse_r)
    rooms.append(apse)

    # Side chapels: 3-5 pairs along nave
    num_chapels = rng.randint(3, 5)
    chapel_spacing = nave_h // (num_chapels + 1)
    for i in range(1, num_chapels + 1):
        chapel_cy = (cy - nave_h // 2) + i * chapel_spacing
        cw = rng.randint(5, 8)
        ch = rng.randint(4, 6)

        # Left chapel
        lx = cx - nave_w // 2 - cw
        lx = max(1, lx)
        left = Rect(lx, chapel_cy - ch // 2, cw, ch)
        _carve_rect(walkable, transparent, left)
        rooms.append(left)
        # Connect
        _carve_h_tunnel(walkable, transparent,
                        left.center()[0], cx - nave_w // 2 + 1, left.center()[1])

        # Right chapel (symmetric)
        rx = cx + nave_w // 2 + 1
        rx = min(rx, width - cw - 2)
        right = Rect(rx, chapel_cy - ch // 2, cw, ch)
        _carve_rect(walkable, transparent, right)
        rooms.append(right)
        _carve_h_tunnel(walkable, transparent,
                        right.center()[0], cx + nave_w // 2, right.center()[1])

    # Pillar rows along nave
    for py_off in range(nave.y1 + 3, nave.y2 - 1, 4):
        for px_off in [cx - nave_w // 4, cx + nave_w // 4]:
            if 1 <= px_off < width - 1 and 1 <= py_off < height - 1:
                if walkable[px_off, py_off]:
                    walkable[px_off, py_off] = False
                    transparent[px_off, py_off] = False

    return rooms


# ── Weight Table & Dispatcher ─────────────────────────────────

GENERATORS = {
    "classic": generate_classic,
    "bsp": generate_bsp,
    "cavern": generate_cavern,
    "drunkard": generate_drunkard,
    "arena": generate_arena,
    "maze": generate_maze,
    "rings": generate_rings,
    "islands": generate_islands,
    "worms": generate_worms,
    "cathedral": generate_cathedral,
}

DEPTH_WEIGHTS = {
    1: {"classic": 25, "cavern": 35, "drunkard": 20, "worms": 15, "islands": 5},
    2: {"classic": 10, "cavern": 30, "drunkard": 25, "worms": 25, "arena": 5, "islands": 5},
    3: {"classic": 15, "bsp": 30, "cathedral": 30, "rings": 15, "arena": 5, "maze": 5},
    4: {"drunkard": 35, "maze": 35, "worms": 15, "classic": 5, "cavern": 5, "cathedral": 5},
    5: {"arena": 25, "cathedral": 25, "islands": 20, "bsp": 10, "rings": 10, "classic": 5, "cavern": 5},
    6: {"bsp": 30, "rings": 25, "maze": 20, "cathedral": 10, "classic": 5, "arena": 5, "islands": 5},
    7: {"cathedral": 25, "arena": 20, "rings": 20, "islands": 15, "bsp": 10, "classic": 5, "maze": 5},
}

# Organic generators get +10 weight when descending, architectural get -10
ORGANIC = {"cavern", "drunkard", "worms"}
ARCHITECTURAL = {"bsp", "maze", "rings", "cathedral"}


def pick_layout(depth, ascending):
    """Pick a layout generator based on depth weights. Returns (generator_function, name)."""
    depth = max(1, min(7, depth))
    rng = random.Random()

    # 5% anomaly: uniform pick from all generators
    if rng.random() < 0.05:
        chosen = rng.choice(list(GENERATORS.keys()))
        return GENERATORS[chosen], chosen.capitalize()

    weights = dict(DEPTH_WEIGHTS[depth])

    # Corrupted variant adjustments
    if not ascending:
        for name in list(weights.keys()):
            if name in ORGANIC:
                weights[name] = weights[name] + 10
            elif name in ARCHITECTURAL:
                weights[name] = max(1, weights[name] - 10)

    names = list(weights.keys())
    wvals = [weights[n] for n in names]
    chosen = rng.choices(names, weights=wvals, k=1)[0]
    return GENERATORS[chosen], chosen.capitalize()
