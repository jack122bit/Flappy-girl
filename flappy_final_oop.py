# -*- coding: utf-8 -*-
# Flappy Bird Game - OOP Refactored - Final Touches (NameError check_collision FIX)

import pygame
import random
import os
import sys
import time
import math # For bird rotation

# Attempt to import vlc, handle failure gracefully
try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    print("--------------------------------------------------------------------")
    print("WARNING: python-vlc library not found. Background Music will be disabled.")
    print("         Install it using command: pip install python-vlc")
    # ... (rest of VLC warning messages)
    VLC_AVAILABLE = False; vlc = None
except Exception as import_err:
    print(f"--------------------------------------------------------------------")
    print(f"WARNING: Error importing vlc library: {import_err}\n         Background Music will be disabled.")
    # ... (rest of VLC warning messages)
    VLC_AVAILABLE = False; vlc = None

# --- Initialization ---
try:
    pygame.init()
    try: pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512); PYGAME_MIXER_OK = True; print("Pygame mixer initialized.")
    except pygame.error as mixer_err: print(f"Warning: Pygame mixer init failed: {mixer_err}. SFX disabled."); PYGAME_MIXER_OK = False
except pygame.error as pg_err: print(f"Fatal: Pygame init failed: {pg_err}"); sys.exit()

# --- Constants ---
WIDTH, HEIGHT = 400, 600
GRAVITY = 0.5
FLAP_STRENGTH = -9
PIPE_GAP_BASE = 160
PIPE_GAP_MIN = 100
PIPE_GAP_REDUCTION_FACTOR = 0.5
BASE_PIPE_SPEED = 3
PIPE_SPEED_INCREASE_FACTOR = 0.1
SCORE_INCREMENT = 1
TARGET_FPS = 60
BIRD_TOP_CLAMP_FACTOR = 0.5
BIRD_MAX_ROTATION = 25
BIRD_ROTATION_VELOCITY = 3
MARIO_TRIGGER_SCORE = 9000 # Lower for testing
MARIO_FALL_SPEED = 5
CREDITS_SCROLL_SPEED = 1
ANIMATION_SPEED_MS = 100
HIGH_SCORE_FILE = "highscore.txt"
GROUND_HEIGHT = 100
FLASH_DURATION = 150
RESTART_DELAY = 500

# Bird Size
BIRD_WIDTH, BIRD_HEIGHT = 40, 30
# Mario Size
MARIO_WIDTH, MARIO_HEIGHT = 40, 50

# Colors
WHITE = (255, 255, 255); BLACK = (0, 0, 0); GREEN = (0, 255, 0)
BLUE = (135, 206, 250); DARK_GRAY = (50, 50, 50); RED = (255, 0, 0)
SEMI_TRANSPARENT_BLACK = (0, 0, 0, 180)

# Game States
START_SCREEN = "START"; PLAYING = "PLAYING"; PAUSED = "PAUSED"
GAME_OVER = "GAME_OVER"; MARIO_EVENT = "MARIO_EVENT"; CREDITS = "CREDITS"

# --- Global Variables ---
vlc_instance = None; flap_sound = None; collision_sound = None; point_sound = None
bg_music_player = None; bg_music_file_path = None
SOUND_ENABLED = False; MUSIC_ENABLED = False
high_score = 0
credits_scroll_pos = HEIGHT
credits_lines = ["Flappy Bird Clone", "", "Enhanced Version", "", "Game By: You & AI", "", "Assets & Libraries:", "Pygame, python-vlc", "(Ensure assets are in Downloads)", "", "Press ESC to Quit"]


# --- Asset Finding Helper ---
def find_asset_path(filename_base, extensions):
    downloads_folder = None
    try: downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    except Exception: return None
    if not os.path.isdir(downloads_folder): return None
    for ext in extensions:
        path = os.path.join(downloads_folder, f"{filename_base}{ext}")
        if os.path.exists(path): return path
    return None

# --- High Score Handling ---
def load_high_score():
    try:
        if os.path.exists(HIGH_SCORE_FILE):
            with open(HIGH_SCORE_FILE, 'r') as f: return int(f.read().strip())
    except Exception: pass
    return 0

def save_high_score(new_high_score):
    # Define filepath function locally or move it globally if needed elsewhere
    def get_highscore_filepath():
        try:
            if getattr(sys, 'frozen', False): exe_dir = os.path.dirname(sys.executable); return os.path.join(exe_dir, HIGH_SCORE_FILE)
            else: script_dir = os.path.dirname(os.path.abspath(__file__)); return os.path.join(script_dir, HIGH_SCORE_FILE)
        except Exception: return HIGH_SCORE_FILE
    filepath = get_highscore_filepath()
    try:
        with open(filepath, 'w') as f: f.write(str(new_high_score))
        print(f"New high score saved: {new_high_score} to {filepath}")
    except Exception as e: print(f"Warning: Could not save high score to {filepath}: {e}")

# --- Audio Helper Functions (Defined globally for callbacks/simplicity) ---
def play_sound(sound_obj):
    global SOUND_ENABLED
    if SOUND_ENABLED and sound_obj:
        try: sound_obj.play()
        except Exception as e: print(f"SFX Play Error: {e}"); SOUND_ENABLED = False

def play_music():
    global MUSIC_ENABLED, vlc_instance, bg_music_player, bg_music_file_path
    if MUSIC_ENABLED and bg_music_player and vlc_instance and bg_music_file_path:
        try:
            state = bg_music_player.get_state()
            if state not in [vlc.State.Playing, vlc.State.Paused]:
                 media = vlc_instance.media_new(bg_music_file_path)
                 if media: bg_music_player.set_media(media); media.release(); bg_music_player.play()
                 else: MUSIC_ENABLED = False
        except Exception as e: print(f"Music Play Error: {e}"); MUSIC_ENABLED = False

