from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random, time, colorsys

# 1.Window & world coordinates
VIEW_W, VIEW_H = 500, 500
WORLD_XMIN, WORLD_XMAX = -250, 250
WORLD_YMIN, WORLD_YMAX = -250, 250

# 2.Game state
bowl_x = 0
catcher_y = -220
bowl_w = 160             
bowl_h = 26             
catcher_step = 28      # amount to move per key press
catcher_alive_color = (1.0, 1.0, 1.0)  # white
catcher_dead_color  = (1.0, 0.0, 0.0)  # red

diamond_active = True             # Diamond (rhombus made of 4 midpoint lines)
gem_x = 0
gem_y = 210
diamond_size = 12
diamond_color = (1.0, 1.0, 0.0)

fall_speed = 85.0        # units / second  (changes with time)
fall_accel = 7.0         # units / second^2 (gradually increases difficulty)

points = 0
is_paused = False
is_game_over = False

_last_time = None

BTN_H = 30        # 3.Buttons' AABBs (in world coordinates, easy rectangular hit areas)
BTN_W = 40
btn_restart = (-230, 220, 60, 30)  # (x, y, w, h) Teal arrow, left-top
btn_toggle  = (-20,  220, 40, 30)  # Amber play/pause, top-center
btn_exit    = ( 190, 220, 60, 30)  # Red X, top-right

def clamp(v, lo, hi):         # Utility-catcher never goes outside scr boundary
    return max(lo, min(hi, v))

def convert_mouse_to_world(mx, my):
    """Convert GLUT mouse (0..W, 0..H from top-left) to world (-250..250 centered)."""
    wx = mx - (VIEW_W / 2)
    wy = (VIEW_H / 2) - my
    return int(round(wx)), int(round(wy))

def random_bright_rgb():
    """Return a bright random RGB (HSV with high S & V)."""
    h = random.random()
    s = random.uniform(0.8, 1.0)
    v = random.uniform(0.9, 1.0)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (r, g, b)

def find_zone(x1, y1, x2, y2):        # 3.Zone helpers (8-way)
    dx = x2 - x1
    dy = y2 - y1
    adx, ady = abs(dx), abs(dy)
    if adx >= ady:
        if dx >= 0 and dy >= 0: return 0
        if dx <  0 and dy >= 0: return 3
        if dx <  0 and dy <  0: return 4
        if dx >= 0 and dy <  0: return 7
    else:
        if dx >= 0 and dy >= 0: return 1
        if dx <  0 and dy >= 0: return 2
        if dx <  0 and dy <  0: return 5
        if dx >= 0 and dy <  0: return 6

def to_zone0(x, y, zone):
    # Map (x,y) from original zone to zone 0
    if zone == 0: return ( x,  y)
    if zone == 1: return ( y,  x)
    if zone == 2: return ( y, -x)
    if zone == 3: return (-x,  y)
    if zone == 4: return (-x, -y)
    if zone == 5: return (-y, -x)
    if zone == 6: return (-y,  x)
    if zone == 7: return ( x, -y)

def from_zone0(x, y, zone):
    if zone == 0: return ( x,  y)
    if zone == 1: return ( y,  x)
    if zone == 2: return (-y,  x)
    if zone == 3: return (-x,  y)
    if zone == 4: return (-x, -y)
    if zone == 5: return (-y, -x)
    if zone == 6: return ( y, -x)
    if zone == 7: return ( x, -y)

