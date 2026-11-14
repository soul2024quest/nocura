"""
NOCURA - Microgravity Solid Combustion Hazard Prediction Engine
ML Training Pipeline & Edge Artifact Exporter (NASA BASS-II PMMA Dataset)
"""

import os
import json
import math
import random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score, confusion_matrix

# Ensure deterministic reproducibility
MODEL_SEED = 42
SPLIT_SEED = 29
random.seed(MODEL_SEED)
np.random.seed(MODEL_SEED)
torch.manual_seed(MODEL_SEED)


class CombustionResNet(nn.Module):
    """
    Compact 2-input Residual Neural Network (2 -> 16 hidden units) with
    a residual skip connection h + F(h) and ReLU activations.
    """
    def __init__(self, input_dim: int = 2, hidden_dim: int = 16):
        super().__init__()
        self.fc_in = nn.Linear(input_dim, hidden_dim)
        self.res_fc1 = nn.Linear(hidden_dim, hidden_dim)
        self.res_fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, 1)
        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Initial projection into hidden space
        h = self.relu(self.fc_in(x))
        # Residual block: F(h)
        f_h = self.relu(self.res_fc1(h))
        f_h = self.res_fc2(f_h)
        # Residual skip connection: h + F(h) followed by ReLU
        h_out = self.relu(h + f_h)
        # Output logit
        logit = self.fc_out(h_out)
        return logit


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_dir, "data", "bass2_flammability.csv")

    # 1. Data Ingestion & Feature Selection
    df = pd.read_csv(data_path)

    # Strictly 2 Independent Inputs
    # Explicitly ignore fuel_thickness_mm (constant 6.35 mm baseline, zero variance)
    # and stretch_rate_s_inv (collinear linear multiple of flow_velocity_cms)
    raw_features = ["ambient_o2_percent", "flow_velocity_cms"]
    transformed_features = ["ambient_o2_percent", "log10_flow_velocity_cms"]
    target_col = "flame_hazard_state"

    # Log10-transform flow_velocity_cms (spans 2 orders of magnitude across quench & blowoff limits)
    o2_vals = df["ambient_o2_percent"].values.astype(np.float32)
    log10_flow_vals = np.log10(np.maximum(df["flow_velocity_cms"].values, 1e-6)).astype(np.float32)

    X = np.column_stack([o2_vals, log10_flow_vals]).astype(np.float32)
    y = df[target_col].values.astype(np.float32)

    # 2. Strict Overfitting & Data Leakage Prevention
    # 80/20 stratified train/test split BEFORE any scaling
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SPLIT_SEED
    )

    # Fit StandardScaler strictly on X_train; transform X_test using training stats
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    X_train_t = torch.tensor(X_train_scaled, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
    X_test_t = torch.tensor(X_test_scaled, dtype=torch.float32)
    y_test_t = torch.tensor(y_test, dtype=torch.float32).unsqueeze(1)

    # 3. Model Initialization, Asymmetric Safety Loss & L2 Regularization
    hidden_dim = 16
    learning_rate = 0.02
    weight_decay = 1e-4
    pos_weight_val = 1.86
    epochs = 250

    model = CombustionResNet(input_dim=2, hidden_dim=hidden_dim)
    pos_weight = torch.tensor([pos_weight_val], dtype=torch.float32)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        logits = model(X_train_t)
        loss = criterion(logits, y_train_t)
        loss.backward()
        optimizer.step()

    # 4. Evaluation Strictly on Held-Out X_test under torch.no_grad()
    model.eval()
    with torch.no_grad():
        test_logits = model(X_test_t)
        test_probs = torch.sigmoid(test_logits).squeeze(1).numpy()
        test_preds = (test_probs >= 0.5).astype(int)

        train_logits = model(X_train_t)
        train_probs = torch.sigmoid(train_logits).squeeze(1).numpy()
        train_preds = (train_probs >= 0.5).astype(int)

    test_acc = float(accuracy_score(y_test, test_preds))
    test_recall = float(recall_score(y_test, test_preds, zero_division=0))
    test_precision = float(precision_score(y_test, test_preds, zero_division=0))
    test_f1 = float(f1_score(y_test, test_preds, zero_division=0))
    cm = confusion_matrix(y_test, test_preds).tolist()

    train_acc = float(accuracy_score(y_train, train_preds))
    train_recall = float(recall_score(y_train, train_preds, zero_division=0))

    print("=== NOCURA BASS-II CombustionResNet Training Complete ===")
    print(f"Dataset Rows: {len(df)} | Train: {len(X_train)} | Held-Out Test: {len(X_test)}")
    print(f"Raw Inputs (2):        {raw_features}")
    print(f"Scaled Features (2):   {transformed_features}")
    print(f"Scaler Mean (train):   {scaler.mean_.tolist()}")
    print(f"Scaler Scale (train):  {scaler.scale_.tolist()}")
    print(f"Held-Out Test Accuracy:  {test_acc:.4f}")
    print(f"Held-Out Test Recall:    {test_recall:.4f}")
    print(f"Held-Out Test Precision: {test_precision:.4f}")
    print(f"Held-Out Test F1 Score:  {test_f1:.4f}")
    print(f"Confusion Matrix (Test): {cm}")

    # 5. Edge Artifact Export to model_artifacts.json
    artifacts = {
        "model_name": "CombustionResNet",
        "model_version": "2.2.0-bass2-logflow",
        "architecture": f"2 -> {hidden_dim} -> ResBlock({hidden_dim}->{hidden_dim}->{hidden_dim}) [h + F(h)] -> 1",
        "raw_inputs": raw_features,
        "features": transformed_features,
        "feature_transforms": {
            "ambient_o2_percent": "identity",
            "flow_velocity_cms": "log10"
        },
        "excluded_features": {
            "fuel_thickness_mm": "Constant 6.35 mm baseline across all 51 rows (zero variance)",
            "stretch_rate_s_inv": "Collinear linear multiple of flow_velocity_cms (a = flow_velocity_cms / 0.21167)"
        },
        "target": target_col,
        "target_rubric": {
            "1": "Sustained / Stable Flame (active fire hazard; combustion persists)",
            "0": "Blowoff or Quench Extinction (safe / self-extinguishing; flame cannot sustain due to radiative quenching at low flow or convective blowoff at high flow)"
        },
        "fuel_baseline_mm": 6.35,
        "fuel_reference_description": "1/4 inch (6.35 mm) cast Polymethyl Methacrylate (PMMA) solid rod",
        "hyperparameters": {
            "hidden_dim": hidden_dim,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "weight_decay_l2": weight_decay,
            "pos_weight": pos_weight_val,
            "test_size": 0.2,
            "split_random_state": SPLIT_SEED,
            "model_seed": MODEL_SEED
        },
        "telemetry_bounds": {
            "ambient_o2_percent": {
                "min": float(df["ambient_o2_percent"].min()),
                "max": float(df["ambient_o2_percent"].max())
            },
            "flow_velocity_cms": {
                "min": float(df["flow_velocity_cms"].min()),
                "max": float(df["flow_velocity_cms"].max()),
                "log10_min": round(math.log10(float(df["flow_velocity_cms"].min())), 6),
                "log10_max": round(math.log10(float(df["flow_velocity_cms"].max())), 6)
            }
        },
        "scaler": {
            "mean": scaler.mean_.tolist(),
            "scale": scaler.scale_.tolist()
        },
        "weights": {
            "fc_in": {
                "weight": model.fc_in.weight.detach().cpu().numpy().tolist(),
                "bias": model.fc_in.bias.detach().cpu().numpy().tolist()
            },
            "res_fc1": {
                "weight": model.res_fc1.weight.detach().cpu().numpy().tolist(),
                "bias": model.res_fc1.bias.detach().cpu().numpy().tolist()
            },
            "res_fc2": {
                "weight": model.res_fc2.weight.detach().cpu().numpy().tolist(),
                "bias": model.res_fc2.bias.detach().cpu().numpy().tolist()
            },
            "fc_out": {
                "weight": model.fc_out.weight.detach().cpu().numpy().tolist(),
                "bias": model.fc_out.bias.detach().cpu().numpy().tolist()
            }
        },
        "evaluation_metrics": {
            "test_accuracy": round(test_acc, 4),
            "test_recall": round(test_recall, 4),
            "test_precision": round(test_precision, 4),
            "test_f1": round(test_f1, 4),
            "test_confusion_matrix": cm,
            "train_accuracy": round(train_acc, 4),
            "train_recall": round(train_recall, 4)
        }
    }

    artifact_path = os.path.join(base_dir, "model_artifacts.json")
    with open(artifact_path, "w", encoding="utf-8") as f:
        json.dump(artifacts, f, indent=2)

    print(f"Exported edge inference artifacts to: {artifact_path}")


if __name__ == "__main__":
    main()