def pause_music():
    if MUSIC_ENABLED and bg_music_player and bg_music_player.is_playing():
        try: bg_music_player.pause()
        except Exception: pass

def resume_music():
     global MUSIC_ENABLED
     if MUSIC_ENABLED and bg_music_player:
        try:
            if bg_music_player.get_state() == vlc.State.Paused: bg_music_player.pause() # Toggles
            elif bg_music_player.get_state() != vlc.State.Playing: play_music() # Restart
        except Exception: MUSIC_ENABLED = False

# --- Collision Check Functions (Defined globally) --- ## <<<< FIX: DEFINED HERE
def check_collision(b_rect, p_rect_list, pipe_w): # Pass pipe_w for efficiency
    """Collision: pipes or ground ONLY."""
    if not b_rect: return False
    if b_rect.bottom >= HEIGHT - GROUND_HEIGHT: return True # Use Ground Constant
    for pipe_rect in p_rect_list: # p_list now contains actual Rect objects
        # Optimization: Broad phase check (optional but can help)
        if pipe_rect.right > b_rect.left and pipe_rect.left < b_rect.right:
             if b_rect.colliderect(pipe_rect): return True # Pipe collision
    return False

def check_mario_collision(b_rect, m_rect):
    if m_rect and b_rect and b_rect.colliderect(m_rect): return True
    return False

# --- Bird Class ---
class Bird:
    def __init__(self, x, y, animation_images):
        self.start_x, self.start_y = x, y
        self.images = animation_images if animation_images else [pygame.Surface((BIRD_WIDTH, BIRD_HEIGHT), pygame.SRCALPHA)]
        if not animation_images: self.images[0].fill(GREEN)
        self.image = self.images[0]
        self.rect = self.image.get_rect(center=(x + BIRD_WIDTH / 2, y + BIRD_HEIGHT / 2))
        self.velocity = 0.0
        self.rotation = 0.0
        self.frame_index = 0
# -*- coding: utf-8 -*-
# Flappy Bird Game - OOP Refactored - Final (PyInstaller Downloads Fix)

import pygame
import random
import os
import sys
import time
import math # For bird rotation

# Attempt to import vlc, handle failure gracefully
try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    print("--------------------------------------------------------------------")
    print("WARNING: python-vlc library not found. Background Music will be disabled.")
    print("         Install it using command: pip install python-vlc")
    print("         You also need the VLC media player application installed.")
    print("--------------------------------------------------------------------")
    VLC_AVAILABLE = False; vlc = None
except Exception as import_err:
    print(f"--------------------------------------------------------------------")
    print(f"WARNING: Error importing vlc library: {import_err}\n         Background Music will be disabled.")
    print(f"--------------------------------------------------------------------")
    VLC_AVAILABLE = False; vlc = None

# --- Initialization ---
try:
    pygame.init()
    try: pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512); PYGAME_MIXER_OK = True; print("Pygame mixer initialized.")
    except pygame.error as mixer_err: print(f"Warning: Pygame mixer init failed: {mixer_err}. SFX disabled."); PYGAME_MIXER_OK = False
except pygame.error as pg_err: print(f"Fatal: Pygame init failed: {pg_err}"); sys.exit()

# --- Constants ---
WIDTH, HEIGHT = 400, 600
GRAVITY = 0.5
FLAP_STRENGTH = -9
PIPE_GAP_BASE = 160
PIPE_GAP_MIN = 100
PIPE_GAP_REDUCTION_FACTOR = 0.5
BASE_PIPE_SPEED = 3
PIPE_SPEED_INCREASE_FACTOR = 0.1
SCORE_INCREMENT = 1
TARGET_FPS = 60
BIRD_TOP_CLAMP_FACTOR = 0.5
BIRD_MAX_ROTATION = 25
BIRD_ROTATION_VELOCITY = 3
MARIO_TRIGGER_SCORE = 9000 # Lower for testing
MARIO_FALL_SPEED = 5
CREDITS_SCROLL_SPEED = 1
ANIMATION_SPEED_MS = 100
HIGH_SCORE_FILE = "highscore.txt" # Filename for high score
GROUND_HEIGHT = 100
FLASH_DURATION = 150
RESTART_DELAY = 500

# Bird Size
BIRD_WIDTH, BIRD_HEIGHT = 40, 30
# Mario Size
MARIO_WIDTH, MARIO_HEIGHT = 40, 50

# Colors
WHITE = (255, 255, 255); BLACK = (0, 0, 0); GREEN = (0, 255, 0)
BLUE = (135, 206, 250); DARK_GRAY = (50, 50, 50); RED = (255, 0, 0)
SEMI_TRANSPARENT_BLACK = (0, 0, 0, 180)

# Game States
START_SCREEN = "START"; PLAYING = "PLAYING"; PAUSED = "PAUSED"
GAME_OVER = "GAME_OVER"; MARIO_EVENT = "MARIO_EVENT"; CREDITS = "CREDITS"

# --- Global Variables ---
# Audio
vlc_instance = None; flap_sound = None; collision_sound = None; point_sound = None
bg_music_player = None; bg_music_file_path = None
SOUND_ENABLED = False; MUSIC_ENABLED = False
# Score
high_score = 0
# Credits
credits_scroll_pos = HEIGHT
credits_lines = ["Flappy Bird Clone", "", "Enhanced Version", "", "Game By: You & AI", "", "Assets & Libraries:", "Pygame, python-vlc", "(Ensure assets are in Downloads)", "", "Press ESC to Quit"]


