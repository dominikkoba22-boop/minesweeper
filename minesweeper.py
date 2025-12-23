
import sys
import os
import pygame
import random
import time

def resource_path(relative_path):
    try:
        # PyInstaller temp folder
        base_path = sys._MEIPASS
    except Exception:
        # Normal Python run
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ========= CONFIG =========
SPRITE_PATH = resource_path("Sprites")
ROWS, COLS = 16, 16
MINES = 40
TILE = 32
MARGIN = 12
HEADER = 72       # slightly bigger to fit bigger smile
SCREEN_W = COLS * TILE + MARGIN * 2
SCREEN_H = ROWS * TILE + MARGIN * 2 + HEADER
FPS = 60
PI_CHANCE = 0.002   # 0.2% chance
# ==========================

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Minesweeper")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 18)
big_font = pygame.font.SysFont("Arial", 24)

# Cell states
COVERED = 0
REVEALED = 1
FLAGGED = 2

# Helper: safe sprite loader
def load_image(name):
    path = os.path.join(SPRITE_PATH, name + ".png")
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (TILE, TILE))
    except Exception as e:
        print("FAILED TO LOAD:", path)
        return None


def make_pressed(img):
    if img is None: return None
    pressed = img.copy()
    dark = pygame.Surface(img.get_size()).convert_alpha()
    dark.fill((200,200,200))
    pressed.blit(dark,(0,0), special_flags=pygame.BLEND_RGB_MULT)
    return pressed

# Load sprites
SPR = {}
SPR["covered"] = load_image("TileWithNoNumber")
SPR["pressed"] = make_pressed(SPR["covered"])
SPR["empty"]   = load_image("TileEmpty")
SPR["flag"]    = load_image("Flag")
SPR["mine"]    = load_image("Mine")
SPR["mine_red"]= load_image("MineRed")
SPR["mine_x"]  = load_image("MineX")
SPR["pi"]      = load_image("pi")     # NEW

# Faces (bigger)
def load_face(name):
    img = load_image(name)
    if img:
        return pygame.transform.scale(img, (48,48))
    return None

SPR["face_smile"] = load_face("Smile")
SPR["face_shock"] = load_face("Shocked")
SPR["face_dead"]  = load_face("GameOver")

# Number tiles
for i in range(1,9):
    SPR[str(i)] = load_image(str(i))

COLORS = {
    "bg": (180,180,180),
    "covered": (160,160,160),
    "mine": (0,0,0),
    "text": (10,10,10),
}

# ===================== GAME CLASS =====================
class Game:
    def __init__(self, rows, cols, mines):
        self.rows, self.cols, self.total_mines = rows, cols, mines
        self.reset()

    def reset(self):
        self.pi_event = False
        self.mines_placed = False
        self.state = "playing"
        self.start_time = None
        self.end_time = None
        self.state_map = [[COVERED]*self.cols for _ in range(self.rows)]
        self.adj = [[0]*self.cols for _ in range(self.rows)]
        self.flags = 0
        self.revealed_count = 0

    def in_bounds(self,r,c): return 0<=r<self.rows and 0<=c<self.cols

    def neighbors(self,r,c):
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr==0 and dc==0: continue
                nr, nc = r+dr, c+dc
                if self.in_bounds(nr,nc): yield nr,nc

    # ====== PI TILE EVENT ======
    def trigger_pi_event(self, r, c):
        self.pi_event = True
        # EVERY tile becomes a mine
        for rr in range(self.rows):
            for cc in range(self.cols):
                self.adj[rr][cc] = -1

        self.mines_placed = True
        self.start_time = time.time()

        # Print warning 10 times with delay
        for _ in range(10):
            print("🔥🔥🔥 PI TILE EVENT TRIGGERED — ALL TILES ARE MINES 🔥🔥🔥")
            pygame.time.delay(200)  # 0.2s delay

        # Reveal pi tile
        self.state_map[r][c] = REVEALED
        self.end_game(lost=True)

    def place_mines(self, safe_r, safe_c):
        # FIRST CLICK → check PI event chance
        if random.random() < PI_CHANCE:
            self.trigger_pi_event(safe_r, safe_c)
            return

        # Normal mine placement
        forbidden = {(safe_r,safe_c), *self.neighbors(safe_r,safe_c)}
        cells = [(r,c) for r in range(self.rows) for c in range(self.cols)
                 if (r,c) not in forbidden]
        mines = random.sample(cells, self.total_mines)

        for r,c in mines:
            self.adj[r][c] = -1

        # adjacency numbers
        for r in range(self.rows):
            for c in range(self.cols):
                if self.adj[r][c] == -1: continue
                self.adj[r][c] = sum(
                    1 for nr,nc in self.neighbors(r,c)
                    if self.adj[nr][nc] == -1
                )

        self.mines_placed = True
        self.start_time = time.time()

    def flood(self,r,c):
        stack=[(r,c)]
        while stack:
            rr,cc = stack.pop()
            if self.state_map[rr][cc] == REVEALED: continue
            self.state_map[rr][cc] = REVEALED
            if self.adj[rr][cc] == 0:
                for nr,nc in self.neighbors(rr,cc):
                    if self.state_map[nr][nc] == COVERED:
                        stack.append((nr,nc))

    def reveal(self,r,c):
        if self.state != "playing": return
        if self.state_map[r][c] != COVERED: return

        if not self.mines_placed:
            self.place_mines(r,c)
            if self.pi_event:
                return

        if self.adj[r][c] == -1:
            self.state_map[r][c] = REVEALED
            self.end_game(lost=True)
            return

        self.flood(r,c)

    def toggle_flag(self,r,c):
        if self.state != "playing": return
        if self.state_map[r][c] == REVEALED: return
        if self.state_map[r][c] == COVERED:
            self.state_map[r][c] = FLAGGED
            self.flags += 1
        elif self.state_map[r][c] == FLAGGED:
            self.state_map[r][c] = COVERED
            self.flags -= 1

    def end_game(self, lost=False):
        self.state = "lost"
        self.end_time = time.time()

    def elapsed(self):
        if not self.start_time: return 0
        if self.end_time: return int(self.end_time - self.start_time)
        return int(time.time() - self.start_time)

