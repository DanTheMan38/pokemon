from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import json
import math
import random

ROOT = Path(__file__).resolve().parents[1]
PPO_DIR = ROOT / "assets" / "ppo"

ACTIONS = ("up", "down", "left", "right", "interact", "fight", "orb", "berry", "run", "wait")
WILD_SPECIES = ("Mothleaf", "Bubbun", "Sparrook")
QUESTS = ("meet_professor", "choose_starter", "survey_grass", "report_back", "free_roam", "ending_ready", "complete")

MEADOW_GRAPH = {
    "start": {"up": "lab_door", "left": "west_grass", "right": "house_door", "down": "south_grass"},
    "lab_door": {"down": "start", "left": "west_grass", "right": "berry_patch"},
    "berry_patch": {"left": "lab_door", "down": "start"},
    "west_grass": {"right": "start", "up": "lab_door"},
    "house_door": {"left": "start", "down": "east_grass", "up": "orb_pickup"},
    "orb_pickup": {"down": "house_door", "left": "start"},
    "south_grass": {"up": "start", "right": "orb_pickup"},
    "east_grass": {"up": "house_door", "left": "start"},
}
LAB_GRAPH = {
    "entry": {"up": "professor", "left": "starter", "down": "exit"},
    "professor": {"down": "entry", "left": "starter"},
    "starter": {"right": "professor", "down": "entry"},
    "exit": {"up": "entry"},
}
HOUSE_GRAPH = {
    "entry": {"up": "chest", "down": "exit"},
    "chest": {"down": "entry"},
    "exit": {"up": "entry"},
}


@dataclass
class StepResult:
    state: tuple
    reward: float
    done: bool


