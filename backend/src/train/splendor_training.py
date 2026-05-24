from __future__ import annotations

import argparse
import json
import random
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn.functional as F
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.tensorboard import SummaryWriter

from .splendor_features import OBS_DIM
from .splendor_network import SplendorPVNet, load_checkpoint, save_checkpoint
from .splendor_selfplay import run_selfplay_batch


@dataclass
class TrainingConfig:
    total_steps: int = 200
    selfplay_every: int = 50
    selfplay_games: int = 2
    mcts_sims: int = 25
    max_moves: int = 150
    temperature_moves: int = 16
    heuristic_mix_rate: float = 0.0
    batch_size: int = 32
    lr: float = 1e-3
    weight_decay: float = 1e-4
    buffer_size: int = 5000
    checkpoint_every: int = 100
    checkpoint_dir: str = "artifacts/checkpoints"
    tensorboard_dir: str = "artifacts/tensorboard"
    device: str = "cuda"
    seed: int = 42
    resume: Optional[str] = None
    hidden_dim: int = 256
    num_blocks: int = 2


def _build_network(cfg: TrainingConfig, device: str) -> SplendorPVNet:
    network = SplendorPVNet(
        obs_dim=OBS_DIM,
        hidden_dim=cfg.hidden_dim,
        num_blocks=cfg.num_blocks,
    )
    network.to(device)
    return network


def _ckpt_path(run_dir: Path, step: int) -> Path:
    return run_dir / f"step_{step:07d}.pt"


def _select_device(requested: str) -> str:
    if requested == "cuda" and not torch.cuda.is_available():
        print("[WARN] CUDA requested but unavailable, falling back to CPU")
        return "cpu"
    return requested


def run_training(cfg: TrainingConfig) -> dict:
    device = _select_device(cfg.device)
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)
    if device.startswith("cuda"):
        torch.cuda.manual_seed_all(cfg.seed)

    base_dir = Path(__file__).resolve().parents[3]
    ckpt_dir = (base_dir / cfg.checkpoint_dir).resolve()
    tb_dir = (base_dir / cfg.tensorboard_dir).resolve()
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    tb_dir.mkdir(parents=True, exist_ok=True)

    network = _build_network(cfg, device)
    start_step = 0
    if cfg.resume:
        network, metadata = load_checkpoint(Path(cfg.resume), device=device)
        start_step = int(metadata.get("step", 0))
        print(f"[resume] loaded {cfg.resume} at step {start_step}")

    optimizer = torch.optim.Adam(network.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=max(1, cfg.total_steps), eta_min=cfg.lr * 0.1)
    writer = SummaryWriter(str(tb_dir))

    replay: deque = deque(maxlen=cfg.buffer_size)
    selfplay_seed_counter = cfg.seed * 1000
    selfplay_stats = {"games": 0, "samples": 0, "wall_seconds": 0.0}

    metrics_summary = {"steps": 0, "policy_loss": 0.0, "value_loss": 0.0, "loss": 0.0}

    for step in range(start_step, cfg.total_steps):
        if step % cfg.selfplay_every == 0:
            network.eval()
            t0 = time.time()
            results = run_selfplay_batch(
                network=network,
                num_games=cfg.selfplay_games,
                mcts_iterations=cfg.mcts_sims,
                max_moves=cfg.max_moves,
                temperature_moves=cfg.temperature_moves,
                base_seed=selfplay_seed_counter,
                device=device,
                heuristic_mix_rate=cfg.heuristic_mix_rate,
            )
            sp_seconds = time.time() - t0
            selfplay_seed_counter += cfg.selfplay_games
            selfplay_stats["games"] += len(results)
            selfplay_stats["wall_seconds"] += sp_seconds

            new_samples = 0
            game_lengths = []
            game_winners_known = 0
            truncated = 0
            for result in results:
                game_lengths.append(result.move_count)
                if result.winner is not None:
                    game_winners_known += 1
                if result.reached_max_turns:
                    truncated += 1
                for sample in result.samples:
                    replay.append((sample.obs, sample.pi, sample.value))
                    new_samples += 1
            selfplay_stats["samples"] += new_samples

            avg_len = float(np.mean(game_lengths)) if game_lengths else 0.0
            truncate_rate = truncated / max(1, len(results))
            writer.add_scalar("selfplay/avg_game_length", avg_len, step)
            writer.add_scalar("selfplay/games_with_winner", game_winners_known, step)
            writer.add_scalar("selfplay/truncate_rate", truncate_rate, step)
            writer.add_scalar("selfplay/new_samples", new_samples, step)
            writer.add_scalar("selfplay/replay_size", len(replay), step)
            writer.add_scalar("selfplay/wall_seconds_per_batch", sp_seconds, step)
            print(
                f"[step {step:6d}] self-play {len(results)} games, "
                f"avg_len={avg_len:.1f}, winner={game_winners_known}/{len(results)}, "
                f"truncate={truncate_rate:.0%}, replay={len(replay)}, took {sp_seconds:.1f}s"
            )

        if len(replay) < cfg.batch_size:
            continue

        network.train()
        batch = random.sample(replay, cfg.batch_size)
        obs_np = np.stack([b[0] for b in batch])
        pi_np = np.stack([b[1] for b in batch])
        value_np = np.stack([b[2] for b in batch])

        obs_t = torch.from_numpy(obs_np).to(device)
        pi_t = torch.from_numpy(pi_np).to(device)
        value_t = torch.from_numpy(value_np).to(device)

        optimizer.zero_grad()
        logits, value_pred = network(obs_t)
        log_probs = F.log_softmax(logits, dim=-1)
        policy_loss = -(pi_t * log_probs).sum(dim=-1).mean()
        value_loss = F.mse_loss(value_pred, value_t)
        loss = policy_loss + value_loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(network.parameters(), max_norm=5.0)
        optimizer.step()
        scheduler.step()

        with torch.no_grad():
            entropy = -(torch.exp(log_probs) * log_probs).sum(dim=-1).mean().item()

        writer.add_scalar("train/loss", loss.item(), step)
        writer.add_scalar("train/policy_loss", policy_loss.item(), step)
        writer.add_scalar("train/value_loss", value_loss.item(), step)
        writer.add_scalar("train/policy_entropy", entropy, step)
        writer.add_scalar("train/lr", optimizer.param_groups[0]["lr"], step)

        metrics_summary = {
            "steps": step + 1,
            "policy_loss": policy_loss.item(),
            "value_loss": value_loss.item(),
            "loss": loss.item(),
            "entropy": entropy,
        }

        if (step + 1) % cfg.checkpoint_every == 0:
            ckpt_path = _ckpt_path(ckpt_dir, step + 1)
            save_checkpoint(
                network,
                ckpt_path,
                metadata={"step": step + 1, "config": asdict(cfg), "metrics": metrics_summary},
            )
            latest_path = ckpt_dir / "latest.pt"
            save_checkpoint(
                network,
                latest_path,
                metadata={"step": step + 1, "config": asdict(cfg), "metrics": metrics_summary},
            )
            print(f"[step {step + 1:6d}] saved checkpoint → {ckpt_path.name} + latest.pt")

    writer.close()
    return {
        "final_step": metrics_summary["steps"],
        "metrics": metrics_summary,
        "selfplay": selfplay_stats,
        "checkpoint_dir": str(ckpt_dir),
        "tensorboard_dir": str(tb_dir),
    }


