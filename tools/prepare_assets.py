from __future__ import annotations

from collections import deque
from pathlib import Path
import json

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "assets" / "raw"
MAP_OUT = ROOT / "assets" / "maps" / "start_area.png"
SPRITE_OUT = ROOT / "assets" / "sprites" / "player_sheet.png"
MANIFEST_OUT = ROOT / "assets" / "sprites" / "player_manifest.json"
PREVIEW_OUT = ROOT / "assets" / "sprites" / "player_sheet_preview.png"
CREATURE_RAW_DIR = RAW_DIR / "creatures"
CREATURE_OUT_DIR = ROOT / "assets" / "creatures"
CREATURE_PREVIEW_OUT = CREATURE_OUT_DIR / "creature_preview_sheet.png"
NPC_RAW_DIR = RAW_DIR / "npcs"
NPC_OUT_DIR = ROOT / "assets" / "npcs"
NPC_PREVIEW_OUT = NPC_OUT_DIR / "npc_preview_sheet.png"
ITEM_RAW_DIR = RAW_DIR / "items"
ITEM_OUT_DIR = ROOT / "assets" / "items"
UI_RAW_DIR = RAW_DIR / "ui"
UI_OUT_DIR = ROOT / "assets" / "ui"
GRASS_RAW_DIR = RAW_DIR / "grass"
GRASS_OUT_DIR = ROOT / "assets" / "grass"
INTERIOR_RAW_DIR = RAW_DIR / "interiors"
INTERIOR_OUT_DIR = ROOT / "assets" / "interiors"
BATTLE_RAW_DIR = RAW_DIR / "battle"
BATTLE_OUT_DIR = ROOT / "assets" / "battle"
BATTLE_BG_OUT = BATTLE_OUT_DIR / "meadow_battle_bg.png"
UI_PANEL_OUT = UI_OUT_DIR / "panel_frame.png"
GRASS_SHEET_OUT = GRASS_OUT_DIR / "tall_grass_sheet.png"

MAP_SOURCE = RAW_DIR / "start_area_source.png"
SPRITE_SOURCE = RAW_DIR / "player_sheet_source.png"
CREATURE_SOURCES = {
    "bloomcub_front": CREATURE_RAW_DIR / "bloomcub_front_source.png",
    "bloomcub_back": CREATURE_RAW_DIR / "bloomcub_back_source.png",
    "pebblit_front": CREATURE_RAW_DIR / "pebblit_front_source.png",
    "pebblit_back": CREATURE_RAW_DIR / "pebblit_back_source.png",
    "cindlet_front": CREATURE_RAW_DIR / "cindlet_front_source.png",
    "cindlet_back": CREATURE_RAW_DIR / "cindlet_back_source.png",
}
NPC_SOURCES = {
    "professor_cedar": NPC_RAW_DIR / "professor_cedar_source.png",
    "ranger_mira": NPC_RAW_DIR / "ranger_mira_source.png",
}
ITEM_SOURCES = {
    "capture_orb": ITEM_RAW_DIR / "capture_orb_source.png",
    "berry": ITEM_RAW_DIR / "berry_source.png",
}
INTERIOR_SOURCES = {
    "cedar_lab": INTERIOR_RAW_DIR / "cedar_lab_source.png",
    "mira_house": INTERIOR_RAW_DIR / "mira_house_source.png",
}
BATTLE_BG_SOURCE = BATTLE_RAW_DIR / "meadow_battle_bg_source.png"
UI_PANEL_SOURCE = UI_RAW_DIR / "panel_frame_source.png"
GRASS_SHEET_SOURCE = GRASS_RAW_DIR / "tall_grass_sheet_source.png"

PLAYER_ROWS = 4
PLAYER_COLS = 3
FRAME_SIZE = (24, 32)
FRAME_MARGIN = 1
MAP_PIXELATE_FACTOR = 3
CREATURE_CANVAS = (160, 160)
CREATURE_MARGIN = 12
NPC_CANVAS = (48, 64)
NPC_MARGIN = 4
ITEM_CANVAS = (28, 28)
ITEM_MARGIN = 2
GRASS_FRAME_SIZE = (64, 42)
INTERIOR_SIZE = (1280, 1280)
BATTLE_BG_SIZE = (960, 640)