class MeadowPPOEnv:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)
        self.reset()

    def reset(self) -> tuple:
        self.scene = "meadow"
        self.node = "start"
        self.quest = "meet_professor"
        self.has_starter = False
        self.charm = False
        self.caught: set[str] = set()
        self.orbs = 0
        self.berries = 0
        self.in_battle = False
        self.enemy = ""
        self.enemy_hp = 0
        self.player_hp = 6
        self.steps = 0
        return self.state()

    def state(self) -> tuple:
        caught_mask = tuple(int(species in self.caught) for species in WILD_SPECIES)
        if self.in_battle:
            return (
                "battle",
                self.quest,
                self.enemy,
                min(3, self.enemy_hp),
                min(3, self.player_hp // 2),
                min(3, self.orbs),
                min(2, self.berries),
                int(self.charm),
                caught_mask,
            )
        return (
            "world",
            self.scene,
            self.node,
            self.quest,
            int(self.has_starter),
            int(self.charm),
            caught_mask,
            min(3, self.orbs),
            min(2, self.berries),
        )

    def graph(self) -> dict[str, dict[str, str]]:
        if self.scene == "cedar_lab":
            return LAB_GRAPH
        if self.scene == "mira_house":
            return HOUSE_GRAPH
        return MEADOW_GRAPH

    def step(self, action_index: int) -> StepResult:
        action = ACTIONS[action_index]
        self.steps += 1
        reward = -0.015

        if self.steps >= 420:
            return StepResult(self.state(), reward - 5.0, True)

        before_quest = self.quest
        before_caught = set(self.caught)
        before_charm = self.charm
        before_progress = self.route_progress_score()

        if self.in_battle:
            reward += self.step_battle(action)
        elif action in {"up", "down", "left", "right"}:
            reward += self.step_move(action)
        elif action == "interact":
            reward += self.step_interact()
        elif action in {"fight", "orb", "berry", "run"}:
            reward -= 0.04
        else:
            reward -= 0.01

        if self.quest != before_quest:
            reward += {
                "choose_starter": 2.0,
                "survey_grass": 3.0,
                "report_back": 5.0,
                "free_roam": 5.0,
                "ending_ready": 9.0,
                "complete": 30.0,
            }.get(self.quest, 0.0)
        for species in self.caught - before_caught:
            reward += 8.0
        if self.charm and not before_charm:
            reward += 7.0
        after_progress = self.route_progress_score()
        if after_progress > before_progress:
            reward += (after_progress - before_progress) * 0.9

        done = self.quest == "complete"
        return StepResult(self.state(), reward, done)

    def route_progress_score(self) -> float:
        if self.quest not in {"report_back", "ending_ready"}:
            return 0.0
        score = 0.0
        if self.scene == "meadow":
            score = {
                "house_door": 0.1,
                "east_grass": 0.1,
                "south_grass": 0.1,
                "west_grass": 0.2,
                "orb_pickup": 0.2,
                "start": 0.6,
                "lab_door": 1.1,
            }.get(self.node, 0.0)
        elif self.scene == "cedar_lab":
            score = {
                "entry": 1.6,
                "starter": 1.8,
                "exit": 1.4,
                "professor": 2.5,
            }.get(self.node, 1.5)
        if self.quest == "ending_ready":
            score *= 1.35
        return score

    def step_move(self, action: str) -> float:
        graph = self.graph()
        if action not in graph.get(self.node, {}):
            return -0.08

        self.node = graph[self.node][action]
        if self.scene == "meadow" and self.node == "lab_door" and action == "up":
            self.scene = "cedar_lab"
            self.node = "entry"
            return 0.15
        if self.scene == "meadow" and self.node == "house_door" and action == "right":
            self.scene = "mira_house"
            self.node = "entry"
            return 0.15
        if self.scene == "cedar_lab" and self.node == "exit":
            self.scene = "meadow"
            self.node = "lab_door"
            return 0.1
        if self.scene == "mira_house" and self.node == "exit":
            self.scene = "meadow"
            self.node = "house_door"
            return 0.1

        if self.scene == "meadow" and self.node == "orb_pickup" and self.orbs < 2 and self.quest not in {"ending_ready", "complete"}:
            self.orbs += 2
            return 0.6
        if self.scene == "meadow" and self.node == "berry_patch" and self.berries < 2 and self.quest not in {"ending_ready", "complete"}:
            self.berries += 2
            return 0.35
        if self.scene == "meadow" and self.node in {"west_grass", "south_grass", "east_grass"} and self.has_starter:
            self.start_battle_for_node()
            return 0.25
        return 0.0

    def step_interact(self) -> float:
        if self.scene == "cedar_lab" and self.node == "professor":
            if self.quest == "meet_professor":
                self.quest = "choose_starter"
                return 1.5
            if self.quest == "report_back":
                self.quest = "free_roam"
                self.orbs += 2
                self.berries += 2
                self.player_hp = 6
                return 2.0
            if self.quest == "ending_ready":
                self.quest = "complete"
                return 10.0
        if self.scene == "cedar_lab" and self.node == "starter" and self.quest == "choose_starter":
            self.has_starter = True
            self.quest = "survey_grass"
            self.orbs += 3
            self.berries += 1
            self.player_hp = 6
            return 2.5
        if self.scene == "mira_house" and self.node == "chest" and self.quest == "free_roam" and not self.charm:
            self.charm = True
            self.orbs += 2
            self.berries += 2
            if set(WILD_SPECIES).issubset(self.caught):
                self.quest = "ending_ready"
            return 3.0
        return -0.08

    def start_battle_for_node(self) -> None:
        if self.quest == "survey_grass":
            self.enemy = "Mothleaf"
        elif self.node == "south_grass":
            self.enemy = "Bubbun"
        elif self.node == "east_grass":
            self.enemy = "Sparrook"
        else:
            self.enemy = "Mothleaf"
        self.enemy_hp = 3 if self.enemy != "Sparrook" else 4
        self.in_battle = True

    def step_battle(self, action: str) -> float:
        if action == "run":
            if self.quest == "survey_grass":
                return -0.8
            self.in_battle = False
            return -0.12
        if action == "berry":
            if self.berries <= 0 or self.player_hp >= 6:
                return -0.12
            self.berries -= 1
            self.player_hp = min(6, self.player_hp + 3)
            self.enemy_attack()
            return 0.15
        if action == "fight":
            needed_capture = self.quest == "free_roam" and self.enemy not in self.caught
            self.enemy_hp -= 1
            reward = 0.2
            if self.enemy_hp <= 0:
                self.end_battle(won=True, caught=False)
                return reward + (-1.2 if needed_capture else 0.9)
            self.enemy_attack()
            return reward
        if action == "orb":
            if self.orbs <= 0:
                return -0.3
            self.orbs -= 1
            hp_bonus = (4 - max(0, self.enemy_hp)) * 0.18
            charm_bonus = 0.12 if self.charm else 0.0
            rate = min(0.9, 0.28 + hp_bonus + charm_bonus)
            if self.rng.random() < rate:
                self.end_battle(won=True, caught=True)
                return 2.0
            self.enemy_attack()
            return -0.2 if self.enemy_hp >= 3 else -0.05
        return -0.05

    def enemy_attack(self) -> None:
        self.player_hp -= 1
        if self.player_hp <= 0:
            self.in_battle = False
            self.scene = "meadow"
            self.node = "house_door"
            self.player_hp = 6

    def end_battle(self, *, won: bool, caught: bool) -> None:
        enemy = self.enemy
        self.in_battle = False
        self.enemy = ""
        self.enemy_hp = 0
        self.player_hp = min(6, self.player_hp + 1)
        if caught:
            self.caught.add(enemy)
        if self.quest == "survey_grass" and enemy == "Mothleaf":
            self.quest = "report_back"
        if self.quest == "free_roam" and self.charm and set(WILD_SPECIES).issubset(self.caught):
            self.quest = "ending_ready"


class TabularPPO:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)
        self.logits: dict[str, list[float]] = defaultdict(lambda: [0.0] * len(ACTIONS))
        self.values: dict[str, float] = defaultdict(float)

    @staticmethod
    def state_key(state: tuple) -> str:
        return json.dumps(state, separators=(",", ":"))

    def probs(self, key: str) -> list[float]:
        logits = self.logits[key]
        top = max(logits)
        exps = [math.exp(value - top) for value in logits]
        total = sum(exps)
        return [value / total for value in exps]

    def sample_action(self, state: tuple) -> tuple[int, float]:
        key = self.state_key(state)
        probs = self.probs(key)
        roll = self.rng.random()
        acc = 0.0
        for index, prob in enumerate(probs):
            acc += prob
            if roll <= acc:
                return index, prob
        return len(probs) - 1, probs[-1]

    def update(self, samples: list[dict], *, lr: float = 0.032, value_lr: float = 0.08, clip: float = 0.2) -> None:
        if not samples:
            return
        adv_mean = sum(sample["adv"] for sample in samples) / len(samples)
        adv_var = sum((sample["adv"] - adv_mean) ** 2 for sample in samples) / len(samples)
        adv_std = math.sqrt(max(1e-8, adv_var))
        for _ in range(3):
            self.rng.shuffle(samples)
            for sample in samples:
                key = sample["key"]
                action = sample["action"]
                old_prob = max(1e-8, sample["old_prob"])
                advantage = (sample["adv"] - adv_mean) / adv_std
                probs = self.probs(key)
                ratio = probs[action] / old_prob
                if (advantage > 0 and ratio > 1 + clip) or (advantage < 0 and ratio < 1 - clip):
                    policy_scale = 0.0
                else:
                    policy_scale = advantage * ratio
                logits = self.logits[key]
                for index in range(len(ACTIONS)):
                    grad = (1.0 if index == action else 0.0) - probs[index]
                    logits[index] += lr * policy_scale * grad
                    logits[index] += lr * 0.003 * (-math.log(max(1e-8, probs[index])) - 1.0)
                value_error = sample["return"] - self.values[key]
                self.values[key] += value_lr * value_error

    def export_policy(self, path: Path, *, label: str, episodes: int, updates: int, seed: int) -> None:
        policy = {
            key: self.probs(key)
            for key in self.logits
        }
        path.write_text(
            json.dumps(
                {
                    "algorithm": "tabular_ppo",
                    "label": label,
                    "episodes": episodes,
                    "updates": updates,
                    "seed": seed,
                    "actions": ACTIONS,
                    "policy": policy,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def collect_rollout(model: TabularPPO, env: MeadowPPOEnv, steps: int, gamma: float = 0.96, lam: float = 0.9) -> tuple[list[dict], int, int]:
    samples: list[dict] = []
    episodes = 0
    wins = 0
    state = env.state()
    for _ in range(steps):
        key = model.state_key(state)
        action, old_prob = model.sample_action(state)
        result = env.step(action)
        samples.append(
            {
                "key": key,
                "action": action,
                "old_prob": old_prob,
                "reward": result.reward,
                "done": result.done,
                "value": model.values[key],
                "next_key": model.state_key(result.state),
            }
        )
        state = result.state
        if result.done:
            if env.quest == "complete":
                wins += 1
        if result.done or env.steps >= 420:
            episodes += 1
            state = env.reset()

    gae = 0.0
    for index in range(len(samples) - 1, -1, -1):
        sample = samples[index]
        next_value = 0.0 if sample["done"] else model.values[sample["next_key"]]
        delta = sample["reward"] + gamma * next_value - sample["value"]
        gae = delta + gamma * lam * gae * (0.0 if sample["done"] else 1.0)
        sample["adv"] = gae
        sample["return"] = gae + sample["value"]
    return samples, episodes, wins


def evaluate(model: TabularPPO, episodes: int = 100) -> float:
    wins = 0
    for seed in range(episodes):
        env = MeadowPPOEnv(seed=10_000 + seed)
        state = env.state()
        for _ in range(420):
            key = model.state_key(state)
            probs = model.probs(key)
            action = max(range(len(probs)), key=lambda index: probs[index])
            result = env.step(action)
            state = result.state
            if result.done:
                if env.quest == "complete":
                    wins += 1
                break
    return wins / episodes


def train() -> None:
    PPO_DIR.mkdir(parents=True, exist_ok=True)
    seed = 20260426
    env = MeadowPPOEnv(seed=seed)
    model = TabularPPO(seed=seed)
    total_episodes = 0
    total_updates = 0
    model.export_policy(
        PPO_DIR / "ppo_tiny.json",
        label="Tiny PPO",
        episodes=total_episodes,
        updates=total_updates,
        seed=seed,
    )
    print(f"saved ppo_tiny.json: episodes={total_episodes} updates={total_updates} eval_win_rate={evaluate(model, episodes=60):.2f}")

    checkpoints = [
        ("ppo_mid.json", "PPO Mid", 4_000),
        ("ppo_max.json", "PPO Max", 16_000),
    ]
    next_checkpoint = 0
    while next_checkpoint < len(checkpoints):
        samples, episodes, wins = collect_rollout(model, env, 512)
        model.update(samples)
        total_episodes += episodes
        total_updates += 1
        target_name, label, target_episodes = checkpoints[next_checkpoint]
        if total_episodes >= target_episodes:
            win_rate = evaluate(model, episodes=60)
            model.export_policy(
                PPO_DIR / target_name,
                label=label,
                episodes=total_episodes,
                updates=total_updates,
                seed=seed,
            )
            print(f"saved {target_name}: episodes={total_episodes} updates={total_updates} eval_win_rate={win_rate:.2f}")
            next_checkpoint += 1


if __name__ == "__main__":
    train()
