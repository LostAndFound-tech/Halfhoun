#!/usr/bin/env python3
"""
Alter Wheel - Desktop Simulation
Uses pygame to simulate the NeoPixel ring display
"""
import pygame
import math
import time
import sys

# ── Window Setup ──
WINDOW_SIZE = 600
CENTER = WINDOW_SIZE // 2
LED_DRAW_RADIUS = 12
FPS = 60

# ── Ring Configuration ──
# Adjust these to match your actual hardware
RINGS = [
    {"start": 0,  "count": 1,  "radius": 0},
    {"start": 1,  "count": 8,  "radius": 30},
    {"start": 9,  "count": 12, "radius": 60},
    {"start": 21, "count": 16, "radius": 90},
    {"start": 37, "count": 24, "radius": 130},
    {"start": 61, "count": 32, "radius": 170},
]

NUM_LEDS = 93
HOST_RINGS = [0, 1, 2, 3]
HOST_BRIGHTNESS = 0.6
BALL_BRIGHTNESS = 1.0
GLOW_RADIUS = 50.0
BOUNDS_RADIUS = 170.0

# ── Color Utilities ──
def dim(color, brightness):
    return tuple(int(c * brightness) for c in color)

def blend(color1, color2, strength):
    return tuple(
        min(255, int(c1 * (1 - strength) + c2 * strength))
        for c1, c2 in zip(color1, color2)
    )

# ── LED Position Mapping ──
def build_led_map():
    led_positions = []
    for ring in RINGS:
        r = ring["radius"]
        for i in range(ring["count"]):
            if r == 0:
                x, y = 0.0, 0.0
            else:
                angle = (2 * math.pi * i) / ring["count"]
                x = r * math.cos(angle)
                y = r * math.sin(angle)
            led_positions.append({
                "x": x,
                "y": y,
                "ring": RINGS.index(ring),
                "color": (0, 0, 0)
            })
    return led_positions

# ── Alter Ball Physics ──
class AlterBall:
    def __init__(self, name, color, size=25.0):
        self.name = name
        self.color = color
        self.size = size
        self.x = 0.0
        self.y = 0.0
        self.vx = 50.0
        self.vy = 30.0
        self.glow_radius = GLOW_RADIUS
        self.trail = []
    
    def update(self, gravity_x, gravity_y, dt):
        # Apply gravity
        self.vx += gravity_x * dt
        self.vy += gravity_y * dt
        
        # Apply damping
        self.vx *= 0.995
        self.vy *= 0.995
        
        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Bounce off circular boundary
        dist = math.sqrt(self.x**2 + self.y**2)
        if dist > BOUNDS_RADIUS - self.size:
            nx = self.x / dist
            ny = self.y / dist
            dot = self.vx * nx + self.vy * ny
            self.vx -= 2 * dot * nx
            self.vy -= 2 * dot * ny
            self.vx *= 0.8
            self.vy *= 0.8
            self.x = nx * (BOUNDS_RADIUS - self.size) * 0.99
            self.y = ny * (BOUNDS_RADIUS - self.size) * 0.99
        
        # Store trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)

def check_ball_collisions(balls):
    for i in range(len(balls)):
        for j in range(i + 1, len(balls)):
            dx = balls[j].x - balls[i].x
            dy = balls[j].y - balls[i].y
            dist = math.sqrt(dx**2 + dy**2)
            min_dist = balls[i].size + balls[j].size
            
            if dist < min_dist and dist > 0:
                nx = dx / dist
                ny = dy / dist
                
                dv_x = balls[i].vx - balls[j].vx
                dv_y = balls[i].vy - balls[j].vy
                dot = dv_x * nx + dv_y * ny
                
                balls[i].vx -= dot * nx
                balls[i].vy -= dot * ny
                balls[j].vx += dot * nx
                balls[j].vy += dot * ny
                
                overlap = min_dist - dist
                balls[i].x -= overlap * 0.5 * nx
                balls[i].y -= overlap * 0.5 * ny
                balls[j].x += overlap * 0.5 * nx
                balls[j].y += overlap * 0.5 * ny