def pixelate_map(image: Image.Image) -> Image.Image:
    small = image.resize(
        (image.width // MAP_PIXELATE_FACTOR, image.height // MAP_PIXELATE_FACTOR),
        Image.Resampling.NEAREST,
    )
    return small.resize(image.size, Image.Resampling.NEAREST)


def is_magenta_background(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, a = pixel
    return a > 0 and r > 150 and b > 150 and g < 135 and abs(r - b) < 120


def strip_magenta_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    background = [[False for _ in range(width)] for _ in range(height)]
    queue: deque[tuple[int, int]] = deque()

    def enqueue(x: int, y: int) -> None:
        if not (0 <= x < width and 0 <= y < height):
            return
        if background[y][x]:
            return
        if not is_magenta_background(pixels[x, y]):
            return

        background[y][x] = True
        queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)

    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            enqueue(nx, ny)

    cleaned = Image.new("RGBA", rgba.size)
    cleaned_pixels = cleaned.load()

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if background[y][x]:
                cleaned_pixels[x, y] = (r, g, b, 0)
            else:
                cleaned_pixels[x, y] = (r, g, b, a)

    return cleaned


def trim_transparent(image: Image.Image) -> Image.Image:
    bbox = image.getbbox()
    if bbox is None:
        raise ValueError("Transparent crop produced an empty sprite.")
    return image.crop(bbox)


def clear_magenta_fringe(image: Image.Image) -> Image.Image:
    source = image.copy()
    cleaned = image.copy()
    src_pixels = source.load()
    out_pixels = cleaned.load()
    width, height = image.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = src_pixels[x, y]
            if a == 0:
                continue
            if not (r > 110 and b > 110 and g < 150 and abs(r - b) < 120):
                continue

            touches_transparent = False
            for nx in (x - 1, x, x + 1):
                for ny in (y - 1, y, y + 1):
                    if nx == x and ny == y:
                        continue
                    if not (0 <= nx < width and 0 <= ny < height):
                        continue
                    if src_pixels[nx, ny][3] == 0:
                        touches_transparent = True
                        break
                if touches_transparent:
                    break

            if touches_transparent:
                out_pixels[x, y] = (0, 0, 0, 0)

    return cleaned


def erase_remaining_magenta(image: Image.Image) -> Image.Image:
    cleaned = image.copy()
    pixels = cleaned.load()
    width, height = image.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            if r > 120 and b > 120 and g < 120 and abs(r - b) < 110:
                pixels[x, y] = (0, 0, 0, 0)

    return cleaned


def pad_to_canvas(
    image: Image.Image,
    size: tuple[int, int],
    *,
    margin: int = CREATURE_MARGIN,
    align: str = "bottom",
) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    inner_width = size[0] - margin * 2
    inner_height = size[1] - margin * 2
    scale = min(inner_width / image.width, inner_height / image.height)
    resized = image.resize(
        (
            max(1, round(image.width * scale)),
            max(1, round(image.height * scale)),
        ),
        Image.Resampling.NEAREST,
    )
    x = (size[0] - resized.width) // 2
    if align == "center":
        y = (size[1] - resized.height) // 2
    else:
        y = size[1] - margin - resized.height
    canvas.alpha_composite(resized, (x, y))
    return canvas


def find_components(image: Image.Image) -> list[tuple[int, int, int, int, int]]:
    alpha = image.getchannel("A")
    width, height = image.size
    visited = [[False for _ in range(width)] for _ in range(height)]
    pixels = alpha.load()
    components: list[tuple[int, int, int, int, int]] = []

    for y in range(height):
        for x in range(width):
            if visited[y][x] or pixels[x, y] <= 12:
                continue

            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited[y][x] = True
            min_x = max_x = x
            min_y = max_y = y
            area = 0

            while queue:
                cx, cy = queue.popleft()
                area += 1
                min_x = min(min_x, cx)
                min_y = min(min_y, cy)
                max_x = max(max_x, cx)
                max_y = max(max_y, cy)

                for nx in (cx - 1, cx, cx + 1):
                    for ny in (cy - 1, cy, cy + 1):
                        if nx == cx and ny == cy:
                            continue
                        if not (0 <= nx < width and 0 <= ny < height):
                            continue
                        if visited[ny][nx] or pixels[nx, ny] <= 12:
                            continue
                        visited[ny][nx] = True
                        queue.append((nx, ny))

            if area > 400:
                components.append((min_x, min_y, max_x + 1, max_y + 1, area))

    return components


def split_rows(
    components: list[tuple[int, int, int, int, int]]
) -> list[list[tuple[int, int, int, int, int]]]:
    ordered = sorted(
        components,
        key=lambda box: (
            (box[1] + box[3]) / 2,
            (box[0] + box[2]) / 2,
        ),
    )
    if len(ordered) < PLAYER_ROWS * PLAYER_COLS:
        raise ValueError(
            f"Expected at least {PLAYER_ROWS * PLAYER_COLS} sprite components, found {len(ordered)}."
        )

    ordered = sorted(ordered, key=lambda box: box[4], reverse=True)[: PLAYER_ROWS * PLAYER_COLS]
    ordered.sort(key=lambda box: ((box[1] + box[3]) / 2, (box[0] + box[2]) / 2))

    rows: list[list[tuple[int, int, int, int, int]]] = []
    for index in range(0, len(ordered), PLAYER_COLS):
        row = ordered[index : index + PLAYER_COLS]
        row.sort(key=lambda box: (box[0] + box[2]) / 2)
        rows.append(row)

    if len(rows) != PLAYER_ROWS or any(len(row) != PLAYER_COLS for row in rows):
        raise ValueError("Could not arrange the detected sprites into a 4x3 grid.")

    return rows


def build_sprite_sheet(image: Image.Image) -> Image.Image:
    components = find_components(image)
    rows = split_rows(components)

    max_width = max(box[2] - box[0] for row in rows for box in row)
    max_height = max(box[3] - box[1] for row in rows for box in row)
    inner_width = FRAME_SIZE[0] - FRAME_MARGIN * 2
    inner_height = FRAME_SIZE[1] - FRAME_MARGIN * 2
    scale = min(inner_width / max_width, inner_height / max_height)

    sheet = Image.new(
        "RGBA",
        (FRAME_SIZE[0] * PLAYER_COLS, FRAME_SIZE[1] * PLAYER_ROWS),
        (0, 0, 0, 0),
    )

    for row_index, row in enumerate(rows):
        for col_index, box in enumerate(row):
            sprite = trim_transparent(image.crop(box[:4]))
            resized = sprite.resize(
                (
                    max(1, round(sprite.width * scale)),
                    max(1, round(sprite.height * scale)),
                ),
                Image.Resampling.NEAREST,
            )
            frame = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
            x = (FRAME_SIZE[0] - resized.width) // 2
            y = FRAME_SIZE[1] - FRAME_MARGIN - resized.height
            frame.alpha_composite(resized, (x, y))
            sheet.alpha_composite(
                frame,
                (col_index * FRAME_SIZE[0], row_index * FRAME_SIZE[1]),
            )

    return sheet


def save_manifest() -> None:
    manifest = {
        "frame_width": FRAME_SIZE[0],
        "frame_height": FRAME_SIZE[1],
        "sheet_columns": PLAYER_COLS,
        "sheet_rows": PLAYER_ROWS,
        "row_directions": ["down", "up", "left", "right"],
        "walk_cycle": [0, 1, 0, 2],
        "render_scale": 2,
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def prepare_creatures() -> None:
    preview_tiles: list[Image.Image] = []

    for name, source in CREATURE_SOURCES.items():
        image = Image.open(source)
        transparent = strip_magenta_background(image)
        trimmed = trim_transparent(clear_magenta_fringe(transparent))
        cleaned = erase_remaining_magenta(trimmed)
        framed = pad_to_canvas(cleaned, CREATURE_CANVAS)
        out_path = CREATURE_OUT_DIR / f"{name}.png"
        framed.save(out_path)
        preview_tiles.append(
            framed.resize(
                (CREATURE_CANVAS[0] * 2, CREATURE_CANVAS[1] * 2),
                Image.Resampling.NEAREST,
            )
        )

    columns = 3
    rows = max(1, (len(preview_tiles) + columns - 1) // columns)
    preview = Image.new(
        "RGBA",
        (CREATURE_CANVAS[0] * 2 * columns, CREATURE_CANVAS[1] * 2 * rows),
        (14, 18, 28, 255),
    )
    for index, tile in enumerate(preview_tiles):
        preview.alpha_composite(
            tile,
            ((index % columns) * tile.width, (index // columns) * tile.height),
        )
    preview.save(CREATURE_PREVIEW_OUT)


def prepare_npcs() -> None:
    preview_tiles: list[Image.Image] = []

    for name, source in NPC_SOURCES.items():
        image = Image.open(source)
        transparent = strip_magenta_background(image)
        trimmed = trim_transparent(clear_magenta_fringe(transparent))
        cleaned = erase_remaining_magenta(trimmed)
        framed = pad_to_canvas(cleaned, NPC_CANVAS, margin=NPC_MARGIN)
        out_path = NPC_OUT_DIR / f"{name}.png"
        framed.save(out_path)
        preview_tiles.append(
            framed.resize((NPC_CANVAS[0] * 4, NPC_CANVAS[1] * 4), Image.Resampling.NEAREST)
        )

    preview = Image.new(
        "RGBA",
        (NPC_CANVAS[0] * 8, NPC_CANVAS[1] * 4),
        (14, 18, 28, 255),
    )
    for index, tile in enumerate(preview_tiles):
        preview.alpha_composite(tile, (index * tile.width, 0))
    preview.save(NPC_PREVIEW_OUT)


def prepare_items() -> None:
    for name, source in ITEM_SOURCES.items():
        image = Image.open(source)
        transparent = strip_magenta_background(image)
        trimmed = trim_transparent(clear_magenta_fringe(transparent))
        cleaned = erase_remaining_magenta(trimmed)
        framed = pad_to_canvas(cleaned, ITEM_CANVAS, margin=ITEM_MARGIN, align="center")
        framed.save(ITEM_OUT_DIR / f"{name}.png")


def prepare_ui() -> None:
    image = Image.open(UI_PANEL_SOURCE)
    transparent = strip_magenta_background(image)
    cleaned = erase_remaining_magenta(clear_magenta_fringe(transparent))
    trim_transparent(cleaned).save(UI_PANEL_OUT)


def prepare_grass_sheet() -> None:
    image = Image.open(GRASS_SHEET_SOURCE)
    transparent = strip_magenta_background(image)
    cleaned = erase_remaining_magenta(clear_magenta_fringe(transparent))
    components = sorted(find_components(cleaned), key=lambda box: box[4], reverse=True)[:3]
    components.sort(key=lambda box: box[0])

    frames: list[Image.Image] = []
    for box in components:
        trimmed = trim_transparent(cleaned.crop(box[:4]))
        frames.append(pad_to_canvas(trimmed, GRASS_FRAME_SIZE, margin=0))

    sheet = Image.new(
        "RGBA",
        (GRASS_FRAME_SIZE[0] * len(frames), GRASS_FRAME_SIZE[1]),
        (0, 0, 0, 0),
    )
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, (index * GRASS_FRAME_SIZE[0], 0))
    sheet.save(GRASS_SHEET_OUT)


def prepare_interiors() -> None:
    for name, source in INTERIOR_SOURCES.items():
        image = Image.open(source).convert("RGBA")
        image.resize(INTERIOR_SIZE, Image.Resampling.NEAREST).save(
            INTERIOR_OUT_DIR / f"{name}.png"
        )


def prepare_battle_background() -> None:
    image = Image.open(BATTLE_BG_SOURCE).convert("RGBA")
    image.resize(BATTLE_BG_SIZE, Image.Resampling.NEAREST).save(BATTLE_BG_OUT)


def main() -> None:
    MAP_OUT.parent.mkdir(parents=True, exist_ok=True)
    SPRITE_OUT.parent.mkdir(parents=True, exist_ok=True)
    CREATURE_OUT_DIR.mkdir(parents=True, exist_ok=True)
    NPC_OUT_DIR.mkdir(parents=True, exist_ok=True)
    ITEM_OUT_DIR.mkdir(parents=True, exist_ok=True)
    UI_OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRASS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERIOR_OUT_DIR.mkdir(parents=True, exist_ok=True)
    BATTLE_OUT_DIR.mkdir(parents=True, exist_ok=True)

    start_area = Image.open(MAP_SOURCE)
    pixelate_map(start_area).save(MAP_OUT)

    raw_sheet = Image.open(SPRITE_SOURCE)
    transparent_sheet = strip_magenta_background(raw_sheet)
    processed_sheet = build_sprite_sheet(clear_magenta_fringe(transparent_sheet))
    processed_sheet = erase_remaining_magenta(processed_sheet)
    processed_sheet.save(SPRITE_OUT)
    processed_sheet.resize(
        (processed_sheet.width * 6, processed_sheet.height * 6),
        Image.Resampling.NEAREST,
    ).save(PREVIEW_OUT)
    save_manifest()
    prepare_creatures()
    prepare_npcs()
    prepare_items()
    prepare_ui()
    prepare_grass_sheet()
    prepare_interiors()
    prepare_battle_background()

    print(f"Saved map: {MAP_OUT}")
    print(f"Saved player sheet: {SPRITE_OUT}")
    print(f"Saved manifest: {MANIFEST_OUT}")
    print(f"Saved creature sprites: {CREATURE_OUT_DIR}")
    print(f"Saved npc sprites: {NPC_OUT_DIR}")
    print(f"Saved item icons: {ITEM_OUT_DIR}")
    print(f"Saved ui panels: {UI_OUT_DIR}")
    print(f"Saved grass sprites: {GRASS_OUT_DIR}")
    print(f"Saved interiors: {INTERIOR_OUT_DIR}")
    print(f"Saved battle background: {BATTLE_BG_OUT}")


if __name__ == "__main__":
    main()
