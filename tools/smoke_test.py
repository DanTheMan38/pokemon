from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame

import main


class FixedRng:
    def random(self) -> float:
        return 0.0

    def randint(self, minimum: int, maximum: int) -> int:
        return minimum

    def uniform(self, minimum: float, maximum: float) -> float:
        return (minimum + maximum) / 2

    def choice(self, values):
        return values[0]


class FakePressed:
    def __init__(self, keys: set[int]) -> None:
        self.keys = keys

    def __getitem__(self, key: int) -> bool:
        return key in self.keys


def drain_battle_messages(game: main.Game, limit: int = 40) -> None:
    for _ in range(limit):
        if game.mode != "battle" or game.battle is None:
            return
        if game.battle.phase == "messages":
            game.advance_battle_messages()
        elif game.battle.phase == "exp_gain":
            game.finish_exp_animation()
        elif game.battle.phase == "command":
            return
        else:
            return
    raise AssertionError("Battle messages did not drain in time.")


def finish_dialogue(game: main.Game, limit: int = 20) -> None:
    for _ in range(limit):
        if game.mode != "dialogue":
            return
        game.advance_dialogue()
    raise AssertionError("Dialogue did not finish in time.")


def run_ai_mode_to_completion(mode_key: str, limit_seconds: int) -> None:
    save_path = ROOT / "tmp_verify" / f"{mode_key}_smoke_save.json"
    if save_path.exists():
        save_path.unlink()
    game = main.Game(headless=True, start_in_title=True, save_path=save_path)
    button_lookup = dict(game.mode_button_rects())
    assert game.handle_mouse_down(button_lookup[mode_key].center)
    assert game.play_mode_key == mode_key
    assert game.autoplayer is not None
    for _ in range(limit_seconds * main.FPS):
        game.update(1 / main.FPS)
        if game.quest_stage == "complete":
            assert set(main.WILD_SPECIES).issubset(game.caught_species)
            assert game.capture_charm
            if save_path.exists():
                save_path.unlink()
            return
    raise AssertionError(f"{mode_key} did not complete the game in time.")


def assert_creature_art_is_framed() -> None:
    starter_min_height = 116
    for species in main.STARTER_SPECIES:
        for view in ("front", "back"):
            surface = pygame.image.load(ROOT / "assets" / "creatures" / f"{species.lower()}_{view}.png").convert_alpha()
            bounds = surface.get_bounding_rect()
            margins = (
                bounds.left,
                bounds.top,
                surface.get_width() - bounds.right,
                surface.get_height() - bounds.bottom,
            )
            assert bounds.height >= starter_min_height, f"{species} {view} sprite looks cropped"
            assert min(margins) >= 8, f"{species} {view} sprite is too close to the canvas edge"