# 4. Midpoint line (Zone-0 core)
def midpoint_line(x1, y1, x2, y2):
    """Draw a midpoint line from (x1,y1) to (x2,y2) using integer arithmetic.
       Internally maps to Zone-0, runs the classic loop, converts each plotted
       pixel back to the original zone before glVertex2f (GL_POINTS only).
    """
    zone = find_zone(x1, y1, x2, y2)

    X1, Y1 = to_zone0(x1, y1, zone)
    X2, Y2 = to_zone0(x2, y2, zone)

    if X1 > X2:
        X1, X2 = X2, X1
        Y1, Y2 = Y2, Y1

    dx = X2 - X1
    dy = Y2 - Y1
    d = 2 * dy - dx
    incE = 2 * dy
    incNE = 2 * (dy - dx)

    y = Y1
    glBegin(GL_POINTS)
    for x in range(X1, X2 + 1):
        rx, ry = from_zone0(x, y, zone)
        glVertex2f(rx, ry)
        if d > 0:
            d += incNE
            y += 1
        else:
            d += incE
    glEnd()

def draw_line(x1, y1, x2, y2):
    """Convenience wrapper – you can set color before calling."""
    midpoint_line(int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2)))

def draw_polyline(points):
    """Draws a closed polyline through points list using midpoint lines."""
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        draw_line(x1, y1, x2, y2)

def draw_gem(cx, cy, s):          #Shapes-with midpoint lines
    top    = (cx,     cy + s)
    right  = (cx + s, cy    )
    bottom = (cx,     cy - s)
    left   = (cx - s, cy    )
    draw_polyline([top, right, bottom, left])

