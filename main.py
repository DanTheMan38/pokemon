from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
import heapq
import json
import math
import random
import pygame

ROOT = Path(__file__).resolve().parent
SCREEN_SIZE = (960, 640)
FPS = 60
WINDOW_TITLE = "Pokemon Fan Meadow"

MAP_PATH = ROOT / "assets" / "maps" / "start_area.png"
PLAYER_SHEET_PATH = ROOT / "assets" / "sprites" / "player_sheet.png"
PLAYER_MANIFEST_PATH = ROOT / "assets" / "sprites" / "player_manifest.json"
CREATURE_DIR = ROOT / "assets" / "creatures"
NPC_DIR = ROOT / "assets" / "npcs"
ITEM_DIR = ROOT / "assets" / "items"
UI_DIR = ROOT / "assets" / "ui"
GRASS_DIR = ROOT / "assets" / "grass"
INTERIOR_DIR = ROOT / "assets" / "interiors"
BATTLE_DIR = ROOT / "assets" / "battle"
AUDIO_DIR = ROOT / "assets" / "audio"
PPO_DIR = ROOT / "assets" / "ppo"
UI_PANEL_PATH = UI_DIR / "panel_frame.png"
GRASS_SHEET_PATH = GRASS_DIR / "tall_grass_sheet.png"
ABILITY_EFFECT_SHEET_PATH = BATTLE_DIR / "ability_effects_sheet.png"
SAVE_PATH = ROOT / "save_data.json"
SAVE_VERSION = 2

SCENE_SCALES = {
    "cedar_lab": 0.58,
    "mira_house": 0.54,
}
INTERIOR_SCENES = set(SCENE_SCALES)
HIT_REACTION_DURATION = 0.72
LUNGE_DURATION = 0.34
EXP_LEVEL_HOLD_DURATION = 0.46
STARTER_SPECIES = ("Leafawn", "Flarekit", "Tidefin")
WILD_SPECIES = ("Mothleaf", "Bubbun", "Sparrook")
SPECIES_ALIASES = {
    "Bloomcub": "Leafawn",
    "Cindlet": "Flarekit",
    "Pebblit": "Mothleaf",
}
PLAY_MODE_ORDER = ("manual", "ppo_tiny", "ppo_trained", "ppo_ultimate")

MOVE_KEYS = {
    "left": (pygame.K_LEFT, pygame.K_a),
    "right": (pygame.K_RIGHT, pygame.K_d),
    "up": (pygame.K_UP, pygame.K_w),
    "down": (pygame.K_DOWN, pygame.K_s),
}
INTERACT_KEYS = {pygame.K_e, pygame.K_SPACE, pygame.K_RETURN}
CONFIRM_KEYS = INTERACT_KEYS
BACK_KEYS = {pygame.K_BACKSPACE, pygame.K_x}
SPRINT_KEYS = {pygame.K_LSHIFT, pygame.K_RSHIFT}

CREAM = (245, 240, 218)
INK = (25, 32, 42)
PANEL = (28, 36, 44)
PANEL_LIGHT = (46, 60, 72)
PANEL_BORDER = (212, 228, 236)
ACCENT = (255, 206, 92)
GREEN = (96, 184, 88)
RED = (222, 84, 84)
BLUE = (92, 138, 218)
PURPLE = (154, 112, 210)
WHITE = (248, 250, 252)
BLACK = (0, 0, 0)

_PANEL_FRAME_SOURCE: pygame.Surface | None = None
_PANEL_FRAME_CACHE: dict[tuple[int, int], pygame.Surface] = {}


def load_player_animations() -> tuple[dict[str, list[pygame.Surface]], list[int]]:
    manifest = json.loads(PLAYER_MANIFEST_PATH.read_text(encoding="utf-8"))
    sheet = pygame.image.load(PLAYER_SHEET_PATH).convert_alpha()
    frame_width = manifest["frame_width"]
    frame_height = manifest["frame_height"]
    render_scale = manifest["render_scale"]
    sheet_columns = manifest["sheet_columns"]

    animations: dict[str, list[pygame.Surface]] = {}
    for row_index, direction in enumerate(manifest["row_directions"]):
        row_frames: list[pygame.Surface] = []
        for col_index in range(sheet_columns):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(
                sheet,
                (0, 0),
                pygame.Rect(
                    col_index * frame_width,
                    row_index * frame_height,
                    frame_width,
                    frame_height,
                ),
            )
            row_frames.append(pygame.transform.scale_by(frame, render_scale))
        animations[direction] = row_frames

    return animations, manifest["walk_cycle"]


def build_static_colliders() -> list[pygame.Rect]:
    return [
        pygame.Rect(0, 0, 358, 520),
        pygame.Rect(759, 0, 104, 173),
        pygame.Rect(840, 0, 414, 102),
        pygame.Rect(1112, 189, 122, 194),
        pygame.Rect(533, 103, 230, 152),
        pygame.Rect(745, 174, 39, 74),
        pygame.Rect(403, 183, 124, 52),
        pygame.Rect(783, 183, 123, 52),
        pygame.Rect(923, 111, 306, 252),
        pygame.Rect(880, 294, 70, 105),
        pygame.Rect(969, 388, 184, 44),
        pygame.Rect(952, 440, 252, 209),
        pygame.Rect(1037, 645, 36, 60),
        pygame.Rect(715, 709, 192, 46),
        pygame.Rect(875, 448, 84, 152),
        pygame.Rect(900, 579, 58, 86),
        pygame.Rect(0, 569, 278, 233),
        pygame.Rect(175, 452, 182, 41),
        pygame.Rect(357, 88, 31, 164),
        pygame.Rect(389, 319, 31, 164),
        pygame.Rect(317, 678, 84, 46),
        pygame.Rect(391, 669, 31, 254),
        pygame.Rect(419, 271, 77, 64),
        pygame.Rect(121, 815, 134, 117),
        pygame.Rect(319, 724, 77, 77),
        pygame.Rect(1083, 616, 115, 119),
        pygame.Rect(886, 874, 86, 58),
        pygame.Rect(0, 933, 508, 105),
        pygame.Rect(624, 933, 630, 105),
        pygame.Rect(503, 933, 33, 109),
        pygame.Rect(620, 933, 31, 109),
        pygame.Rect(0, 1169, 347, 85),
        pygame.Rect(0, 1012, 181, 242),
        pygame.Rect(189, 1081, 154, 173),
        pygame.Rect(737, 1010, 517, 244),
    ]


def build_lab_colliders() -> list[pygame.Rect]:
    return [
        pygame.Rect(0, 0, 1280, 94),
        pygame.Rect(0, 0, 74, 1280),
        pygame.Rect(1208, 0, 72, 1280),
        pygame.Rect(0, 1180, 562, 100),
        pygame.Rect(720, 1180, 560, 100),
        pygame.Rect(276, 194, 426, 132),
        pygame.Rect(816, 176, 152, 250),
        pygame.Rect(1044, 174, 170, 298),
        pygame.Rect(94, 445, 166, 234),
        pygame.Rect(356, 446, 570, 210),
        pygame.Rect(1088, 424, 94, 224),
        pygame.Rect(900, 866, 248, 112),
        pygame.Rect(125, 958, 264, 102),
    ]


def build_house_colliders() -> list[pygame.Rect]:
    return [
        pygame.Rect(0, 0, 1280, 88),
        pygame.Rect(0, 0, 76, 1280),
        pygame.Rect(1206, 0, 74, 1280),
        pygame.Rect(0, 1182, 560, 98),
        pygame.Rect(720, 1182, 560, 98),
        pygame.Rect(144, 350, 252, 224),
        pygame.Rect(420, 282, 244, 146),
        pygame.Rect(806, 246, 138, 204),
        pygame.Rect(1020, 206, 176, 266),
        pygame.Rect(802, 556, 114, 170),
        pygame.Rect(930, 610, 132, 118),
        pygame.Rect(244, 744, 250, 152),
        pygame.Rect(644, 662, 252, 222),
        pygame.Rect(194, 1092, 316, 68),
        pygame.Rect(874, 1086, 236, 70),
    ]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def scene_scale(scene_key: str) -> float:
    return SCENE_SCALES.get(scene_key, 1.0)


def scale_rect(rect: pygame.Rect, scale: float) -> pygame.Rect:
    if scale == 1.0:
        return rect.copy()
    return pygame.Rect(
        round(rect.x * scale),
        round(rect.y * scale),
        max(1, round(rect.width * scale)),
        max(1, round(rect.height * scale)),
    )


def scale_point(point: tuple[float, float] | pygame.Vector2, scale: float) -> tuple[float, float]:
    if scale == 1.0:
        return (float(point[0]), float(point[1]))
    return (round(point[0] * scale), round(point[1] * scale))


def scale_vector(point: tuple[float, float], scale: float) -> pygame.Vector2:
    return pygame.Vector2(scale_point(point, scale))


def scale_surface(surface: pygame.Surface, scale: float) -> pygame.Surface:
    if scale == 1.0:
        return surface
    size = (
        max(1, round(surface.get_width() * scale)),
        max(1, round(surface.get_height() * scale)),
    )
    return pygame.transform.smoothscale(surface, size)


def crop_alpha_surface(surface: pygame.Surface, padding: int = 0) -> pygame.Surface:
    bounds = surface.get_bounding_rect()
    if bounds.width <= 0 or bounds.height <= 0:
        return surface.copy()
    if padding > 0:
        bounds.inflate_ip(padding * 2, padding * 2)
        bounds.clamp_ip(surface.get_rect())
    cropped = pygame.Surface(bounds.size, pygame.SRCALPHA)
    cropped.blit(surface, (0, 0), bounds)
    return cropped


def fit_surface_to_canvas(
    surface: pygame.Surface,
    canvas_size: tuple[int, int],
    *,
    padding: int = 0,
    align: str = "bottom",
) -> pygame.Surface:
    trimmed = crop_alpha_surface(surface)
    canvas_width, canvas_height = canvas_size
    max_width = max(1, canvas_width - padding * 2)
    max_height = max(1, canvas_height - padding * 2)
    scale = min(max_width / max(1, trimmed.get_width()), max_height / max(1, trimmed.get_height()))
    scaled_size = (
        max(1, round(trimmed.get_width() * scale)),
        max(1, round(trimmed.get_height() * scale)),
    )
    scaled = pygame.transform.smoothscale(trimmed, scaled_size)
    canvas = pygame.Surface(canvas_size, pygame.SRCALPHA)
    rect = scaled.get_rect()
    if align == "center":
        rect.center = (canvas_width // 2, canvas_height // 2)
    else:
        rect.midbottom = (canvas_width // 2, canvas_height - padding)
    canvas.blit(scaled, rect)
    return canvas


def with_surface_alpha(surface: pygame.Surface, alpha: int) -> pygame.Surface:
    alpha = int(clamp(alpha, 0, 255))
    if alpha >= 255:
        return surface
    faded = surface.copy()
    faded.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return faded


def get_panel_frame(size: tuple[int, int]) -> pygame.Surface | None:
    global _PANEL_FRAME_SOURCE

    if not UI_PANEL_PATH.exists():
        return None

    if _PANEL_FRAME_SOURCE is None:
        _PANEL_FRAME_SOURCE = pygame.image.load(UI_PANEL_PATH).convert_alpha()

    if size not in _PANEL_FRAME_CACHE:
        _PANEL_FRAME_CACHE[size] = pygame.transform.scale(_PANEL_FRAME_SOURCE, size)
    return _PANEL_FRAME_CACHE[size]


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int] = PANEL,
    border: tuple[int, int, int] = PANEL_BORDER,
) -> None:
    frame = get_panel_frame(rect.size)
    if frame is not None:
        surface.blit(frame, rect)
        inner = rect.inflate(-28, -24)
        if inner.width > 0 and inner.height > 0:
            overlay = pygame.Surface(inner.size, pygame.SRCALPHA)
            overlay.fill((*fill, 210))
            surface.blit(overlay, inner.topleft)
        if border != PANEL_BORDER:
            accent_rect = rect.inflate(-12, -10)
            pygame.draw.rect(surface, border, accent_rect, width=2, border_radius=12)
        return

    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, border, rect, width=3, border_radius=12)


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_multiline_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    rect: pygame.Rect,
    color: tuple[int, int, int] = WHITE,
    line_gap: int = 4,
) -> None:
    lines = wrap_text(font, text, rect.width)
    y = rect.top
    for line in lines:
        rendered = font.render(line, True, color)
        surface.blit(rendered, (rect.left, y))
        y += rendered.get_height() + line_gap


def make_shadow(width: int, height: int, alpha: int = 110) -> pygame.Surface:
    shadow = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, alpha), shadow.get_rect())
    return shadow


def build_item_icons() -> dict[str, pygame.Surface]:
    icons: dict[str, pygame.Surface] = {}

    for key in ("capture_orb", "berry"):
        path = ITEM_DIR / f"{key}.png"
        if path.exists():
            icons[key] = pygame.transform.scale(
                pygame.image.load(path).convert_alpha(),
                (20, 20),
            )

    if "capture_orb" not in icons:
        orb = pygame.Surface((18, 18), pygame.SRCALPHA)
        pygame.draw.circle(orb, (232, 72, 72), (9, 7), 6)
        pygame.draw.circle(orb, (250, 250, 250), (9, 11), 6)
        pygame.draw.line(orb, (24, 24, 24), (3, 9), (15, 9), 2)
        pygame.draw.circle(orb, (24, 24, 24), (9, 9), 6, 2)
        pygame.draw.circle(orb, (250, 250, 250), (9, 9), 2)
        icons["capture_orb"] = orb

    if "berry" not in icons:
        berry = pygame.Surface((18, 18), pygame.SRCALPHA)
        pygame.draw.circle(berry, (145, 86, 196), (6, 11), 4)
        pygame.draw.circle(berry, (160, 96, 214), (11, 8), 4)
        pygame.draw.circle(berry, (176, 112, 228), (11, 13), 4)
        pygame.draw.line(berry, (70, 120, 44), (9, 3), (9, 7), 2)
        pygame.draw.polygon(berry, (88, 168, 76), [(9, 2), (13, 6), (9, 5), (5, 6)])
        icons["berry"] = berry

    return icons


def load_grass_frames(*, scale: float = 1.0) -> list[pygame.Surface]:
    if not GRASS_SHEET_PATH.exists():
        return []

    sheet = pygame.image.load(GRASS_SHEET_PATH).convert_alpha()
    frame_width = sheet.get_width() // 3
    frames: list[pygame.Surface] = []
    for index in range(3):
        frame = pygame.Surface((frame_width, sheet.get_height()), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), pygame.Rect(index * frame_width, 0, frame_width, sheet.get_height()))
        if scale != 1.0:
            frame = pygame.transform.scale_by(frame, scale)
        frames.append(frame)
    return frames


class AudioManager:
    def __init__(self, *, enabled: bool) -> None:
        self.enabled = False
        self.music_muted = False
        self.current_music: str | None = None
        self.sound_effects: dict[str, pygame.mixer.Sound] = {}
        self.music_paths = {
            "world": AUDIO_DIR / "overworld_theme.wav",
            "battle": AUDIO_DIR / "battle_theme.wav",
        }
        if not enabled:
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        except pygame.error:
            return

        self.enabled = True
        effect_volumes = {
            "menu_move": 0.25,
            "confirm": 0.34,
            "cancel": 0.28,
            "interact": 0.34,
            "pickup": 0.36,
            "grass_step": 0.22,
            "encounter": 0.40,
            "attack": 0.34,
            "hit": 0.36,
            "heal": 0.36,
            "orb": 0.36,
            "capture": 0.38,
            "level_up": 0.40,
            "quest": 0.42,
            "run": 0.32,
            "faint": 0.34,
            "error": 0.30,
            "victory_jingle": 0.42,
        }
        for name, volume in effect_volumes.items():
            path = AUDIO_DIR / f"{name}.wav"
            try:
                sound = pygame.mixer.Sound(path)
            except pygame.error:
                continue
            sound.set_volume(volume)
            self.sound_effects[name] = sound

    def play_music(self, track: str | None) -> None:
        if not self.enabled or self.music_muted or track is None or self.current_music == track:
            return
        path = self.music_paths.get(track)
        if path is None:
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.22 if track == "battle" else 0.18)
            pygame.mixer.music.play(-1)
            self.current_music = track
        except pygame.error:
            self.enabled = False

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self.sound_effects.get(name)
        if sound is not None:
            sound.play()

    def toggle_music_mute(self) -> bool:
        self.music_muted = not self.music_muted
        if self.enabled:
            try:
                if self.music_muted:
                    pygame.mixer.music.pause()
                else:
                    pygame.mixer.music.unpause()
            except pygame.error:
                self.enabled = False
        return self.music_muted


@dataclass(frozen=True)
class Move:
    name: str
    power: int
    accuracy: float
    text: str
    kind: str = "attack"
    effect_key: str | None = None


@dataclass
class Species:
    key: str
    name: str
    element: str
    base_hp: int
    front_sprite: pygame.Surface
    back_sprite: pygame.Surface
    icon: pygame.Surface
    moves: tuple[Move, Move, Move]
    accent: tuple[int, int, int]


@dataclass
class Creature:
    species: Species
    level: int
    max_hp: int = 0
    hp: int = 0
    exp: int = 0
    guarding: bool = False

    def __post_init__(self) -> None:
        if self.max_hp <= 0:
            self.max_hp = self.species.base_hp + (self.level - 1) * 4
        if self.hp <= 0:
            self.hp = self.max_hp

    @property
    def name(self) -> str:
        return self.species.name

    @property
    def is_fainted(self) -> bool:
        return self.hp <= 0

    def heal_full(self) -> None:
        self.hp = self.max_hp
        self.guarding = False

    def heal(self, amount: int) -> int:
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    def take_damage(self, amount: int) -> tuple[int, bool]:
        guarded = self.guarding
        if guarded:
            amount = max(1, math.ceil(amount * 0.55))
            self.guarding = False
        actual = min(self.hp, amount)
        self.hp -= actual
        return actual, guarded

    def exp_to_next(self) -> int:
        return 10 + self.level * 5

    def gain_exp(self, amount: int) -> list[str]:
        messages = [f"{self.name} gained {amount} experience."]
        self.exp += amount

        while self.exp >= self.exp_to_next():
            threshold = self.exp_to_next()
            self.exp -= threshold
            self.level += 1
            hp_gain = 4 + self.level // 3
            self.max_hp += hp_gain
            self.hp = self.max_hp
            messages.append(
                f"{self.name} grew to Lv.{self.level}! Max HP rose by {hp_gain}."
            )

        return messages


@dataclass
class NPC:
    key: str
    name: str
    position: pygame.Vector2
    sprite: pygame.Surface
    prompt: str
    marker_color: tuple[int, int, int]

    def hitbox(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, 16, 10)
        rect.midbottom = (round(self.position.x), round(self.position.y))
        return rect


@dataclass
class ItemPickup:
    key: str
    position: pygame.Vector2
    item_name: str
    amount: int
    label: str
    collected: bool = False

    def rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, 18, 18)
        rect.center = (round(self.position.x), round(self.position.y))
        return rect


@dataclass
class GrassPatch:
    key: str
    rect: pygame.Rect
    tufts: tuple[tuple[int, int], ...]
    activity: float = 0.15


@dataclass(frozen=True)
class PlayModeSpec:
    key: str
    short_label: str
    title: str
    subtitle: str
    detail: str
    color: tuple[int, int, int]
    seed: int
    checkpoint: str = ""


PLAY_MODE_SPECS = {
    "manual": PlayModeSpec(
        key="manual",
        short_label="Play",
        title="Player Mode",
        subtitle="You control the whole run.",
        detail="Fresh run",
        color=ACCENT,
        seed=0,
    ),
    "ppo_tiny": PlayModeSpec(
        key="ppo_tiny",
        short_label="Tiny PPO",
        title="PPO Tiny",
        subtitle="Barely trained. Walks, bumps around, and rarely completes tasks.",
        detail="0 updates",
        color=PANEL_BORDER,
        seed=21,
        checkpoint="0.5k PPO",
    ),
    "ppo_trained": PlayModeSpec(
        key="ppo_trained",
        short_label="PPO Mid",
        title="PPO Trained",
        subtitle="Task-aware but messy. It catches Pokemon and can finish with wasted steps.",
        detail="4k episodes",
        color=BLUE,
        seed=84,
        checkpoint="80k PPO",
    ),
    "ppo_ultimate": PlayModeSpec(
        key="ppo_ultimate",
        short_label="PPO Max",
        title="PPO Plateau",
        subtitle="Fast route. Knows the map, battles, charm, and ending requirements.",
        detail="16k episodes",
        color=GREEN,
        seed=355,
        checkpoint="Plateau",
    ),
}


@dataclass(frozen=True)
class Doorway:
    key: str
    rect: pygame.Rect
    target_scene: str
    target_position: tuple[float, float]
    target_direction: str = "down"


@dataclass
class DamagePopup:
    text: str
    side: str
    color: tuple[int, int, int]
    timer: float = 0.0
    duration: float = 0.95

    @property
    def progress(self) -> float:
        return clamp(self.timer / max(0.001, self.duration), 0.0, 1.0)


@dataclass
class BattleEffect:
    move_name: str
    source_side: str
    target_side: str
    duration: float = 0.86
    timer: float = 0.0
    hit_on_impact: bool = False
    impact_at: float = 0.5
    impact_done: bool = False
    missed: bool = False
    guard: bool = False
    popup_text: str | None = None
    popup_color: tuple[int, int, int] = WHITE

    @property
    def progress(self) -> float:
        return clamp(self.timer / max(0.001, self.duration), 0.0, 1.0)


@dataclass(frozen=True)
class ExpGainSegment:
    level: int
    start_exp: int
    end_exp: int
    threshold: int
    level_up: bool = False


@dataclass
class BattleExpAnimation:
    creature_name: str
    gain_amount: int
    segments: list[ExpGainSegment]
    post_messages: list[str]
    next_phase: str
    display_level: int
    display_exp: float
    segment_index: int = 0
    segment_elapsed: float = 0.0
    segment_duration: float = 0.0
    hold_timer: float = 0.0
    banner_text: str = ""

    def current_segment(self) -> ExpGainSegment | None:
        if self.segment_index >= len(self.segments):
            return None
        return self.segments[self.segment_index]


@dataclass
class SceneData:
    key: str
    surface: pygame.Surface
    walk_bounds: pygame.Rect
    colliders: list[pygame.Rect]
    props: dict[str, pygame.Rect]
    doorways: list[Doorway]
    grass_patches: list[GrassPatch]
    pickups: list[ItemPickup]
    npcs: dict[str, NPC]


@dataclass
class BattleState:
    enemy: Creature
    messages: deque[str] = field(default_factory=deque)
    phase: str = "messages"
    next_phase: str | None = "command"
    command_index: int = 0
    move_index: int = 0
    party_index: int = 0
    effects: list[BattleEffect] = field(default_factory=list)
    damage_popups: list[DamagePopup] = field(default_factory=list)
    player_hit_timer: float = 0.0
    enemy_hit_timer: float = 0.0
    player_lunge_timer: float = 0.0
    enemy_lunge_timer: float = 0.0
    screen_shake_timer: float = 0.0
    screen_shake_strength: float = 0.0
    exp_animation: BattleExpAnimation | None = None