# ===================== DRAWING =====================
ox = MARGIN
oy = HEADER

def cell_at(px,py):
    if px < ox or py < oy: return None
    cx = (px-ox)//TILE
    cy = (py-oy)//TILE
    if 0 <= cx < COLS and 0 <= cy < ROWS:
        return cy,cx
    return None

def draw_board(mouse_held, hover):
    screen.fill(COLORS["bg"])

    # Header strip
    pygame.draw.rect(screen, (100,100,100), (0,0,SCREEN_W,HEADER))

    # Mines left
    text = big_font.render(f"Mines: {MINES - game.flags}", True, (255,255,255))
    screen.blit(text,(20,HEADER//2 - text.get_height()//2))

    # Timer
    tt = big_font.render(f"Time: {game.elapsed():03d}", True, (255,255,255))
    screen.blit(tt,(SCREEN_W - 140, HEADER//2 - tt.get_height()//2))

    # Face
    face_rect = pygame.Rect(SCREEN_W//2 - 24, HEADER//2 - 24, 48,48)
    face = SPR["face_smile"]
    if game.state == "lost": face = SPR["face_dead"]
    elif mouse_held: face = SPR["face_shock"]
    if face:
        screen.blit(face, face_rect.topleft)
    else:
        pygame.draw.rect(screen,(255,255,0), face_rect)

    # Grid
    for r in range(ROWS):
        for c in range(COLS):
            x = ox + c*TILE
            y = oy + r*TILE

            state = game.state_map[r][c]
            v = game.adj[r][c]

            rect = pygame.Rect(x,y,TILE,TILE)

            # COVERED
            if state == COVERED:
                screen.blit(SPR["covered"], (x,y))
                if mouse_held and hover == (r,c) and SPR["pressed"]:
                    screen.blit(SPR["pressed"], (x,y))

            # FLAGGED
            elif state == FLAGGED:
                screen.blit(SPR["covered"], (x,y))
                if SPR["flag"]:
                    screen.blit(SPR["flag"], (x,y))

            # REVEALED
            elif state == REVEALED:
                if game.pi_event and (r,c)==hover and SPR["pi"]:
                    screen.blit(SPR["pi"], (x,y))
                elif v == -1:
                    screen.blit(SPR["mine"], (x,y))
                elif v == 0:
                    screen.blit(SPR["empty"], (x,y))
                else:
                    screen.blit(SPR[str(v)], (x,y))

    pygame.display.flip()

# ===================== MAIN LOOP =====================
game = Game(ROWS,COLS,MINES)
mouse_held = False
hover = (-1,-1)
face_rect = pygame.Rect(SCREEN_W//2 - 24, HEADER//2 - 24, 48,48)

running = True
while running:
    clock.tick(FPS)
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False

        elif ev.type == pygame.MOUSEBUTTONDOWN:
            mx,my = ev.pos
            cell = cell_at(mx,my)
            if ev.button == 1:
                mouse_held = True
            elif ev.button == 3 and cell:
                r,c = cell
                game.toggle_flag(r,c)

        elif ev.type == pygame.MOUSEBUTTONUP:
            mx,my = ev.pos
            cell = cell_at(mx,my)
            if ev.button == 1:
                if face_rect.collidepoint((mx,my)):
                    game.reset()
                elif cell:
                    r,c = cell
                    game.reveal(r,c)
                mouse_held = False

        elif ev.type == pygame.MOUSEMOTION:
            mx,my = ev.pos
            hover = cell_at(mx,my) or (-1,-1)

    draw_board(mouse_held, hover)

pygame.quit()
sys.exit()
