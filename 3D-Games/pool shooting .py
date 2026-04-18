from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import math
import time
import random

WIN_W, WIN_H = 1000, 800
ASPECT = WIN_W / float(WIN_H)
fovY = 120

cam_mode = "third"
cam_angle = 0.0
cam_height = 200.0
cam_radius = 400.0

GRID_LENGTH = 600.0
CELL = 60.0
BOUNDARY_H = 120.0

player_pos = [0.0, 0.0, 0.0]
player_yaw = 0.0
player_speed = 500.0
player_radius = 28.0

bullets = []
bullet_speed = 700.0
bullet_half = 8.0
bullet_ttl = 2.0
time_since_last_shot = 0.0
fire_cooldown = 0.08

enemies = []
ENEMY_COUNT = 5
enemy_base_r = 25.0
enemy_pulse_amp = 8.0
enemy_speed = 60.0

cheat_mode = False
cheat_follow_cam = False
cheat_spin_speed = 180.0
cheat_lock_eps = 7.0

lives = 5
score = 0
bullets_missed = 0
game_over = False

_prev_time = None


def clamp(v, a, b):
    return max(a, min(b, v))

def forward_dir_from_yaw_deg(yaw_deg):
    a = math.radians(yaw_deg)
    return [math.cos(a), math.sin(a)]

def dist2D(ax, ay, bx, by):
    dx, dy = ax - bx, ay - by
    return math.hypot(dx, dy)

def angle_diff_deg(a, b):
    return (a - b + 180.0) % 360.0 - 180.0

def random_perimeter_point():
    L = GRID_LENGTH * 0.9
    side = random.randint(0, 3)
    if side == 0:
        return [-L, random.uniform(-L, L), 0.0]
    if side == 1:
        return [L, random.uniform(-L, L), 0.0]
    if side == 2:
        return [random.uniform(-L, L), -L, 0.0]
    return [random.uniform(-L, L), L, 0.0]


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_cuboid(w, d, h):
    s = max(w, d, h)
    glPushMatrix()
    glScalef(w / s, d / s, h / s)
    glutSolidCube(s)
    glPopMatrix()