class Player:
    def __init__(
        self,
        animations: dict[str, list[pygame.Surface]],
        walk_cycle: list[int],
        start_position: tuple[float, float],
    ) -> None:
        self.animations = animations
        self.walk_cycle = walk_cycle
        self.position = pygame.Vector2(start_position)
        self.direction = "down"
        self.current_frame = 0
        self.animation_timer = 0.0
        self.hitbox_size = (16, 10)
        self.moving = False
        self.sprinting = False

    def hitbox(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, *self.hitbox_size)
        rect.midbottom = (round(self.position.x), round(self.position.y))
        return rect

    def interaction_point(self) -> pygame.Vector2:
        offsets = {
            "up": pygame.Vector2(0, -26),
            "down": pygame.Vector2(0, 18),
            "left": pygame.Vector2(-22, 0),
            "right": pygame.Vector2(22, 0),
        }
        return self.position + offsets[self.direction]

    def update(
        self,
        dt: float,
        pressed: pygame.key.ScancodeWrapper,
        world_rect: pygame.Rect,
        colliders: list[pygame.Rect],
        speed: float,
    ) -> float:
        raw_move = pygame.Vector2(
            self._pressed("right", pressed) - self._pressed("left", pressed),
            self._pressed("down", pressed) - self._pressed("up", pressed),
        )
        moving = raw_move.length_squared() > 0
        self.moving = moving
        start = self.position.copy()

        if moving:
            move = raw_move.normalize()
            self._update_direction(raw_move)
            distance = move * speed * dt
            self._move_axis(distance.x, "x", world_rect, colliders)
            self._move_axis(distance.y, "y", world_rect, colliders)
            self.animation_timer += dt * 10
            self.current_frame = self.walk_cycle[int(self.animation_timer) % len(self.walk_cycle)]
        else:
            self.current_frame = 0
            self.animation_timer = 0.0

        return (self.position - start).length()

    def draw(self, surface: pygame.Surface, camera: pygame.Vector2) -> None:
        sprite = self.animations[self.direction][self.current_frame]
        shadow = make_shadow(28, 10, 96)
        shadow_rect = shadow.get_rect(
            center=(
                round(self.position.x - camera.x),
                round(self.position.y - camera.y - 4),
            )
        )
        surface.blit(shadow, shadow_rect)

        sprite_rect = sprite.get_rect(
            midbottom=(
                round(self.position.x - camera.x),
                round(self.position.y - camera.y),
            )
        )
        surface.blit(sprite, sprite_rect)

    def _move_axis(
        self,
        amount: float,
        axis: str,
        world_rect: pygame.Rect,
        colliders: list[pygame.Rect],
    ) -> None:
        if amount == 0:
            return

        if axis == "x":
            self.position.x += amount
        else:
            self.position.y += amount

        hitbox = self.hitbox()

        if hitbox.left < world_rect.left:
            self.position.x += world_rect.left - hitbox.left
            hitbox = self.hitbox()
        if hitbox.right > world_rect.right:
            self.position.x -= hitbox.right - world_rect.right
            hitbox = self.hitbox()
        if hitbox.top < world_rect.top:
            self.position.y += world_rect.top - hitbox.top
            hitbox = self.hitbox()
        if hitbox.bottom > world_rect.bottom:
            self.position.y -= hitbox.bottom - world_rect.bottom
            hitbox = self.hitbox()

        for collider in colliders:
            if not hitbox.colliderect(collider):
                continue

            if axis == "x":
                if amount > 0:
                    self.position.x -= hitbox.right - collider.left
                else:
                    self.position.x += collider.right - hitbox.left
            else:
                if amount > 0:
                    self.position.y -= hitbox.bottom - collider.top
                else:
                    self.position.y += collider.bottom - hitbox.top
            hitbox = self.hitbox()

    def _update_direction(self, raw_move: pygame.Vector2) -> None:
        if abs(raw_move.x) > abs(raw_move.y):
            self.direction = "right" if raw_move.x > 0 else "left"
        elif raw_move.y != 0:
            self.direction = "down" if raw_move.y > 0 else "up"

    @staticmethod
    def _pressed(name: str, pressed: pygame.key.ScancodeWrapper) -> int:
        return int(any(pressed[key] for key in MOVE_KEYS[name]))


class VirtualPressed:
    def __init__(self, keys: set[int]) -> None:
        self.keys = keys

    def __getitem__(self, key: int) -> bool:
        return key in self.keys


PPO_ACTIONS = ("up", "down", "left", "right", "interact", "fight", "orb", "berry", "run", "wait")
PPO_FILES = {
    "ppo_tiny": "ppo_tiny.json",
    "ppo_trained": "ppo_mid.json",
    "ppo_ultimate": "ppo_max.json",
}
PPO_GRAPHS = {
    "meadow": {
        "start": {"up": "lab_door", "left": "west_grass", "right": "house_door", "down": "south_grass"},
        "lab_door": {"down": "start", "left": "west_grass", "right": "berry_patch"},
        "berry_patch": {"left": "lab_door", "down": "start"},
        "west_grass": {"right": "start", "up": "lab_door"},
        "house_door": {"left": "start", "down": "east_grass", "up": "orb_pickup"},
        "orb_pickup": {"down": "house_door", "left": "start"},
        "south_grass": {"up": "start", "right": "orb_pickup"},
        "east_grass": {"up": "house_door", "left": "start"},
    },
    "cedar_lab": {
        "entry": {"up": "professor", "left": "starter", "down": "exit"},
        "professor": {"down": "entry", "left": "starter"},
        "starter": {"right": "professor", "down": "entry"},
        "exit": {"up": "entry"},
    },
    "mira_house": {
        "entry": {"up": "chest", "down": "exit"},
        "chest": {"down": "entry"},
        "exit": {"up": "entry"},
    },
}


class PPOAutoplayer:
    def __init__(self, game: "Game", mode_key: str) -> None:
        self.game = game
        self.spec = PLAY_MODE_SPECS[mode_key]
        self.mode_key = mode_key
        self.rng = random.Random(self.spec.seed)
        self.policy_data = self.load_policy()
        self.policy = self.policy_data.get("policy", {})
        self.actions = tuple(self.policy_data.get("actions", PPO_ACTIONS))
        self.node = self.closest_node()
        self.target_node: str | None = None
        self.path: list[pygame.Vector2] = []
        self.action_timer = 0.0
        self.repath_timer = 0.0
        self.goal_hold_timer = 0.0
        self.pending_goal_label = "loading PPO checkpoint"
        self.last_position = game.player.position.copy()
        self.last_scene_key = game.scene_key
        self.last_target_distance: float | None = None
        self.no_progress_timer = 0.0
        self.progress_anchor = game.player.position.copy()
        self.progress_timer = 0.0
        self.stuck_timer = 0.0

    def load_policy(self) -> dict:
        path = PPO_DIR / PPO_FILES[self.mode_key]
        if not path.exists():
            return {"actions": PPO_ACTIONS, "policy": {}}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"actions": PPO_ACTIONS, "policy": {}}

    @property
    def confirm_interval(self) -> float:
        if self.mode_key == "ppo_ultimate":
            return 1.05
        if self.mode_key == "ppo_trained":
            return 1.28
        return 0.9

    @property
    def command_interval(self) -> float:
        if self.mode_key == "ppo_ultimate":
            return 0.46
        if self.mode_key == "ppo_trained":
            return 0.7
        return 0.9

    def update(self, dt: float) -> set[int]:
        self.action_timer = max(0.0, self.action_timer - dt)
        self.repath_timer = max(0.0, self.repath_timer - dt)
        self.game.ai_status_text = f"{self.spec.title}: {self.pending_goal_label}"

        if self.game.mode in {"dialogue", "ending"}:
            self.tap_confirm()
            return set()
        if self.game.mode == "battle":
            self.drive_battle()
            return set()
        if self.game.mode != "world":
            self.clear_path_progress()
            return set()

        self.sync_node_to_scene()
        if self.target_node is not None:
            return self.move_to_target(dt)

        action = self.predict_action()
        self.pending_goal_label = f"policy action: {action}"
        if action in {"up", "down", "left", "right"}:
            graph = PPO_GRAPHS.get(self.game.scene_key, {})
            next_node = graph.get(self.node, {}).get(action)
            if next_node is not None:
                self.begin_target(next_node)
                return self.move_to_target(dt)
            return set()
        if action == "interact":
            if self.action_timer == 0:
                self.prepare_world_interaction()
                self.game.handle_world_interaction()
                self.action_timer = self.confirm_interval
            return set()
        if action == "wait":
            self.try_grass_encounter(dt)
        return set()

    def begin_target(self, node: str) -> None:
        self.target_node = node
        self.path = []
        self.repath_timer = 0.0
        self.clear_path_progress()

    def clear_path_progress(self) -> None:
        self.last_target_distance = None
        self.no_progress_timer = 0.0
        self.stuck_timer = 0.0
        self.last_position = self.game.player.position.copy()
        self.progress_anchor = self.game.player.position.copy()
        self.progress_timer = 0.0

    def tap_confirm(self) -> None:
        if self.action_timer > 0:
            return
        self.game.handle_keydown(pygame.K_e)
        self.action_timer = self.confirm_interval

    def prepare_world_interaction(self) -> None:
        if self.game.scene_key == "cedar_lab" and self.node in {"professor", "starter"}:
            self.game.player.direction = "up"
        elif self.game.scene_key == "mira_house" and self.node == "chest":
            self.game.player.direction = "up"

    def sync_node_to_scene(self) -> None:
        if self.last_scene_key != self.game.scene_key:
            self.last_scene_key = self.game.scene_key
            self.node = self.closest_node()
            self.target_node = None
            self.path = []
            self.clear_path_progress()
        elif self.node not in self.node_positions().get(self.game.scene_key, {}):
            self.node = self.closest_node()
            self.target_node = None
            self.path = []
            self.clear_path_progress()

    def move_to_target(self, dt: float) -> set[int]:
        if self.target_node is None:
            return set()
        positions = self.node_positions().get(self.game.scene_key, {})
        target = positions.get(self.target_node)
        if target is None:
            self.node = self.closest_node()
            self.target_node = None
            self.path = []
            self.clear_path_progress()
            return set()
        self.maybe_trigger_door_node()
        if self.game.mode != "world":
            return set()
        distance = self.game.player.position.distance_to(target)
        arrival_distance = 48 if self.target_node == "berry_patch" else 34 if self.target_node == "orb_pickup" else 12
        if distance < arrival_distance:
            self.node = self.target_node
            self.target_node = None
            self.path = []
            self.clear_path_progress()
            self.collect_node_pickup(self.node)
            self.try_grass_encounter(1 / FPS, force=True)
            return set()
        moved = self.game.player.position.distance_to(self.last_position)
        self.last_position = self.game.player.position.copy()
        if moved < 0.2:
            self.stuck_timer += dt
        else:
            self.stuck_timer = 0.0
        if self.game.player.position.distance_to(self.progress_anchor) > 18:
            self.progress_anchor = self.game.player.position.copy()
            self.progress_timer = 0.0
        else:
            self.progress_timer += dt
        if self.stuck_timer > 1.1 or self.progress_timer > 1.55:
            self.recover_from_navigation_stall(positions)
            return set()
        if not self.path or self.repath_timer == 0:
            self.path = self.find_path(self.game.player.position, target)
            self.repath_timer = 0.55
        if self.path and self.game.player.position.distance_to(self.path[0]) > 96:
            self.path = []
            self.path = self.find_path(self.game.player.position, target)
            self.repath_timer = 0.55
        while self.path and self.game.player.position.distance_to(self.path[0]) < 10:
            self.path.pop(0)
        waypoint = self.path[0] if self.path else target
        delta = waypoint - self.game.player.position
        keys: set[int] = set()
        if abs(delta.x) > 2:
            keys.add(pygame.K_d if delta.x > 0 else pygame.K_a)
        if abs(delta.y) > 2:
            keys.add(pygame.K_s if delta.y > 0 else pygame.K_w)
        if self.game.sprint_unlocked and self.mode_key == "ppo_ultimate":
            keys.add(pygame.K_LSHIFT)
        return keys

    def maybe_trigger_door_node(self) -> None:
        if self.game.scene_key != "meadow" or self.target_node not in {"lab_door", "house_door"}:
            return
        target_scene = "cedar_lab" if self.target_node == "lab_door" else "mira_house"
        doorway = self.game.doorway_to(target_scene)
        if doorway is None:
            return
        player_box = self.game.player.hitbox()
        door_center = pygame.Vector2(doorway.rect.center)
        entry_radius = 112 if self.target_node == "house_door" else 34
        if player_box.colliderect(doorway.rect) or self.game.player.position.distance_to(door_center) < entry_radius:
            self.game.start_door_transition(doorway)
            self.target_node = None
            self.path = []
            self.clear_path_progress()

    def recover_from_navigation_stall(self, positions: dict[str, pygame.Vector2]) -> None:
        base = self.recovery_position_for_node(positions)
        if base is not None:
            self.game.player.position.update(base)
        self.path = []
        self.repath_timer = 0.0
        self.clear_path_progress()

    def collect_node_pickup(self, node: str) -> None:
        pickup_key = {
            "berry_patch": "berry_patch",
            "orb_pickup": "trail_orbs",
        }.get(node)
        if pickup_key is None:
            return
        for pickup in self.game.current_scene().pickups:
            if pickup.key != pickup_key:
                continue
            if pickup.collected and self.game.inventory[pickup.item_name] >= 2:
                return
            if not pickup.collected:
                pickup.collected = True
            self.game.inventory[pickup.item_name] += pickup.amount
            self.game.audio.play("pickup")
            self.game.push_toast(f"Found {pickup.amount} {pickup.label}.", ACCENT)
            self.game.save_game()
            return

    def recovery_position_for_node(self, positions: dict[str, pygame.Vector2]) -> pygame.Vector2 | None:
        if self.game.scene_key == "meadow" and self.node == "house_door":
            return pygame.Vector2(1048, 760)
        if self.game.scene_key == "meadow" and self.node == "lab_door":
            return pygame.Vector2(625, 274)
        node_position = positions.get(self.node)
        if node_position is None:
            return None
        cell = self.nearest_walkable_cell(self.point_to_cell(node_position, 22), 22)
        if cell is None:
            return pygame.Vector2(node_position)
        return self.cell_to_point(cell, 22)

    def find_path(self, start: pygame.Vector2, target: pygame.Vector2) -> list[pygame.Vector2]:
        step = 22
        start_cell = self.nearest_walkable_cell(self.point_to_cell(start, step), step)
        target_cell = self.nearest_walkable_cell(self.point_to_cell(target, step), step)
        if start_cell is None or target_cell is None:
            return [target]
        open_heap: list[tuple[float, int, tuple[int, int]]] = []
        heapq.heappush(open_heap, (0.0, 0, start_cell))
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        costs: dict[tuple[int, int], int] = {start_cell: 0}
        while open_heap:
            _, cost, current = heapq.heappop(open_heap)
            if current == target_cell:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                candidate = (current[0] + dx, current[1] + dy)
                if not self.cell_walkable(candidate, step):
                    continue
                new_cost = cost + 1
                if candidate in costs and new_cost >= costs[candidate]:
                    continue
                costs[candidate] = new_cost
                priority = new_cost + abs(candidate[0] - target_cell[0]) + abs(candidate[1] - target_cell[1])
                heapq.heappush(open_heap, (priority, new_cost, candidate))
                came_from[candidate] = current
        if target_cell not in costs:
            return [target]
        cells = [target_cell]
        while cells[-1] != start_cell:
            cells.append(came_from[cells[-1]])
        cells.reverse()
        points = [self.cell_to_point(cell, step) for cell in cells[1:]]
        points.append(target)
        return self.simplify_path(points)

    def simplify_path(self, points: list[pygame.Vector2]) -> list[pygame.Vector2]:
        if len(points) <= 2:
            return points
        simplified = [points[0]]
        last_dir = pygame.Vector2()
        for index in range(1, len(points)):
            delta = points[index] - points[index - 1]
            direction = pygame.Vector2(
                0 if abs(delta.x) < 1 else math.copysign(1, delta.x),
                0 if abs(delta.y) < 1 else math.copysign(1, delta.y),
            )
            if index == 1:
                last_dir = direction
            elif direction != last_dir:
                simplified.append(points[index - 1])
                last_dir = direction
        simplified.append(points[-1])
        return simplified

    def point_to_cell(self, point: pygame.Vector2, step: int) -> tuple[int, int]:
        return (round(point.x / step), round(point.y / step))

    def cell_to_point(self, cell: tuple[int, int], step: int) -> pygame.Vector2:
        return pygame.Vector2(cell[0] * step, cell[1] * step)

    def nearest_walkable_cell(self, cell: tuple[int, int], step: int) -> tuple[int, int] | None:
        if self.cell_walkable(cell, step):
            return cell
        for radius in range(1, 8):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue
                    candidate = (cell[0] + dx, cell[1] + dy)
                    if self.cell_walkable(candidate, step):
                        return candidate
        return None

    def cell_walkable(self, cell: tuple[int, int], step: int) -> bool:
        point = self.cell_to_point(cell, step)
        rect = pygame.Rect(0, 0, *self.game.player.hitbox_size)
        rect.midbottom = (round(point.x), round(point.y))
        scene = self.game.current_scene()
        if not scene.walk_bounds.contains(rect):
            return False
        return not any(rect.colliderect(collider) for collider in self.game.dynamic_colliders())

    def try_grass_encounter(self, dt: float, *, force: bool = False) -> None:
        if self.game.mode != "world" or not self.game.party or self.game.scene_key != "meadow":
            self.goal_hold_timer = 0.0
            return
        species = {
            "west_grass": "Mothleaf",
            "south_grass": "Bubbun",
            "east_grass": "Sparrook",
        }.get(self.node)
        if species is None:
            self.goal_hold_timer = 0.0
            return
        if force:
            if self.game.quest_stage == "survey_grass":
                species = "Mothleaf"
            if self.game.quest_stage == "survey_grass" or species not in self.game.caught_species:
                self.game.trigger_encounter(species, 3 if species != "Sparrook" else 4)
            self.goal_hold_timer = 0.0
            return
        self.goal_hold_timer += dt
        threshold = 0.32 if self.mode_key == "ppo_ultimate" else 0.9
        if self.goal_hold_timer >= threshold:
            if self.game.quest_stage == "survey_grass":
                species = "Mothleaf"
            self.game.trigger_encounter(species, 3 if species != "Sparrook" else 4)
            self.goal_hold_timer = 0.0

    def drive_battle(self) -> None:
        battle = self.game.battle
        if battle is None or self.action_timer > 0:
            return
        if battle.phase == "messages":
            self.game.advance_battle_messages()
            self.action_timer = self.confirm_interval
            return
        if battle.phase == "exp_gain":
            self.action_timer = self.confirm_interval
            return
        if battle.phase == "move_select":
            self.game.perform_player_move(self.best_move_index())
            self.action_timer = self.command_interval
            return
        if battle.phase == "party_select":
            self.game.handle_battle_input(pygame.K_e)
            self.action_timer = self.command_interval
            return
        if battle.phase != "command":
            return
        action = self.predict_action()
        labels = self.game.battle_command_labels()
        if action == "fight":
            self.game.perform_battle_command(labels.index("Fight"))
        elif action == "orb":
            self.game.perform_battle_command(labels.index("Orb"))
        elif action == "berry":
            self.game.perform_battle_command(labels.index("Berry"))
        elif action == "run":
            self.game.perform_battle_command(labels.index("Run"))
        else:
            self.game.perform_battle_command(labels.index("Fight"))
        self.action_timer = self.command_interval

    def best_move_index(self) -> int:
        lead = self.game.lead_creature()
        battle = self.game.battle
        if lead is None or battle is None:
            return 0
        best_index = 0
        best_score = -999.0
        for index, move in enumerate(lead.species.moves):
            score = 0.5 if move.kind == "guard" else move.power * move.accuracy * self.game.type_multiplier(lead.species.element, battle.enemy.species.element)
            if score > best_score:
                best_score = score
                best_index = index
        return best_index

    def predict_action(self) -> str:
        if self.mode_key == "ppo_tiny":
            return self.rng.choice(PPO_ACTIONS)
        key = json.dumps(self.state(), separators=(",", ":"))
        probs = self.policy.get(key)
        if not probs:
            return self.rng.choice(PPO_ACTIONS) if self.mode_key == "ppo_trained" else "wait"
        if self.mode_key == "ppo_trained":
            roll = self.rng.random()
            acc = 0.0
            for index, prob in enumerate(probs):
                acc += prob
                if roll <= acc:
                    return self.actions[index]
        index = max(range(len(probs)), key=lambda item: probs[item])
        return self.actions[index]

    def state(self) -> tuple:
        caught_mask = tuple(int(species in self.game.caught_species) for species in WILD_SPECIES)
        if self.game.mode == "battle" and self.game.battle is not None:
            enemy = self.game.battle.enemy
            lead = self.game.lead_creature()
            enemy_hp = max(0, math.ceil(3 * enemy.hp / max(1, enemy.max_hp)))
            player_hp = 0 if lead is None else max(0, math.ceil(3 * lead.hp / max(1, lead.max_hp)))
            return (
                "battle",
                self.game.quest_stage,
                enemy.species.key,
                min(3, enemy_hp),
                min(3, player_hp),
                min(3, self.game.inventory["capture_orb"]),
                min(2, self.game.inventory["berry"]),
                int(self.game.capture_charm),
                caught_mask,
            )
        return (
            "world",
            self.game.scene_key,
            self.node,
            self.game.quest_stage,
            int(bool(self.game.party)),
            int(self.game.capture_charm),
            caught_mask,
            min(3, self.game.inventory["capture_orb"]),
            min(2, self.game.inventory["berry"]),
        )

    def closest_node(self) -> str:
        positions = self.node_positions().get(self.game.scene_key, {})
        if not positions:
            return "start"
        return min(positions, key=lambda key: self.game.player.position.distance_to(positions[key]))

    def node_positions(self) -> dict[str, dict[str, pygame.Vector2]]:
        lab_scale = scene_scale("cedar_lab")
        house_scale = scene_scale("mira_house")
        return {
            "meadow": {
                "start": pygame.Vector2(626, 645),
                "lab_door": pygame.Vector2(625, 242),
                "berry_patch": pygame.Vector2(458, 310),
                "west_grass": pygame.Vector2(300, 550),
                "house_door": pygame.Vector2(1048, 684),
                "orb_pickup": pygame.Vector2(896, 930),
                "south_grass": pygame.Vector2(572, 1064),
                "east_grass": pygame.Vector2(866, 526),
            },
            "cedar_lab": {
                "entry": pygame.Vector2(scale_point((640, 1108), lab_scale)),
                "professor": scale_vector((760, 848), lab_scale) + pygame.Vector2(0, 28),
                "starter": pygame.Vector2(scale_point((640, 748), lab_scale)),
                "exit": pygame.Vector2(scale_rect(pygame.Rect(590, 1158, 100, 88), lab_scale).center),
            },
            "mira_house": {
                "entry": pygame.Vector2(scale_point((640, 1110), house_scale)),
                "chest": pygame.Vector2(scale_point((936, 770), house_scale)),
                "exit": pygame.Vector2(scale_rect(pygame.Rect(588, 1158, 104, 96), house_scale).center),
            },
        }


