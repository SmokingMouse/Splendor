"""Supervised pre-training of SplendorPVNet from heuristic data.

Loads (obs, pi, value) tuples from `--data`, trains policy + value heads to
mimic the heuristic. Output checkpoint can be `--resume`d by the main RL
training script for AlphaZero fine-tuning.

Usage:
    uv run python -m scripts.pretrain_warmstart \
        --data artifacts/warmstart_data.npz \
        --epochs 100 --batch-size 128 --lr 1e-3 \
        --output artifacts/checkpoints/warmstart.pt
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from src.train.splendor_action_space import ACTION_SPACE_SIZE
from src.train.splendor_features import NUM_PLAYERS, OBS_DIM
from src.train.splendor_network import SplendorPVNet, save_checkpoint


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="artifacts/warmstart_data.npz")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--num-blocks", type=int, default=4)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--output", type=str, default="artifacts/checkpoints/warmstart.pt")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-split", type=float, default=0.1)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    print(f"Loading {args.data} ...")
    payload = np.load(args.data)
    obs_all = payload["obs"].astype(np.float32)
    pi_all = payload["pi"].astype(np.float32)
    value_all = payload["value"].astype(np.float32)
    n_total = len(obs_all)
    print(f"  loaded: obs={obs_all.shape}, pi={pi_all.shape}, value={value_all.shape}")

    # Shuffle + split
    rng = np.random.default_rng(args.seed)
    perm = rng.permutation(n_total)
    obs_all, pi_all, value_all = obs_all[perm], pi_all[perm], value_all[perm]

    n_val = int(n_total * args.val_split)
    obs_train, obs_val = obs_all[n_val:], obs_all[:n_val]
    pi_train, pi_val = pi_all[n_val:], pi_all[:n_val]
    value_train, value_val = value_all[n_val:], value_all[:n_val]
    print(f"  train: {len(obs_train)}  val: {len(obs_val)}")

    device = args.device
    net = SplendorPVNet(
        obs_dim=OBS_DIM,
        action_dim=ACTION_SPACE_SIZE,
        hidden_dim=args.hidden_dim,
        num_blocks=args.num_blocks,
        value_dim=NUM_PLAYERS,
    ).to(device)
    optimizer = torch.optim.Adam(net.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    n_train = len(obs_train)

    def eval_val() -> tuple[float, float, float]:
        net.eval()
        with torch.no_grad():
            obs_t = torch.from_numpy(obs_val).to(device)
            pi_t = torch.from_numpy(pi_val).to(device)
            value_t = torch.from_numpy(value_val).to(device)
            logits, value_pred = net(obs_t)
            log_probs = F.log_softmax(logits, dim=-1)
            policy_loss = -(pi_t * log_probs).sum(dim=-1).mean().item()
            value_loss = F.mse_loss(value_pred, value_t).item()
            # accuracy = fraction where argmax matches heuristic choice
            preds = logits.argmax(dim=-1)
            targets = pi_t.argmax(dim=-1)
            acc = (preds == targets).float().mean().item()
        return policy_loss, value_loss, acc

    print(f"\nStarting SL pretraining: {args.epochs} epochs, lr={args.lr}")
    t0 = time.time()

    for epoch in range(args.epochs):
        net.train()
        epoch_perm = rng.permutation(n_train)
        epoch_p_loss = 0.0
        epoch_v_loss = 0.0
        n_batches = 0

        for start in range(0, n_train, args.batch_size):
            batch_idx = epoch_perm[start : start + args.batch_size]
            obs_b = torch.from_numpy(obs_train[batch_idx]).to(device)
            pi_b = torch.from_numpy(pi_train[batch_idx]).to(device)
            value_b = torch.from_numpy(value_train[batch_idx]).to(device)

            optimizer.zero_grad()
            logits, value_pred = net(obs_b)
            log_probs = F.log_softmax(logits, dim=-1)
            policy_loss = -(pi_b * log_probs).sum(dim=-1).mean()
            value_loss = F.mse_loss(value_pred, value_b)
            loss = policy_loss + value_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), max_norm=5.0)
            optimizer.step()

            epoch_p_loss += policy_loss.item()
            epoch_v_loss += value_loss.item()
            n_batches += 1

        if (epoch + 1) % 10 == 0 or epoch == 0:
            val_p, val_v, val_acc = eval_val()
            print(
                f"  epoch {epoch + 1:3d}/{args.epochs}  "
                f"train_p={epoch_p_loss / n_batches:.4f} train_v={epoch_v_loss / n_batches:.4f}  "
                f"val_p={val_p:.4f} val_v={val_v:.4f} val_acc={val_acc:.2%}"
            )

    elapsed = time.time() - t0
    final_p, final_v, final_acc = eval_val()
    print(f"\n=== Pretraining done in {elapsed:.1f}s ===")
    print(f"  Final: val policy_loss={final_p:.4f}  val value_loss={final_v:.4f}  val accuracy={final_acc:.2%}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_checkpoint(
        net,
        out_path,
        metadata={
            "step": 0,
            "warmstart": True,
            "epochs": args.epochs,
            "val_policy_loss": final_p,
            "val_value_loss": final_v,
            "val_acc": final_acc,
        },
    )
    print(f"  saved to {out_path}")


if __name__ == "__main__":
    main()