# ── Render LEDs ──
def calculate_led_colors(leds, host_color, balls):
    for led in leds:
        # Start with host field
        if led["ring"] in HOST_RINGS:
            color = dim(host_color, HOST_BRIGHTNESS)
        elif led["ring"] == 4:
            hc = ((host_color[0]/2) + 66, (host_color[1]/2) + 66, (host_color[2]/2) + 66)
            color = dim(hc, HOST_BRIGHTNESS)
        else:
            color = (66, 66, 66)
        
        # Layer alter balls
        for ball in balls:
            dx = led["x"] - ball.x
            dy = led["y"] - ball.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance < ball.size * 0.5:
                color = dim(ball.color, BALL_BRIGHTNESS)
            elif distance < ball.glow_radius:
                strength = 1.0 - (distance / ball.glow_radius)
                strength = strength ** 2
                color = blend(color, ball.color, strength * 0.7)
        
        led["color"] = color

# ── Host Transition ──
class HostTransition:
    def __init__(self):
        self.transitioning = False
        self.from_color = (0, 0, 0)
        self.to_color = (0, 0, 0)
        self.progress = 0.0
        self.duration = 2.0
    
    def start(self, from_color, to_color):
        self.transitioning = True
        self.from_color = from_color
        self.to_color = to_color
        self.progress = 0.0
    
    def update(self, dt):
        if not self.transitioning:
            return self.to_color
        
        self.progress += dt / self.duration
        if self.progress >= 1.0:
            self.progress = 1.0
            self.transitioning = False
        
        smooth = self.progress * self.progress * (3 - 2 * self.progress)
        return blend(self.from_color, self.to_color, smooth)