def draw_bowl(cx, cy, w, h):
    bl = (cx - w // 2, cy)
    br = (cx + w // 2, cy)
    tl = (cx - w // 4, cy + h)
    tr = (cx + w // 4, cy + h)
    draw_polyline([bl, br, tr, tl])

def draw_left_arrow(x, y, size):
    head = (x, y)
    tip1 = (x + size, y + size)
    tip2 = (x + size, y - size)
    shaft_end = (x + 2*size, y)
    draw_line(*head, *tip1)
    draw_line(*head, *tip2)
    draw_line(*tip1, *shaft_end)

def draw_pause_icon(cx, cy, h, gap=10):
    half = h // 2
    draw_line(cx - gap, cy - half, cx - gap, cy + half)
    draw_line(cx + gap, cy - half, cx + gap, cy + half)

def draw_play_icon(cx, cy, size):
    p1 = (cx - size//2, cy - size)
    p2 = (cx - size//2, cy + size)
    p3 = (cx + size,    cy)
    draw_polyline([p1, p2, p3])

def draw_cross(cx, cy, size):
    draw_line(cx - size, cy - size, cx + size, cy + size)
    draw_line(cx - size, cy + size, cx + size, cy - size)

def aabb(x, y, w, h):          #AABB collision
    return {'x': x, 'y': y, 'w': w, 'h': h}

def overlap(A, B):
    return (A['x'] < B['x'] + B['w'] and
            A['x'] + A['w'] > B['x'] and
            A['y'] < B['y'] + B['h'] and
            A['y'] + A['h'] > B['y'])

def catcher_aabb():
    return aabb(bowl_x - bowl_w//2, catcher_y, bowl_w, bowl_h)

def diamond_aabb():
    return aabb(gem_x - diamond_size, gem_y - diamond_size, 2*diamond_size, 2*diamond_size)

# 7) Game helpers
def spawn_new_diamond():
    global gem_x, gem_y, diamond_color, diamond_active, fall_speed
    gem_x = random.randint(WORLD_XMIN + 40, WORLD_XMAX - 40)
    gem_y = WORLD_YMAX - 40
    diamond_color = random_bright_rgb()
    diamond_active = True
    print("Score:", points)

def restart_game():
    global points, is_paused, is_game_over, bowl_x, fall_speed
    points = 0
    is_paused = False
    is_game_over = False
    bowl_x = 0
    fall_speed = 85.0
    spawn_new_diamond()
    print("Starting over!")

def setup_projection():           # 8.GLUT callbacks
    glViewport(0, 0, VIEW_W, VIEW_H)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(WORLD_XMIN, WORLD_XMAX, WORLD_YMIN, WORLD_YMAX, 0, 1)
    glMatrixMode(GL_MODELVIEW)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    setup_projection()
    glPointSize(2)  # lines look crisp while staying GL_POINTS-only

    glColor3f(0.0, 0.9, 0.9)
    rx, ry, rw, rh = btn_restart
    draw_left_arrow(rx + 12, ry + rh//2, 10)

    glColor3f(1.0, 0.75, 0.0)
    tx, ty, tw, th = btn_toggle
    if is_paused or is_game_over:
        draw_play_icon(tx + tw//2, ty + th//2, 12)
    else:
        draw_pause_icon(tx + tw//2, ty + th//2, 26, gap=6)

    # Exit (red)
    glColor3f(1.0, 0.1, 0.1)
    ex, ey, ew, eh = btn_exit
    draw_cross(ex + ew//2, ey + eh//2, 12)

    if diamond_active:
        glColor3f(*diamond_color)
        draw_gem(gem_x, gem_y, diamond_size)

    if is_game_over:
        glColor3f(*catcher_dead_color)
    else:
        glColor3f(*catcher_alive_color)
    draw_bowl(bowl_x, catcher_y, bowl_w, bowl_h)

    glutSwapBuffers()

def tick():
    global _last_time, gem_y, fall_speed, points, diamond_active, is_game_over

    now = time.time()
    if _last_time is None:
        _last_time = now
    dt = now - _last_time
    _last_time = now

    if not is_paused and not is_game_over:
        if diamond_active:
            gem_y -= fall_speed * dt
            fall_speed += fall_accel * dt  # difficulty ramps over time

            if overlap(diamond_aabb(), catcher_aabb()):    # Collision?
                points += 1
                spawn_new_diamond()

            else:                # Missed?
                # If the diamond fell below catcher bottom:
                if gem_y - diamond_size <= catcher_y:
                    # Game over: vanish diamond & lock controls
                    diamond_active = False
                    is_game_over = True
                    print(f"Game Over! Score: {points}")

    glutPostRedisplay()

def special_key_listener(key, x, y):
    global bowl_x
    if is_paused or is_game_over:
        return
    if key == GLUT_KEY_LEFT:
        bowl_x -= catcher_step
    elif key == GLUT_KEY_RIGHT:
        bowl_x += catcher_step

    half = bowl_w // 2                          # Keep catcher within screen
    bowl_x = clamp(bowl_x, WORLD_XMIN + half + 4, WORLD_XMAX - half - 4)
    glutPostRedisplay()

def keyboard_listener(key, x, y):
    k = key.lower()
    if k == b'r':
        restart_game()
    elif k == b'q':
        print(f"Goodbye! Score: {points}")
        glutLeaveMainLoop()

def mouse_listener(button, state, mx, my):
    global is_paused
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        wx, wy = convert_mouse_to_world(mx, my)

        x, y, w, h = btn_restart               # Restart
        if x <= wx <= x + w and y <= wy <= y + h:
            restart_game()
            return

        x, y, w, h = btn_toggle                  # Play/Pause toggle
        if x <= wx <= x + w and y <= wy <= y + h:
            is_paused = not is_paused
            glutPostRedisplay()
            return

        x, y, w, h = btn_exit     # Exit
        if x <= wx <= x + w and y <= wy <= y + h:
            print(f"Goodbye! Score: {points}")
            glutLeaveMainLoop()
            return

def main():                       #9.main
    global diamond_color, gem_x, gem_y, _last_time
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(VIEW_W, VIEW_H)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Catch the Diamonds! - CSE423")

    glClearColor(0.0, 0.0, 0.0, 1.0)  # black background

    glutDisplayFunc(display)
    glutIdleFunc(tick)
    glutSpecialFunc(special_key_listener)
    glutKeyboardFunc(keyboard_listener)
    glutMouseFunc(mouse_listener)

    diamond_color = random_bright_rgb()
    gem_x = 0
    gem_y = WORLD_YMAX - 40
    _last_time = None

    glutMainLoop()

if __name__ == "__main__":
    main()