def _parse_args(argv: list[str] | None = None) -> TrainingConfig:
    parser = argparse.ArgumentParser(description="Train Splendor AlphaZero")
    cfg = TrainingConfig()
    parser.add_argument("--total-steps", type=int, default=cfg.total_steps)
    parser.add_argument("--selfplay-every", type=int, default=cfg.selfplay_every)
    parser.add_argument("--selfplay-games", type=int, default=cfg.selfplay_games)
    parser.add_argument("--mcts-sims", type=int, default=cfg.mcts_sims)
    parser.add_argument("--max-moves", type=int, default=cfg.max_moves)
    parser.add_argument("--temperature-moves", type=int, default=cfg.temperature_moves)
    parser.add_argument("--heuristic-mix-rate", type=float, default=cfg.heuristic_mix_rate,
                        help="0.0=pure self-play, 0.5=half games mix heuristic opponents (v3 anchor)")
    parser.add_argument("--batch-size", type=int, default=cfg.batch_size)
    parser.add_argument("--lr", type=float, default=cfg.lr)
    parser.add_argument("--weight-decay", type=float, default=cfg.weight_decay)
    parser.add_argument("--buffer-size", type=int, default=cfg.buffer_size)
    parser.add_argument("--checkpoint-every", type=int, default=cfg.checkpoint_every)
    parser.add_argument("--checkpoint-dir", type=str, default=cfg.checkpoint_dir)
    parser.add_argument("--tensorboard-dir", type=str, default=cfg.tensorboard_dir)
    parser.add_argument("--device", type=str, default=cfg.device)
    parser.add_argument("--seed", type=int, default=cfg.seed)
    parser.add_argument("--resume", type=str, default=cfg.resume)
    parser.add_argument("--hidden-dim", type=int, default=cfg.hidden_dim)
    parser.add_argument("--num-blocks", type=int, default=cfg.num_blocks)
    args = parser.parse_args(argv)
    return TrainingConfig(
        total_steps=args.total_steps,
        selfplay_every=args.selfplay_every,
        selfplay_games=args.selfplay_games,
        mcts_sims=args.mcts_sims,
        max_moves=args.max_moves,
        temperature_moves=args.temperature_moves,
        heuristic_mix_rate=args.heuristic_mix_rate,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        buffer_size=args.buffer_size,
        checkpoint_every=args.checkpoint_every,
        checkpoint_dir=args.checkpoint_dir,
        tensorboard_dir=args.tensorboard_dir,
        device=args.device,
        seed=args.seed,
        resume=args.resume,
        hidden_dim=args.hidden_dim,
        num_blocks=args.num_blocks,
    )


def main(argv: list[str] | None = None) -> None:
    cfg = _parse_args(argv)
    result = run_training(cfg)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