def draw_grid_checkerboard():
    half = GRID_LENGTH
    i_min = int(-half // CELL)
    i_max = int(half // CELL)
    j_min = int(-half // CELL)
    j_max = int(half // CELL)

    glBegin(GL_QUADS)
    for i in range(i_min, i_max):
        for j in range(j_min, j_max):
            x0 = i * CELL
            y0 = j * CELL
            x1 = x0 + CELL
            y1 = y0 + CELL

            if (i + j) & 1:
                glColor3f(0.7, 0.5, 0.95)
            else:
                glColor3f(1.0, 1.0, 1.0)

            glVertex3f(x0, y0, 0)
            glVertex3f(x1, y0, 0)
            glVertex3f(x1, y1, 0)
            glVertex3f(x0, y1, 0)
    glEnd()

def draw_boundaries():
    L = GRID_LENGTH
    H = BOUNDARY_H

    glBegin(GL_QUADS)

    glColor3f(0.2, 1.0, 0.2)
    glVertex3f(L, -L, 0); glVertex3f(L,  L, 0); glVertex3f(L,  L, H); glVertex3f(L, -L, H)

    glColor3f(0.2, 0.2, 1.0)
    glVertex3f(-L, -L, 0); glVertex3f(-L,  L, 0); glVertex3f(-L,  L, H); glVertex3f(-L, -L, H)

    glColor3f(0.2, 1.0, 1.0)
    glVertex3f(-L, L, 0); glVertex3f( L, L, 0); glVertex3f( L, L, H); glVertex3f(-L, L, H)

    glColor3f(1.0, 0.2, 1.0)
    glVertex3f(-L, -L, 0); glVertex3f( L, -L, 0); glVertex3f( L, -L, H); glVertex3f(-L, -L, H)

    glEnd()

def draw_player():
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])

    if game_over:
        glRotatef(90, 1, 0, 0)

    glRotatef(player_yaw, 0, 0, 1)

    q = gluNewQuadric()

    if cam_mode != "first":
        glColor3f(0.30, 0.80, 0.40)
        glPushMatrix()
        glTranslatef(0, 0, 38)
        draw_cuboid(40, 28, 62)
        glPopMatrix()

    if cam_mode != "first":
        glColor3f(0.0, 0.0, 0.0)
        glPushMatrix()
        glTranslatef(0, 0, 86)
        gluSphere(q, 18, 16, 16)
        glPopMatrix()

    shoulder_z = 62
    shoulder_offset_y = 22
    glColor3f(0.85, 0.85, 0.85)
    for s in (-1, 1):
        glPushMatrix()
        glTranslatef(10, s * shoulder_offset_y, shoulder_z)
        glRotatef(90, 0, 1, 0)
        gluCylinder(q, 5.0, 5.0, 34, 16, 1)
        glPopMatrix()

    glColor3f(0.30, 0.30, 0.30)
    glPushMatrix()
    glTranslatef(28, 0, shoulder_z)
    glRotatef(90, 0, 1, 0)
    gluCylinder(q, 4.2, 4.2, 42, 16, 1)
    glPopMatrix()

    glColor3f(0.05, 0.20, 1.00)
    hip_sep = 14
    hip_x = 4
    hip_z = 26
    leg_h = 32

    for s in (-1, 1):
        glPushMatrix()
        glTranslatef(hip_x, s * hip_sep, hip_z)
        glRotatef(180, 1, 0, 0)
        gluCylinder(q, 7.2, 5.2, leg_h, 16, 1)
        glPopMatrix()

        glPushMatrix()
        glTranslatef(hip_x, s * hip_sep, hip_z - leg_h - 2)
        draw_cuboid(10, 8, 4)
        glPopMatrix()

    glPopMatrix()

def draw_enemy(e):
    q = gluNewQuadric()
    r = e["base_r"] + enemy_pulse_amp * math.sin(e["phase"])

    glPushMatrix()
    glTranslatef(e["pos"][0], e["pos"][1], 0.0)

    glColor3f(1.0, 0.1, 0.1)
    gluSphere(q, r, 16, 16)

    glColor3f(0.0, 0.0, 0.0)
    glTranslatef(0, 0, r * 0.9)
    gluSphere(q, r * 0.35, 12, 12)

    glPopMatrix()

def draw_bullet(b):
    glColor3f(1.0, 0.0, 0.0)
    glPushMatrix()
    glTranslatef(b["pos"][0], b["pos"][1], b["pos"][2])
    draw_cuboid(bullet_half * 2, bullet_half * 2, bullet_half * 2)
    glPopMatrix()


def muzzle_world_position():
    f = forward_dir_from_yaw_deg(player_yaw)
    return [player_pos[0] + f[0] * 40.0, player_pos[1] + f[1] * 40.0, 18.0]

def eye_world_position():
    f = forward_dir_from_yaw_deg(player_yaw)
    return [player_pos[0] + f[0] * 8.0, player_pos[1] + f[1] * 8.0, 84.0]

def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, ASPECT, 0.1, 2000.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if cam_mode == "third":
        cx = cam_radius * math.cos(cam_angle)
        cy = cam_radius * math.sin(cam_angle)
        cz = cam_height
        gluLookAt(cx, cy, cz, 0, 0, 0, 0, 0, 1)
    else:
        e = eye_world_position()
        f = forward_dir_from_yaw_deg(player_yaw)

        lead = 100.0 if (cheat_mode and cheat_follow_cam) else 80.0
        center = (e[0] + f[0] * lead, e[1] + f[1] * lead, e[2] + 2.0)

        gluLookAt(e[0], e[1], e[2], center[0], center[1], center[2], 0, 0, 1)


def init_game_state():
    global player_pos, player_yaw, lives, score, bullets_missed, game_over
    global enemies, bullets, time_since_last_shot, cam_mode, cam_angle, cam_height

    player_pos = [0.0, 0.0, 0.0]
    player_yaw = 0.0
    lives = 5
    score = 0
    bullets_missed = 0
    game_over = False

    time_since_last_shot = 0.0
    bullets = []

    enemies = []
    for _ in range(ENEMY_COUNT):
        p = random_perimeter_point()
        enemies.append({
            "pos": p,
            "base_r": enemy_base_r,
            "phase": random.uniform(0, math.pi * 2.0),
            "speed": enemy_speed
        })

    cam_mode = "third"
    cam_angle = 0.6
    cam_height = 500.0


def move_player(direction, dt):
    f = forward_dir_from_yaw_deg(player_yaw)
    step = player_speed * dt * direction
    player_pos[0] = clamp(player_pos[0] + f[0] * step, -GRID_LENGTH * 0.95, GRID_LENGTH * 0.95)
    player_pos[1] = clamp(player_pos[1] + f[1] * step, -GRID_LENGTH * 0.95, GRID_LENGTH * 0.95)

def fire_bullet():
    global time_since_last_shot
    if time_since_last_shot < fire_cooldown:
        return None
    f = forward_dir_from_yaw_deg(player_yaw)
    pos = muzzle_world_position()
    bullets.append({"pos": [pos[0], pos[1], pos[2]], "dir": [f[0], f[1]], "ttl": bullet_ttl})
    time_since_last_shot = 0.0


def update_bullets(dt):
    global bullets, bullets_missed
    keep = []
    L = GRID_LENGTH
    eps = 0.5

    for b in bullets:
        b["pos"][0] += b["dir"][0] * bullet_speed * dt
        b["pos"][1] += b["dir"][1] * bullet_speed * dt
        b["pos"][2] = 18.0
        b["ttl"] -= dt

        if b["ttl"] <= 0:
            bullets_missed += 1
            continue

        if abs(b["pos"][0]) >= L - eps or abs(b["pos"][1]) >= L - eps:
            bullets_missed += 1
            continue

        keep.append(b)

    bullets = keep

def step_towards_player(e, dt):
    dx = player_pos[0] - e["pos"][0]
    dy = player_pos[1] - e["pos"][1]
    d = math.hypot(dx, dy)
    if d > 1e-4:
        e["pos"][0] += (dx / d) * e["speed"] * dt
        e["pos"][1] += (dy / d) * e["speed"] * dt


def enemy_aligned_with_gun():
    if not enemies:
        return False

    best_abs = 1e9
    for e in enemies:
        dx = e["pos"][0] - player_pos[0]
        dy = e["pos"][1] - player_pos[1]
        ang = math.degrees(math.atan2(dy, dx))
        diff = abs(angle_diff_deg(ang, player_yaw))
        if diff < best_abs:
            best_abs = diff

    return best_abs <= cheat_lock_eps


def lives_dec():
    global lives, enemies
    lives_dec.called = True
    lives = max(0, lives - 1)
    for e in enemies:
        e["pos"] = random_perimeter_point()

lives_dec.called = False

def handle_collisions():
    global score, bullets

    new_bullets = []
    for b in bullets:
        hit = False
        for e in enemies:
            r = e["base_r"] + enemy_pulse_amp * math.sin(e["phase"])
            if dist2D(b["pos"][0], b["pos"][1], e["pos"][0], e["pos"][1]) <= (r + bullet_half * 1.2):
                score += 1
                e["pos"] = random_perimeter_point()
                e["phase"] = random.uniform(0, math.pi * 2.0)
                hit = True
                break
        if not hit:
            new_bullets.append(b)

    bullets = new_bullets

    for e in enemies:
        r = e["base_r"] + enemy_pulse_amp * math.sin(e["phase"])
        if dist2D(player_pos[0], player_pos[1], e["pos"][0], e["pos"][1]) <= (r + player_radius):
            lives_dec()


def keyboardListener(key, x, y):
    global player_yaw, cheat_mode, cheat_follow_cam, game_over

    if key == b'w':
        move_player(+1, 1 / 60.0)
    elif key == b's':
        move_player(-1, 1 / 60.0)
    elif key == b'a':
        player_yaw = (player_yaw + 6.0) % 360.0
    elif key == b'd':
        player_yaw = (player_yaw - 6.0) % 360.0
    elif key == b'c':
        cheat_mode = not cheat_mode
    elif key == b'v':
        cheat_follow_cam = not cheat_follow_cam
    elif key == b'r':
        if game_over:
            init_game_state()

def specialKeyListener(key, x, y):
    global cam_angle, cam_height

    if key == GLUT_KEY_LEFT:
        cam_angle -= 0.04
    elif key == GLUT_KEY_RIGHT:
        cam_angle += 0.04
    elif key == GLUT_KEY_UP:
        cam_height = clamp(cam_height + 16.0, 120.0, 1000.0)
    elif key == GLUT_KEY_DOWN:
        cam_height = clamp(cam_height - 16.0, 120.0, 1000.0)

def mouseListener(button, state, mx, my):
    global cam_mode

    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        fire_bullet()
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        cam_mode = "first" if cam_mode == "third" else "third"


def idle():
    global _prev_time, time_since_last_shot, player_yaw, game_over

    now = time.time()
    if _prev_time is None:
        _prev_time = now

    dt = now - _prev_time
    _prev_time = now
    dt = clamp(dt, 0.0, 0.04)

    if game_over:
        glutPostRedisplay()
        return

    if cheat_mode:
        player_yaw = (player_yaw + cheat_spin_speed * dt) % 360.0
        if time_since_last_shot >= fire_cooldown and enemy_aligned_with_gun():
            fire_bullet()

    update_bullets(dt)

    for e in enemies:
        step_towards_player(e, dt)
        e["phase"] += 6.0 * dt

    handle_collisions()

    if lives <= 0 or bullets_missed >= 10:
        game_over = True

    time_since_last_shot += dt
    glutPostRedisplay()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, WIN_W, WIN_H)

    setupCamera()

    draw_grid_checkerboard()
    draw_boundaries()

    for e in enemies:
        draw_enemy(e)
    for b in bullets:
        draw_bullet(b)
    draw_player()

    draw_text(10, WIN_H - 30, f"Player Life Remaining: {lives}")
    draw_text(10, WIN_H - 60, f"Game Score: {score}")
    draw_text(10, WIN_H - 90, f"Player Bullets Missed: {bullets_missed}")

    if cheat_mode:
        draw_text(WIN_W - 260, WIN_H - 30, "CHEAT MODE: ON")

    if game_over:
        draw_text(WIN_W // 2 - 80, WIN_H // 2 + 20, "GAME OVER")
        draw_text(WIN_W // 2 - 180, WIN_H // 2 - 10, "Press R to Restart")

    glutSwapBuffers()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Bullet Frenzy - CSE423 Lab 03")

    glEnable(GL_DEPTH_TEST)

    init_game_state()

    glutDisplayFunc(showScreen)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)

    glutMainLoop()

if __name__ == "__main__":
    main()