# ── Main ──
def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    pygame.display.set_caption("Alter Wheel Simulation")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 14)
    title_font = pygame.font.SysFont("monospace", 20, bold=True)
    
    leds = build_led_map()
    
    # ── Alter Definitions ──
    # CUSTOMIZE THESE
    alters = [
        {"name": "Princess",  "color": (255, 0, 119),   "host": True},
        {"name": "Oren",    "color": (122, 119, 120),   "host": False},
        {"name": "Kaylee",   "color": (96, 191, 191),   "host": False},
        {"name": "Solara",   "color": (189, 21, 21),   "host": False},
        {"name": "Count",  "color": (137, 173, 99),   "host": False},
    ]
    
    # Find host
    host = next(a for a in alters if a["host"])
    host_color = host["color"]
    transition = HostTransition()
    transition.to_color = host_color
    
    # Create balls for non-host alters
    balls = []
    non_hosts = [a for a in alters if not a["host"]]
    for i, alter in enumerate(non_hosts):
        ball = AlterBall(alter["name"], alter["color"])
        angle = (2 * math.pi * i) / max(len(non_hosts), 1)
        ball.x = 100 * math.cos(angle)
        ball.y = 100 * math.sin(angle)
        ball.vx = 40 * math.sin(angle)
        ball.vy = -40 * math.cos(angle)
        balls.append(ball)
    
    # Gravity (simulated accelerometer)
    gravity_x = 0.0
    gravity_y = 100.0
    gravity_strength = 150.0
    
    # Mouse gravity mode
    use_mouse_gravity = False
    
    running = True
    last_time = time.monotonic()
    
    while running:
        now = time.monotonic()
        dt = min(now - last_time, 0.05)
        last_time = now
        
        # ── Events ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                # Press M to toggle mouse gravity
                if event.key == pygame.K_m:
                    use_mouse_gravity = not use_mouse_gravity
                
                # Press 1-9 to switch host
                if pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(alters):
                        # Old host becomes ball
                        old_host = next(a for a in alters if a["host"])
                        old_host["host"] = False
                        new_ball = AlterBall(old_host["name"], old_host["color"])
                        new_ball.x = 0
                        new_ball.y = 0
                        new_ball.vx = 60
                        new_ball.vy = -40
                        balls.append(new_ball)
                        
                        # New host
                        new_host = alters[idx]
                        new_host["host"] = True
                        
                        # Remove new host from balls
                        balls = [b for b in balls if b.name != new_host["name"]]
                        
                        # Transition
                        transition.start(host_color, new_host["color"])
                        host_color = new_host["color"]
                
                # Press R to give balls a random kick
                if event.key == pygame.K_r:
                    import random
                    for ball in balls:
                        ball.vx += random.uniform(-100, 100)
                        ball.vy += random.uniform(-100, 100)
                
                # Press ESCAPE to quit
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # ── Gravity ──
        if use_mouse_gravity:
            mx, my = pygame.mouse.get_pos()
            gx = mx - CENTER
            gy = my - CENTER
            dist = math.sqrt(gx**2 + gy**2)
            if dist > 0:
                gravity_x = (gx / dist) * gravity_strength
                gravity_y = (gy / dist) * gravity_strength
        else:
            # Default gentle downward gravity
            gravity_x = 0
            gravity_y = gravity_strength
        
        # ── Update ──
        current_host_color = transition.update(dt)
        
        for ball in balls:
            ball.update(gravity_x, gravity_y, dt)
        check_ball_collisions(balls)
        
        calculate_led_colors(leds, current_host_color, balls)
        
        # ── Draw ──
        screen.fill((10, 10, 10))
        
        # Draw boundary circle
        pygame.draw.circle(
            screen, (30, 30, 30),
            (CENTER, CENTER),
            int(BOUNDS_RADIUS) + LED_DRAW_RADIUS + 5,
            2
        )
        
        # Draw LEDs
        for led in leds:
            sx = int(CENTER + led["x"])
            sy = int(CENTER + led["y"])
            
            # Glow effect behind LED
            glow_color = tuple(min(255, c // 3) for c in led["color"])
            if any(c > 10 for c in led["color"]):
                pygame.draw.circle(screen, glow_color, (sx, sy), LED_DRAW_RADIUS + 4)
            
            # LED itself
            pygame.draw.circle(screen, led["color"], (sx, sy), LED_DRAW_RADIUS)
            
            # LED outline
            pygame.draw.circle(screen, (40, 40, 40), (sx, sy), LED_DRAW_RADIUS, 1)
        
        # Draw ball positions (subtle indicator)
        # for ball in balls:
        #     bx = int(CENTER + ball.x)
        #     by = int(CENTER + ball.y)
        #     pygame.draw.circle(
        #         screen,
        #         tuple(min(255, c + 50) for c in ball.color),
        #         (bx, by),
        #         3
        #     )
        
        # ── UI Text ──
        y_offset = 10
        
        title = title_font.render("ALTER WHEEL SIMULATION", True, (200, 200, 200))
        screen.blit(title, (10, y_offset))
        y_offset += 30
        
        # Host display
        host_alter = next(a for a in alters if a["host"])
        host_text = font.render(f"HOST: {host_alter['name']}", True, host_alter["color"])
        screen.blit(host_text, (10, y_offset))
        y_offset += 20
        
        # Co-conscious
        for ball in balls:
            ball_text = font.render(f"  CO: {ball.name}", True, ball.color)
            screen.blit(ball_text, (10, y_offset))
            y_offset += 18
        
        y_offset += 10
        
        # Controls
        controls = [
            "─── Controls ───",
            "M: Toggle mouse gravity",
            "R: Random kick",
            "1-9: Switch host",
            "ESC: Quit",
        ]
        
        if use_mouse_gravity:
            controls.append("")
            controls.append("Mouse gravity: ON")
        
        for line in controls:
            ctrl_text = font.render(line, True, (100, 100, 100))
            screen.blit(ctrl_text, (10, y_offset))
            y_offset += 18
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()

if __name__ == "__main__":
    main()