class Game:
    def __init__(
        self,
        *,
        headless: bool = False,
        rng: random.Random | None = None,
        start_in_title: bool = True,
        save_path: Path | None = None,
    ) -> None:
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.clock = pygame.time.Clock()
        self.headless = headless
        self.rng = rng or random.Random()
        self.audio = AudioManager(enabled=not headless)
        self.save_path = save_path or SAVE_PATH
        self.save_snapshot_cache: dict | None = None

        self.font_small = pygame.font.Font(None, 24)
        self.font_medium = pygame.font.Font(None, 30)
        self.font_large = pygame.font.Font(None, 40)
        self.font_title = pygame.font.Font(None, 68)

        self.item_icons = build_item_icons()
        self.grass_frames = load_grass_frames()
        self.grass_overlay_frames = load_grass_frames(scale=0.72) or self.grass_frames
        self.ability_effects = self.load_ability_effects()
        self.species = self.load_species_catalog()
        self.scenes = self.build_scenes()
        self.scene_key = "meadow"
        self.map_surface = self.scenes["meadow"].surface
        self.battle_background = pygame.image.load(BATTLE_DIR / "meadow_battle_bg.png").convert()
        animations, walk_cycle = load_player_animations()
        self.player = Player(animations, walk_cycle, start_position=(626, 645))

        self.mode = "title" if start_in_title else "world"
        self.running = True
        self.elapsed = 0.0
        self.toast_text = ""
        self.toast_timer = 0.0
        self.toast_color = WHITE
        self.toast_queue: deque[tuple[str, tuple[int, int, int]]] = deque()
        self.camera = pygame.Vector2()
        self.ambient_life = [
            (226, 520, 0.0, (255, 232, 140)),
            (284, 548, 1.3, (188, 230, 132)),
            (530, 438, 2.1, (255, 232, 140)),
            (876, 520, 0.6, (255, 210, 126)),
            (904, 584, 1.8, (188, 230, 132)),
            (576, 1122, 2.7, (255, 232, 140)),
            (1032, 252, 0.9, (180, 220, 255)),
            (1110, 312, 1.9, (180, 220, 255)),
        ]

        self.quest_stage = "meet_professor"
        self.party: list[Creature] = []
        self.lead_index = 0
        self.journal_index = 0
        self.inventory = {"capture_orb": 0, "berry": 0}
        self.seen_species: set[str] = set()
        self.caught_species: set[str] = set()
        self.sprint_unlocked = False
        self.capture_charm = False
        self.house_treasure_claimed = False
        self.encounter_progress = 0.0
        self.next_encounter_at = self.roll_next_encounter_distance()
        self.encounter_cooldown = 0.0
        self.encounter_warning_shown = False
        self.grass_sfx_cooldown = 0.0
        self.scene_transition_cooldown = 0.0
        self.no_starter_hint_shown = False

        self.dialogue_title = ""
        self.dialogue_pages: list[str] = []
        self.dialogue_index = 0
        self.dialogue_on_complete = None
        self.ending_pages: list[str] = []
        self.ending_index = 0

        self.transition_timer = 0.0
        self.transition_total = 0.0
        self.transition_kind = "encounter"
        self.pending_scene_entry: tuple[str, tuple[float, float], str | None] | None = None
        self.transition_switched_scene = False
        self.pending_enemy: Creature | None = None
        self.battle: BattleState | None = None
        self.play_mode_key = "manual"
        self.autoplayer: PPOAutoplayer | None = None
        self.ai_pressed_keys: set[int] = set()
        self.ai_status_text = "Player Mode: manual control"
        self.paused = False

    def load_ability_effects(self) -> dict[str, pygame.Surface]:
        if not ABILITY_EFFECT_SHEET_PATH.exists():
            return {}

        sheet = pygame.image.load(ABILITY_EFFECT_SHEET_PATH).convert_alpha()
        cell_width = sheet.get_width() // 3
        cell_height = sheet.get_height() // 3
        move_order = [
            "Leaf Dash",
            "Seed Pop",
            "Leaf Guard",
            "Pebble Toss",
            "Shell Bump",
            "Moss Guard",
            "Ember Pounce",
            "Kindled Dash",
            "Flame Curl",
        ]

        effects: dict[str, pygame.Surface] = {}
        for index, move_name in enumerate(move_order):
            cell = pygame.Surface((cell_width, cell_height), pygame.SRCALPHA)
            source = pygame.Rect(
                (index % 3) * cell_width,
                (index // 3) * cell_height,
                cell_width,
                cell_height,
            )
            cell.blit(sheet, (0, 0), source)
            effects[move_name] = cell

        extra_effects = {
            "Bubble Jet": BATTLE_DIR / "bubble_jet.png",
            "Tide Dash": BATTLE_DIR / "tide_dash.png",
            "Shell Splash": BATTLE_DIR / "shell_splash.png",
        }
        for move_name, path in extra_effects.items():
            if path.exists():
                effects[move_name] = pygame.image.load(path).convert_alpha()
        return effects

    def load_species_catalog(self) -> dict[str, Species]:
        def load_pair(asset_key: str) -> tuple[pygame.Surface, pygame.Surface]:
            front = pygame.image.load(CREATURE_DIR / f"{asset_key}_front.png").convert_alpha()
            back = pygame.image.load(CREATURE_DIR / f"{asset_key}_back.png").convert_alpha()
            return front, back

        def make_front_sprite(surface: pygame.Surface) -> pygame.Surface:
            framed = fit_surface_to_canvas(surface, (148, 148), padding=12, align="bottom")
            return pygame.transform.scale_by(framed, 1.24)

        def make_back_sprite(surface: pygame.Surface) -> pygame.Surface:
            framed = fit_surface_to_canvas(surface, (148, 148), padding=14, align="bottom")
            return pygame.transform.scale_by(framed, 1.16)

        def make_icon(surface: pygame.Surface) -> pygame.Surface:
            return fit_surface_to_canvas(surface, (60, 60), padding=4, align="bottom")

        leafawn_front, leafawn_back = load_pair("leafawn")
        flarekit_front, flarekit_back = load_pair("flarekit")
        tidefin_front, tidefin_back = load_pair("tidefin")
        mothleaf_front, mothleaf_back = load_pair("mothleaf")
        bubbun_front, bubbun_back = load_pair("bubbun")
        sparrook_front, sparrook_back = load_pair("sparrook")

        return {
            "Leafawn": Species(
                key="Leafawn",
                name="Leafawn",
                element="Grass",
                base_hp=30,
                front_sprite=make_front_sprite(leafawn_front),
                back_sprite=make_back_sprite(leafawn_back),
                icon=make_icon(leafawn_front),
                moves=(
                    Move("Leaf Dash", 9, 0.92, "{target} was slashed by leaves for {damage} damage!"),
                    Move("Seed Pop", 11, 0.82, "Bursting seeds popped around {target} for {damage} damage!"),
                    Move("Leaf Guard", 0, 1.0, "Leafawn tucked in behind its leaves.", "guard"),
                ),
                accent=(114, 197, 98),
            ),
            "Flarekit": Species(
                key="Flarekit",
                name="Flarekit",
                element="Fire",
                base_hp=28,
                front_sprite=make_front_sprite(flarekit_front),
                back_sprite=make_back_sprite(flarekit_back),
                icon=make_icon(flarekit_front),
                moves=(
                    Move("Ember Pounce", 9, 0.92, "{target} was singed for {damage} damage!"),
                    Move("Kindled Dash", 11, 0.84, "Flarekit dashed through sparks and dealt {damage} damage to {target}!"),
                    Move("Flame Curl", 0, 1.0, "Flarekit curled into a warm defensive flame.", "guard"),
                ),
                accent=(236, 142, 72),
            ),
            "Tidefin": Species(
                key="Tidefin",
                name="Tidefin",
                element="Water",
                base_hp=32,
                front_sprite=make_front_sprite(tidefin_front),
                back_sprite=make_back_sprite(tidefin_back),
                icon=make_icon(tidefin_front),
                moves=(
                    Move("Bubble Jet", 9, 0.93, "Bubbles burst over {target} for {damage} damage!"),
                    Move("Tide Dash", 11, 0.84, "Tidefin rushed in on a wave for {damage} damage!"),
                    Move("Shell Splash", 0, 1.0, "Tidefin hid behind a curling splash.", "guard"),
                ),
                accent=(84, 164, 226),
            ),
            "Mothleaf": Species(
                key="Mothleaf",
                name="Mothleaf",
                element="Grass",
                base_hp=27,
                front_sprite=make_front_sprite(mothleaf_front),
                back_sprite=make_back_sprite(mothleaf_back),
                icon=make_icon(mothleaf_front),
                moves=(
                    Move("Leaf Dash", 8, 0.94, "{target} was clipped by leafy wings for {damage} damage!"),
                    Move("Seed Pop", 10, 0.84, "Pollen seeds popped around {target} for {damage} damage!"),
                    Move("Leaf Guard", 0, 1.0, "Mothleaf folded its wings into a leafy shield.", "guard"),
                ),
                accent=(156, 202, 86),
            ),
            "Bubbun": Species(
                key="Bubbun",
                name="Bubbun",
                element="Water",
                base_hp=31,
                front_sprite=make_front_sprite(bubbun_front),
                back_sprite=make_back_sprite(bubbun_back),
                icon=make_icon(bubbun_front),
                moves=(
                    Move("Bubble Jet", 8, 0.95, "Bubbun splashed {target} for {damage} damage!"),
                    Move("Tide Dash", 10, 0.86, "Bubbun bounced forward on a wave for {damage} damage!"),
                    Move("Shell Splash", 0, 1.0, "Bubbun hid inside a wobbling bubble.", "guard"),
                ),
                accent=(90, 170, 228),
            ),
            "Sparrook": Species(
                key="Sparrook",
                name="Sparrook",
                element="Fire",
                base_hp=29,
                front_sprite=make_front_sprite(sparrook_front),
                back_sprite=make_back_sprite(sparrook_back),
                icon=make_icon(sparrook_front),
                moves=(
                    Move("Ember Pounce", 8, 0.94, "Sparrook snapped embers at {target} for {damage} damage!"),
                    Move("Kindled Dash", 10, 0.86, "Sparrook streaked through sparks for {damage} damage!"),
                    Move("Flame Curl", 0, 1.0, "Sparrook fluffed its heated feathers.", "guard"),
                ),
                accent=(230, 184, 76),
            ),
        }

    def build_npcs(self, scene_key: str) -> dict[str, NPC]:
        professor_sprite = pygame.image.load(NPC_DIR / "professor_cedar.png").convert_alpha()
        healer_sprite = pygame.image.load(NPC_DIR / "ranger_mira.png").convert_alpha()
        professor_sprite = pygame.transform.scale_by(professor_sprite, 1.08)
        healer_sprite = pygame.transform.scale_by(healer_sprite, 1.08)

        if scene_key == "cedar_lab":
            scale = scene_scale(scene_key)
            return {
                "professor": NPC(
                    key="professor",
                    name="Professor Cedar",
                    position=scale_vector((760, 848), scale),
                    sprite=professor_sprite,
                    prompt="Talk",
                    marker_color=ACCENT,
                )
            }
        if scene_key == "meadow":
            return {
                "healer": NPC(
                    key="healer",
                    name="Ranger Mira",
                    position=pygame.Vector2(1055, 742),
                    sprite=healer_sprite,
                    prompt="Rest",
                    marker_color=BLUE,
                )
            }
        if scene_key == "mira_house":
            scale = scene_scale(scene_key)
            return {
                "healer": NPC(
                    key="healer",
                    name="Ranger Mira",
                    position=scale_vector((1040, 800), scale),
                    sprite=healer_sprite,
                    prompt="Rest",
                    marker_color=BLUE,
                )
            }
        return {}

    def build_pickups(self, scene_key: str) -> list[ItemPickup]:
        if scene_key != "meadow":
            return []
        return [
            ItemPickup("berry_patch", pygame.Vector2(458, 310), "berry", 2, "Sweet Berries"),
            ItemPickup("trail_orbs", pygame.Vector2(896, 930), "capture_orb", 2, "Capture Orbs"),
            ItemPickup("southern_berries", pygame.Vector2(518, 1180), "berry", 3, "Trail Berries"),
        ]

    def build_grass_patches(self, scene_key: str) -> list[GrassPatch]:
        if scene_key != "meadow":
            return []
        return [
            GrassPatch(
                "lab_side",
                pygame.Rect(710, 232, 112, 60),
                ((729, 289), (766, 281), (804, 289)),
            ),
            GrassPatch(
                "west_clearing",
                pygame.Rect(180, 488, 176, 76),
                ((208, 560), (252, 553), (298, 560), (229, 538), (276, 531), (322, 538)),
            ),
            GrassPatch(
                "crossroads",
                pygame.Rect(494, 392, 92, 62),
                ((515, 451), (548, 445), (580, 451)),
            ),
            GrassPatch(
                "east_grove",
                pygame.Rect(846, 470, 98, 170),
                ((869, 525), (906, 525), (869, 567), (906, 567), (888, 611)),
            ),
            GrassPatch(
                "yard_edge",
                pygame.Rect(500, 748, 98, 58),
                ((521, 804), (553, 794), (586, 804)),
            ),
            GrassPatch(
                "trail_east",
                pygame.Rect(704, 794, 110, 58),
                ((727, 848), (763, 840), (800, 848)),
            ),
            GrassPatch(
                "south_steps",
                pygame.Rect(514, 1074, 112, 58),
                ((536, 1130), (572, 1120), (608, 1130)),
            ),
        ]

    def build_props(self, scene_key: str) -> dict[str, pygame.Rect]:
        if scene_key == "meadow":
            return {
                "sign": pygame.Rect(878, 295, 78, 120),
                "pond": pygame.Rect(916, 110, 320, 250),
            }
        if scene_key == "cedar_lab":
            scale = scene_scale(scene_key)
            props = {
                "starter_leafawn": pygame.Rect(404, 450, 134, 274),
                "starter_flarekit": pygame.Rect(573, 450, 134, 274),
                "starter_tidefin": pygame.Rect(742, 450, 134, 274),
                "lab_terminal": pygame.Rect(468, 180, 280, 170),
            }
            return {key: scale_rect(rect, scale) for key, rect in props.items()}
        if scene_key == "mira_house":
            scale = scene_scale(scene_key)
            props = {
                "treasure_chest": pygame.Rect(912, 546, 152, 192),
                "guest_bed": pygame.Rect(980, 190, 190, 296),
            }
            return {key: scale_rect(rect, scale) for key, rect in props.items()}
        return {}

    def build_doorways(self, scene_key: str) -> list[Doorway]:
        if scene_key == "meadow":
            return [
                Doorway(
                    "cedar_lab",
                    pygame.Rect(604, 228, 42, 28),
                    "cedar_lab",
                    scale_point((640, 1108), scene_scale("cedar_lab")),
                    "up",
                ),
                Doorway(
                    "mira_house",
                    pygame.Rect(1028, 642, 42, 30),
                    "mira_house",
                    scale_point((640, 1110), scene_scale("mira_house")),
                    "up",
                ),
            ]
        if scene_key == "cedar_lab":
            scale = scene_scale(scene_key)
            return [
                Doorway("lab_exit", scale_rect(pygame.Rect(590, 1158, 100, 88), scale), "meadow", (625, 274), "down")
            ]
        if scene_key == "mira_house":
            scale = scene_scale(scene_key)
            return [
                Doorway("house_exit", scale_rect(pygame.Rect(588, 1158, 104, 96), scale), "meadow", (1048, 760), "down")
            ]
        return []

    def build_scenes(self) -> dict[str, SceneData]:
        meadow_surface = pygame.image.load(MAP_PATH).convert()
        lab_scale = scene_scale("cedar_lab")
        house_scale = scene_scale("mira_house")
        lab_surface = scale_surface(pygame.image.load(INTERIOR_DIR / "cedar_lab.png").convert(), lab_scale)
        house_surface = scale_surface(pygame.image.load(INTERIOR_DIR / "mira_house.png").convert(), house_scale)

        return {
            "meadow": SceneData(
                key="meadow",
                surface=meadow_surface,
                walk_bounds=meadow_surface.get_rect(),
                colliders=build_static_colliders(),
                props=self.build_props("meadow"),
                doorways=self.build_doorways("meadow"),
                grass_patches=self.build_grass_patches("meadow"),
                pickups=self.build_pickups("meadow"),
                npcs=self.build_npcs("meadow"),
            ),
            "cedar_lab": SceneData(
                key="cedar_lab",
                surface=lab_surface,
                walk_bounds=scale_rect(pygame.Rect(78, 96, 1124, 1130), lab_scale),
                colliders=[scale_rect(rect, lab_scale) for rect in build_lab_colliders()],
                props=self.build_props("cedar_lab"),
                doorways=self.build_doorways("cedar_lab"),
                grass_patches=[],
                pickups=[],
                npcs=self.build_npcs("cedar_lab"),
            ),
            "mira_house": SceneData(
                key="mira_house",
                surface=house_surface,
                walk_bounds=scale_rect(pygame.Rect(78, 96, 1124, 1130), house_scale),
                colliders=[scale_rect(rect, house_scale) for rect in build_house_colliders()],
                props=self.build_props("mira_house"),
                doorways=self.build_doorways("mira_house"),
                grass_patches=[],
                pickups=[],
                npcs=self.build_npcs("mira_house"),
            ),
        }

    def current_scene(self) -> SceneData:
        return self.scenes[self.scene_key]

    def has_save_file(self) -> bool:
        return self.save_path.exists()

    def save_progress_data(self) -> dict | None:
        if self.save_snapshot_cache is not None:
            return self.save_snapshot_cache
        if not self.has_save_file():
            return None
        try:
            data = json.loads(self.save_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        self.save_snapshot_cache = self.migrate_save_data(data)
        return self.save_snapshot_cache

    def migrate_save_data(self, data: dict) -> dict:
        changed = False
        version = int(data.get("version", 0))
        if version < SAVE_VERSION:
            party = data.get("party", [])
            if (
                version < 2
                and isinstance(party, list)
                and len(party) == 1
                and data.get("quest_stage") == "survey_grass"
                and not data.get("caught_species")
            ):
                lead = party[0]
                species_key = SPECIES_ALIASES.get(lead.get("species"), lead.get("species"))
                if (
                    isinstance(lead, dict)
                    and species_key in STARTER_SPECIES
                    and int(lead.get("level", 1)) == 5
                    and int(lead.get("exp", 0)) == 0
                ):
                    lead.update(self.serialize_creature(self.make_creature(str(species_key), 1)))
                    changed = True
            data["version"] = SAVE_VERSION
            changed = True

        if changed:
            try:
                self.save_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except OSError:
                pass
        return data

    def save_summary_text(self) -> str | None:
        data = self.save_progress_data()
        if data is None:
            if self.has_save_file():
                return "Save data found"
            return None
        try:
            scene_key = data.get("scene_key")
        except AttributeError:
            return "Save data found"

        scene_name = {
            "meadow": "Verdant Meadow",
            "cedar_lab": "Cedar Lab",
            "mira_house": "Mira's House",
        }.get(scene_key, "Verdant Meadow")
        party = data.get("party", [])
        lead_index = int(clamp(int(data.get("lead_index", 0)), 0, max(0, len(party) - 1))) if party else 0
        lead = party[lead_index] if party else None
        caught_species = {SPECIES_ALIASES.get(key, key) for key in data.get("caught_species", [])}
        wild_caught = len(set(WILD_SPECIES).intersection(caught_species))
        charm_done = bool(data.get("capture_charm", False))
        survey = "Complete" if wild_caught >= len(WILD_SPECIES) and charm_done else f"{wild_caught}/{len(WILD_SPECIES)} survey"
        if lead:
            lead_name = SPECIES_ALIASES.get(lead.get("species"), lead.get("species", "Partner"))
            return f"{lead_name} Lv.{lead.get('level', 1)} in {scene_name}  |  {survey}"
        return f"Saved at {scene_name}  |  {survey}"

    def serialize_creature(self, creature: Creature) -> dict[str, int | str | bool]:
        return {
            "species": creature.species.key,
            "level": creature.level,
            "max_hp": creature.max_hp,
            "hp": creature.hp,
            "exp": creature.exp,
            "guarding": creature.guarding,
        }

    def restore_creature(self, data: dict) -> Creature | None:
        species_key = SPECIES_ALIASES.get(data.get("species"), data.get("species"))
        if species_key not in self.species:
            return None
        creature = self.make_creature(str(species_key), int(data.get("level", 1)))
        creature.max_hp = max(1, int(data.get("max_hp", creature.max_hp)))
        creature.hp = int(clamp(int(data.get("hp", creature.max_hp)), 0, creature.max_hp))
        creature.exp = max(0, int(data.get("exp", 0)))
        creature.guarding = bool(data.get("guarding", False))
        return creature

    def collected_pickup_keys(self) -> list[str]:
        keys: list[str] = []
        for scene in self.scenes.values():
            keys.extend(pickup.key for pickup in scene.pickups if pickup.collected)
        return sorted(keys)

    def save_game(self, *, quiet: bool = True) -> None:
        if self.mode == "title":
            return

        data = {
            "version": SAVE_VERSION,
            "scene_key": self.scene_key,
            "player": {
                "x": round(self.player.position.x, 2),
                "y": round(self.player.position.y, 2),
                "direction": self.player.direction,
            },
            "quest_stage": self.quest_stage,
            "party": [self.serialize_creature(creature) for creature in self.party],
            "lead_index": self.lead_index,
            "journal_index": self.journal_index,
            "inventory": self.inventory,
            "seen_species": sorted(self.seen_species),
            "caught_species": sorted(self.caught_species),
            "sprint_unlocked": self.sprint_unlocked,
            "capture_charm": self.capture_charm,
            "house_treasure_claimed": self.house_treasure_claimed,
            "collected_pickups": self.collected_pickup_keys(),
        }

        try:
            self.save_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            if not quiet:
                self.audio.play("error")
                self.push_toast("Save failed. Check the project folder permissions.", RED)
            return
        self.save_snapshot_cache = data

        if not quiet:
            self.audio.play("confirm")
            self.push_toast("Adventure saved.", ACCENT)

    def load_game(self) -> bool:
        try:
            data = json.loads(self.save_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.audio.play("error")
            self.push_toast("Could not load save data.", RED)
            return False
        self.save_snapshot_cache = self.migrate_save_data(data)
        data = self.save_snapshot_cache

        scene_key = data.get("scene_key", "meadow")
        if scene_key not in self.scenes:
            scene_key = "meadow"

        party = [
            creature
            for creature in (self.restore_creature(raw) for raw in data.get("party", []))
            if creature is not None
        ]
        self.party = party
        self.lead_index = int(clamp(int(data.get("lead_index", 0)), 0, max(0, len(self.party) - 1)))
        self.journal_index = int(clamp(int(data.get("journal_index", 0)), 0, max(0, len(self.party) - 1)))
        self.inventory = {
            "capture_orb": max(0, int(data.get("inventory", {}).get("capture_orb", 0))),
            "berry": max(0, int(data.get("inventory", {}).get("berry", 0))),
        }
        self.quest_stage = data.get("quest_stage", "meet_professor")
        valid_quests = {
            "meet_professor",
            "choose_starter",
            "survey_grass",
            "report_back",
            "free_roam",
            "ending_ready",
            "complete",
        }
        if self.quest_stage not in valid_quests:
            self.quest_stage = "meet_professor"
        self.seen_species = {
            mapped
            for key in data.get("seen_species", [])
            if (mapped := SPECIES_ALIASES.get(key, key)) in self.species
        }
        self.caught_species = {
            mapped
            for key in data.get("caught_species", [])
            if (mapped := SPECIES_ALIASES.get(key, key)) in self.species
        }
        self.sprint_unlocked = bool(data.get("sprint_unlocked", False))
        self.capture_charm = bool(data.get("capture_charm", False))
        self.house_treasure_claimed = bool(data.get("house_treasure_claimed", False))
        if self.quest_stage == "free_roam" and self.ending_requirements_met():
            self.quest_stage = "ending_ready"

        collected = set(data.get("collected_pickups", []))
        for scene in self.scenes.values():
            for pickup in scene.pickups:
                pickup.collected = pickup.key in collected

        player_data = data.get("player", {})
        default_position = (626, 645)
        position = (
            float(player_data.get("x", default_position[0])),
            float(player_data.get("y", default_position[1])),
        )
        self.enter_scene(scene_key, position, direction=player_data.get("direction", "down"))
        self.mode = "world"
        self.dialogue_on_complete = None
        self.dialogue_pages = []
        self.ending_pages = []
        self.ending_index = 0
        self.battle = None
        self.pending_enemy = None
        self.pending_scene_entry = None
        self.transition_timer = 0.0
        self.transition_total = 0.0
        self.push_toast("Adventure loaded.", ACCENT)
        return True

    def start_new_adventure(self) -> None:
        if self.save_path.exists():
            try:
                self.save_path.unlink()
            except OSError:
                pass
        self.save_snapshot_cache = None
        self.scene_key = "meadow"
        self.player.position.update(626, 645)
        self.player.direction = "down"
        self.quest_stage = "meet_professor"
        self.party.clear()
        self.lead_index = 0
        self.journal_index = 0
        self.inventory = {"capture_orb": 0, "berry": 0}
        self.seen_species.clear()
        self.caught_species.clear()
        self.sprint_unlocked = False
        self.capture_charm = False
        self.house_treasure_claimed = False
        self.encounter_progress = 0.0
        self.encounter_cooldown = 0.0
        self.encounter_warning_shown = False
        self.next_encounter_at = self.roll_next_encounter_distance()
        self.no_starter_hint_shown = False
        self.ending_pages = []
        self.ending_index = 0
        self.dialogue_title = ""
        self.dialogue_pages = []
        self.dialogue_index = 0
        self.dialogue_on_complete = None
        self.transition_timer = 0.0
        self.transition_total = 0.0
        self.pending_scene_entry = None
        self.pending_enemy = None
        self.battle = None
        self.paused = False
        for scene in self.scenes.values():
            for pickup in scene.pickups:
                pickup.collected = False
        self.mode = "world"
        self.push_toast("Step into Cedar Lab and start your survey.", ACCENT)

    def select_play_mode(self, mode_key: str) -> None:
        if mode_key not in PLAY_MODE_SPECS:
            return
        self.play_mode_key = mode_key
        spec = PLAY_MODE_SPECS[mode_key]
        if mode_key != "manual":
            self.rng = random.Random(spec.seed)
        self.start_new_adventure()
        if mode_key == "manual":
            self.autoplayer = None
            self.ai_pressed_keys = set()
            self.ai_status_text = "Player Mode: manual control"
        else:
            self.autoplayer = PPOAutoplayer(self, mode_key)
            self.ai_status_text = f"{spec.title}: {spec.detail}"
        self.paused = False
        self.push_toast(f"{spec.title} started fresh.", spec.color, duration=3.0)

    def enter_scene(
        self,
        scene_key: str,
        position: tuple[float, float],
        *,
        direction: str | None = None,
    ) -> None:
        self.scene_key = scene_key
        self.player.position.update(*position)
        if direction is not None:
            self.player.direction = direction
        self.scene_transition_cooldown = 0.35
        self.encounter_progress = 0.0
        self.next_encounter_at = self.roll_next_encounter_distance()
        self.save_game()

    def start_door_transition(self, doorway: Doorway) -> None:
        self.pending_scene_entry = (
            doorway.target_scene,
            doorway.target_position,
            doorway.target_direction,
        )
        self.transition_kind = "door"
        self.transition_total = 0.62
        self.transition_timer = self.transition_total
        self.transition_switched_scene = False
        self.mode = "transition"
        self.audio.play("interact")

    def make_creature(self, species_key: str, level: int) -> Creature:
        return Creature(self.species[species_key], level)

    def lead_creature(self) -> Creature | None:
        if not self.party:
            return None
        self.lead_index = int(clamp(self.lead_index, 0, len(self.party) - 1))
        return self.party[self.lead_index]

    def has_healthy_party(self) -> bool:
        return any(not creature.is_fainted for creature in self.party)

    def first_healthy_party_index(self, exclude: int | None = None) -> int | None:
        for index, creature in enumerate(self.party):
            if exclude is not None and index == exclude:
                continue
            if not creature.is_fainted:
                return index
        return None

    def heal_party(self) -> None:
        for creature in self.party:
            creature.heal_full()

    def current_speed(self, pressed: pygame.key.ScancodeWrapper) -> float:
        is_sprinting = self.sprint_unlocked and any(pressed[key] for key in SPRINT_KEYS)
        self.player.sprinting = is_sprinting
        speed = 270.0 if is_sprinting else 190.0
        if self.scene_key in INTERIOR_SCENES:
            speed *= 0.88
        if self.autoplayer is not None and self.play_mode_key in {"ppo_trained", "ppo_ultimate"}:
            speed *= 0.72
        return speed

    def dynamic_colliders(self) -> list[pygame.Rect]:
        scene = self.current_scene()
        return scene.colliders + [npc.hitbox() for npc in scene.npcs.values()]

    def roll_next_encounter_distance(self) -> float:
        if getattr(self, "quest_stage", "") == "survey_grass":
            return self.rng.uniform(48.0, 82.0)
        return self.rng.uniform(120.0, 220.0)

    def capture_rate_for(self, enemy: Creature) -> float:
        catch_rate = 0.22 + 0.52 * (1.0 - enemy.hp / max(1, enemy.max_hp))
        if enemy.species.key == "Sparrook":
            catch_rate -= 0.05
        if self.capture_charm:
            catch_rate += 0.08
        return clamp(catch_rate, 0.12, 0.92)

    def sync_music(self) -> None:
        desired = "battle" if self.mode == "battle" else "world"
        self.audio.play_music(desired)

    def push_toast(
        self,
        text: str,
        color: tuple[int, int, int] = WHITE,
        *,
        duration: float = 2.6,
    ) -> None:
        if self.toast_timer > 0:
            self.toast_queue.append((text, color))
            return
        self.toast_text = text
        self.toast_color = color
        self.toast_timer = duration

    def update_toasts(self, dt: float) -> None:
        if self.toast_timer > 0:
            self.toast_timer = max(0.0, self.toast_timer - dt)
            if self.toast_timer == 0 and self.toast_queue:
                text, color = self.toast_queue.popleft()
                self.push_toast(text, color)

    def start_dialogue(
        self,
        title: str,
        pages: list[str],
        on_complete=None,
    ) -> None:
        self.dialogue_title = title
        self.dialogue_pages = pages
        self.dialogue_index = 0
        self.dialogue_on_complete = on_complete
        self.mode = "dialogue"

    def advance_dialogue(self) -> None:
        self.audio.play("confirm")
        if self.dialogue_index < len(self.dialogue_pages) - 1:
            self.dialogue_index += 1
            return

        callback = self.dialogue_on_complete
        self.dialogue_on_complete = None
        self.mode = "world"
        if callback is not None:
            callback()

    def scene_title(self) -> str:
        return {
            "meadow": "Verdant Meadow",
            "cedar_lab": "Cedar Lab",
            "mira_house": "Mira's House",
        }[self.scene_key]

    def doorway_to(self, scene_key: str) -> Doorway | None:
        for doorway in self.current_scene().doorways:
            if doorway.target_scene == scene_key:
                return doorway
        return self.current_scene().doorways[0] if self.current_scene().doorways else None

    def objective_marker(self) -> tuple[pygame.Vector2, str] | None:
        scene = self.current_scene()

        if self.quest_stage in {"meet_professor", "report_back", "ending_ready"} or (
            self.quest_stage == "free_roam" and self.ending_requirements_met()
        ):
            if scene.key == "cedar_lab":
                professor = scene.npcs.get("professor")
                if professor is not None:
                    return professor.position, "Cedar"
            doorway = self.doorway_to("cedar_lab")
            return (pygame.Vector2(doorway.rect.center), "Lab") if doorway is not None else None

        if self.quest_stage == "choose_starter":
            if scene.key == "cedar_lab":
                rect = scene.props.get("starter_flarekit")
                if rect is not None:
                    return pygame.Vector2(rect.center), "Choose"
            doorway = self.doorway_to("cedar_lab")
            return (pygame.Vector2(doorway.rect.center), "Lab") if doorway is not None else None

        if self.quest_stage == "survey_grass":
            if scene.key == "meadow":
                patch = next((patch for patch in scene.grass_patches if patch.key == "west_clearing"), None)
                if patch is not None:
                    return pygame.Vector2(patch.rect.center), "Grass"
            doorway = self.doorway_to("meadow")
            return (pygame.Vector2(doorway.rect.center), "Exit") if doorway is not None else None

        if self.quest_stage == "free_roam" and self.capture_charm and self.remaining_wild_species():
            if scene.key == "meadow":
                target_patch_key = {
                    "Mothleaf": "west_clearing",
                    "Bubbun": "south_steps",
                    "Sparrook": "east_grove",
                }.get(self.remaining_wild_species()[0], "east_grove")
                patch = next((patch for patch in scene.grass_patches if patch.key == target_patch_key), None)
                if patch is not None:
                    return pygame.Vector2(patch.rect.center), "Wilds"
            doorway = self.doorway_to("meadow")
            return (pygame.Vector2(doorway.rect.center), "Exit") if doorway is not None else None

        if self.quest_stage == "free_roam" and not self.capture_charm:
            if scene.key == "mira_house":
                rect = scene.props.get("treasure_chest")
                if rect is not None:
                    return pygame.Vector2(rect.center), "Secret"
            doorway = self.doorway_to("mira_house")
            return (pygame.Vector2(doorway.rect.center), "House") if doorway is not None else None

        return None

    def current_objective(self) -> str:
        if self.quest_stage == "meet_professor" and self.scene_key == "cedar_lab":
            return "Speak with Professor Cedar inside the lab."
        if self.quest_stage == "free_roam":
            remaining = self.remaining_wild_species()
            if remaining and not self.capture_charm:
                return f"Catch {', '.join(remaining)} and uncover Mira's hidden charm."
            if remaining:
                return f"Catch the remaining wilds: {', '.join(remaining)}."
            if not self.capture_charm:
                return "Find Mira's hidden charm, then return to Professor Cedar."
            return "Return to Professor Cedar with your completed meadow survey."
        objectives = {
            "meet_professor": "Enter Cedar Lab and speak with Professor Cedar.",
            "choose_starter": "Choose Leafawn, Flarekit, or Tidefin on Cedar's lab table.",
            "survey_grass": "Step into the tall grass outside and handle one wild Mothleaf encounter.",
            "report_back": "Return to Professor Cedar in the lab with your field report.",
            "free_roam": "Catch Mothleaf, Bubbun, and Sparrook, then uncover Mira's hidden charm.",
            "ending_ready": "Return to Professor Cedar with your completed meadow survey.",
            "complete": "Your meadow survey is complete. Free roam remains open across the meadow.",
        }
        return objectives[self.quest_stage]

    def ending_requirements_met(self) -> bool:
        return self.capture_charm and set(WILD_SPECIES).issubset(self.caught_species)

    def remaining_wild_species(self) -> list[str]:
        return [species_key for species_key in WILD_SPECIES if species_key not in self.caught_species]

    def survey_progress_text(self) -> str:
        caught = len(set(WILD_SPECIES).intersection(self.caught_species))
        total = len(WILD_SPECIES)
        if caught >= total and self.capture_charm:
            return "Survey: Complete"
        suffix = " + Charm" if self.capture_charm else ""
        return f"Survey: {caught}/{total}{suffix}"

    def compact_species_list(self, species_keys: list[str], *, limit: int = 2) -> str:
        if len(species_keys) <= limit:
            return ", ".join(species_keys)
        shown = ", ".join(species_keys[:limit])
        return f"{shown} +{len(species_keys) - limit}"

    def habitat_hint(self, species_key: str) -> str:
        return {
            "Mothleaf": "Mothleaf tends to drift through the west clearing and the grass near the lab.",
            "Bubbun": "Bubbun favors the southern grass and the wetter patches near the pond trail.",
            "Sparrook": "Sparrook likes the hotter eastern grass and the route near Mira's side of the meadow.",
        }.get(species_key, "")

    def type_color(self, element: str) -> tuple[int, int, int]:
        return {
            "Grass": (118, 198, 92),
            "Fire": (236, 148, 82),
            "Water": (92, 158, 228),
        }.get(element, ACCENT)

    def type_multiplier(self, attack_element: str, defend_element: str) -> float:
        strengths = {
            "Grass": "Water",
            "Fire": "Grass",
            "Water": "Fire",
        }
        if strengths.get(attack_element) == defend_element:
            return 1.25
        if strengths.get(defend_element) == attack_element:
            return 0.82
        return 1.0

    def exp_ratio(self, level: int, exp_value: float) -> float:
        return clamp(exp_value / max(1, 10 + level * 5), 0.0, 1.0)

    def build_exp_segments(self, creature: Creature, amount: int) -> list[ExpGainSegment]:
        if amount <= 0:
            return []

        segments: list[ExpGainSegment] = []
        level = creature.level
        exp_value = creature.exp
        remaining = amount
        while remaining > 0:
            threshold = 10 + level * 5
            gain = min(remaining, threshold - exp_value)
            end_exp = exp_value + gain
            leveled = end_exp >= threshold
            segments.append(
                ExpGainSegment(
                    level=level,
                    start_exp=exp_value,
                    end_exp=threshold if leveled else end_exp,
                    threshold=threshold,
                    level_up=leveled,
                )
            )
            remaining -= gain
            if leveled:
                level += 1
                exp_value = 0
            else:
                exp_value = end_exp
        return segments

    def exp_segment_duration(self, segment: ExpGainSegment) -> float:
        distance = max(1, segment.end_exp - segment.start_exp)
        return clamp(0.28 + distance / 28.0, 0.28, 0.92)

    def start_exp_animation(
        self,
        creature: Creature,
        amount: int,
        segments: list[ExpGainSegment],
        post_messages: list[str],
        next_phase: str,
    ) -> None:
        if self.battle is None or not segments:
            self.queue_battle_messages(post_messages or ["The meadow grew quiet again."], next_phase)
            return

        animation = BattleExpAnimation(
            creature_name=creature.name,
            gain_amount=amount,
            segments=segments,
            post_messages=post_messages,
            next_phase=next_phase,
            display_level=segments[0].level,
            display_exp=float(segments[0].start_exp),
            segment_duration=self.exp_segment_duration(segments[0]),
            banner_text=f"{creature.name} gained {amount} EXP",
        )
        self.battle.exp_animation = animation
        self.battle.phase = "exp_gain"

    def finish_exp_animation(self) -> None:
        if self.battle is None or self.battle.exp_animation is None:
            return

        animation = self.battle.exp_animation
        messages = animation.post_messages or ["The meadow grew quiet again."]
        next_phase = animation.next_phase
        self.battle.exp_animation = None
        self.queue_battle_messages(messages, next_phase)

    def update_exp_animation(self, dt: float) -> None:
        if self.battle is None or self.battle.exp_animation is None:
            return

        animation = self.battle.exp_animation
        segment = animation.current_segment()
        if segment is None:
            self.finish_exp_animation()
            return

        if animation.hold_timer > 0:
            animation.hold_timer = max(0.0, animation.hold_timer - dt)
            if animation.hold_timer == 0:
                segment = animation.current_segment()
                if segment is None:
                    self.finish_exp_animation()
                else:
                    animation.display_level = segment.level
                    animation.display_exp = float(segment.start_exp)
                    animation.segment_elapsed = 0.0
                    animation.segment_duration = self.exp_segment_duration(segment)
                    animation.banner_text = f"{animation.creature_name} gained {animation.gain_amount} EXP"
            return

        animation.segment_elapsed += dt
        progress = clamp(animation.segment_elapsed / max(0.001, animation.segment_duration), 0.0, 1.0)
        animation.display_level = segment.level
        animation.display_exp = segment.start_exp + (segment.end_exp - segment.start_exp) * progress

        if progress < 1.0:
            return

        animation.display_exp = float(segment.end_exp)
        animation.segment_elapsed = 0.0
        animation.segment_index += 1

        if segment.level_up:
            animation.banner_text = f"Level Up! {animation.creature_name} reached Lv.{segment.level + 1}"
            animation.hold_timer = EXP_LEVEL_HOLD_DURATION
            self.audio.play("level_up")
            return

        next_segment = animation.current_segment()
        if next_segment is None:
            self.finish_exp_animation()
            return

        animation.display_level = next_segment.level
        animation.display_exp = float(next_segment.start_exp)
        animation.segment_duration = self.exp_segment_duration(next_segment)

    def start_ending(self) -> None:
        lead = self.lead_creature()
        lead_name = lead.name if lead is not None else "your partner"
        self.quest_stage = "complete"
        self.heal_party()
        self.audio.play("quest")
        self.ending_pages = [
            "Professor Cedar pins the finished meadow report to the wall, then steps back with a smile that says the long day was worth it.",
            "Ranger Mira lights the porch for the last round of evening walkers while Mothleaf, Bubbun, and Sparrook settle back into the grass you mapped.",
            f"{lead_name} leans against your boots while the lab windows glow warm behind you. Verdant Meadow finally feels known, safe, and fully alive.",
            "Survey complete. Verdant Meadow is yours to revisit whenever you like.",
        ]
        self.ending_index = 0
        self.mode = "ending"
        self.save_game()

    def finish_ending(self) -> None:
        self.mode = "world"
        self.ending_pages = []
        self.ending_index = 0
        self.push_toast("Final report complete. Free roam stays open.", ACCENT, duration=3.2)
        self.save_game()

    def unlock_starter_choice(self) -> None:
        if self.quest_stage != "meet_professor":
            return
        self.quest_stage = "choose_starter"
        self.audio.play("quest")
        self.push_toast("Pick your first partner from the lab table.", ACCENT)

    def professor_dialogue(self) -> None:
        if self.quest_stage == "free_roam" and self.ending_requirements_met():
            self.quest_stage = "ending_ready"

        if self.quest_stage == "meet_professor":
            self.start_dialogue(
                "Professor Cedar",
                [
                    "Welcome to my little field lab. The whole meadow outside is active today, and I want fresh readings from its tall grass.",
                    "Pick one partner from the three on the table: Leafawn, Flarekit, or Tidefin. Once you've chosen, head outside, survive one real encounter, and report back to me.",
                ],
                on_complete=self.unlock_starter_choice,
            )
        elif self.quest_stage == "choose_starter":
            self.start_dialogue(
                "Professor Cedar",
                [
                    "Take your time and choose the partner that feels right. Leafawn is grassy and steady, Flarekit burns bright, and Tidefin keeps cool under pressure.",
                ],
            )
        elif self.quest_stage == "survey_grass":
            self.start_dialogue(
                "Professor Cedar",
                [
                    "Those new grass patches outside are perfect for field readings. A Mothleaf should be wandering in there right now.",
                    "Try your partner's moves, toss an Orb if you want, and come back once you've finished one encounter.",
                ],
            )
        elif self.quest_stage == "report_back":
            self.start_dialogue(
                "Professor Cedar",
                [
                    "Wonderful work. The meadow settled down the moment you stepped in and finished the first reading.",
                    "Take this field boost. You can sprint with Shift now, and I topped off your Orbs for extra exploring.",
                ],
                on_complete=self.complete_professor_report,
            )
        elif self.quest_stage == "ending_ready":
            self.start_dialogue(
                "Professor Cedar",
                [
                    "Leafawn, Flarekit, Tidefin, and the wild meadow trio are all logged. You even found Mira's hidden charm.",
                    "This is a complete field survey. The meadow is safer, the lab has real data, and your team made it happen.",
                    "Let's close the report together.",
                ],
                on_complete=self.start_ending,
            )
        elif self.quest_stage == "complete":
            self.start_dialogue(
                "Professor Cedar",
                [
                    "The final report is framed on the lab wall now. Whenever you want, the meadow is yours to revisit.",
                ],
            )
        else:
            remaining = self.remaining_wild_species()
            if not self.capture_charm:
                reminder = "Mira's hidden charm is still out there, and it matters for the final report."
            elif remaining:
                reminder = f"You're close. I still need entries for {', '.join(remaining)}."
            else:
                reminder = "You already have every wild entry logged. Bring that final report back to me."
            habitat_note = self.habitat_hint(remaining[0]) if remaining else "The meadow is in excellent shape today."
            self.start_dialogue(
                "Professor Cedar",
                [
                    reminder,
                    habitat_note,
                ],
            )

    def healer_dialogue(self) -> None:
        def finish_rest() -> None:
            self.heal_party()
            self.audio.play("heal")
            self.push_toast("Ranger Mira healed your whole team.", BLUE)
            self.save_game()

        if not self.party:
            if self.scene_key == "mira_house":
                self.start_dialogue(
                    "Ranger Mira",
                    [
                        "Make yourself at home. Professor Cedar keeps the first partner orbs in the lab, so go choose one and come back if you need rest.",
                    ],
                )
                return
            self.start_dialogue(
                "Ranger Mira",
                [
                    "Professor Cedar is waiting inside the lab. Pick a partner first, then come back and I'll patch you up anytime.",
                ],
            )
            return

        if self.quest_stage == "complete":
            self.start_dialogue(
                "Ranger Mira",
                [
                    "You really finished Cedar's whole survey. The meadow feels lighter tonight, doesn't it?",
                    "Come rest whenever you want. Around here, you're part of the route now.",
                ],
                on_complete=finish_rest,
            )
            return

        if self.quest_stage == "free_roam" and not self.capture_charm and self.scene_key == "meadow":
            self.start_dialogue(
                "Ranger Mira",
                [
                    "If you're still chasing the last part of Cedar's report, take another careful look inside my house.",
                    "I tucked away a little explorer's charm in there years ago. It might still help more than you'd think.",
                ],
                on_complete=finish_rest,
            )
            return

        if self.scene_key == "mira_house":
            self.start_dialogue(
                "Ranger Mira",
                [
                    "You found my little recovery corner. The kettle's warm, the blanket is clean, and your team can rest here anytime.",
                    "There we go. Everyone is patched up and ready for the grass again.",
                ],
                on_complete=finish_rest,
            )
            return

        self.start_dialogue(
            "Ranger Mira",
            [
                "Deep breath. Sit for a moment and let me freshen up your team.",
                "All set. If a battle ever goes badly, my porch is the safest place on the map.",
            ],
            on_complete=finish_rest,
        )

    def receive_starter(self, species_key: str = "Leafawn") -> None:
        if self.party:
            return

        self.party.append(self.make_creature(species_key, 1))
        self.seen_species.add(species_key)
        self.inventory["capture_orb"] += 3
        self.inventory["berry"] += 1
        self.quest_stage = "survey_grass"
        self.audio.play("quest")
        self.push_toast(f"{species_key} joined your team. You received 3 Capture Orbs.", GREEN)
        self.save_game()

    def try_choose_starter(self, species_key: str) -> None:
        if self.party:
            self.start_dialogue(
                species_key,
                [f"{species_key} already has a partner out in the meadow with you."],
            )
            return

        if self.quest_stage == "meet_professor":
            self.start_dialogue(
                "Starter Table",
                ["Professor Cedar should explain the survey before you choose a partner."],
            )
            return

        if self.quest_stage != "choose_starter":
            self.start_dialogue(
                species_key,
                [f"{species_key}'s orb slot is empty now, but the memory of your first choice still lingers here."],
            )
            return

        flavor = {
            "Leafawn": "Calm and bright-eyed, Leafawn looks ready to guide you through the meadow.",
            "Flarekit": "Flarekit bounces in place, its flame tufts flickering with eager energy.",
            "Tidefin": "Tidefin watches you with a cool, steady smile and a splash-ready tail.",
        }[species_key]
        self.start_dialogue(
            species_key,
            [
                flavor,
                f"Professor Cedar places {species_key}'s orb into your hands and sends you out to start the mission.",
            ],
            on_complete=lambda species_key=species_key: self.receive_starter(species_key),
        )

    def complete_professor_report(self) -> None:
        self.quest_stage = "free_roam"
        self.sprint_unlocked = True
        self.inventory["capture_orb"] += 2
        self.inventory["berry"] += 2
        self.heal_party()
        self.audio.play("quest")
        self.push_toast("Sprint unlocked. Hold Shift to dash across the route.", ACCENT)
        self.save_game()

    def claim_house_treasure(self) -> None:
        if self.house_treasure_claimed:
            return
        self.house_treasure_claimed = True
        self.capture_charm = True
        self.inventory["capture_orb"] += 2
        self.inventory["berry"] += 2
        if self.quest_stage == "free_roam" and self.ending_requirements_met():
            self.quest_stage = "ending_ready"
        self.audio.play("quest")
        self.push_toast("Explorer Charm found. Capture odds improved and supplies restocked.", ACCENT)
        if self.quest_stage == "ending_ready":
            self.push_toast("Survey complete: return to Professor Cedar for the final report.", BLUE)
        self.save_game()

    def inspect_prop(self, key: str) -> None:
        if key == "sign":
            pages = [
                "Verdant Meadow. One peaceful route, one tiny field lab, and a lot of hidden energy in the grass.",
            ]
            if self.quest_stage == "complete":
                pages.append("Someone added a neat line beneath it: \"Survey complete. Welcome back anytime.\"")
            self.start_dialogue("Wooden Sign", pages)
        elif key == "pond":
            pages = [
                "The pond reflects the sky with almost no ripple. Something small keeps peeking between the lily pads.",
            ]
            if self.quest_stage in {"free_roam", "complete"}:
                pages.append("It feels like the whole meadow is calmer now that the survey is complete.")
            self.start_dialogue("Quiet Pond", pages)
        elif key == "starter_leafawn":
            self.try_choose_starter("Leafawn")
        elif key == "starter_flarekit":
            self.try_choose_starter("Flarekit")
        elif key == "starter_tidefin":
            self.try_choose_starter("Tidefin")
        elif key == "lab_terminal":
            if self.quest_stage == "complete":
                self.start_dialogue(
                    "Final Report",
                    [
                        "Professor Cedar's finished survey is archived here beside the field charts: Leafawn, Flarekit, Tidefin, Mothleaf, Bubbun, Sparrook, and Mira's recovered charm are all entered.",
                        "A final note blinks at the bottom: \"Verdant Meadow stable. Continue observation visits whenever possible.\"",
                    ],
                )
            else:
                self.start_dialogue(
                    "Lab Notes",
                    [
                        "Charts of meadow growth, creature sightings, and water purity glow across the screen. Cedar really does study this whole route from one room.",
                    ],
                )
        elif key == "treasure_chest":
            if self.house_treasure_claimed:
                self.start_dialogue(
                    "Open Chest",
                    ["Only a folded note remains: \"Explorers deserve a little luck.\""],
                )
            else:
                self.start_dialogue(
                    "Treasure Chest",
                    [
                        "Inside the chest is an Explorer Charm and a tidy bundle of field supplies.",
                        "From now on your Capture Orbs will work a little better, and Mira left a few extra goodies for you too.",
                    ],
                    on_complete=self.claim_house_treasure,
                )
        elif key == "guest_bed":
            if self.party:
                def finish_rest() -> None:
                    self.heal_party()
                    self.audio.play("heal")
                    self.push_toast("You rested at Mira's house. Your team is refreshed.", BLUE)
                    self.save_game()

                self.start_dialogue(
                    "Guest Bed",
                    [
                        "The guest bed is tucked neatly beside the window, with a folded trail blanket waiting at the foot.",
                        "You take a short rest and let the quiet house do its work.",
                    ],
                    on_complete=finish_rest,
                )
            else:
                self.start_dialogue(
                    "Guest Bed",
                    [
                        "The bed is tucked so neatly it almost makes you want to stop exploring and take a nap.",
                    ],
                )

    def handle_world_interaction(self) -> None:
        target = self.find_interactable()
        if target is None:
            self.audio.play("error")
            return

        self.audio.play("interact")
        kind, key = target
        if kind == "npc":
            if key == "professor":
                self.professor_dialogue()
            elif key == "healer":
                self.healer_dialogue()
        elif kind == "prop":
            self.inspect_prop(key)

    def find_interactable(self) -> tuple[str, str] | None:
        point = self.player.interaction_point()
        scene = self.current_scene()

        for npc in scene.npcs.values():
            npc_zone = npc.hitbox().inflate(28, 26)
            if npc_zone.collidepoint(point):
                return ("npc", npc.key)

        for key, rect in scene.props.items():
            if rect.inflate(16, 16).collidepoint(point):
                return ("prop", key)

        return None

    def update_scene_doorways(self, dt: float) -> None:
        if self.scene_transition_cooldown > 0:
            self.scene_transition_cooldown = max(0.0, self.scene_transition_cooldown - dt)
            return

        player_box = self.player.hitbox()
        for doorway in self.current_scene().doorways:
            if player_box.colliderect(doorway.rect):
                self.start_door_transition(doorway)
                return

    def update_grass_activity(self, dt: float, distance: float) -> bool:
        player_box = self.player.hitbox()
        in_grass = False
        moving = distance > 0.5

        if self.grass_sfx_cooldown > 0:
            self.grass_sfx_cooldown = max(0.0, self.grass_sfx_cooldown - dt)

        for patch in self.current_scene().grass_patches:
            player_inside = patch.rect.colliderect(player_box)
            if player_inside:
                in_grass = True
                patch.activity = clamp(
                    patch.activity + dt * (5.0 if moving else 1.2),
                    0.16,
                    1.0,
                )
            else:
                patch.activity = clamp(patch.activity - dt * 2.2, 0.12, 1.0)

        if in_grass and moving and self.grass_sfx_cooldown == 0:
            self.audio.play("grass_step")
            self.grass_sfx_cooldown = 0.18

        return in_grass

    def update_pickups(self) -> None:
        player_box = self.player.hitbox()
        for pickup in self.current_scene().pickups:
            if pickup.collected or not player_box.colliderect(pickup.rect()):
                continue
            pickup.collected = True
            self.inventory[pickup.item_name] += pickup.amount
            self.audio.play("pickup")
            self.push_toast(f"Found {pickup.amount} {pickup.label}.", GREEN)
            self.save_game()

    def player_is_in_grass(self) -> bool:
        player_box = self.player.hitbox()
        return any(patch.rect.colliderect(player_box) for patch in self.current_scene().grass_patches)

    def current_grass_patch_key(self) -> str | None:
        player_box = self.player.hitbox()
        for patch in self.current_scene().grass_patches:
            if patch.rect.colliderect(player_box):
                return patch.key
        return None

    def choose_encounter_species(self) -> str:
        if self.quest_stage in {"survey_grass", "report_back"}:
            return "Mothleaf"
        patch_key = self.current_grass_patch_key()
        roll = self.rng.random()
        if patch_key in {"east_grove", "trail_east"}:
            return "Sparrook" if roll < 0.62 else "Bubbun"
        if patch_key in {"south_steps", "yard_edge"}:
            return "Bubbun" if roll < 0.62 else "Mothleaf"
        if patch_key in {"west_clearing", "lab_side"}:
            return "Mothleaf" if roll < 0.62 else "Sparrook"
        roll = self.rng.random()
        if roll < 0.34:
            return "Mothleaf"
        if roll < 0.67:
            return "Bubbun"
        return "Sparrook"

    def choose_encounter_level(self, species_key: str) -> int:
        if species_key == "Sparrook":
            return self.rng.randint(3, 6)
        if species_key == "Bubbun":
            return self.rng.randint(3, 6)
        return self.rng.randint(2, 5)

    def trigger_encounter(self, species_key: str | None = None, level: int | None = None) -> None:
        if not self.party:
            if not self.no_starter_hint_shown:
                self.audio.play("error")
                self.push_toast("The grass feels risky. Choose a partner in Cedar Lab first.", ACCENT)
                self.no_starter_hint_shown = True
            return

        chosen_species = species_key or self.choose_encounter_species()
        chosen_level = level or self.choose_encounter_level(chosen_species)
        self.pending_enemy = self.make_creature(chosen_species, chosen_level)
        self.pending_scene_entry = None
        self.transition_kind = "encounter"
        self.transition_total = 0.55
        self.transition_timer = self.transition_total
        self.transition_switched_scene = False
        self.mode = "transition"
        self.audio.play("encounter")
        self.encounter_progress = 0.0
        self.encounter_warning_shown = False
        self.next_encounter_at = self.roll_next_encounter_distance()

    def start_battle_for_test(self, species_key: str, level: int = 3) -> None:
        self.pending_enemy = self.make_creature(species_key, level)
        self.begin_battle()

    def begin_battle(self) -> None:
        if self.pending_enemy is None:
            return

        enemy = self.pending_enemy
        self.pending_enemy = None
        self.battle = BattleState(enemy=enemy)
        self.mode = "battle"

        intro_messages = [f"A wild {enemy.name} appeared!"]
        if enemy.species.key not in self.seen_species:
            intro_messages.append(f"New field entry: {enemy.name}.")
        self.seen_species.add(enemy.species.key)
        lead = self.lead_creature()
        if lead is not None:
            intro_messages.append(f"Go, {lead.name}!")
        self.queue_battle_messages(intro_messages, "command")

    def queue_battle_messages(self, messages: list[str], next_phase: str | None) -> None:
        if self.battle is None:
            return
        self.battle.messages = deque(messages)
        self.battle.phase = "messages"
        self.battle.next_phase = next_phase

    def advance_battle_messages(self) -> None:
        if self.battle is None or not self.battle.messages:
            return
        self.battle.messages.popleft()
        if not self.battle.messages:
            self.resolve_battle_transition()

    def resolve_battle_transition(self) -> None:
        if self.battle is None:
            return

        next_phase = self.battle.next_phase
        self.battle.next_phase = None

        if next_phase == "command":
            self.battle.phase = "command"
        elif next_phase == "move_select":
            self.battle.phase = "move_select"
        elif next_phase == "enemy_turn":
            self.perform_enemy_turn()
        elif next_phase == "reward_win":
            self.process_battle_reward("win")
        elif next_phase == "reward_catch":
            self.process_battle_reward("catch")
        elif next_phase == "exit_world":
            self.end_battle()
        elif next_phase == "blackout":
            self.handle_blackout()
        else:
            self.battle.phase = "command"

    def battle_command_labels(self) -> list[str]:
        return ["Fight", "Switch", "Orb", "Berry", "Run"]

    def can_switch_to_party_index(self, party_index: int) -> bool:
        return (
            0 <= party_index < len(self.party)
            and party_index != self.lead_index
            and not self.party[party_index].is_fainted
        )

    def open_battle_party_select(self) -> None:
        if self.battle is None:
            return

        candidates = [
            index for index, creature in enumerate(self.party)
            if index != self.lead_index and not creature.is_fainted
        ]
        if not candidates:
            self.audio.play("error")
            self.queue_battle_messages(["No other Pokemon is ready to switch in."], "command")
            return

        self.battle.party_index = candidates[0]
        self.battle.phase = "party_select"

    def switch_battle_creature(self, party_index: int) -> None:
        if self.battle is None or not self.can_switch_to_party_index(party_index):
            self.audio.play("error")
            return

        outgoing = self.lead_creature()
        incoming = self.party[party_index]
        if outgoing is not None:
            outgoing.guarding = False
        incoming.guarding = False
        self.lead_index = party_index
        self.battle.move_index = 0
        self.battle.command_index = 0
        self.queue_battle_messages(
            [
                f"Come back, {outgoing.name}!",
                f"Go, {incoming.name}!",
            ],
            "enemy_turn",
        )

    def perform_battle_command(self, command_index: int) -> None:
        if self.battle is None:
            return

        commands = self.battle_command_labels()
        command = commands[command_index]

        if command == "Fight":
            self.battle.phase = "move_select"
            return
        if command == "Switch":
            self.open_battle_party_select()
            return
        if command == "Orb":
            self.use_capture_orb()
            return
        if command == "Berry":
            self.use_battle_berry()
            return
        if command == "Run":
            self.try_to_run()

    def use_capture_orb(self) -> None:
        if self.battle is None:
            return
        if self.inventory["capture_orb"] <= 0:
            self.audio.play("error")
            self.queue_battle_messages(["You're out of Capture Orbs."], "command")
            return

        self.inventory["capture_orb"] -= 1
        self.audio.play("orb")
        enemy = self.battle.enemy
        catch_rate = self.capture_rate_for(enemy)

        messages = [f"You tossed a Capture Orb at {enemy.name}!"]
        if self.rng.random() < catch_rate:
            self.audio.play("capture")
            self.trigger_item_effect("capture_orb", "player", "enemy", "Caught!", GREEN)
            messages.append(f"Click. {enemy.name} was caught!")
            self.queue_battle_messages(messages, "reward_catch")
        else:
            self.trigger_item_effect("capture_orb", "player", "enemy", "Breakout", ACCENT)
            messages.append(f"{enemy.name} burst right back out!")
            self.queue_battle_messages(messages, "enemy_turn")

    def use_battle_berry(self) -> None:
        lead = self.lead_creature()
        if self.battle is None or lead is None:
            return
        if self.inventory["berry"] <= 0:
            self.audio.play("error")
            self.queue_battle_messages(["You don't have any berries left."], "command")
            return
        if lead.hp >= lead.max_hp:
            self.audio.play("error")
            self.queue_battle_messages([f"{lead.name} is already full of energy."], "command")
            return

        self.inventory["berry"] -= 1
        healed = lead.heal(12)
        self.audio.play("heal")
        self.trigger_item_effect("berry", "player", "player", f"+{healed}", GREEN)
        self.queue_battle_messages(
            [f"{lead.name} munched a berry and recovered {healed} HP."],
            "enemy_turn",
        )

    def try_to_run(self) -> None:
        if self.battle is None:
            return
        if self.quest_stage == "survey_grass":
            self.audio.play("error")
            self.queue_battle_messages(
                ["Professor Cedar really needs a reading from one battle. You should stay in."],
                "command",
            )
            return

        if self.rng.random() < 0.88:
            self.audio.play("run")
            self.queue_battle_messages(["You slipped away safely."], "exit_world")
        else:
            self.queue_battle_messages(["You tried to run, but the wild creature cut you off!"], "enemy_turn")

    def trigger_battle_effect(
        self,
        move: Move,
        source_side: str,
        target_side: str,
        *,
        hit: bool = False,
        damage: int = 0,
        guarded: bool = False,
        missed: bool = False,
    ) -> None:
        if self.battle is None:
            return

        is_guard = move.kind == "guard"
        popup_text: str | None = None
        popup_color = WHITE
        if is_guard:
            popup_text = "Guard"
            popup_color = ACCENT
            target_side = source_side
        elif missed:
            popup_text = "Miss"
            popup_color = PANEL_BORDER
        elif damage > 0:
            popup_text = f"-{damage}"
            popup_color = ACCENT if guarded else RED

        effect = BattleEffect(
            move_name=move.effect_key or move.name,
            source_side=source_side,
            target_side=target_side,
            duration=0.96 if is_guard else 0.86,
            hit_on_impact=hit,
            impact_at=0.34 if is_guard else 0.52,
            missed=missed,
            guard=is_guard,
            popup_text=popup_text,
            popup_color=popup_color,
        )
        self.battle.effects.append(effect)

        if not is_guard:
            setattr(self.battle, f"{source_side}_lunge_timer", LUNGE_DURATION)

    def trigger_item_effect(
        self,
        item_name: str,
        source_side: str,
        target_side: str,
        popup_text: str,
        popup_color: tuple[int, int, int],
    ) -> None:
        if self.battle is None:
            return
        self.battle.effects.append(
            BattleEffect(
                move_name=item_name,
                source_side=source_side,
                target_side=target_side,
                duration=0.92,
                impact_at=0.58,
                popup_text=popup_text,
                popup_color=popup_color,
            )
        )

    def start_hit_reaction(self, side: str) -> None:
        if self.battle is None:
            return
        setattr(self.battle, f"{side}_hit_timer", HIT_REACTION_DURATION)
        self.battle.screen_shake_timer = 0.22
        self.battle.screen_shake_strength = 7.0 if side == "player" else 5.0

    def add_damage_popup(self, side: str, text: str, color: tuple[int, int, int]) -> None:
        if self.battle is None:
            return
        self.battle.damage_popups.append(DamagePopup(text=text, side=side, color=color))

    def update_battle(self, dt: float) -> None:
        if self.battle is None:
            return

        if self.battle.phase == "exp_gain":
            self.update_exp_animation(dt)

        self.battle.player_hit_timer = max(0.0, self.battle.player_hit_timer - dt)
        self.battle.enemy_hit_timer = max(0.0, self.battle.enemy_hit_timer - dt)
        self.battle.player_lunge_timer = max(0.0, self.battle.player_lunge_timer - dt)
        self.battle.enemy_lunge_timer = max(0.0, self.battle.enemy_lunge_timer - dt)
        self.battle.screen_shake_timer = max(0.0, self.battle.screen_shake_timer - dt)

        for effect in self.battle.effects:
            effect.timer += dt
            if not effect.impact_done and effect.progress >= effect.impact_at:
                if effect.hit_on_impact:
                    self.start_hit_reaction(effect.target_side)
                if effect.popup_text:
                    self.add_damage_popup(effect.target_side, effect.popup_text, effect.popup_color)
                effect.impact_done = True

        self.battle.effects = [
            effect for effect in self.battle.effects if effect.timer < effect.duration
        ]

        for popup in self.battle.damage_popups:
            popup.timer += dt
        self.battle.damage_popups = [
            popup for popup in self.battle.damage_popups if popup.timer < popup.duration
        ]

    def perform_player_move(self, move_index: int) -> None:
        if self.battle is None:
            return
        lead = self.lead_creature()
        if lead is None:
            return

        move = lead.species.moves[move_index]
        enemy = self.battle.enemy
        messages = [f"{lead.name} used {move.name}!"]
        self.audio.play("attack")

        if move.kind == "guard":
            lead.guarding = True
            self.trigger_battle_effect(move, "player", "player")
            messages.append(move.text)
            self.queue_battle_messages(messages, "enemy_turn")
            return

        if self.rng.random() > move.accuracy:
            self.trigger_battle_effect(move, "player", "enemy", missed=True)
            messages.append("It missed!")
            self.queue_battle_messages(messages, "enemy_turn")
            return

        damage = max(2, move.power + lead.level + self.rng.randint(-2, 2))
        multiplier = self.type_multiplier(lead.species.element, enemy.species.element)
        damage = max(2, round(damage * multiplier))
        dealt, guarded = enemy.take_damage(damage)
        self.trigger_battle_effect(
            move,
            "player",
            "enemy",
            hit=dealt > 0,
            damage=dealt,
            guarded=guarded,
        )
        if dealt > 0:
            self.audio.play("hit")
        if guarded:
            messages.append(f"{enemy.name} braced and softened the hit.")
        messages.append(move.text.format(target=enemy.name, damage=dealt))
        if multiplier > 1.0:
            messages.append("It's super effective!")
        elif multiplier < 1.0:
            messages.append("It's not very effective.")

        if enemy.is_fainted:
            self.audio.play("faint")
            messages.append(f"The wild {enemy.name} fainted!")
            self.queue_battle_messages(messages, "reward_win")
        else:
            self.queue_battle_messages(messages, "enemy_turn")

    def perform_enemy_turn(self) -> None:
        if self.battle is None:
            return
        lead = self.lead_creature()
        enemy = self.battle.enemy
        if lead is None:
            self.queue_battle_messages(["You have no creature ready to fight."], "blackout")
            return

        available_moves = [move for move in enemy.species.moves if move.kind == "attack"]
        if self.rng.random() < 0.25:
            move = enemy.species.moves[2]
        else:
            move = self.rng.choice(available_moves)

        messages = [f"Wild {enemy.name} used {move.name}!"]
        self.audio.play("attack")

        if move.kind == "guard":
            enemy.guarding = True
            self.trigger_battle_effect(move, "enemy", "enemy")
            messages.append(move.text)
            self.queue_battle_messages(messages, "command")
            return

        if self.rng.random() > move.accuracy:
            self.trigger_battle_effect(move, "enemy", "player", missed=True)
            messages.append("It missed!")
            self.queue_battle_messages(messages, "command")
            return

        damage = max(2, move.power + enemy.level + self.rng.randint(-2, 2))
        multiplier = self.type_multiplier(enemy.species.element, lead.species.element)
        damage = max(2, round(damage * multiplier))
        dealt, guarded = lead.take_damage(damage)
        self.trigger_battle_effect(
            move,
            "enemy",
            "player",
            hit=dealt > 0,
            damage=dealt,
            guarded=guarded,
        )
        if dealt > 0:
            self.audio.play("hit")
        if guarded:
            messages.append(f"{lead.name} guarded and absorbed part of the blow.")
        messages.append(move.text.format(target=lead.name, damage=dealt))
        if multiplier > 1.0:
            messages.append("It's super effective!")
        elif multiplier < 1.0:
            messages.append("It's not very effective.")

        if lead.is_fainted:
            self.audio.play("faint")
            messages.append(f"{lead.name} fainted!")
            backup_index = self.first_healthy_party_index(exclude=self.lead_index)
            if backup_index is not None:
                self.lead_index = backup_index
                messages.append(f"Go, {self.lead_creature().name}!")
                self.queue_battle_messages(messages, "command")
            else:
                self.queue_battle_messages(messages, "blackout")
        else:
            self.queue_battle_messages(messages, "command")

    def process_battle_reward(self, result: str) -> None:
        if self.battle is None:
            return

        enemy = self.battle.enemy
        messages: list[str] = []
        lead = self.lead_creature()

        if result == "catch":
            self.caught_species.add(enemy.species.key)
            self.audio.play("victory_jingle")
            if all(creature.species.key != enemy.species.key for creature in self.party):
                self.party.append(self.make_creature(enemy.species.key, enemy.level))
                messages.append(f"{enemy.name} joined your team!")
            else:
                messages.append(f"{enemy.name} was logged in your survey journal.")
        elif result == "win":
            self.audio.play("victory_jingle")

        if lead is not None:
            reward = 10 + enemy.level * 3
            exp_segments = self.build_exp_segments(lead, reward)
            level_before = lead.level
            exp_messages = lead.gain_exp(reward)
            if lead.level > level_before:
                messages.extend(exp_messages[1:])
        else:
            reward = 0
            exp_segments = []

        if self.quest_stage == "survey_grass" and enemy.species.key == "Mothleaf":
            self.quest_stage = "report_back"
            self.audio.play("quest")
            messages.append("Survey updated: return to Professor Cedar in the lab.")

        if self.quest_stage == "free_roam" and self.ending_requirements_met():
            self.quest_stage = "ending_ready"
            self.audio.play("quest")
            messages.append("Survey complete: return to Professor Cedar for the final report.")

        if lead is not None and reward > 0 and exp_segments:
            self.start_exp_animation(
                lead,
                reward,
                exp_segments,
                messages or ["The meadow grew quiet again."],
                "exit_world",
            )
            return

        self.queue_battle_messages(messages or ["The meadow grew quiet again."], "exit_world")

    def handle_blackout(self) -> None:
        self.heal_party()
        self.audio.play("heal")
        self.enter_scene("meadow", (1048, 760), direction="up")
        self.push_toast("Mira rushed you back to the porch and healed your team.", RED)
        self.end_battle()

    def end_battle(self) -> None:
        self.battle = None
        self.mode = "world"
        self.encounter_cooldown = 2.2
        self.encounter_progress = 0.0
        self.next_encounter_at = self.roll_next_encounter_distance()
        self.save_game()

    def find_prompt(self) -> str | None:
        target = self.find_interactable()
        if target is None:
            return None
        kind, key = target
        if kind == "npc":
            npc = self.current_scene().npcs[key]
            return f"E: {npc.prompt} {npc.name}"
        starter_label = "Choose" if self.quest_stage == "choose_starter" and not self.party else "Inspect"
        prop_prompts = {
            "sign": "E: Read Sign",
            "pond": "E: Look at Pond",
            "starter_leafawn": f"E: {starter_label} Leafawn",
            "starter_flarekit": f"E: {starter_label} Flarekit",
            "starter_tidefin": f"E: {starter_label} Tidefin",
            "lab_terminal": "E: Read Final Report" if self.quest_stage == "complete" else "E: Read Lab Notes",
            "treasure_chest": "E: Open Chest" if not self.house_treasure_claimed else "E: Inspect Chest",
            "guest_bed": "E: Inspect Bed",
        }
        return prop_prompts.get(key, f"E: Inspect {key.title()}")

    def compute_camera(self) -> pygame.Vector2:
        scene_surface = self.current_scene().surface
        max_x = max(0, scene_surface.get_width() - SCREEN_SIZE[0])
        max_y = max(0, scene_surface.get_height() - SCREEN_SIZE[1])
        x = clamp(self.player.position.x - SCREEN_SIZE[0] / 2, 0, max_x)
        y = clamp(self.player.position.y - SCREEN_SIZE[1] / 2, 0, max_y)
        return pygame.Vector2(x, y)

    def update_world(self, dt: float) -> None:
        pressed = VirtualPressed(self.ai_pressed_keys) if self.autoplayer is not None else pygame.key.get_pressed()
        scene = self.current_scene()
        distance = self.player.update(
            dt,
            pressed,
            scene.walk_bounds,
            self.dynamic_colliders(),
            self.current_speed(pressed),
        )
        self.update_scene_doorways(dt)
        self.update_pickups()

        if self.encounter_cooldown > 0:
            self.encounter_cooldown = max(0.0, self.encounter_cooldown - dt)

        in_grass = self.update_grass_activity(dt, distance)
        if in_grass and distance > 0 and self.party and self.encounter_cooldown == 0:
            self.encounter_progress += distance
            if (
                not self.encounter_warning_shown
                and self.encounter_progress >= self.next_encounter_at * 0.66
            ):
                self.encounter_warning_shown = True
                self.push_toast("Something rustles deeper in the grass...", ACCENT, duration=1.5)
            if self.encounter_progress >= self.next_encounter_at:
                self.trigger_encounter()
        elif not in_grass:
            self.encounter_progress = 0.0
            self.encounter_warning_shown = False

    def update_transition(self, dt: float) -> None:
        self.transition_timer = max(0.0, self.transition_timer - dt)
        progress = 1.0 - (self.transition_timer / max(0.001, self.transition_total))

        if self.transition_kind == "door":
            if (
                self.pending_scene_entry is not None
                and not self.transition_switched_scene
                and progress >= 0.5
            ):
                scene_key, position, direction = self.pending_scene_entry
                self.enter_scene(scene_key, position, direction=direction)
                self.transition_switched_scene = True
            if self.transition_timer == 0:
                self.pending_scene_entry = None
                self.mode = "world"
            return

        if self.transition_timer == 0:
            self.begin_battle()

    def update(self, dt: float) -> None:
        if self.paused:
            self.sync_music()
            self.ai_pressed_keys = set()
            return

        self.elapsed += dt
        self.update_toasts(dt)
        self.sync_music()
        if self.autoplayer is not None:
            self.ai_pressed_keys = self.autoplayer.update(dt)
        else:
            self.ai_pressed_keys = set()

        if self.mode == "world":
            self.update_world(dt)
        elif self.mode == "transition":
            self.update_transition(dt)
        elif self.mode == "battle":
            self.update_battle(dt)

        self.camera = self.compute_camera()

    def move_grid_selection(self, current: int, key: int, total: int, *, columns: int = 1) -> int:
        if total <= 0:
            return current

        if columns > 1:
            col = current % columns
            row = current // columns
            row_count = math.ceil(total / columns)

            if key in {pygame.K_LEFT, pygame.K_a}:
                col = max(0, col - 1)
            elif key in {pygame.K_RIGHT, pygame.K_d}:
                col = min(columns - 1, col + 1)
            elif key in {pygame.K_UP, pygame.K_w}:
                row = max(0, row - 1)
            elif key in {pygame.K_DOWN, pygame.K_s}:
                row = min(row_count - 1, row + 1)

            candidate = row * columns + col
            while candidate >= total and col > 0:
                col -= 1
                candidate = row * columns + col
            return min(candidate, total - 1)

        if total == 4:
            col = current % 2
            row = current // 2
            if key in {pygame.K_LEFT, pygame.K_a}:
                col = max(0, col - 1)
            elif key in {pygame.K_RIGHT, pygame.K_d}:
                col = min(1, col + 1)
            elif key in {pygame.K_UP, pygame.K_w}:
                row = max(0, row - 1)
            elif key in {pygame.K_DOWN, pygame.K_s}:
                row = min(1, row + 1)
            return row * 2 + col

        if key in {pygame.K_UP, pygame.K_w}:
            return (current - 1) % total
        if key in {pygame.K_DOWN, pygame.K_s}:
            return (current + 1) % total
        return current

    def handle_battle_input(self, key: int) -> None:
        if self.battle is None:
            return

        if self.battle.phase == "messages":
            if key in CONFIRM_KEYS:
                self.advance_battle_messages()
            return

        if self.battle.phase == "exp_gain":
            if key in CONFIRM_KEYS:
                self.finish_exp_animation()
            return

        if self.battle.phase == "command":
            old_index = self.battle.command_index
            self.battle.command_index = self.move_grid_selection(
                self.battle.command_index,
                key,
                len(self.battle_command_labels()),
                columns=2,
            )
            if self.battle.command_index != old_index:
                self.audio.play("menu_move")
            if key in CONFIRM_KEYS:
                self.audio.play("confirm")
                self.perform_battle_command(self.battle.command_index)
            return

        if self.battle.phase == "party_select":
            old_index = self.battle.party_index
            self.battle.party_index = self.move_grid_selection(self.battle.party_index, key, len(self.party))
            if self.battle.party_index != old_index:
                self.audio.play("menu_move")
            if key in CONFIRM_KEYS:
                if self.can_switch_to_party_index(self.battle.party_index):
                    self.audio.play("confirm")
                    self.switch_battle_creature(self.battle.party_index)
                else:
                    self.audio.play("error")
            elif key in BACK_KEYS or key == pygame.K_ESCAPE:
                self.audio.play("cancel")
                self.battle.phase = "command"
            return

        if self.battle.phase == "move_select":
            move_total = len(self.lead_creature().species.moves) if self.lead_creature() else 0
            old_index = self.battle.move_index
            self.battle.move_index = self.move_grid_selection(self.battle.move_index, key, move_total)
            if self.battle.move_index != old_index:
                self.audio.play("menu_move")
            if key in CONFIRM_KEYS:
                self.audio.play("confirm")
                self.perform_player_move(self.battle.move_index)
            elif key in BACK_KEYS or key == pygame.K_ESCAPE:
                self.audio.play("cancel")
                self.battle.phase = "command"

    def mode_button_rects(self) -> list[tuple[str, pygame.Rect]]:
        if self.mode == "world":
            x = SCREEN_SIZE[0] - 154
            y = 260
        elif self.mode == "battle":
            x = 12
            y = 170
        else:
            x = SCREEN_SIZE[0] - 154
            y = 172
        width = 142
        height = 38
        gap = 8
        return [
            (mode_key, pygame.Rect(x, y + index * (height + gap), width, height))
            for index, mode_key in enumerate(PLAY_MODE_ORDER)
        ]

    def handle_mouse_down(self, pos: tuple[int, int]) -> bool:
        for mode_key, rect in self.mode_button_rects():
            if rect.collidepoint(pos):
                self.audio.play("confirm")
                self.select_play_mode(mode_key)
                return True
        return False

    def handle_journal_input(self, key: int) -> None:
        if key in {pygame.K_TAB, pygame.K_ESCAPE}:
            self.audio.play("cancel")
            self.mode = "world"
            return

        if not self.party:
            return

        if key in {pygame.K_UP, pygame.K_w}:
            self.audio.play("menu_move")
            self.journal_index = (self.journal_index - 1) % len(self.party)
        elif key in {pygame.K_DOWN, pygame.K_s}:
            self.audio.play("menu_move")
            self.journal_index = (self.journal_index + 1) % len(self.party)
        elif key in CONFIRM_KEYS:
            if not self.party[self.journal_index].is_fainted:
                self.audio.play("confirm")
                self.lead_index = self.journal_index
                self.push_toast(f"{self.lead_creature().name} is now leading the team.", ACCENT)
                self.mode = "world"
            else:
                self.audio.play("error")

    def handle_keydown(self, key: int) -> None:
        if self.mode == "title":
            if key in CONFIRM_KEYS:
                self.audio.play("confirm")
                if self.has_save_file() and self.load_game():
                    return
                self.start_new_adventure()
            elif key == pygame.K_n:
                self.audio.play("confirm")
                self.start_new_adventure()
            elif key == pygame.K_ESCAPE:
                self.audio.play("cancel")
                self.running = False
            return

        if key == pygame.K_p:
            self.paused = not self.paused
            self.audio.play("confirm" if self.paused else "cancel")
            return

        if self.paused:
            return

        if key == pygame.K_F5 and self.mode in {"world", "dialogue", "journal"}:
            self.save_game(quiet=False)
            return

        if key == pygame.K_m and self.mode in {"world", "dialogue", "journal", "help", "ending"}:
            muted = self.audio.toggle_music_mute()
            self.push_toast("Music muted." if muted else "Music unmuted.", PANEL_BORDER)
            return

        if self.mode == "dialogue":
            if key in CONFIRM_KEYS:
                self.advance_dialogue()
            elif key == pygame.K_ESCAPE:
                self.audio.play("cancel")
                self.mode = "world"
            return

        if self.mode == "journal":
            self.handle_journal_input(key)
            return

        if self.mode == "help":
            if key in {pygame.K_h, pygame.K_ESCAPE, pygame.K_TAB} or key in CONFIRM_KEYS:
                self.audio.play("cancel")
                self.mode = "world"
            return

        if self.mode == "ending":
            if key in CONFIRM_KEYS:
                self.audio.play("confirm")
                if self.ending_index < len(self.ending_pages) - 1:
                    self.ending_index += 1
                else:
                    self.finish_ending()
            elif key == pygame.K_ESCAPE:
                self.audio.play("cancel")
                self.finish_ending()
            return

        if self.mode == "battle":
            self.handle_battle_input(key)
            return

        if self.mode == "transition":
            return

        if key == pygame.K_ESCAPE:
            self.audio.play("cancel")
            self.save_game()
            self.running = False
        elif key == pygame.K_h:
            self.audio.play("confirm")
            self.mode = "help"
        elif key == pygame.K_TAB:
            self.audio.play("confirm")
            self.mode = "journal"
        elif key in INTERACT_KEYS:
            self.handle_world_interaction()

    def draw_tall_grass(self, surface: pygame.Surface) -> None:
        if not self.grass_frames:
            return

        for patch_index, patch in enumerate(self.current_scene().grass_patches):
            for tuft_index, tuft in enumerate(patch.tufts):
                world_x, world_y = tuft
                sway = math.sin(self.elapsed * 5.4 + patch_index * 0.8 + tuft_index * 0.65) * (1.0 + patch.activity * 2.6)
                frame_index = int((self.elapsed * 8 + patch_index + tuft_index * 0.35) % len(self.grass_frames))
                frame = self.grass_frames[frame_index]
                rect = frame.get_rect(
                    midbottom=(
                        round(world_x - self.camera.x + sway),
                        round(world_y - self.camera.y),
                    )
                )
                surface.blit(frame, rect)

    def draw_ambient_life(self, surface: pygame.Surface) -> None:
        if self.scene_key != "meadow":
            return

        for index, (world_x, world_y, phase, color) in enumerate(self.ambient_life):
            drift_x = math.sin(self.elapsed * 1.7 + phase) * 10
            drift_y = math.sin(self.elapsed * 2.4 + phase * 1.7) * 5
            wing = 2 + abs(math.sin(self.elapsed * 9 + index)) * 2
            alpha = round(100 + 70 * math.sin(self.elapsed * 2.2 + phase) ** 2)
            center = (
                round(world_x - self.camera.x + drift_x),
                round(world_y - self.camera.y + drift_y),
            )
            mote = pygame.Surface((22, 18), pygame.SRCALPHA)
            pygame.draw.ellipse(mote, (*color, alpha), (6 - wing, 7, wing + 3, 5))
            pygame.draw.ellipse(mote, (*color, alpha), (12, 7, wing + 3, 5))
            pygame.draw.circle(mote, (255, 255, 230, min(255, alpha + 50)), (11, 10), 2)
            surface.blit(mote, mote.get_rect(center=center))

    def draw_player_grass_overlay(self, surface: pygame.Surface) -> None:
        player_box = self.player.hitbox()
        if not any(patch.rect.colliderect(player_box) for patch in self.current_scene().grass_patches):
            return
        if not self.grass_overlay_frames:
            return

        base_x = round(self.player.position.x - self.camera.x)
        base_y = round(self.player.position.y - self.camera.y + 6)
        for index, offset in enumerate((-18, 0, 18)):
            frame = self.grass_overlay_frames[(int(self.elapsed * 9) + index) % len(self.grass_overlay_frames)]
            rect = frame.get_rect(midbottom=(base_x + offset, base_y))
            surface.blit(frame, rect)

    def draw_pickups(self, surface: pygame.Surface) -> None:
        for index, pickup in enumerate(self.current_scene().pickups):
            if pickup.collected:
                continue
            bob = math.sin(self.elapsed * 3.8 + index) * 2
            pos = pygame.Vector2(pickup.position.x - self.camera.x, pickup.position.y - self.camera.y + bob)
            icon = self.item_icons[pickup.item_name]
            shadow = make_shadow(18, 8, 80)
            shadow_rect = shadow.get_rect(center=(round(pos.x), round(pos.y + 9)))
            surface.blit(shadow, shadow_rect)
            icon_rect = icon.get_rect(center=(round(pos.x), round(pos.y)))
            surface.blit(icon, icon_rect)

    def draw_doorways(self, surface: pygame.Surface) -> None:
        for index, doorway in enumerate(self.current_scene().doorways):
            rect = doorway.rect.move(-round(self.camera.x), -round(self.camera.y))
            if not rect.colliderect(surface.get_rect()):
                continue

            distance = pygame.Vector2(doorway.rect.center).distance_to(self.player.position)
            near = distance < 96
            pulse = 0.5 + 0.5 * math.sin(self.elapsed * 5.6 + index)
            alpha = round((70 if near else 34) + pulse * (70 if near else 28))
            glow_rect = rect.inflate(26 if near else 16, 18 if near else 10)
            glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (*ACCENT, alpha), glow.get_rect(), border_radius=8)
            pygame.draw.rect(glow, (*WHITE, min(220, alpha + 44)), glow.get_rect(), width=2, border_radius=8)
            surface.blit(glow, glow_rect)

            if near:
                arrow_y = glow_rect.top - 10 + math.sin(self.elapsed * 7) * 2
                points = [
                    (glow_rect.centerx, round(arrow_y)),
                    (glow_rect.centerx - 8, round(arrow_y - 10)),
                    (glow_rect.centerx + 8, round(arrow_y - 10)),
                ]
                pygame.draw.polygon(surface, ACCENT, points)

    def starter_slots(self) -> list[tuple[str, pygame.Vector2]]:
        scale = scene_scale("cedar_lab")
        return [
            ("Leafawn", scale_vector((472, 618), scale)),
            ("Flarekit", scale_vector((640, 612), scale)),
            ("Tidefin", scale_vector((808, 618), scale)),
        ]

    def draw_lab_starters(self, surface: pygame.Surface) -> None:
        if self.scene_key != "cedar_lab":
            return

        show_choices = not self.party or self.quest_stage in {"meet_professor", "choose_starter"}
        for index, (species_key, position) in enumerate(self.starter_slots()):
            species = self.species[species_key]
            bob = math.sin(self.elapsed * 3.4 + index * 0.9) * 2.2
            glow = 70 + int(40 * math.sin(self.elapsed * 4 + index))
            screen_x = round(position.x - self.camera.x)
            screen_y = round(position.y - self.camera.y + bob)

            halo = pygame.Surface((74, 26), pygame.SRCALPHA)
            pygame.draw.ellipse(halo, (*species.accent, max(48, glow)), halo.get_rect())
            halo_rect = halo.get_rect(center=(screen_x, screen_y + 18))
            surface.blit(halo, halo_rect)

            shadow = make_shadow(52, 14, 96)
            shadow_rect = shadow.get_rect(center=(screen_x, screen_y + 14))
            surface.blit(shadow, shadow_rect)

            sprite = pygame.transform.scale_by(species.icon, 1.12 if show_choices else 0.98)
            sprite_rect = sprite.get_rect(midbottom=(screen_x, screen_y + 8))
            surface.blit(sprite, sprite_rect)

            if show_choices and position.distance_to(self.player.position) < 260:
                label = self.font_small.render(species.name, True, WHITE)
                label_bg = pygame.Rect(0, 0, label.get_width() + 14, 22)
                label_bg.midtop = (screen_x, screen_y + 22)
                pygame.draw.rect(surface, (20, 24, 32, 210), label_bg, border_radius=8)
                pygame.draw.rect(surface, species.accent, label_bg, width=2, border_radius=8)
                surface.blit(label, label.get_rect(center=label_bg.center))

    def draw_npc(self, surface: pygame.Surface, npc: NPC) -> None:
        shadow = make_shadow(28, 10, 92)
        shadow_rect = shadow.get_rect(
            center=(round(npc.position.x - self.camera.x), round(npc.position.y - self.camera.y - 4))
        )
        surface.blit(shadow, shadow_rect)

        rect = npc.sprite.get_rect(
            midbottom=(round(npc.position.x - self.camera.x), round(npc.position.y - self.camera.y))
        )
        surface.blit(npc.sprite, rect)

        important = (
            (npc.key == "professor" and self.quest_stage in {"meet_professor", "choose_starter", "report_back", "ending_ready"})
            or (npc.key == "healer" and any(creature.hp < creature.max_hp for creature in self.party))
        )
        if important:
            bob = math.sin(self.elapsed * 6 + npc.position.x * 0.02) * 2
            marker_rect = pygame.Rect(0, 0, 18, 18)
            marker_rect.midbottom = (rect.centerx, rect.top - 4 + bob)
            pygame.draw.ellipse(surface, npc.marker_color, marker_rect)
            pygame.draw.ellipse(surface, WHITE, marker_rect, 2)
            text = self.font_small.render("!", True, INK)
            text_rect = text.get_rect(center=marker_rect.center)
            surface.blit(text, text_rect)

    def draw_sprint_dust(self, surface: pygame.Surface) -> None:
        if not (self.player.sprinting and self.player.moving):
            return

        behind = {
            "up": pygame.Vector2(0, 22),
            "down": pygame.Vector2(0, -16),
            "left": pygame.Vector2(18, 2),
            "right": pygame.Vector2(-18, 2),
        }[self.player.direction]
        side = {
            "up": pygame.Vector2(1, 0),
            "down": pygame.Vector2(1, 0),
            "left": pygame.Vector2(0, 1),
            "right": pygame.Vector2(0, 1),
        }[self.player.direction]
        base = pygame.Vector2(self.player.position.x - self.camera.x, self.player.position.y - self.camera.y)
        for index, spread in enumerate((-1, 0, 1)):
            phase = (self.elapsed * 9 + index * 0.7) % 1.0
            center = base + behind * (0.7 + phase * 0.55) + side * spread * (8 + phase * 4)
            width = round(12 - phase * 5)
            height = round(5 - phase * 2)
            dust = pygame.Surface((22, 14), pygame.SRCALPHA)
            alpha = round(120 * (1.0 - phase))
            pygame.draw.ellipse(dust, (216, 196, 150, alpha), (3, 5, width, height))
            surface.blit(dust, dust.get_rect(center=(round(center.x), round(center.y - 2))))

    def draw_world(self) -> None:
        scene = self.current_scene()
        self.screen.fill((16, 28, 34))
        self.screen.blit(scene.surface, (-self.camera.x, -self.camera.y))
        self.draw_doorways(self.screen)
        self.draw_ambient_life(self.screen)
        self.draw_tall_grass(self.screen)
        self.draw_pickups(self.screen)
        self.draw_lab_starters(self.screen)

        characters = [("npc", npc.position.y, npc) for npc in scene.npcs.values()]
        characters.append(("player", self.player.position.y, self.player))
        for kind, _, obj in sorted(characters, key=lambda item: item[1]):
            if kind == "npc":
                self.draw_npc(self.screen, obj)
            else:
                self.draw_sprint_dust(self.screen)
                obj.draw(self.screen, self.camera)

        self.draw_player_grass_overlay(self.screen)
        if self.mode == "world":
            self.draw_objective_marker()
        self.draw_world_ui()

        if self.mode == "dialogue":
            self.draw_dialogue()
        elif self.mode == "journal":
            self.draw_journal()
        elif self.mode == "help":
            self.draw_help()
        elif self.mode == "transition":
            self.draw_transition()

        if self.mode == "world":
            self.draw_toast()

    def draw_toast(self) -> None:
        if self.toast_timer <= 0 or not self.toast_text:
            return
        panel = pygame.Rect(0, 0, min(560, SCREEN_SIZE[0] - 80), 48)
        panel.midbottom = (SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] - 18)
        draw_panel(self.screen, panel, (20, 28, 36), self.toast_color)
        text = self.font_medium.render(self.toast_text, True, WHITE)
        text_rect = text.get_rect(center=panel.center)
        self.screen.blit(text, text_rect)

    def draw_prompt(self) -> None:
        prompt = self.find_prompt()
        if prompt is None:
            return
        panel = pygame.Rect(0, 0, min(360, SCREEN_SIZE[0] - 60), 38)
        bottom = SCREEN_SIZE[1] - 76 if self.toast_timer <= 0 else SCREEN_SIZE[1] - 132
        panel.midbottom = (SCREEN_SIZE[0] // 2, bottom)
        draw_panel(self.screen, panel, (24, 32, 40), ACCENT)
        text = self.font_small.render(prompt, True, WHITE)
        text_rect = text.get_rect(center=panel.center)
        self.screen.blit(text, text_rect)

    def draw_creature_bar(
        self,
        creature: Creature,
        rect: pygame.Rect,
        accent_color: tuple[int, int, int],
        *,
        active: bool = False,
        display_level: int | None = None,
        display_exp: float | None = None,
        show_exp: bool = True,
    ) -> None:
        level = display_level if display_level is not None else creature.level
        exp_value = display_exp if display_exp is not None else creature.exp
        exp_threshold = 10 + level * 5
        fill = (34, 40, 48) if active else (26, 32, 38)
        draw_panel(self.screen, rect, fill, accent_color if active else PANEL_BORDER)
        fill_ratio = creature.hp / max(1, creature.max_hp)
        if active and 0 < fill_ratio <= 0.25:
            pulse = 0.5 + 0.5 * math.sin(self.elapsed * 8)
            warning = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                warning,
                (222, 84, 84, round(28 + pulse * 44)),
                warning.get_rect(),
                border_radius=12,
            )
            pygame.draw.rect(
                warning,
                (255, 206, 92, round(90 + pulse * 90)),
                warning.get_rect().inflate(-6, -6),
                width=2,
                border_radius=10,
            )
            self.screen.blit(warning, rect)

        name_text = self.font_medium.render(f"{creature.name}  Lv.{level}", True, WHITE)
        self.screen.blit(name_text, (rect.left + 14, rect.top + 10))
        hp_text = self.font_small.render(f"{creature.hp}/{creature.max_hp} HP", True, WHITE)
        self.screen.blit(hp_text, (rect.right - hp_text.get_width() - 14, rect.top + 12))

        type_badge = pygame.Rect(rect.left + 14, rect.top + 38, 76, 22)
        pygame.draw.rect(self.screen, (52, 60, 72), type_badge, border_radius=7)
        pygame.draw.rect(self.screen, self.type_color(creature.species.element), type_badge, width=2, border_radius=7)
        type_text = self.font_small.render(creature.species.element, True, WHITE)
        self.screen.blit(type_text, type_text.get_rect(center=type_badge.center))

        if creature.guarding:
            badge = pygame.Rect(rect.left + 96, rect.top + 38, 76, 22)
            pygame.draw.rect(self.screen, (62, 72, 88), badge, border_radius=6)
            pygame.draw.rect(self.screen, ACCENT, badge, width=2, border_radius=6)
            shield = self.font_small.render("Guard", True, ACCENT)
            self.screen.blit(shield, shield.get_rect(center=badge.center))

        hp_bottom = 34 if show_exp else 22
        meter = pygame.Rect(rect.left + 14, rect.bottom - hp_bottom, rect.width - 28, 10)
        pygame.draw.rect(self.screen, (60, 68, 76), meter, border_radius=5)
        hp_color = GREEN if fill_ratio > 0.5 else ACCENT if fill_ratio > 0.25 else RED
        fill_width = round(meter.width * fill_ratio)
        if fill_width > 0:
            pygame.draw.rect(self.screen, hp_color, (meter.left, meter.top, fill_width, meter.height), border_radius=5)

        if show_exp:
            exp_meter = pygame.Rect(rect.left + 14, rect.bottom - 18, rect.width - 28, 8)
            pygame.draw.rect(self.screen, (44, 54, 64), exp_meter, border_radius=4)
            exp_fill_width = round(exp_meter.width * self.exp_ratio(level, exp_value))
            if exp_fill_width > 0:
                pygame.draw.rect(self.screen, BLUE, (exp_meter.left, exp_meter.top, exp_fill_width, exp_meter.height), border_radius=4)
            exp_text = self.font_small.render(f"EXP {int(exp_value)}/{exp_threshold}", True, PANEL_BORDER)
            self.screen.blit(exp_text, (rect.right - exp_text.get_width() - 14, rect.top + 40))

    def draw_world_ui(self) -> None:
        objective_panel = pygame.Rect(16, 16, 384, 112)
        draw_panel(self.screen, objective_panel)
        objective_title = "Professor Cedar's Survey"
        if self.quest_stage == "ending_ready":
            objective_title = "Final Report"
        elif self.quest_stage == "complete":
            objective_title = "Survey Complete"
        title = self.font_medium.render(objective_title, True, ACCENT)
        self.screen.blit(title, (objective_panel.left + 14, objective_panel.top + 10))
        draw_multiline_text(
            self.screen,
            self.font_small,
            self.current_objective(),
            pygame.Rect(objective_panel.left + 14, objective_panel.top + 40, objective_panel.width - 28, 62),
        )

        tracker_panel = pygame.Rect(SCREEN_SIZE[0] - 278, 16, 262, 196)
        draw_panel(self.screen, tracker_panel, (24, 32, 38))
        area = self.font_small.render(self.scene_title(), True, ACCENT)
        seen = self.font_small.render(f"Seen: {len(self.seen_species)}/{len(self.species)}", True, WHITE)
        caught = self.font_small.render(f"Caught: {len(self.caught_species)}/{len(self.species)}", True, WHITE)
        orbs = self.font_small.render(f"Orbs: {self.inventory['capture_orb']}", True, WHITE)
        berries = self.font_small.render(f"Berries: {self.inventory['berry']}", True, WHITE)
        self.screen.blit(area, (tracker_panel.left + 14, tracker_panel.top + 10))
        self.screen.blit(seen, (tracker_panel.left + 14, tracker_panel.top + 36))
        self.screen.blit(caught, (tracker_panel.left + 146, tracker_panel.top + 36))
        self.screen.blit(orbs, (tracker_panel.left + 44, tracker_panel.top + 62))
        self.screen.blit(berries, (tracker_panel.left + 176, tracker_panel.top + 62))
        self.screen.blit(self.item_icons["capture_orb"], (tracker_panel.left + 16, tracker_panel.top + 58))
        self.screen.blit(self.item_icons["berry"], (tracker_panel.left + 148, tracker_panel.top + 58))

        survey = self.font_small.render(self.survey_progress_text(), True, BLUE if self.capture_charm else PANEL_BORDER)
        charm_text = "Charm: Ready" if self.capture_charm else "Charm: Hidden"
        charm = self.font_small.render(charm_text, True, PANEL_BORDER)
        sprint_text = "Sprint: Ready" if self.sprint_unlocked else "Sprint: Locked"
        sprint = self.font_small.render(sprint_text, True, PANEL_BORDER)
        music_text = "Music: Off (M)" if self.audio.music_muted else "Music: On (M)"
        music = self.font_small.render(music_text, True, PANEL_BORDER)
        self.screen.blit(survey, (tracker_panel.left + 14, tracker_panel.top + 88))
        self.screen.blit(charm, (tracker_panel.left + 14, tracker_panel.top + 106))
        self.screen.blit(sprint, (tracker_panel.left + 14, tracker_panel.top + 124))
        self.screen.blit(music, (tracker_panel.left + 14, tracker_panel.top + 142))

        remaining = self.remaining_wild_species()
        if self.quest_stage in {"free_roam", "ending_ready", "complete"} and remaining:
            missing = self.font_small.render(f"Need: {self.compact_species_list(remaining)}", True, PANEL_BORDER)
            self.screen.blit(missing, (tracker_panel.left + 14, tracker_panel.top + 164))

        lead = self.lead_creature()
        if lead is not None:
            bar_rect = pygame.Rect(16, SCREEN_SIZE[1] - 110, 320, 90)
            self.draw_creature_bar(self.party[self.lead_index], bar_rect, lead.species.accent, active=True)

        if self.mode == "world":
            self.draw_prompt()

    def draw_mode_sidebar(self) -> None:
        rects = self.mode_button_rects()
        panel = pygame.Rect(rects[0][1].left - 8, rects[0][1].top - 42, rects[0][1].width + 16, 236)
        backdrop = pygame.Surface(panel.size, pygame.SRCALPHA)
        backdrop.fill((14, 18, 26, 194))
        self.screen.blit(backdrop, panel)
        pygame.draw.rect(self.screen, (62, 72, 84), panel, width=2, border_radius=8)

        title = self.font_small.render("Modes", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.top + 17)))
        hint = self.font_small.render("click = fresh run", True, PANEL_BORDER)
        self.screen.blit(hint, hint.get_rect(center=(panel.centerx, panel.top + 36)))

        for mode_key, rect in rects:
            spec = PLAY_MODE_SPECS[mode_key]
            active = mode_key == self.play_mode_key
            fill = spec.color if active else (30, 38, 48)
            border = WHITE if active else spec.color
            pygame.draw.rect(self.screen, fill, rect, border_radius=8)
            pygame.draw.rect(self.screen, border, rect, width=2, border_radius=8)
            text_color = INK if active and spec.color != PANEL_BORDER else WHITE
            label = self.font_small.render(spec.short_label, True, text_color)
            self.screen.blit(label, label.get_rect(center=(rect.centerx, rect.centery - 6)))
            detail = self.font_small.render(spec.detail, True, text_color if active else PANEL_BORDER)
            self.screen.blit(detail, detail.get_rect(center=(rect.centerx, rect.centery + 10)))

    def draw_objective_marker(self) -> None:
        marker = self.objective_marker()
        if marker is None:
            return

        world_pos, label = marker
        screen_pos = pygame.Vector2(world_pos.x - self.camera.x, world_pos.y - self.camera.y)
        margin = 34
        on_screen = (
            margin <= screen_pos.x <= SCREEN_SIZE[0] - margin
            and margin <= screen_pos.y <= SCREEN_SIZE[1] - margin
        )
        pulse = 0.5 + 0.5 * math.sin(self.elapsed * 5.2)

        if on_screen:
            radius = round(18 + pulse * 5)
            glow = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
            center = (radius + 4, radius + 4)
            pygame.draw.circle(glow, (*ACCENT, 74), center, radius)
            pygame.draw.circle(glow, (*WHITE, 160), center, radius, width=2)
            self.screen.blit(glow, glow.get_rect(center=(round(screen_pos.x), round(screen_pos.y))))
            label_y = round(screen_pos.y - radius - 22)
        else:
            clamped = pygame.Vector2(
                clamp(screen_pos.x, margin, SCREEN_SIZE[0] - margin),
                clamp(screen_pos.y, margin, SCREEN_SIZE[1] - margin),
            )
            direction = screen_pos - pygame.Vector2(SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] / 2)
            if direction.length_squared() == 0:
                direction = pygame.Vector2(0, -1)
            direction = direction.normalize()
            tangent = pygame.Vector2(-direction.y, direction.x)
            tip = clamped + direction * (7 + pulse * 4)
            points = [tip, clamped - direction * 13 + tangent * 9, clamped - direction * 13 - tangent * 9]
            pygame.draw.polygon(self.screen, ACCENT, points)
            pygame.draw.polygon(self.screen, WHITE, points, width=2)
            screen_pos = clamped
            label_y = round(clamped.y + 16)

        text = self.font_small.render(label, True, WHITE)
        bg = pygame.Rect(0, 0, text.get_width() + 14, 22)
        bg.center = (round(screen_pos.x), label_y)
        pygame.draw.rect(self.screen, (16, 22, 30, 230), bg, border_radius=8)
        pygame.draw.rect(self.screen, ACCENT, bg, width=2, border_radius=8)
        self.screen.blit(text, text.get_rect(center=bg.center))

    def draw_help(self) -> None:
        overlay = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        overlay.fill((6, 10, 18, 205))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(110, 80, SCREEN_SIZE[0] - 220, SCREEN_SIZE[1] - 160)
        draw_panel(self.screen, panel, (18, 24, 32), ACCENT)
        title = self.font_title.render("Field Help", True, ACCENT)
        self.screen.blit(title, (panel.left + 24, panel.top + 20))

        lines = [
            "Move: WASD or Arrow Keys",
            "Interact / Confirm: E, Space, or Enter",
            "Journal and team lead: Tab",
            "Pause / resume: P",
            "Manual save: F5",
            "Mute / unmute music: M",
            "Sprint: hold Shift after Cedar's reward",
            "Battle: choose Fight, Switch, Orb, Berry, or Run",
            "Grass beats Water, Water beats Fire, Fire beats Grass",
            "Moves show power, accuracy, guard effects, and EXP gain",
            "Close this help: H, Tab, Esc, or Enter",
        ]
        y = panel.top + 102
        for index, line in enumerate(lines):
            color = WHITE if index < 7 else PANEL_BORDER
            rendered = self.font_medium.render(line, True, color)
            self.screen.blit(rendered, (panel.left + 34, y))
            y += 34

    def draw_dialogue(self) -> None:
        outer = pygame.Rect(32, SCREEN_SIZE[1] - 176, SCREEN_SIZE[0] - 64, 144)
        draw_panel(self.screen, outer, (20, 26, 34), ACCENT)
        title = self.font_large.render(self.dialogue_title, True, ACCENT)
        self.screen.blit(title, (outer.left + 18, outer.top + 12))
        page = self.dialogue_pages[self.dialogue_index]
        draw_multiline_text(
            self.screen,
            self.font_medium,
            page,
            pygame.Rect(outer.left + 18, outer.top + 50, outer.width - 36, 70),
        )
        prompt = self.font_small.render("Press E / Space to continue", True, PANEL_BORDER)
        self.screen.blit(prompt, (outer.right - prompt.get_width() - 18, outer.bottom - 26))

    def draw_journal(self) -> None:
        overlay = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        overlay.fill((6, 10, 18, 200))
        self.screen.blit(overlay, (0, 0))

        journal = pygame.Rect(60, 48, SCREEN_SIZE[0] - 120, SCREEN_SIZE[1] - 96)
        draw_panel(self.screen, journal, (18, 24, 30), PANEL_BORDER)

        title = self.font_title.render("Field Journal", True, ACCENT)
        self.screen.blit(title, (journal.left + 22, journal.top + 16))

        left_col = pygame.Rect(journal.left + 24, journal.top + 88, 280, journal.height - 120)
        right_col = pygame.Rect(left_col.right + 24, left_col.top, journal.width - left_col.width - 72, left_col.height)

        party_title = self.font_large.render("Team", True, WHITE)
        self.screen.blit(party_title, (left_col.left, left_col.top))

        if not self.party:
            draw_multiline_text(
                self.screen,
                self.font_medium,
                "No partner yet. Head into Cedar Lab and choose one of the three starters on the table.",
                pygame.Rect(left_col.left, left_col.top + 42, left_col.width, 120),
            )
        else:
            for index, creature in enumerate(self.party):
                row = pygame.Rect(left_col.left, left_col.top + 46 + index * 110, left_col.width, 98)
                selected = index == self.journal_index
                lead = index == self.lead_index
                draw_panel(
                    self.screen,
                    row,
                    (30, 38, 48) if selected else (22, 28, 36),
                    creature.species.accent if lead else PANEL_BORDER,
                )
                icon = creature.species.icon
                icon_rect = icon.get_rect(midleft=(row.left + 24, row.centery))
                self.screen.blit(icon, icon_rect)
                name = self.font_medium.render(f"{creature.name}  Lv.{creature.level}", True, WHITE)
                self.screen.blit(name, (row.left + 78, row.top + 14))
                status = "Fainted" if creature.is_fainted else "Ready"
                if lead:
                    status = f"{status}  |  Lead"
                status_text = self.font_small.render(status, True, PANEL_BORDER)
                self.screen.blit(status_text, (row.left + 78, row.top + 42))
                type_text = self.font_small.render(creature.species.element, True, creature.species.accent)
                self.screen.blit(type_text, (row.right - type_text.get_width() - 18, row.top + 16))
                meter = pygame.Rect(row.left + 78, row.bottom - 28, row.width - 96, 10)
                pygame.draw.rect(self.screen, (56, 64, 72), meter, border_radius=5)
                ratio = creature.hp / max(1, creature.max_hp)
                hp_color = GREEN if ratio > 0.5 else ACCENT if ratio > 0.25 else RED
                fill_width = round(meter.width * ratio)
                if fill_width > 0:
                    pygame.draw.rect(
                        self.screen,
                        hp_color,
                        (meter.left, meter.top, fill_width, meter.height),
                        border_radius=5,
                    )
                exp_meter = pygame.Rect(row.left + 78, row.bottom - 14, row.width - 96, 6)
                pygame.draw.rect(self.screen, (42, 50, 58), exp_meter, border_radius=3)
                exp_fill_width = round(exp_meter.width * self.exp_ratio(creature.level, creature.exp))
                if exp_fill_width > 0:
                    pygame.draw.rect(
                        self.screen,
                        BLUE,
                        (exp_meter.left, exp_meter.top, exp_fill_width, exp_meter.height),
                        border_radius=3,
                    )
                exp_text = self.font_small.render(
                    f"EXP {creature.exp}/{creature.exp_to_next()}",
                    True,
                    PANEL_BORDER,
                )
                self.screen.blit(exp_text, (row.left + 78, row.top + 60))

        info_title = self.font_large.render("Survey", True, WHITE)
        self.screen.blit(info_title, (right_col.left, right_col.top))
        detail_card = pygame.Rect(right_col.left, right_col.top + 40, right_col.width, 152)
        draw_panel(self.screen, detail_card, (24, 30, 38), PANEL_BORDER)
        selected = self.party[self.journal_index] if self.party else None
        if selected is None:
            draw_multiline_text(
                self.screen,
                self.font_medium,
                "Once you choose a partner, this panel will show its type, moves, and growth.",
                pygame.Rect(detail_card.left + 18, detail_card.top + 18, detail_card.width - 36, detail_card.height - 36),
            )
        else:
            icon = pygame.transform.scale_by(selected.species.icon, 1.28)
            self.screen.blit(icon, icon.get_rect(midleft=(detail_card.left + 42, detail_card.top + 70)))
            heading = self.font_large.render(f"{selected.name}  Lv.{selected.level}", True, WHITE)
            self.screen.blit(heading, (detail_card.left + 118, detail_card.top + 16))
            type_line = self.font_medium.render(selected.species.element, True, selected.species.accent)
            self.screen.blit(type_line, (detail_card.left + 120, detail_card.top + 48))
            stats = self.font_small.render(
                f"HP {selected.hp}/{selected.max_hp}   EXP {selected.exp}/{selected.exp_to_next()}",
                True,
                PANEL_BORDER,
            )
            self.screen.blit(stats, (detail_card.left + 120, detail_card.top + 78))
            move_names = "  |  ".join(move.name for move in selected.species.moves)
            draw_multiline_text(
                self.screen,
                self.font_small,
                f"Moves: {move_names}",
                pygame.Rect(detail_card.left + 18, detail_card.top + 104, detail_card.width - 36, 32),
                WHITE,
            )

        summary_lines = [
            f"Objective: {self.current_objective()}",
            f"Survey progress: {self.survey_progress_text()}  |  Remaining: {', '.join(self.remaining_wild_species()) or 'None'}",
            f"Seen species: {', '.join(sorted(self.seen_species)) or 'None yet'}",
            f"Caught species: {', '.join(sorted(self.caught_species)) or 'None yet'}",
            f"Capture Orbs: {self.inventory['capture_orb']}   Berries: {self.inventory['berry']}",
            f"Explorer Charm: {'Found in Mira House' if self.capture_charm else 'Still hidden somewhere'}",
        ]
        for index, line in enumerate(summary_lines):
            top = right_col.top + 198 + index * 36
            height = 48 if index == 0 else 30
            draw_multiline_text(
                self.screen,
                self.font_small,
                line,
                pygame.Rect(right_col.left, top, right_col.width, height),
                WHITE if index == 0 else PANEL_BORDER,
            )

        hint = self.font_small.render(
            "Tab / Esc: Close   Up/Down: Select   Enter: Set lead creature",
            True,
            PANEL_BORDER,
        )
        self.screen.blit(hint, (journal.left + 24, journal.bottom - 34))

    def battle_shake_offset(self) -> pygame.Vector2:
        if self.battle is None or self.battle.screen_shake_timer <= 0:
            return pygame.Vector2()
        ratio = self.battle.screen_shake_timer / 0.22
        strength = self.battle.screen_shake_strength * ratio
        return pygame.Vector2(
            math.sin(self.elapsed * 82) * strength,
            math.cos(self.elapsed * 69) * strength * 0.55,
        )

    def battle_anchor(self, side: str) -> pygame.Vector2:
        if side == "enemy":
            return pygame.Vector2(736, 148) + self.battle_shake_offset()
        return pygame.Vector2(278, 328) + self.battle_shake_offset()

    def battle_sprite_offset(self, side: str) -> pygame.Vector2:
        if self.battle is None:
            return pygame.Vector2()

        offset = pygame.Vector2()
        hit_timer = getattr(self.battle, f"{side}_hit_timer")
        if hit_timer > 0:
            offset.x += math.sin(hit_timer * 90) * 8
            offset.y += math.sin(hit_timer * 63) * 2

        lunge_timer = getattr(self.battle, f"{side}_lunge_timer")
        if lunge_timer > 0:
            progress = 1.0 - lunge_timer / max(0.001, LUNGE_DURATION)
            amount = math.sin(progress * math.pi) * 24
            if side == "player":
                offset.update(amount, -amount * 0.34)
            else:
                offset.update(-amount, amount * 0.34)
        return offset

    def battle_sprite_visible(self, side: str) -> bool:
        if self.battle is None:
            return True
        hit_timer = getattr(self.battle, f"{side}_hit_timer")
        return hit_timer <= 0 or int(hit_timer * 18) % 2 == 1

    def draw_battle_creature_sprite(self, creature: Creature, side: str) -> None:
        if side == "enemy":
            bottom = pygame.Vector2(736, 272)
            shadow_size = (170, 34)
            sprite = creature.species.front_sprite
        else:
            bottom = pygame.Vector2(278, 444)
            shadow_size = (196, 40)
            sprite = creature.species.back_sprite

        visual_offset = self.battle_sprite_offset(side) + self.battle_shake_offset()
        shadow = make_shadow(*shadow_size, 106)
        shadow_rect = shadow.get_rect(center=(round(bottom.x + visual_offset.x * 0.35), round(bottom.y + 20)))
        self.screen.blit(shadow, shadow_rect)

        if not self.battle_sprite_visible(side):
            return

        drawable = sprite
        if creature.is_fainted:
            drawable = with_surface_alpha(sprite, 145)
        rect = drawable.get_rect(
            midbottom=(round(bottom.x + visual_offset.x), round(bottom.y + visual_offset.y))
        )
        self.screen.blit(drawable, rect)

        hit_timer = getattr(self.battle, f"{side}_hit_timer") if self.battle is not None else 0.0
        if hit_timer > 0:
            flash = sprite.copy()
            flash.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_ADD)
            flash = with_surface_alpha(flash, 150)
            self.screen.blit(flash, rect)

    def draw_battle_effects(self) -> None:
        if self.battle is None:
            return

        for effect in self.battle.effects:
            art = self.ability_effects.get(effect.move_name)
            item_icon = self.item_icons.get(effect.move_name)
            progress = effect.progress

            if effect.guard:
                center = self.battle_anchor(effect.source_side)
                size = round(188 + math.sin(progress * math.pi) * 54)
                alpha = round(230 * (1.0 - progress * 0.45))
            else:
                start = self.battle_anchor(effect.source_side)
                end = self.battle_anchor(effect.target_side)
                if effect.missed:
                    miss_x = 82 if effect.source_side == "player" else -82
                    end += pygame.Vector2(miss_x, -76)
                travel = min(1.0, progress / 0.72)
                ease = 1.0 - (1.0 - travel) ** 2
                center = start.lerp(end, ease)
                center.y -= math.sin(travel * math.pi) * 22
                burst = max(0.0, (progress - 0.48) / 0.52)
                size = round(158 + travel * 72 + math.sin(burst * math.pi) * 44)
                alpha = round(245 * (1.0 - max(0.0, progress - 0.72) / 0.28))

            if item_icon is not None:
                start = self.battle_anchor(effect.source_side)
                end = self.battle_anchor(effect.target_side)
                travel = min(1.0, progress / 0.72)
                ease = 1.0 - (1.0 - travel) ** 2
                center = start.lerp(end, ease)
                center.y -= 46 + math.sin(progress * math.pi) * 36
                size = round(40 + math.sin(progress * math.pi) * 22)
                frame = pygame.transform.smoothscale(item_icon, (size, size))
                frame = with_surface_alpha(frame, round(245 * (1.0 - max(0.0, progress - 0.78) / 0.22)))
                rect = frame.get_rect(center=(round(center.x), round(center.y)))
                self.screen.blit(frame, rect)
                sparkle_alpha = round(180 * math.sin(progress * math.pi))
                if sparkle_alpha > 0:
                    radius = max(8, size // 3)
                    sparkle = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(
                        sparkle,
                        (*WHITE, sparkle_alpha),
                        (radius + 2, radius + 2),
                        radius,
                        width=2,
                    )
                    self.screen.blit(sparkle, sparkle.get_rect(center=rect.center))
                continue

            if art is None:
                radius = max(8, size // 5)
                pygame.draw.circle(self.screen, (*ACCENT, max(0, alpha)), center, radius)
                continue

            frame = art
            if effect.source_side == "enemy" and not effect.guard:
                frame = pygame.transform.flip(frame, True, False)
            frame = pygame.transform.smoothscale(frame, (size, size))
            frame = with_surface_alpha(frame, max(0, min(255, alpha)))
            rect = frame.get_rect(center=(round(center.x), round(center.y)))
            self.screen.blit(frame, rect)

    def draw_damage_popups(self) -> None:
        if self.battle is None:
            return

        for popup in self.battle.damage_popups:
            progress = popup.progress
            anchor = self.battle_anchor(popup.side)
            y = anchor.y - 82 - progress * 42
            wobble = math.sin(progress * math.pi * 2) * 5
            text = self.font_large.render(popup.text, True, popup.color)
            shadow = self.font_large.render(popup.text, True, (10, 14, 18))
            alpha = round(255 * (1.0 - progress))
            text.set_alpha(alpha)
            shadow.set_alpha(alpha)
            rect = text.get_rect(center=(round(anchor.x + wobble), round(y)))
            self.screen.blit(shadow, shadow.get_rect(center=(rect.centerx + 2, rect.centery + 2)))
            self.screen.blit(text, rect)

    def draw_battle(self) -> None:
        self.screen.blit(self.battle_background, (0, 0))
        battle_shade = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        battle_shade.fill((10, 18, 26, 38))
        self.screen.blit(battle_shade, (0, 0))

        enemy = self.battle.enemy
        lead = self.lead_creature()
        exp_animation = self.battle.exp_animation

        self.draw_battle_creature_sprite(enemy, "enemy")
        if lead is not None:
            self.draw_battle_creature_sprite(lead, "player")

        self.draw_battle_effects()
        self.draw_damage_popups()

        enemy_bar = pygame.Rect(36, 34, 320, 84)
        self.draw_creature_bar(enemy, enemy_bar, enemy.species.accent, active=True, show_exp=False)
        if lead is not None:
            player_bar = pygame.Rect(SCREEN_SIZE[0] - 356, 344, 320, 84)
            if exp_animation is not None:
                self.draw_creature_bar(
                    lead,
                    player_bar,
                    lead.species.accent,
                    active=True,
                    display_level=exp_animation.display_level,
                    display_exp=exp_animation.display_exp,
                )
            else:
                self.draw_creature_bar(lead, player_bar, lead.species.accent, active=True)

        if self.battle.phase == "exp_gain" and exp_animation is not None:
            box = pygame.Rect(30, SCREEN_SIZE[1] - 176, SCREEN_SIZE[0] - 60, 144)
            draw_panel(self.screen, box, (20, 24, 32), BLUE)
            title = self.font_large.render(exp_animation.banner_text, True, WHITE)
            self.screen.blit(title, (box.left + 18, box.top + 18))
            subtitle = self.font_medium.render(
                f"Level {exp_animation.display_level} progress",
                True,
                PANEL_BORDER,
            )
            self.screen.blit(subtitle, (box.left + 18, box.top + 58))
            hint = self.font_small.render("EXP is filling in real time. Press E / Space to skip.", True, PANEL_BORDER)
            self.screen.blit(hint, (box.left + 18, box.bottom - 28))
            return

        if self.battle.phase == "messages":
            box = pygame.Rect(30, SCREEN_SIZE[1] - 156, SCREEN_SIZE[0] - 60, 126)
            draw_panel(self.screen, box, (20, 24, 32), ACCENT)
            text = self.battle.messages[0] if self.battle.messages else ""
            draw_multiline_text(
                self.screen,
                self.font_large,
                text,
                pygame.Rect(box.left + 18, box.top + 18, box.width - 36, box.height - 40),
            )
            prompt = self.font_small.render("E / Space: Continue", True, PANEL_BORDER)
            self.screen.blit(prompt, (box.right - prompt.get_width() - 18, box.bottom - 24))
            return

        if self.battle.phase == "command":
            box = pygame.Rect(30, SCREEN_SIZE[1] - 204, SCREEN_SIZE[0] - 60, 174)
            draw_panel(self.screen, box, (20, 24, 32), PANEL_BORDER)
            prompt = self.font_large.render("Choose an action", True, WHITE)
            self.screen.blit(prompt, (box.left + 18, box.top + 18))
            enemy = self.battle.enemy
            catch_hint = round(self.capture_rate_for(enemy) * 100)
            wild_info = self.font_small.render(
                f"Wild {enemy.name}  Lv.{enemy.level}  {enemy.species.element}",
                True,
                PANEL_BORDER,
            )
            resource_info = self.font_small.render(
                f"Orbs {self.inventory['capture_orb']}  |  Berries {self.inventory['berry']}  |  Catch {catch_hint}%",
                True,
                PANEL_BORDER,
            )
            self.screen.blit(wild_info, (box.left + 18, box.top + 54))
            self.screen.blit(resource_info, (box.left + 18, box.top + 76))
            commands = self.battle_command_labels()
            for index, label in enumerate(commands):
                cell = pygame.Rect(box.left + 322 + (index % 2) * 152, box.top + 16 + (index // 2) * 48, 136, 40)
                selected = index == self.battle.command_index
                draw_panel(self.screen, cell, PANEL_LIGHT if selected else PANEL, ACCENT if selected else PANEL_BORDER)
                text = self.font_medium.render(label, True, WHITE)
                self.screen.blit(text, text.get_rect(center=cell.center))
            return

        if self.battle.phase == "party_select":
            box = pygame.Rect(88, 86, SCREEN_SIZE[0] - 176, SCREEN_SIZE[1] - 172)
            draw_panel(self.screen, box, (20, 24, 32), PANEL_BORDER)
            heading = self.font_large.render("Choose a Pokemon", True, WHITE)
            self.screen.blit(heading, (box.left + 18, box.top + 18))

            selected_party = self.party[self.battle.party_index] if self.party else None
            for index, creature in enumerate(self.party):
                row = pygame.Rect(box.left + 18, box.top + 58 + index * 68, box.width - 36, 56)
                selected = index == self.battle.party_index
                border = creature.species.accent if selected else PANEL_BORDER
                fill = PANEL_LIGHT if selected else PANEL
                draw_panel(self.screen, row, fill, border)
                icon = creature.species.icon
                self.screen.blit(icon, icon.get_rect(midleft=(row.left + 18, row.centery)))
                title = self.font_medium.render(f"{creature.name}  Lv.{creature.level}", True, WHITE)
                self.screen.blit(title, (row.left + 70, row.top + 8))
                hp = self.font_small.render(f"HP {creature.hp}/{creature.max_hp}", True, PANEL_BORDER)
                self.screen.blit(hp, (row.left + 70, row.top + 32))

                status = ""
                status_color = PANEL_BORDER
                if index == self.lead_index:
                    status = "In battle"
                    status_color = ACCENT
                elif creature.is_fainted:
                    status = "Fainted"
                    status_color = RED
                else:
                    status = "Ready"
                    status_color = GREEN
                status_text = self.font_small.render(status, True, status_color)
                self.screen.blit(status_text, (row.right - status_text.get_width() - 16, row.top + 18))

            hint_text = "Pick another Pokemon to send out."
            if selected_party is not None:
                if self.battle.party_index == self.lead_index:
                    hint_text = f"{selected_party.name} is already in battle."
                elif selected_party.is_fainted:
                    hint_text = f"{selected_party.name} can't battle right now."
                else:
                    hint_text = f"Switch to {selected_party.name}. The wild Pokemon will move next."
            draw_multiline_text(
                self.screen,
                self.font_small,
                hint_text,
                pygame.Rect(box.left + 18, box.bottom - 58, box.width - 36, 30),
                PANEL_BORDER,
            )
            cancel = self.font_small.render("Backspace / X / Esc: Back", True, PANEL_BORDER)
            self.screen.blit(cancel, (box.right - cancel.get_width() - 18, box.bottom - 28))
            return

        if self.battle.phase == "move_select" and lead is not None:
            box = pygame.Rect(30, SCREEN_SIZE[1] - 214, SCREEN_SIZE[0] - 60, 184)
            draw_panel(self.screen, box, (20, 24, 32), PANEL_BORDER)
            heading = self.font_large.render("Pick a move", True, WHITE)
            self.screen.blit(heading, (box.left + 18, box.top + 16))
            for index, move in enumerate(lead.species.moves):
                row = pygame.Rect(box.left + 18, box.top + 54 + index * 30, box.width - 36, 26)
                selected = index == self.battle.move_index
                if selected:
                    pygame.draw.rect(self.screen, (52, 64, 80), row, border_radius=6)
                label = move.name if move.kind != "guard" else f"{move.name}  (Guard)"
                label_x = row.left + 8
                effect_art = self.ability_effects.get(move.effect_key or move.name)
                if effect_art is not None:
                    thumb = pygame.transform.smoothscale(effect_art, (26, 26))
                    thumb = with_surface_alpha(thumb, 245 if selected else 190)
                    self.screen.blit(thumb, (row.left + 6, row.top))
                    label_x += 34
                text = self.font_medium.render(label, True, ACCENT if selected else WHITE)
                self.screen.blit(text, (label_x, row.top + 2))
                detail = "Blocks the next hit" if move.kind == "guard" else f"Power {move.power}  |  Accuracy {round(move.accuracy * 100)}%"
                meta = self.font_small.render(detail, True, PANEL_BORDER)
                self.screen.blit(meta, (box.right - meta.get_width() - 18, row.top + 4))
            selected_move = lead.species.moves[self.battle.move_index]
            flavor = selected_move.text.replace("{target}", "the foe").replace("{damage}", "damage")
            flavor = flavor.replace("damage damage", "damage")
            if selected_move.kind == "guard":
                flavor = "Raises a guard effect for the next incoming hit."
                matchup = "Use this to soften a dangerous turn."
            else:
                multiplier = self.type_multiplier(lead.species.element, enemy.species.element)
                if multiplier > 1.0:
                    matchup = f"Matchup: strong into {enemy.species.element}."
                elif multiplier < 1.0:
                    matchup = f"Matchup: weak into {enemy.species.element}."
                else:
                    matchup = f"Matchup: even against {enemy.species.element}."
            draw_multiline_text(
                self.screen,
                self.font_small,
                f"{lead.species.element} move: {flavor}",
                pygame.Rect(box.left + 18, box.bottom - 54, box.width - 36, 28),
                PANEL_BORDER,
            )
            matchup_text = self.font_small.render(matchup, True, PANEL_BORDER)
            self.screen.blit(matchup_text, (box.left + 18, box.bottom - 26))
            hint = self.font_small.render("Backspace / X: Back", True, PANEL_BORDER)
            self.screen.blit(hint, (box.right - hint.get_width() - 18, box.bottom - 26))

    def draw_transition(self) -> None:
        progress = 1.0 - (self.transition_timer / max(0.001, self.transition_total))

        if self.transition_kind == "door":
            close = 1.0 - abs(progress - 0.5) * 2.0
            close = clamp(close, 0.0, 1.0)
            overlay = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, round(205 * close)))
            panel_width = round(SCREEN_SIZE[0] * 0.5 * close)
            pygame.draw.rect(overlay, (8, 10, 16, 235), pygame.Rect(0, 0, panel_width, SCREEN_SIZE[1]))
            pygame.draw.rect(
                overlay,
                (8, 10, 16, 235),
                pygame.Rect(SCREEN_SIZE[0] - panel_width, 0, panel_width, SCREEN_SIZE[1]),
            )
            if close > 0.22:
                door_rect = pygame.Rect(0, 0, round(96 * close), round(168 * close))
                door_rect.center = (SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2 + 10)
                pygame.draw.rect(overlay, (36, 26, 20, 210), door_rect, border_radius=10)
                pygame.draw.rect(overlay, ACCENT, door_rect, width=3, border_radius=10)
                knob = (door_rect.right - max(8, round(18 * close)), door_rect.centery)
                pygame.draw.circle(overlay, ACCENT, knob, max(3, round(5 * close)))
            self.screen.blit(overlay, (0, 0))

            if close > 0.6:
                target = self.pending_scene_entry[0] if self.pending_scene_entry else self.scene_key
                title = {
                    "meadow": "Verdant Meadow",
                    "cedar_lab": "Cedar Lab",
                    "mira_house": "Mira's House",
                }[target]
                label = self.font_large.render(title, True, WHITE)
                label.set_alpha(round(255 * min(1.0, (close - 0.6) / 0.4)))
                self.screen.blit(label, label.get_rect(center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2 + 130)))
            return

        overlay = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        for index in range(0, SCREEN_SIZE[1], 24):
            stripe_alpha = int(90 + 100 * abs(math.sin(progress * 18 + index * 0.15)))
            if (index // 24) % 2 == 0:
                pygame.draw.rect(overlay, (255, 255, 255, stripe_alpha), pygame.Rect(0, index, SCREEN_SIZE[0], 12))
        overlay.fill((0, 0, 0, int(progress * 180)), special_flags=pygame.BLEND_RGBA_SUB)
        self.screen.blit(overlay, (0, 0))

        banner = self.font_title.render("Wild Encounter!", True, WHITE)
        banner_rect = banner.get_rect(center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2))
        self.screen.blit(banner, banner_rect)

    def draw_ending(self) -> None:
        preview_camera = pygame.Vector2(220, 218)
        self.screen.blit(self.map_surface, (-preview_camera.x, -preview_camera.y))

        overlay = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        overlay.fill((8, 12, 18, 188))
        self.screen.blit(overlay, (0, 0))

        title_panel = pygame.Rect(84, 44, SCREEN_SIZE[0] - 168, 82)
        body_panel = pygame.Rect(84, 148, SCREEN_SIZE[0] - 168, 220)
        cast_panel = pygame.Rect(84, 390, SCREEN_SIZE[0] - 168, 160)
        draw_panel(self.screen, title_panel, (20, 26, 34), ACCENT)
        draw_panel(self.screen, body_panel, (18, 24, 32), PANEL_BORDER)
        draw_panel(self.screen, cast_panel, (18, 24, 32), PANEL_BORDER)

        title = self.font_title.render("Survey Complete", True, ACCENT)
        self.screen.blit(title, title.get_rect(center=title_panel.center))

        page = self.ending_pages[self.ending_index] if self.ending_pages else ""
        draw_multiline_text(
            self.screen,
            self.font_large,
            page,
            pygame.Rect(body_panel.left + 24, body_panel.top + 28, body_panel.width - 48, body_panel.height - 56),
        )

        professor = pygame.transform.scale_by(self.scenes["cedar_lab"].npcs["professor"].sprite, 1.08)
        mira = pygame.transform.scale_by(self.scenes["mira_house"].npcs["healer"].sprite, 1.08)
        cast_text = self.font_medium.render("Cedar, Mira, your starter team, and the meadow trio", True, PANEL_BORDER)
        self.screen.blit(cast_text, cast_text.get_rect(center=(cast_panel.centerx + 54, cast_panel.top + 18)))

        shadow_y = cast_panel.bottom - 22
        self.screen.blit(professor, professor.get_rect(midbottom=(cast_panel.left + 92, cast_panel.bottom - 16)))
        self.screen.blit(mira, mira.get_rect(midbottom=(cast_panel.left + 210, cast_panel.bottom - 16)))

        icon_row = [
            self.species["Leafawn"].icon,
            self.species["Flarekit"].icon,
            self.species["Tidefin"].icon,
            self.species["Mothleaf"].icon,
            self.species["Bubbun"].icon,
            self.species["Sparrook"].icon,
        ]
        for index, icon in enumerate(icon_row):
            center_x = cast_panel.left + 358 + index * 66
            halo = pygame.Surface((52, 22), pygame.SRCALPHA)
            pygame.draw.ellipse(halo, (*ACCENT, 56), halo.get_rect())
            self.screen.blit(halo, halo.get_rect(center=(center_x, shadow_y)))
            self.screen.blit(icon, icon.get_rect(midbottom=(center_x, cast_panel.bottom - 18)))

        if self.ending_index == len(self.ending_pages) - 1 and self.ending_pages:
            end_text = self.font_large.render("The End", True, ACCENT)
            self.screen.blit(end_text, end_text.get_rect(center=(body_panel.centerx, body_panel.bottom - 32)))

        prompt_text = "Press E / Space to return to the meadow" if self.ending_index == len(self.ending_pages) - 1 else "Press E / Space to continue"
        prompt = self.font_small.render(prompt_text, True, PANEL_BORDER)
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] - 26)))

    def draw_title(self) -> None:
        self.screen.fill((12, 18, 26))
        preview_camera = pygame.Vector2(260, 250)
        self.screen.blit(self.map_surface, (-preview_camera.x, -preview_camera.y))

        shade = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        shade.fill((6, 10, 18, 150))
        self.screen.blit(shade, (0, 0))
        save_data = self.save_progress_data()

        panel = pygame.Rect(76, 48, SCREEN_SIZE[0] - 152, SCREEN_SIZE[1] - 96)
        draw_panel(self.screen, panel, (16, 22, 30), PANEL_BORDER)

        title = self.font_title.render("Pokemon Fan Meadow", True, ACCENT)
        subtitle_text = "A one-map mini adventure"
        if save_data is not None and save_data.get("quest_stage") == "complete":
            subtitle_text = "Survey complete. Keep exploring the meadow."
        subtitle = self.font_large.render(subtitle_text, True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_SIZE[0] // 2, 146)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_SIZE[0] // 2, 196)))

        if save_data is not None and save_data.get("quest_stage") == "complete":
            ribbon = pygame.Rect(0, 0, 188, 30)
            ribbon.center = (SCREEN_SIZE[0] // 2, 228)
            pygame.draw.rect(self.screen, (30, 54, 78), ribbon, border_radius=10)
            pygame.draw.rect(self.screen, BLUE, ribbon, width=2, border_radius=10)
            ribbon_text = self.font_small.render("Survey Complete Save", True, WHITE)
            self.screen.blit(ribbon_text, ribbon_text.get_rect(center=ribbon.center))

        for species_key, center in (
            ("Leafawn", (232, 278)),
            ("Flarekit", (480, 278)),
            ("Tidefin", (728, 278)),
        ):
            bob = math.sin(self.elapsed * 3.2 + center[0] * 0.01) * 4
            icon = pygame.transform.scale_by(self.species[species_key].icon, 1.26)
            self.screen.blit(icon, icon.get_rect(midbottom=(center[0], center[1] + bob + 16)))
            label = self.font_small.render(species_key, True, WHITE)
            self.screen.blit(label, label.get_rect(center=(center[0], 324)))

        lines = [
            "Choose Leafawn, Flarekit, or Tidefin in Cedar Lab, then step into the meadow.",
            "Catch the wild meadow trio, report back to Cedar,",
            "and finish the survey with Mira's hidden charm and the final ending.",
        ]
        for index, line in enumerate(lines):
            rendered = self.font_medium.render(line, True, WHITE)
            self.screen.blit(rendered, rendered.get_rect(center=(SCREEN_SIZE[0] // 2, 352 + index * 28)))

        left_controls = [
            "Move: WASD / Arrow Keys",
            "Interact: E / Space / Enter",
            "Journal: Tab",
        ]
        right_controls = [
            "Save: F5",
            "Help: H",
            "Pause: P",
            "Music: M",
            "Sprint: Shift after reward",
        ]
        controls_top = 432
        for index, line in enumerate(left_controls):
            rendered = self.font_small.render(line, True, PANEL_BORDER)
            self.screen.blit(rendered, rendered.get_rect(midleft=(230, controls_top + index * 27)))
        for index, line in enumerate(right_controls):
            rendered = self.font_small.render(line, True, PANEL_BORDER)
            self.screen.blit(rendered, rendered.get_rect(midleft=(560, controls_top + index * 27)))

        pulse = 180 + int(60 * math.sin(self.elapsed * 4))
        if self.has_save_file():
            start_text = "Enter: Continue"
            second_text = "N: New Adventure    Esc: Quit"
        else:
            start_text = "Press Enter to Start"
            second_text = "Esc: Quit"
        start = self.font_large.render(start_text, True, (pulse, pulse, 255))
        self.screen.blit(start, start.get_rect(center=(SCREEN_SIZE[0] // 2, 522)))
        summary = self.save_summary_text()
        if summary is not None:
            save_text = self.font_small.render(summary, True, ACCENT)
            self.screen.blit(save_text, save_text.get_rect(center=(SCREEN_SIZE[0] // 2, 548)))
        secondary = self.font_medium.render(second_text, True, PANEL_BORDER)
        self.screen.blit(secondary, secondary.get_rect(center=(SCREEN_SIZE[0] // 2, 578 if summary else 562)))

    def draw(self) -> None:
        if self.mode == "title":
            self.draw_title()
        elif self.mode == "ending":
            self.draw_ending()
        elif self.mode == "battle":
            self.draw_battle()
        else:
            self.draw_world()
        self.draw_mode_sidebar()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_game()
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_keydown(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_mouse_down(event.pos)

            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