def main_test() -> None:
    save_path = ROOT / "tmp_verify" / "smoke_save.json"
    save_path.parent.mkdir(exist_ok=True)
    if save_path.exists():
        save_path.unlink()

    pygame.display.set_mode((1, 1))
    assert_creature_art_is_framed()

    game = main.Game(headless=True, rng=FixedRng(), start_in_title=False, save_path=save_path)
    assert game.mode == "world"
    assert game.quest_stage == "meet_professor"
    assert game.scene_key == "meadow"
    assert game.type_multiplier("Water", "Fire") > 1.0
    assert game.type_multiplier("Fire", "Water") < 1.0

    game.handle_keydown(pygame.K_h)
    assert game.mode == "help"
    game.handle_keydown(pygame.K_h)
    assert game.mode == "world"
    game.handle_keydown(pygame.K_m)
    assert game.audio.music_muted
    game.handle_keydown(pygame.K_m)
    assert not game.audio.music_muted
    game.handle_keydown(pygame.K_p)
    assert game.paused
    paused_position = game.player.position.copy()
    game.update(1.0)
    assert game.player.position == paused_position
    game.handle_keydown(pygame.K_p)
    assert not game.paused

    game.enter_scene("cedar_lab", main.scale_point((730, 848), main.scene_scale("cedar_lab")), direction="right")
    assert game.scene_key == "cedar_lab"
    assert game.find_prompt() == "E: Talk Professor Cedar"

    game.handle_world_interaction()
    finish_dialogue(game)
    assert game.quest_stage == "choose_starter"

    game.enter_scene("cedar_lab", main.scale_point((470, 730), main.scene_scale("cedar_lab")), direction="up")
    assert game.find_prompt() == "E: Choose Leafawn"
    game.handle_world_interaction()
    finish_dialogue(game)
    lead = game.lead_creature()
    assert lead is not None
    assert lead.name == "Leafawn"
    assert lead.level == 1
    assert game.inventory["capture_orb"] == 3
    assert game.quest_stage == "survey_grass"
    assert save_path.exists()

    loaded = main.Game(headless=True, rng=FixedRng(), start_in_title=True, save_path=save_path)
    assert loaded.has_save_file()
    assert loaded.load_game()
    assert loaded.mode == "world"
    assert loaded.quest_stage == "survey_grass"
    assert loaded.lead_creature() is not None
    assert loaded.lead_creature().name == "Leafawn"
    assert loaded.lead_creature().level == 1
    assert "survey" in (loaded.save_summary_text() or "").lower()

    legacy_save_path = ROOT / "tmp_verify" / "legacy_starter_save.json"
    legacy_save_path.write_text(
        """{
  "version": 1,
  "scene_key": "meadow",
  "player": {
    "x": 625.0,
    "y": 645.0,
    "direction": "down"
  },
  "quest_stage": "survey_grass",
  "party": [
    {
      "species": "Flarekit",
      "level": 5,
      "max_hp": 44,
      "hp": 44,
      "exp": 0,
      "guarding": false
    }
  ],
  "lead_index": 0,
  "journal_index": 0,
  "inventory": {
    "capture_orb": 3,
    "berry": 1
  },
  "seen_species": [
    "Flarekit"
  ],
  "caught_species": [],
  "sprint_unlocked": false,
  "capture_charm": false,
  "house_treasure_claimed": false,
  "collected_pickups": []
}""",
        encoding="utf-8",
    )
    legacy_game = main.Game(headless=True, rng=FixedRng(), start_in_title=True, save_path=legacy_save_path)
    assert "Lv.1" in (legacy_game.save_summary_text() or "")
    assert legacy_game.load_game()
    assert legacy_game.lead_creature() is not None
    assert legacy_game.lead_creature().level == 1

    game.enter_scene("mira_house", main.scale_point((640, 1110), main.scene_scale("mira_house")), direction="up")
    assert game.find_prompt() is None
    game.enter_scene("mira_house", main.scale_point((960, 760), main.scene_scale("mira_house")), direction="up")
    assert game.find_prompt() == "E: Open Chest"
    game.handle_world_interaction()
    finish_dialogue(game)
    assert game.capture_charm
    assert game.house_treasure_claimed
    assert game.inventory["capture_orb"] == 5
    assert game.inventory["berry"] == 3
    lead.hp = max(1, lead.hp - 9)
    game.inspect_prop("guest_bed")
    finish_dialogue(game)
    assert lead.hp == lead.max_hp

    game.enter_scene("meadow", (625, 645), direction="down")
    lead.hp = max(1, lead.hp - 7)
    game.heal_party()
    assert lead.hp == lead.max_hp

    game.start_battle_for_test("Mothleaf", level=3)
    assert game.mode == "battle"
    drain_battle_messages(game)
    assert game.battle is not None
    assert game.battle.phase == "command"

    game.battle.enemy.hp = 1
    game.use_capture_orb()

    for _ in range(60):
        if game.mode == "world":
            break
        if game.battle is not None:
            if game.battle.phase == "messages":
                game.advance_battle_messages()
            elif game.battle.phase == "exp_gain":
                game.finish_exp_animation()
    else:
        raise AssertionError("Battle did not return to the world.")

    assert game.quest_stage == "report_back"
    assert "Mothleaf" in game.caught_species
    assert any(creature.species.key == "Mothleaf" for creature in game.party)

    game.start_battle_for_test("Sparrook", level=4)
    assert game.mode == "battle"
    drain_battle_messages(game)
    assert game.battle is not None
    switch_index = game.battle_command_labels().index("Switch")
    game.perform_battle_command(switch_index)
    assert game.battle.phase == "party_select"
    assert game.party[game.battle.party_index].species.key == "Mothleaf"
    game.handle_battle_input(pygame.K_e)
    assert game.lead_creature() is not None
    assert game.lead_creature().species.key == "Mothleaf"
    while game.battle is not None and game.battle.phase == "messages":
        game.advance_battle_messages()
    if game.battle is not None and game.battle.phase == "exp_gain":
        game.finish_exp_animation()
    if game.mode == "battle":
        game.end_battle()

    game.enter_scene("cedar_lab", main.scale_point((730, 848), main.scene_scale("cedar_lab")), direction="right")
    assert game.find_prompt() == "E: Talk Professor Cedar"
    game.handle_world_interaction()
    finish_dialogue(game)
    assert game.quest_stage == "free_roam"
    assert game.sprint_unlocked

    game.enter_scene("meadow", (625, 645), direction="down")
    start = game.player.position.copy()
    pressed = FakePressed({pygame.K_d, pygame.K_LSHIFT})
    speed = game.current_speed(pressed)
    game.player.update(0.2, pressed, game.current_scene().walk_bounds, game.dynamic_colliders(), speed)
    assert game.player.position.x > start.x

    game.caught_species.update({"Mothleaf", "Bubbun", "Sparrook"})
    game.quest_stage = "free_roam"
    game.enter_scene("cedar_lab", main.scale_point((730, 848), main.scene_scale("cedar_lab")), direction="right")
    game.handle_world_interaction()
    finish_dialogue(game)
    assert game.mode == "ending"
    while game.mode == "ending":
        game.handle_keydown(pygame.K_e)
    assert game.mode == "world"
    assert game.quest_stage == "complete"
    game.enter_scene("cedar_lab", main.scale_point((690, 212), main.scene_scale("cedar_lab")), direction="up")
    assert game.find_prompt() == "E: Read Final Report"

    run_ai_mode_to_completion("ppo_ultimate", 240)
    run_ai_mode_to_completion("ppo_trained", 330)

    pygame.quit()
    if save_path.exists():
        save_path.unlink()
    if legacy_save_path.exists():
        legacy_save_path.unlink()
    print("smoke test passed")


if __name__ == "__main__":
    main_test()
