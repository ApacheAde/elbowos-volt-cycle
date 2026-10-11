#!/usr/bin/env python3
"""Volt Cycle — neon light-cycle arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv

if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/VOLT_CYCLE_ElbowOS.mp4")
TITLE, HANDLE = "VOLT CYCLE", "x.com/ElbowOS"

# Palette
BG = (8, 4, 22)
GRID = (30, 18, 48)
CYAN = (0, 255, 240)
MAG = (255, 40, 180)
GOLD = (255, 220, 40)
LIME = (80, 255, 120)
WHITE = (240, 245, 255)
ORANGE = (255, 140, 40)

class Cycle:
    def __init__(self, x, y, dir, color):
        self.x, self.y = float(x), float(y)
        self.dir = dir  # 0=right,1=down,2=left,3=up
        self.speed = 8.0
        self.trail = [(x, y)]
        self.color = color
        self.alive = True
        self.score = 0
        self.boost = 0

    def turn(self, d):
        self.dir = (self.dir + d) % 4

    def step(self):
        if not self.alive:
            return
        dx, dy = [(self.speed, 0), (0, self.speed), (-self.speed, 0), (0, -self.speed)][self.dir]
        if self.boost > 0:
            dx *= 1.4
            dy *= 1.4
            self.boost -= 1
        self.x += dx
        self.y += dy
        # wrap? no, walls kill
        self.trail.append((self.x, self.y))
        if len(self.trail) > 400:
            self.trail.pop(0)

    def pos(self):
        return (self.x, self.y)

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            self.screen = pygame.display.set_mode((W, H), pygame.HIDDEN)
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("Arial", 96, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 54, bold=True)
        self.font_sm = pygame.font.SysFont("Arial", 36)
        self.reset()

    def reset(self):
        self.player = Cycle(W//2, H//2, 0, CYAN)
        self.orbs = []
        self.spawn_orbs(6)
        self.frame = 0
        self.running = True

    def spawn_orbs(self, n):
        for _ in range(n):
            self.orbs.append((random.randint(80, W-80), random.randint(200, H-200), random.choice([GOLD, LIME, ORANGE])))

    def check_collisions(self, c):
        # walls
        if c.x < 40 or c.x > W-40 or c.y < 160 or c.y > H-80:
            c.alive = False
            return
        # own trail (skip recent)
        for i, (tx, ty) in enumerate(c.trail[:-12]):
            if math.hypot(c.x - tx, c.y - ty) < 10:
                c.alive = False
                return
        # orbs
        for i, (ox, oy, col) in enumerate(self.orbs[:]):
            if math.hypot(c.x - ox, c.y - oy) < 28:
                c.score += 100
                c.boost = 40
                self.orbs.pop(i)
                if len(self.orbs) < 4:
                    self.spawn_orbs(2)

    def ai_control(self, c):
        # simple look-ahead avoid
        if not c.alive:
            return
        look = 60
        dx, dy = [(look,0),(0,look),(-look,0),(0,-look)][c.dir]
        nx, ny = c.x + dx, c.y + dy
        danger = (nx < 60 or nx > W-60 or ny < 180 or ny > H-100)
        if not danger:
            for tx, ty in c.trail[-80:-10]:
                if math.hypot(nx - tx, ny - ty) < 22:
                    danger = True
                    break
        if danger:
            # prefer left or right
            c.turn(random.choice([-1, 1]))
        elif random.random() < 0.02:
            c.turn(random.choice([-1, 1]))

    def draw(self, surf):
        surf.fill(BG)
        # faint grid
        for x in range(0, W, 60):
            pygame.draw.line(surf, GRID, (x, 140), (x, H), 1)
        for y in range(140, H, 60):
            pygame.draw.line(surf, GRID, (0, y), (W, y), 1)
        # border glow
        pygame.draw.rect(surf, CYAN, (30, 150, W-60, H-220), 4)
        # trail
        if len(self.player.trail) > 1:
            pts = [(int(x), int(y)) for x, y in self.player.trail]
            if len(pts) > 1:
                pygame.draw.lines(surf, self.player.color, False, pts, 6)
                # glow
                pygame.draw.lines(surf, (0, 180, 160), False, pts, 10)
        # head
        hx, hy = int(self.player.x), int(self.player.y)
        pygame.draw.circle(surf, WHITE, (hx, hy), 14)
        pygame.draw.circle(surf, self.player.color, (hx, hy), 10)
        # orbs
        for ox, oy, col in self.orbs:
            pygame.draw.circle(surf, col, (int(ox), int(oy)), 16)
            pygame.draw.circle(surf, WHITE, (int(ox), int(oy)), 6)
        # overlays
        title_s = self.font_big.render(TITLE, True, CYAN)
        surf.blit(title_s, (W//2 - title_s.get_width()//2, 40))
        sc_s = self.font_med.render(f"SCORE  {self.player.score}", True, GOLD)
        surf.blit(sc_s, (W//2 - sc_s.get_width()//2, 140))
        hand_s = self.font_sm.render(HANDLE, True, MAG)
        surf.blit(hand_s, (W//2 - hand_s.get_width()//2, H - 70))
        if not self.player.alive:
            over = self.font_med.render("CRASHED", True, ORANGE)
            surf.blit(over, (W//2 - over.get_width()//2, H//2))

    def update(self):
        self.frame += 1
        if RECORD:
            self.ai_control(self.player)
        self.player.step()
        self.check_collisions(self.player)
        if not self.player.alive and self.frame % 60 == 0:
            self.reset()  # keep action for video

    def play_interactive(self):
        while self.running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                if e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_LEFT, pygame.K_a):
                        self.player.turn(-1)
                    if e.key in (pygame.K_RIGHT, pygame.K_d):
                        self.player.turn(1)
                    if e.key == pygame.K_r:
                        self.reset()
            self.update()
            self.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def record(self):
        frames = FPS * SECS
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            "-movflags", "+faststart", "-an", OUT
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        for i in range(frames):
            self.update()
            self.draw(self.screen)
            raw = pygame.image.tostring(self.screen, "RGB")
            try:
                proc.stdin.write(raw)
            except BrokenPipeError:
                break
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "ignore")
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1500:]}")
        print("wrote", OUT)
        pygame.quit()

def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()

if __name__ == "__main__":
    main()