# --- Helper Functions (PyInstaller Aware - Downloads for Dev) --- ## <<<< UPDATED SECTION
def resource_path(relative_path):
    """ Get absolute path to resource.
        Looks in Downloads during development (running .py),
        and in PyInstaller's temporary folder when frozen (.exe).
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        # When frozen, the relative path is just the filename because
        # we add data files to the root of the bundle using '.'
        # print(f"Frozen mode detected, using base path: {base_path}") # Debug
    except Exception:
        # Not frozen (running as .py): look in the Downloads folder
        try:
            base_path = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.isdir(base_path):
                 print(f"WARNING: Downloads folder not found at {base_path}. Trying script directory.")
                 base_path = os.path.dirname(os.path.abspath(__file__)) # Fallback to script dir
            # print(f"Development mode, using Downloads/Fallback path: {base_path}") # Debug
        except Exception as e:
             print(f"Warning: Error getting Downloads/script path: {e}. Using current directory as fallback.")
             base_path = "." # Fallback to current directory

    return os.path.join(base_path, relative_path)

def find_asset_path(filename_base, extensions):
    """Tries to find a file relative to appropriate base path using resource_path."""
    for ext in extensions:
        # The relative path is just the filename itself now
        relative_file = f"{filename_base}{ext}"
        try:
            full_path = resource_path(relative_file) # resource_path handles base dir
            # print(f"Checking path: {full_path}") # Debug
            if os.path.exists(full_path):
                # print(f"Found asset: {full_path}") # Reduce spam
                return full_path
        except Exception as e:
            print(f"Error constructing path for {relative_file}: {e}")
            continue
    # print(f"Asset not found: '{filename_base}' with extensions {extensions}") # Reduce spam
    return None

# --- High Score Handling (PyInstaller Aware - Saves next to EXE/Script) --- ## <<<< UPDATED SECTION
def get_highscore_filepath():
    """ Determines the path for the highscore file (next to exe or script). """
    try:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'): # Running as bundled app
             exe_dir = os.path.dirname(sys.executable)
             return os.path.join(exe_dir, HIGH_SCORE_FILE)
        else: # Running as script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(script_dir, HIGH_SCORE_FILE)
    except Exception:
        print("Warning: Could not determine optimal high score path. Using current directory.")
        return HIGH_SCORE_FILE # Fallback

def load_high_score():
    filepath = get_highscore_filepath()
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f: return int(f.read().strip())
    except Exception as e:
        print(f"Warning: Could not read or parse high score from '{filepath}': {e}")
    return 0

def save_high_score(new_high_score):
    filepath = get_highscore_filepath()
    try:
        with open(filepath, 'w') as f: f.write(str(new_high_score))
        print(f"New high score saved: {new_high_score} to {filepath}")
    except Exception as e: print(f"Warning: Could not save high score to {filepath}: {e}")

# --- Set up Display (Moved after helpers, before Game class needs it) ---
screen = None
try:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Flappy Bird OOP - Final")
    print("Display mode set successfully.")
except pygame.error as display_err: print(f"Fatal Error: Could not set display mode: {display_err}"); pygame.quit(); sys.exit()

# --- Bird Class ---
# (Bird class remains the same)
class Bird:
    def __init__(self, x, y, animation_images):
        self.start_x, self.start_y = x, y
        self.images = animation_images if animation_images else [pygame.Surface((BIRD_WIDTH, BIRD_HEIGHT), pygame.SRCALPHA)]
        if not animation_images: self.images[0].fill(GREEN)
        self.image = self.images[0]
        self.rect = self.image.get_rect(center=(x + BIRD_WIDTH / 2, y + BIRD_HEIGHT / 2))
        self.velocity = 0.0; self.rotation = 0.0; self.frame_index = 0
        self.last_animation_time = pygame.time.get_ticks()
    def flap(self):
        self.velocity = float(FLAP_STRENGTH); self.rotation = float(BIRD_MAX_ROTATION + 5)
    def update(self):
        self.velocity += GRAVITY; self.rect.y += self.velocity
        self.rect.top = max(self.rect.top, -BIRD_HEIGHT * BIRD_TOP_CLAMP_FACTOR)
        if len(self.images) > 1:
            now = pygame.time.get_ticks()
            if now - self.last_animation_time > ANIMATION_SPEED_MS:
                self.frame_index = (self.frame_index + 1) % len(self.images)
                self.last_animation_time = now
            self.image = self.images[self.frame_index]
        if self.velocity > 1: self.rotation -= BIRD_ROTATION_VELOCITY
        else: self.rotation += BIRD_ROTATION_VELOCITY * 1.5
        self.rotation = max(-90.0, min(self.rotation, float(BIRD_MAX_ROTATION)))
    def get_rotated(self):
        current_image = self.image if self.image else self.images[0]
        rotated_image = pygame.transform.rotate(current_image, self.rotation)
        new_rect = rotated_image.get_rect(center=self.rect.center)
        return rotated_image, new_rect
    def draw(self, surface):
        rotated_image, rotated_rect = self.get_rotated()
        surface.blit(rotated_image, (round(rotated_rect.x), round(rotated_rect.y)))
    def reset(self):
        self.rect.center = (self.start_x + BIRD_WIDTH / 2, self.start_y + BIRD_HEIGHT / 2)
        self.velocity = 0.0; self.rotation = 0.0; self.frame_index = 0
        self.last_animation_time = pygame.time.get_ticks()
        self.image = self.images[self.frame_index]


# --- Pipe Manager Class ---
# (PipeManager class remains the same)
class PipeManager:
    def __init__(self, pipe_img_surface, game_instance):
        self.pipe_img = pipe_img_surface
        self.game = game_instance
        self.pipe_width = self.pipe_img.get_width() if self.pipe_img else 50
        self.pipe_height = self.pipe_img.get_height() if self.pipe_img else HEIGHT
        self.pipes = []
        self.spacing = 250.0
        self.current_speed = float(BASE_PIPE_SPEED)
        self._create_initial_pipes()
    def _create_pipe_pair(self, x_pos):
        gap_reduction = (self.game.score // 15) * PIPE_GAP_REDUCTION_FACTOR
        current_gap = max(PIPE_GAP_MIN, PIPE_GAP_BASE - gap_reduction)
        min_h, max_h = 60, HEIGHT - GROUND_HEIGHT - current_gap - 60
        if max_h <= min_h: max_h = min_h + 10
        max_h_int = int(max_h)
        h_upper = random.randint(min_h, max_h_int)
        h_lower = HEIGHT - GROUND_HEIGHT - (h_upper + current_gap)
        y_lower = h_upper + current_gap
        upper_rect = pygame.Rect(round(x_pos), 0, self.pipe_width, h_upper)
        lower_rect = pygame.Rect(round(x_pos), round(y_lower), self.pipe_width, round(h_lower))
        return {'upper': upper_rect, 'lower': lower_rect, 'passed': False, 'x': float(x_pos)}
    def _create_initial_pipes(self):
        self.pipes.append(self._create_pipe_pair(float(WIDTH + 100)))
        self.pipes.append(self._create_pipe_pair(float(WIDTH + 100) + self.spacing))
    def update(self, bird_rect):
        score_increase = 0
        speed_increase = (self.game.score // 10) * PIPE_SPEED_INCREASE_FACTOR
        self.current_speed = min(float(BASE_PIPE_SPEED) + speed_increase, float(BASE_PIPE_SPEED) * 2.5)
        self.spacing = 250.0 + (self.current_speed - BASE_PIPE_SPEED) * 5.0
        for pipe in self.pipes:
            pipe['x'] -= self.current_speed
            pipe['upper'].x = round(pipe['x'])
            pipe['lower'].x = round(pipe['x'])
            if not pipe['passed'] and bird_rect and pipe['upper'].right < bird_rect.left:
                score_increase += SCORE_INCREMENT; pipe['passed'] = True
                self.game.play_sfx(point_sound)
        self.pipes = [p for p in self.pipes if p['upper'].right > 0]
        if not self.pipes or self.pipes[-1]['upper'].x < WIDTH - self.spacing:
            self.pipes.append(self._create_pipe_pair(float(WIDTH)))
        return score_increase
    def draw(self, surface):
        for p in self.pipes:
            if self.pipe_img:
                upper_draw_y = p['upper'].height - self.pipe_height
                surface.blit(self.pipe_img, (p['upper'].x, round(upper_draw_y)))
                lower_draw_y = p['lower'].y
                draw_height = min(p['lower'].height, self.pipe_height)
                surface.blit(self.pipe_img, (p['lower'].x, round(lower_draw_y)), area=(0, 0, self.pipe_width, round(draw_height)))
            else: # Fallback
                pygame.draw.rect(surface, DARK_GRAY, p['upper'])
                pygame.draw.rect(surface, DARK_GRAY, p['lower'])
    def get_collision_rects(self):
        return [p['upper'] for p in self.pipes] + [p['lower'] for p in self.pipes]
    def reset(self):
        self.pipes = []; self.current_speed = float(BASE_PIPE_SPEED); self.spacing = 250.0
        self._create_initial_pipes()

# --- Background Manager Class ---
# (BackgroundManager class remains the same)
class BackgroundManager:
    def __init__(self, bg_img, ground_img):
        self.bg_image = bg_img; self.ground_image = ground_img
        self.bg_width = self.bg_image.get_width() if self.bg_image else WIDTH
        self.bg_x1 = 0.0; self.bg_x2 = float(self.bg_width)
        self.ground_height = GROUND_HEIGHT
        self.ground_width = self.ground_image.get_width() if self.ground_image else WIDTH
        self.ground_x1 = 0.0; self.ground_x2 = float(self.ground_width)
        self.ground_y = HEIGHT - self.ground_height
        self.current_scroll_speed = float(BASE_PIPE_SPEED)
    def update(self, speed):
        self.current_scroll_speed = float(speed)
        if self.bg_image:
            scroll_speed_bg = max(1.0, self.current_scroll_speed * 0.3)
            self.bg_x1 -= scroll_speed_bg; self.bg_x2 -= scroll_speed_bg
            if self.bg_x1 <= -self.bg_width: self.bg_x1 = self.bg_x2 + self.bg_width
            if self.bg_x2 <= -self.bg_width: self.bg_x2 = self.bg_x1 + self.bg_width
        if self.ground_image:
            scroll_speed_ground = self.current_scroll_speed
            self.ground_x1 -= scroll_speed_ground; self.ground_x2 -= scroll_speed_ground
            if self.ground_x1 <= -self.ground_width: self.ground_x1 = self.ground_x2 + self.ground_width
            if self.ground_x2 <= -self.ground_width: self.ground_x2 = self.ground_x1 + self.ground_width
    def draw(self, surface):
        if self.bg_image:
            surface.blit(self.bg_image, (round(self.bg_x1), 0)); surface.blit(self.bg_image, (round(self.bg_x2), 0))
        else: surface.fill(BLUE)
        if self.ground_image:
            surface.blit(self.ground_image, (round(self.ground_x1), self.ground_y)); surface.blit(self.ground_image, (round(self.ground_x2), self.ground_y))
        else: pygame.draw.rect(surface, GREEN, (0, self.ground_y, WIDTH, self.ground_height))
    def reset(self):
        self.bg_x1 = 0.0; self.bg_x2 = float(self.bg_width); self.ground_x1 = 0.0; self.ground_x2 = float(self.ground_width)
        self.current_scroll_speed = float(BASE_PIPE_SPEED)

# --- UI Manager Class ---
# (UIManager class remains the same)
class UIManager:
    def __init__(self, normal_font, big_font): self.font = normal_font; self.big_font = big_font; self.resume_button_rect = None
    def _render_text(self, txt, fnt, clr, center_pos=None, topleft_pos=None):
        if fnt:
            try: surf = fnt.render(str(txt), True, clr); rect = surf.get_rect(center=center_pos) if center_pos else surf.get_rect(topleft=topleft_pos if topleft_pos else (0,0)); return surf, rect
            except Exception: pass
        return None, None
    def draw_start_screen(self, surface, high_score_value):
        title_surf, title_rect = self._render_text("Flappy Bird", self.big_font, BLACK, center_pos=(WIDTH // 2, HEIGHT // 4))
        instr_surf, instr_rect = self._render_text("Press SPACE to Start", self.font, BLACK, center_pos=(WIDTH // 2, HEIGHT // 2))
        hs_surf, hs_rect = self._render_text(f"High Score: {high_score_value}", self.font, BLACK, center_pos=(WIDTH // 2, HEIGHT * 3 // 4))
        if title_surf: surface.blit(title_surf, title_rect)
        if instr_surf: surface.blit(instr_surf, instr_rect)
        if hs_surf: surface.blit(hs_surf, hs_rect)
    def draw_playing_ui(self, surface, score_value, high_score_value):
        score_surf, score_rect = self._render_text(f"Score: {score_value}", self.font, BLACK, topleft_pos=(10, 10))
        hs_surf, hs_rect = self._render_text(f"Hi: {high_score_value}", self.font, BLACK)
        if score_surf: surface.blit(score_surf, score_rect)
        if hs_surf: hs_rect.topright = (WIDTH - 10, 10); surface.blit(hs_surf, hs_rect)
    def draw_pause_overlay(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(SEMI_TRANSPARENT_BLACK); surface.blit(overlay, (0, 0))
        pause_surf, pause_rect = self._render_text("Paused", self.big_font, WHITE, center_pos=(WIDTH // 2, HEIGHT // 3))
        if pause_surf: surface.blit(pause_surf, pause_rect)
        self.resume_button_rect = pygame.Rect(0, 0, 150, 50); self.resume_button_rect.center = (WIDTH // 2, HEIGHT // 2)
        pygame.draw.rect(surface, DARK_GRAY, self.resume_button_rect, border_radius=10)
        pygame.draw.rect(surface, WHITE, self.resume_button_rect, width=2, border_radius=10)
        res_surf, res_rect = self._render_text("Resume", self.font, WHITE, center_pos=self.resume_button_rect.center)
        if res_surf: surface.blit(res_surf, res_rect)
        return self.resume_button_rect
    def draw_game_over_screen(self, surface, score_value, high_score_value, is_new_high):
        go_surf, go_rect = self._render_text("Game Over!", self.big_font, WHITE, center_pos=(WIDTH // 2, HEIGHT // 3))
        nhs_surf, nhs_rect = (self._render_text("New High Score!", self.font, RED, center_pos=(WIDTH // 2, HEIGHT // 2 - 50))) if is_new_high else (None, None)
        score_surf, score_rect = self._render_text(f"Score: {score_value}", self.font, WHITE, center_pos=(WIDTH // 2, HEIGHT // 2 - 10))
        hs_surf, hs_rect = self._render_text(f"High Score: {high_score_value}", self.font, WHITE, center_pos=(WIDTH // 2, HEIGHT // 2 + 30))
        instr_surf, instr_rect = self._render_text("Press SPACE to Restart", self.font, WHITE, center_pos=(WIDTH // 2, HEIGHT * 2 // 3 + 20))
        all_rects = [r for r in [go_rect, score_rect, hs_rect, instr_rect, nhs_rect] if r]
        if not all_rects: return
        min_y, max_y = min(r.top for r in all_rects), max(r.bottom for r in all_rects)
        h = max_y - min_y + 60
        bg_rect = pygame.Rect(0, 0, WIDTH * 0.85, h); bg_rect.center = (WIDTH // 2, HEIGHT // 2)
        pygame.draw.rect(surface, BLACK, bg_rect, border_radius=15)
        if go_surf: surface.blit(go_surf, go_rect)
        if is_new_high and nhs_surf: surface.blit(nhs_surf, nhs_rect)
        if score_surf: surface.blit(score_surf, score_rect)
        if hs_surf: surface.blit(hs_surf, hs_rect)
        if instr_surf: surface.blit(instr_surf, instr_rect)
    def draw_credits(self, surface, scroll_pos, lines):
        surface.fill(BLACK)
        line_h = self.font.get_linesize() if self.font else 25
        for i, line in enumerate(lines):
            y = scroll_pos + i * line_h
            if -line_h < y < HEIGHT:
                 surf, rect = self._render_text(line, self.font, WHITE, center_pos=(WIDTH // 2, round(y)))
                 if surf: surface.blit(surf, rect)
        quit_surf, quit_rect = self._render_text("Press ESC to Quit", self.font, WHITE, center_pos=(WIDTH // 2, HEIGHT - 30))
        if quit_surf: surface.blit(quit_surf, quit_rect)
    def draw_flash(self, surface):
        flash_surface = pygame.Surface((WIDTH, HEIGHT)); flash_surface.fill(WHITE); flash_surface.set_alpha(150)
        surface.blit(flash_surface, (0, 0))


# --- Game Class ---
class Game:
    def __init__(self):
        if not pygame.get_init(): pygame.init()
        if not pygame.display.get_init(): pygame.display.init()
        if not pygame.font.get_init(): pygame.font.init()
        if not pygame.mixer.get_init() and PYGAME_MIXER_OK: pygame.mixer.init()

        try: self.screen = pygame.display.set_mode((WIDTH, HEIGHT)); pygame.display.set_caption("Flappy Bird OOP - Final")
        except pygame.error as e: print(f"Fatal: Display mode failed: {e}"); pygame.quit(); sys.exit()

        self.clock = pygame.time.Clock()
        self.running = True
        self.game_state = START_SCREEN
        self.score = 0
        self.assets = self._load_assets()
        self._load_audio()

        self.bird = Bird(50, HEIGHT // 2, self.assets['bird_images'])
        self.pipe_manager = PipeManager(self.assets['pipe'], self)
        self.background_manager = BackgroundManager(self.assets['background'], self.assets['ground'])
        self.ui_manager = UIManager(self.assets['font'], self.assets['big_font'])

        self.mario_img = self.assets['mario']
        self.mario_x = WIDTH // 2 - MARIO_WIDTH // 2
        self.mario_y = -MARIO_HEIGHT
        self.mario_rect = self.mario_img.get_rect(topleft=(self.mario_x, self.mario_y)) if self.mario_img else None

        self.high_score = load_high_score()
        self.credits_scroll_pos = float(HEIGHT)
        self.credits_lines = credits_lines

        self.death_time = 0; self.show_flash = False; self.new_high_score_flag = False

    def _load_assets(self):
        # (Asset loading logic - unchanged)
        print("-" * 10 + " Loading Game Assets " + "-" * 10)
        assets = {'bird_images': [], 'pipe': None, 'background': None, 'ground': None, 'mario': None, 'font': None, 'big_font': None}
        # ... [Rest of image loading logic] ...
        downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        print(f"Searching in: {downloads_folder}")
        try:
            bird_paths = [find_asset_path(f"bird_{n}", [".png"]) for n in ["down", "mid", "up"]]
            pipe_path, bg_path = find_asset_path("pipe", [".png"]), find_asset_path("background", [".png"])
            mario_path, ground_path = find_asset_path("mario", [".png"]), find_asset_path("ground", [".png"])
            bird_frames_loaded = False
            if all(bird_paths): assets['bird_images'] = [pygame.transform.scale(pygame.image.load(p).convert_alpha(), (BIRD_WIDTH, BIRD_HEIGHT)) for p in bird_paths]; bird_frames_loaded = True;
            else: print(" - Bird anim frames missing.")
            if pipe_path: assets['pipe'] = pygame.image.load(pipe_path).convert_alpha();
            else: print(" - Pipe fail.")
            if bg_path: assets['background'] = pygame.image.load(bg_path).convert();
            else: print(" - Background fail.")
            if ground_path: assets['ground'] = pygame.image.load(ground_path).convert_alpha();
            else: print(" - Ground fail.")
            if mario_path: assets['mario'] = pygame.transform.scale(pygame.image.load(mario_path).convert_alpha(), (MARIO_WIDTH, MARIO_HEIGHT));
            else: print(" - Mario fail.")
            if not (bird_frames_loaded and assets['pipe'] and assets['mario'] and assets['ground']): print("Using fallback for core missing images.")
            elif not assets['background']: print(" - Using fallback background.")
            else: print("Core images loaded.")
        except Exception as e: print(f" Img Load Err: {e}. Using Fallbacks.")
        if not assets['bird_images']: bf = pygame.Surface((BIRD_WIDTH,BIRD_HEIGHT),pygame.SRCALPHA); bf.fill(GREEN); assets['bird_images']=[bf]*3; print(" Fallback bird.")
        if assets['pipe'] is None: assets['pipe'] = pygame.Surface((50, HEIGHT)); assets['pipe'].fill(DARK_GRAY); print(" Fallback pipe.")
        if assets['background'] is None: assets['background'] = pygame.Surface((WIDTH, HEIGHT)); assets['background'].fill(BLUE); print(" Fallback background.")
        if assets['ground'] is None: assets['ground'] = pygame.Surface((WIDTH,GROUND_HEIGHT)); assets['ground'].fill(GREEN); print(" Fallback ground.")
        if assets['mario'] is None: assets['mario'] = pygame.Surface((MARIO_WIDTH,MARIO_HEIGHT),pygame.SRCALPHA); assets['mario'].fill(RED); print(" Fallback Mario.")
        try: assets['font'] = pygame.font.Font(None, 36); assets['big_font'] = pygame.font.Font(None, 60); assert assets['font'] and assets['big_font']
        except Exception: print("Warn: Font load fail. Text disabled."); assets['font']=None; assets['big_font']=None
        print("-" * 38)
        return assets

    def _load_audio(self):
        # (Audio loading logic - unchanged)
        global flap_sound, collision_sound, point_sound, bg_music_player, vlc_instance, bg_music_file_path, SOUND_ENABLED, MUSIC_ENABLED
        if PYGAME_MIXER_OK:
            try:
                print("Loading SFX (Pygame - WAV)...")
                fs_path, cs_path = find_asset_path("flap", [".wav"]), find_asset_path("collision", [".wav"])
                pt_path = find_asset_path("point", [".wav"])
                sfx_ok = True
                if fs_path: flap_sound = pygame.mixer.Sound(fs_path)
                else: print(" - flap.wav missing."); sfx_ok = False
                if cs_path: collision_sound = pygame.mixer.Sound(cs_path)
                else: print(" - collision.wav missing."); sfx_ok = False
                if pt_path: point_sound = pygame.mixer.Sound(pt_path)
                else: print(" - point.wav missing."); sfx_ok = False
                SOUND_ENABLED = sfx_ok
                if SOUND_ENABLED: print("SFX loaded.")
                else: print("SFX disabled.")
            except Exception as e: print(f" SFX Load Err: {e}. Disabled."); SOUND_ENABLED = False
        else: print("SFX disabled."); SOUND_ENABLED = False
        if VLC_AVAILABLE:
            try:
                print("Loading Music (VLC - WAV)...")
                bg_music_path = find_asset_path("background_music", [".wav"])
                bg_music_file_path = bg_music_path
                if bg_music_path:
                    if vlc is None: raise ImportError()
                    vlc_instance = vlc.Instance('--no-xlib --quiet')
                    if not vlc_instance: raise RuntimeError()
                    bg_music_player = vlc_instance.media_player_new()
                    if not bg_music_player: raise RuntimeError()

                    def restart_music_callback(event):
                        global vlc_instance, bg_music_player, bg_music_file_path, MUSIC_ENABLED
                        if bg_music_player and vlc_instance and bg_music_file_path:
                            try:
                                media = vlc_instance.media_new(bg_music_file_path)
                                if media: bg_music_player.set_media(media); media.release(); bg_music_player.play()
                                else: MUSIC_ENABLED = False
                            except Exception: MUSIC_ENABLED = False
                        else: MUSIC_ENABLED = False

                    ev_mgr = bg_music_player.event_manager()
                    if ev_mgr:
                        ev_mgr.event_attach(vlc.EventType.MediaPlayerEndReached, restart_music_callback)
                        media = vlc_instance.media_new(bg_music_path)
                        if media: bg_music_player.set_media(media); media.release(); print("Music loaded."); MUSIC_ENABLED = True
                        else: print("Error: Music media create failed."); MUSIC_ENABLED = False
                    else: print("Warn: VLC event manager failed."); MUSIC_ENABLED = False
                else: print(" - background_music.wav missing."); MUSIC_ENABLED = False
            except Exception as e:
                print(f" Music Load Warn: Err:{e}. Disabled.")
                if bg_music_player: bg_music_player.release(); bg_music_player = None
                if vlc_instance: vlc_instance.release(); vlc_instance = None
                MUSIC_ENABLED = False
        else: print("Music disabled."); MUSIC_ENABLED = False
        print("-" * 38)

    # --- Audio Playback Methods ---
    def play_sfx(self, sound_obj): play_sound(sound_obj)
    def play_bg_music(self): play_music()
    def pause_bg_music(self): pause_music()
    def resume_bg_music(self): resume_music()

    # --- Game State Management ---
    def set_state(self, new_state):
        print(f"State: {self.game_state} -> {new_state}")
        self.game_state = new_state
        if new_state == CREDITS:
            self.credits_scroll_pos = float(HEIGHT)

    def initialize_and_reset(self):
        global high_score
        print("\n--- Resetting Game ---")
        self.new_high_score_flag = False
        self.bird.reset()
        self.pipe_manager.reset()
        self.background_manager.reset()
        self.score = 0
        self.mario_y = -MARIO_HEIGHT
        if self.mario_rect: self.mario_rect.topleft = (self.mario_x, self.mario_y)
        self.death_time = 0; self.show_flash = False
        self.set_state(PLAYING)
        self.play_bg_music()

    # --- Core Game Loop Methods ---
    def handle_events(self):
        clicked = False; mouse_pos = pygame.mouse.get_pos(); current_time = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: clicked = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.game_state == CREDITS: self.running = False
                    elif self.game_state == PLAYING: self.set_state(PAUSED); self.pause_bg_music()
                    elif self.game_state == PAUSED: self.set_state(PLAYING); self.resume_bg_music()
                elif self.game_state == START_SCREEN and event.key == pygame.K_SPACE:
                    self.initialize_and_reset()
                elif self.game_state == PLAYING:
                    if event.key == pygame.K_SPACE: self.bird.flap(); self.play_sfx(flap_sound)
                    elif event.key == pygame.K_p: self.set_state(PAUSED); self.pause_bg_music()
                elif self.game_state == PAUSED and event.key == pygame.K_p: self.set_state(PLAYING); self.resume_bg_music()
                elif self.game_state == GAME_OVER and event.key == pygame.K_SPACE:
                    if current_time - self.death_time > RESTART_DELAY: self.initialize_and_reset()
        if self.game_state == PAUSED and clicked and self.ui_manager.resume_button_rect:
             if self.ui_manager.resume_button_rect.collidepoint(mouse_pos): self.set_state(PLAYING); self.resume_bg_music()

    def update(self):
        global high_score

        if self.game_state == PLAYING:
            self.bird.update()
            score_increase = self.pipe_manager.update(self.bird.rect)
            self.score += score_increase
            self.background_manager.update(self.pipe_manager.current_speed)

            pipe_rects = self.pipe_manager.get_collision_rects()
            if check_collision(self.bird.rect, pipe_rects, self.pipe_manager.pipe_width): # Pass width
                self.play_sfx(collision_sound)
                self.new_high_score_flag = (self.score > high_score)
                if self.new_high_score_flag: high_score = self.score; save_high_score(high_score)
                self.death_time = pygame.time.get_ticks()
                self.show_flash = True
                self.set_state(GAME_OVER)
                if MUSIC_ENABLED and bg_music_player: bg_music_player.stop()

            if self.score >= MARIO_TRIGGER_SCORE:
                 print("MARIO TIME!")
                 self.new_high_score_flag = (self.score > high_score)
                 if self.new_high_score_flag: high_score = self.score; save_high_score(high_score)
                 self.set_state(MARIO_EVENT)
                 self.mario_y = -MARIO_HEIGHT
                 self.mario_x = self.bird.rect.centerx - MARIO_WIDTH // 2 if self.bird.rect else WIDTH // 2 - MARIO_WIDTH // 2
                 if self.mario_rect: self.mario_rect.topleft = (self.mario_x, self.mario_y)
                 if MUSIC_ENABLED and bg_music_player: bg_music_player.stop()

        elif self.game_state == MARIO_EVENT:
            if self.mario_rect:
                self.mario_y += MARIO_FALL_SPEED
                self.mario_rect.topleft = (self.mario_x, self.mario_y)
                if self.bird.rect and check_mario_collision(self.bird.rect, self.mario_rect):
                    print("Mario caught the bird!")
                    self.new_high_score_flag = (self.score > high_score)
                    if self.new_high_score_flag: high_score = self.score; save_high_score(high_score)
                    self.set_state(CREDITS)

        elif self.game_state in [START_SCREEN, PAUSED, GAME_OVER]:
             speed = self.pipe_manager.current_speed if self.game_state != START_SCREEN else BASE_PIPE_SPEED
             self.background_manager.update(speed)

        elif self.game_state == CREDITS:
            self.credits_scroll_pos -= CREDITS_SCROLL_SPEED

    def draw(self):
        self.background_manager.draw(self.screen)
        if self.game_state == START_SCREEN:
            self.ui_manager.draw_start_screen(self.screen, high_score)
        elif self.game_state == PLAYING:
            self.pipe_manager.draw(self.screen)
            self.bird.draw(self.screen)
            self.ui_manager.draw_playing_ui(self.screen, self.score, high_score)
        elif self.game_state == PAUSED:
            self.pipe_manager.draw(self.screen)
            self.bird.draw(self.screen)
            self.ui_manager.draw_playing_ui(self.screen, self.score, high_score)
            resume_btn_rect = self.ui_manager.draw_pause_overlay(self.screen) # Store returned rect if needed elsewhere
        elif self.game_state == GAME_OVER:
             self.pipe_manager.draw(self.screen)
             self.bird.draw(self.screen)
             self.ui_manager.draw_game_over_screen(self.screen, self.score, high_score, self.new_high_score_flag)
             current_time = pygame.time.get_ticks()
             if self.show_flash and current_time - self.death_time < FLASH_DURATION: self.ui_manager.draw_flash(self.screen)
             elif self.show_flash: self.show_flash = False
        elif self.game_state == MARIO_EVENT:
             self.pipe_manager.draw(self.screen)
             self.bird.draw(self.screen)
             if self.mario_rect and self.mario_img: self.screen.blit(self.mario_img, self.mario_rect)
             self.ui_manager.draw_playing_ui(self.screen, self.score, high_score)
        elif self.game_state == CREDITS:
            self.ui_manager.draw_credits(self.screen, self.credits_scroll_pos, self.credits_lines)
        pygame.display.flip()

    def run(self):
        global high_score
        print("\n--- Starting Game Loop ---")
        high_score = load_high_score()

        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(TARGET_FPS)
        self.shutdown()

    def shutdown(self):
        print("Exiting game...")
        pygame.quit()
        global vlc_instance, bg_music_player
        if vlc_instance:
            print("Releasing VLC resources...")
            if bg_music_player: bg_music_player.release()
            vlc_instance.release()
        print("Cleanup complete. Goodbye!")
        sys.exit()

# --- Audio Helper Functions (Remain Global) ---
# (Keep these defined globally)
def play_sound(sound_obj):
    global SOUND_ENABLED
    if SOUND_ENABLED and sound_obj:
        try: sound_obj.play()
        except Exception as e: print(f"SFX Play Error: {e}"); SOUND_ENABLED = False
def play_music():
    global MUSIC_ENABLED, vlc_instance, bg_music_player, bg_music_file_path
    if MUSIC_ENABLED and bg_music_player and vlc_instance and bg_music_file_path:
        try:
            state = bg_music_player.get_state()
            if state not in [vlc.State.Playing, vlc.State.Paused]:
                 media = vlc_instance.media_new(bg_music_file_path)
                 if media: bg_music_player.set_media(media); media.release(); bg_music_player.play()
                 else: MUSIC_ENABLED = False
        except Exception as e: print(f"Music Play Error: {e}"); MUSIC_ENABLED = False
def pause_music():
    if MUSIC_ENABLED and bg_music_player and bg_music_player.is_playing():
        try: bg_music_player.pause()
        except Exception: pass
def resume_music():
     global MUSIC_ENABLED
     if MUSIC_ENABLED and bg_music_player:
        try:
            if bg_music_player.get_state() == vlc.State.Paused: bg_music_player.pause()
            elif bg_music_player.get_state() != vlc.State.Playing: play_music()
        except Exception: MUSIC_ENABLED = False

# --- Main Execution ---
if __name__ == "__main__":
    if pygame.get_init() and pygame.display.get_init():
        game = Game()
        globals()['game'] = game # Make game instance globally accessible if needed
        game.run()
    else:
        print("Fatal Error: Pygame display not initialized before creating Game object.")
        sys.exit()