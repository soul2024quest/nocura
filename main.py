"""
NOCURA - Microgravity Solid Combustion Hazard Prediction Engine
FastAPI Inference Server & Groq-Qwen Astronaut Briefing Bridge
"""

import os
import json
import math
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Environment Configuration (Never hardcode API keys)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen/qwen3.8-27b")
CORS_ORIGINS_RAW = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
)
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_RAW.split(",") if origin.strip()]
if "http://localhost:5173" not in CORS_ORIGINS:
    CORS_ORIGINS.append("http://localhost:5173")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Load Pre-Generated Edge Model Artifacts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_PATH = os.path.join(BASE_DIR, "model_artifacts.json")

with open(ARTIFACT_PATH, "r", encoding="utf-8") as f:
    MODEL_ARTIFACTS: Dict[str, Any] = json.load(f)

app = FastAPI(
    title="NOCURA Microgravity Combustion Hazard API",
    description="2-Feature NASA BASS-II Solid Combustion Prediction & Groq-Qwen Astronaut Briefing Engine",
    version=MODEL_ARTIFACTS.get("model_version", "2.1.0-bass2-2feat")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Schemas ---

class TelemetryInput(BaseModel):
    ambient_o2_percent: float = Field(
        ...,
        description="Cabin ambient oxygen concentration (% O2)",
        examples=[16.1]
    )
    flow_velocity_cms: float = Field(
        ...,
        description="Local cabin ventilation airflow velocity (cm/s)",
        examples=[4.5]
    )
    fuel_thickness_mm: Optional[float] = Field(
        default=6.35,
        description="Optional backwards-compatible fuel thickness (ignored by 2-input neural net; baseline 6.35 mm PMMA rod)"
    )


class PredictionResponse(BaseModel):
    flame_hazard_state: int
    hazard_label: str
    confidence_probability: float
    risk_classification: str
    ambient_o2_percent: float
    flow_velocity_cms: float
    fuel_baseline_mm: float
    boundary_warnings: List[str]
    model_version: str


class BriefingResponse(BaseModel):
    flame_hazard_state: int
    confidence_probability: float
    risk_classification: str
    briefing_source: str
    model_used: str
    briefing: str
    local_analysis: str
    boundary_warnings: List[str]


# --- Pure-Python 2-Feature Matrix Dot-Product Inference ---

def _relu_vec(vec: List[float]) -> List[float]:
    return [max(0.0, v) for v in vec]


def _linear_layer(x: List[float], weight: List[List[float]], bias: List[float]) -> List[float]:
    out = []
    for row, b in zip(weight, bias):
        dot = sum(w_ij * x_j for w_ij, x_j in zip(row, x)) + b
        out.append(dot)
    return out


def _sigmoid(logit: float) -> float:
    if logit >= 0:
        z = math.exp(-logit)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(logit)
        return z / (1.0 + z)


def classify_risk_tier(score: float) -> str:
    """
    Maps continuous model probability strictly to the five required risk classifications.
    """
    if score < 0.25:
        return "Nominal / Safe"
    elif score < 0.50:
        return "Probable Safety Risk"
    elif score < 0.75:
        return "Moderate Safety Risk"
    elif score < 0.90:
        return "High Risk"
    else:
        return "Critical Hazard"


def check_boundary_warnings(o2: float, flow: float, fuel_thickness_mm: Optional[float]) -> List[str]:
    warnings: List[str] = []
    bounds = MODEL_ARTIFACTS.get("telemetry_bounds", {})
    o2_bounds = bounds.get("ambient_o2_percent", {"min": 13.5, "max": 21.9})
    flow_bounds = bounds.get("flow_velocity_cms", {"min": 0.106, "max": 16.298})

    if o2 < o2_bounds["min"] or o2 > o2_bounds["max"]:
        warnings.append(
            f"ambient_o2_percent ({o2}%) is outside NASA BASS-II experimental bounds "
            f"[{o2_bounds['min']}%, {o2_bounds['max']}%]."
        )
    if flow < flow_bounds["min"] or flow > flow_bounds["max"]:
        warnings.append(
            f"flow_velocity_cms ({flow} cm/s) is outside NASA BASS-II experimental bounds "
            f"[{flow_bounds['min']} cm/s, {flow_bounds['max']} cm/s]."
        )
    if flow <= 0.35:
        warnings.append(
            "Low-velocity regime (< 0.35 cm/s): Near radiative quench extinction boundary."
        )
    elif flow >= 10.0:
        warnings.append(
            "High-velocity regime (>= 10.0 cm/s): Approaching high-flow blowoff boundary."
        )
    if fuel_thickness_mm is not None and abs(fuel_thickness_mm - 6.35) > 1e-3:
        warnings.append(
            f"Provided fuel_thickness_mm ({fuel_thickness_mm} mm) ignored by 2-input model; "
            "predictions are referenced to the 6.35 mm (1/4 inch) PMMA baseline."
        )
    return warnings


def run_pure_python_inference(o2: float, flow: float) -> Dict[str, Any]:
    """
    Executes sub-millisecond 2-input CombustionResNet forward pass in pure Python
    using model_artifacts.json weights, biases, and StandardScaler statistics.
    """
    means = MODEL_ARTIFACTS["scaler"]["mean"]
    scales = MODEL_ARTIFACTS["scaler"]["scale"]

    # Standardize strictly the 2 independent features
    x_scaled = [
        (o2 - means[0]) / scales[0],
        (flow - means[1]) / scales[1]
    ]

    w = MODEL_ARTIFACTS["weights"]

    # Layer 1: fc_in + ReLU
    h = _relu_vec(_linear_layer(x_scaled, w["fc_in"]["weight"], w["fc_in"]["bias"]))

    # Residual block F(h): res_fc1 + ReLU -> res_fc2
    f_h = _relu_vec(_linear_layer(h, w["res_fc1"]["weight"], w["res_fc1"]["bias"]))
    f_h = _linear_layer(f_h, w["res_fc2"]["weight"], w["res_fc2"]["bias"])

    # Skip connection: ReLU(h + F(h))
    h_out = _relu_vec([h_i + f_i for h_i, f_i in zip(h, f_h)])

    # Output layer: fc_out -> scalar logit -> probability
    logit = _linear_layer(h_out, w["fc_out"]["weight"], w["fc_out"]["bias"])[0]
    prob = float(_sigmoid(logit))
    hazard_state = 1 if prob >= 0.5 else 0
    risk_tier = classify_risk_tier(prob)

    return {
        "flame_hazard_state": hazard_state,
        "hazard_label": (
            "Sustained / Stable Flame"
            if hazard_state == 1
            else "Blowoff or Quench Extinction"
        ),
        "confidence_probability": round(prob, 4),
        "risk_classification": risk_tier
    }


# --- Plain-English Deterministic Fallback & Qwen System Prompt ---

QWEN_SYSTEM_PROMPT = """You are a direct, no-nonsense mission communicator speaking directly to an astronaut in plain, everyday English.

STRICT RULES:
1. NEVER use technical jargon, academic disclaimers, or machine learning terms. Strictly forbidden words: "sigmoid", "logits", "tensors", "pyrolysis", "convective", "CSV", "calibration", "neural", "weights", "dataset". Avoid all fluff.
2. Map the hazard score strictly to one of these five risk classifications:
   - score < 0.25: Nominal / Safe (well inside quench/blowoff zone; fire cannot sustain itself).
   - 0.25 <= score < 0.50: Probable Safety Risk (approaching ignition threshold; monitor cabin air and airflow closely).
   - 0.50 <= score < 0.75: Moderate Safety Risk (sustained flame regime crossed; adjust airflow and oxygen controls immediately).
   - 0.75 <= score < 0.90: High Risk (strong sustained combustion conditions; shut down nearby fans and isolate electronics).
   - score >= 0.90: Critical Hazard (severe fire danger; execute immediate fire containment, isolate ventilation, and prepare suppression).
3. Format your response into ONLY these two clear, short parts:

What's Happening:
State the exact risk classification above and explain in plain language whether a fire would stay lit (1 = sustained/stable) or go out on its own (0 = quench/blowoff) under the current cabin oxygen and airflow.

What You Need to Do:
Simple, direct bullet points telling the astronaut the exact physical steps to take right now matching that risk level."""


def generate_local_analysis(o2: float, flow: float, score: float, hazard_state: int) -> str:
    """
    Deterministic plain-English fallback that uses the exact same five-tier thresholds
    and two-part format when GROQ_API_KEY is missing or the Groq API times out.
    """
    tier = classify_risk_tier(score)
    flame_behavior = (
        "a fire will stay lit and keep burning on its own (1 = sustained/stable)"
        if hazard_state == 1
        else "a fire will go out on its own (0 = quench/blowoff)"
    )

    if score < 0.25:
        happening = (
            f"Risk Level: {tier} (Score: {score:.2f}). With cabin oxygen at {o2:.1f}% and "
            f"airflow at {flow:.2f} cm/s, you are well inside the safe zone where {flame_behavior}."
        )
        actions = [
            "- Continue normal cabin operations and standard work routines.",
            "- Keep routine eye on oxygen and ventilation fan displays.",
            "- Keep standard fire extinguishers in their normal accessible brackets."
        ]
    elif score < 0.50:
        happening = (
            f"Risk Level: {tier} (Score: {score:.2f}). With cabin oxygen at {o2:.1f}% and "
            f"airflow at {flow:.2f} cm/s, {flame_behavior}, but cabin conditions are getting close to the point where a flame could stay lit."
        )
        actions = [
            "- Watch cabin oxygen and airflow readings closely over the next 15 minutes.",
            "- Clear any loose plastic, wipes, or clutter away from warm equipment.",
            "- Double-check that cabin air fans are not drifting into a steady draft over open wiring."
        ]
    elif score < 0.75:
        happening = (
            f"Risk Level: {tier} (Score: {score:.2f}). With cabin oxygen at {o2:.1f}% and "
            f"airflow at {flow:.2f} cm/s, you have crossed into the danger zone where {flame_behavior}."
        )
        actions = [
            "- Adjust cabin airflow and lower oxygen supply controls right away.",
            "- Turn off non-essential heat-producing gear in the immediate module.",
            "- Confirm the nearest portable fire extinguisher is unlatched and ready."
        ]
    elif score < 0.90:
        happening = (
            f"Risk Level: {tier} (Score: {score:.2f}). With cabin oxygen at {o2:.1f}% and "
            f"airflow at {flow:.2f} cm/s, cabin air strongly feeds fire and {flame_behavior}."
        )
        actions = [
            "- Shut down nearby circulation fans immediately to stop feeding fresh air to potential flames.",
            "- Isolate and power down electronics in the affected rack or bay.",
            "- Station a crew member with a fire extinguisher while oxygen levels are brought down."
        ]
    else:
        happening = (
            f"Risk Level: {tier} (Score: {score:.2f}). Severe fire danger at {o2:.1f}% oxygen and "
            f"{flow:.2f} cm/s airflow—under these conditions {flame_behavior} rapidly."
        )
        actions = [
            "- Execute immediate fire containment procedures for this module.",
            "- Isolate cabin ventilation and shut off local air supply ducts now.",
            "- Cut power to the work bay and prepare fire suppression gear for immediate use."
        ]

    return "What's Happening:\n" + happening + "\n\nWhat You Need to Do:\n" + "\n".join(actions)


# --- API Endpoints ---

@app.get("/health")
async def health_check():
    """
    Returns API status, model version, and whether GROQ_API_KEY is configured.
    """
    return {
        "status": "healthy",
        "model_name": MODEL_ARTIFACTS.get("model_name", "CombustionResNet"),
        "model_version": MODEL_ARTIFACTS.get("model_version", "2.1.0-bass2-2feat"),
        "features": MODEL_ARTIFACTS.get("features", ["ambient_o2_percent", "flow_velocity_cms"]),
        "fuel_baseline_mm": MODEL_ARTIFACTS.get("fuel_baseline_mm", 6.35),
        "groq_api_key_configured": bool(GROQ_API_KEY and len(GROQ_API_KEY.strip()) > 0),
        "qwen_model": QWEN_MODEL
    }


@app.post("/api/predict", response_model=PredictionResponse)
async def predict_hazard(telemetry: TelemetryInput):
    """
    Runs pure-Python 2-feature inference using model_artifacts.json and returns
    flame_hazard_state (1 or 0), confidence_probability, and boundary warnings.
    """
    pred = run_pure_python_inference(
        o2=telemetry.ambient_o2_percent,
        flow=telemetry.flow_velocity_cms
    )
    warnings = check_boundary_warnings(
        o2=telemetry.ambient_o2_percent,
        flow=telemetry.flow_velocity_cms,
        fuel_thickness_mm=telemetry.fuel_thickness_mm
    )

    return PredictionResponse(
        flame_hazard_state=pred["flame_hazard_state"],
        hazard_label=pred["hazard_label"],
        confidence_probability=pred["confidence_probability"],
        risk_classification=pred["risk_classification"],
        ambient_o2_percent=telemetry.ambient_o2_percent,
        flow_velocity_cms=telemetry.flow_velocity_cms,
        fuel_baseline_mm=MODEL_ARTIFACTS.get("fuel_baseline_mm", 6.35),
        boundary_warnings=warnings,
        model_version=MODEL_ARTIFACTS.get("model_version", "2.1.0-bass2-2feat")
    )


@app.post("/api/briefing", response_model=BriefingResponse)
async def astronaut_briefing(telemetry: TelemetryInput):
    """
    Computes the hazard score from ambient_o2_percent and flow_velocity_cms
    and forwards the telemetry to Groq using Qwen (qwen/qwen3.8-27b), with a
    deterministic local_analysis fallback.
    """
    pred = run_pure_python_inference(
        o2=telemetry.ambient_o2_percent,
        flow=telemetry.flow_velocity_cms
    )
    score = pred["confidence_probability"]
    hazard_state = pred["flame_hazard_state"]
    risk_tier = pred["risk_classification"]

    warnings = check_boundary_warnings(
        o2=telemetry.ambient_o2_percent,
        flow=telemetry.flow_velocity_cms,
        fuel_thickness_mm=telemetry.fuel_thickness_mm
    )

    local_fallback = generate_local_analysis(
        o2=telemetry.ambient_o2_percent,
        flow=telemetry.flow_velocity_cms,
        score=score,
        hazard_state=hazard_state
    )

    if not GROQ_API_KEY or not GROQ_API_KEY.strip():
        return BriefingResponse(
            flame_hazard_state=hazard_state,
            confidence_probability=score,
            risk_classification=risk_tier,
            briefing_source="local_analysis_fallback",
            model_used="deterministic-tier-engine",
            briefing=local_fallback,
            local_analysis=local_fallback,
            boundary_warnings=warnings
        )

    state_desc = "1 = sustained/stable flame" if hazard_state == 1 else "0 = quench/blowoff self-extinguishing"
    user_message = (
        f"Cabin Telemetry:\n"
        f"- Cabin Oxygen (ambient_o2_percent): {telemetry.ambient_o2_percent:.2f}%\n"
        f"- Cabin Airflow Speed (flow_velocity_cms): {telemetry.flow_velocity_cms:.3f} cm/s\n"
        f"- Model Hazard Score: {score:.4f}\n"
        f"- Risk Classification: {risk_tier}\n"
        f"- Flame State Outcome: {hazard_state} ({state_desc})\n\n"
        f"Write the two-part crew briefing (What's Happening and What You Need to Do) now."
    )

    payload = json.dumps({
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": QWEN_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.2,
        "max_tokens": 350
    }).encode("utf-8")

    req = urllib.request.Request(
        GROQ_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "NOCURA-Backend/2.1"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            qwen_text = data["choices"][0]["message"]["content"].strip()

            return BriefingResponse(
                flame_hazard_state=hazard_state,
                confidence_probability=score,
                risk_classification=risk_tier,
                briefing_source="groq_qwen",
                model_used=QWEN_MODEL,
                briefing=qwen_text,
                local_analysis=local_fallback,
                boundary_warnings=warnings
            )
    except Exception:
        return BriefingResponse(
            flame_hazard_state=hazard_state,
            confidence_probability=score,
            risk_classification=risk_tier,
            briefing_source="local_analysis_fallback",
            model_used="deterministic-tier-engine",
            briefing=local_fallback,
            local_analysis=local_fallback,
            boundary_warnings=warnings
        )
