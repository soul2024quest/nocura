import os
import json
import math
import logging
from typing import Optional, List, Dict, Any
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nocura-api")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_PATH = os.path.join(BASE_DIR, "model_artifacts.json")

with open(ARTIFACTS_PATH, "r", encoding="utf-8") as f:
    ARTIFACTS: Dict[str, Any] = json.load(f)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen/qwen3.8-27b").strip()
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

# Supported experimental envelope from NASA BASS-II PMMA rod dataset
O2_MIN = float(ARTIFACTS["telemetry_bounds"]["ambient_o2_percent"]["min"])   # 13.5%
O2_MAX = float(ARTIFACTS["telemetry_bounds"]["ambient_o2_percent"]["max"])   # 21.9%
FLOW_MIN = float(ARTIFACTS["telemetry_bounds"]["flow_velocity_cms"]["min"])  # 0.106 cm/s
FLOW_MAX = float(ARTIFACTS["telemetry_bounds"]["flow_velocity_cms"]["max"])  # 16.298 cm/s
SUPPORTED_FUEL_MM = float(ARTIFACTS.get("fuel_baseline_mm", 6.35))

# Curated NASA Physical Sciences Informatics (PSI) & NTRS Investigation Catalog
PSI_INVESTIGATIONS: List[Dict[str, Any]] = [
    {
        "psi_id": "PSI-25",
        "title": "Burning and Suppression of Solids - II (BASS-II)",
        "facility": "Microgravity Science Glovebox (MSG), ISS",
        "fuels": ["Cast PMMA rods (6.35 mm)", "PMMA slabs & spheres", "SIBAL cotton-fiberglass", "Nomex"],
        "oxygen_range_percent": [13.5, 21.9],
        "flow_velocity_range_cms": [0.106, 40.0],
        "flow_regime": "Opposed and concurrent forced flow (low-velocity wind tunnel)",
        "primary_sensors": ["Color video camera", "Radiometer", "CSA-CP & CDM gas/smoke sensors"],
        "key_findings": (
            "Established U-shaped stagnation flammability boundaries for 6.35 mm PMMA rods: "
            "flames quench via radiative heat loss below ~0.11–0.38 cm/s and blow off at high stretch rates, "
            "while sustaining steady combustion down to 13.6% O2 at intermediate convective flows."
        ),
        "citation": "Ferkul, Olson et al., NASA NTRS 20160000593 / NASA/TM-20210011385",
        "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25",
        "fire_safety_relevance_score": 0.98,
    },
    {
        "psi_id": "PSI-99",
        "title": "Spacecraft Fire Experiment-II (Saffire-II)",
        "facility": "Orbital ATK Cygnus Resupply Vehicle (post-ISS unberthing)",
        "fuels": ["SIBAL fabric", "Silicone", "Structured & flat PMMA", "PMMA-Nomex composites"],
        "oxygen_range_percent": [18.0, 21.0],
        "flow_velocity_range_cms": [20.0, 30.0],
        "flow_regime": "Large-scale ducted concurrent and opposed airflow (5 cm x 29 cm sample cards)",
        "primary_sensors": ["Dual flame cameras", "Thermocouples", "Radiometers", "O2/CO2 sensors", "Anemometers"],
        "key_findings": (
            "Demonstrated large-scale microgravity flame growth and extinction limits across spacecraft materials "
            "under realistic ventilation velocities (20–30 cm/s), bridging small-scale MSG tests and vehicle-scale fire spread."
        ),
        "citation": "Urban, Ruff, Olson et al., PSI-99 (DOI: 10.60555/2chp-m469)",
        "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-99",
        "fire_safety_relevance_score": 0.95,
    },
    {
        "psi_id": "SAME",
        "title": "Smoke and Aerosol Measurement Experiment (SAME / SAME-R)",
        "facility": "Microgravity Science Glovebox (MSG), ISS",
        "fuels": ["Teflon", "Kapton", "Silicone rubber", "Cellulose", "PMMA"],
        "oxygen_range_percent": [20.9, 21.0],
        "flow_velocity_range_cms": [0.0, 10.0],
        "flow_regime": "Low-flow smoldering and early-stage pyrolysis aerosol transport",
        "primary_sensors": ["DustTrak aerosol monitor", "P-Trak condensation particle counter", "Thermophoretic precipitator"],
        "key_findings": (
            "Quantified microgravity smoke particle size distributions during early overheating, showing that "
            "low-gravity combustion produces larger coagulated soot/aerosol aggregates that affect spacecraft smoke detector response."
        ),
        "citation": "Urban, Mulholland et al., NASA Glenn Research Center (PSI Smoke & Aerosol Archive)",
        "source_url": "https://psi.nasa.gov/",
        "fire_safety_relevance_score": 0.91,
    },
    {
        "psi_id": "FLEX",
        "title": "Flame Extinguishment Experiment (FLEX / FLEX-2)",
        "facility": "Combustion Integrated Rack (CIR), ISS",
        "fuels": ["Heptane", "Methanol", "Decane", "Multi-component hydrocarbon droplets"],
        "oxygen_range_percent": [14.0, 21.0],
        "flow_velocity_range_cms": [0.0, 5.0],
        "flow_regime": "Quiescent microgravity spherical droplet combustion with CO2/He/N2 diluents",
        "primary_sensors": ["Multi-user Droplet Combustion Apparatus (MDCA)", "UV/IR radiometers", "High-speed cameras"],
        "key_findings": (
            "Measured limiting oxygen indices and inert gas suppression concentrations (CO2 vs. He) in microgravity, "
            "discovering low-temperature cool-flame burning regimes after visible flame extinction."
        ),
        "citation": "Dietrich, Nayagam, Williams et al., NASA Glenn Research Center (PSI FLEX Archive)",
        "source_url": "https://psi.nasa.gov/",
        "fire_safety_relevance_score": 0.88,
    },
]

app = FastAPI(
    title="NOCURA Microgravity Combustion & PSI Research API",
    version=ARTIFACTS.get("model_version", "2.2.0-bass2-logflow"),
    description="Edge-aligned BASS-II PMMA flame-sustainment estimator and NASA PSI investigation catalog.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TelemetryRequest(BaseModel):
    ambient_o2_percent: float = Field(..., description="Ambient oxygen mole fraction (%)")
    flow_velocity_cms: float = Field(..., description="Forced convective airflow velocity (cm/s)")
    fuel_thickness_mm: Optional[float] = Field(
        default=6.35,
        description="Fuel rod diameter in mm; model strictly supports 6.35 mm (1/4 in) cast PMMA baseline",
    )

    @field_validator("ambient_o2_percent", "flow_velocity_cms")
    @classmethod
    def check_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Telemetry inputs must be finite real numbers.")
        return v

    @field_validator("fuel_thickness_mm")
    @classmethod
    def check_fuel_finite(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not math.isfinite(v):
            raise ValueError("fuel_thickness_mm must be a finite real number.")
        return v


def validate_supported_envelope(req: TelemetryRequest) -> List[str]:
    """Return list of out-of-envelope violations if inputs exceed supported experimental scope."""
    violations: List[str] = []
    if req.fuel_thickness_mm is not None and abs(req.fuel_thickness_mm - SUPPORTED_FUEL_MM) > 1e-3:
        violations.append(
            f"Unsupported fuel_thickness_mm={req.fuel_thickness_mm} mm. "
            f"Model is calibrated exclusively for {SUPPORTED_FUEL_MM} mm (1/4 in) cast PMMA rods."
        )
    if req.ambient_o2_percent < O2_MIN or req.ambient_o2_percent > O2_MAX:
        violations.append(
            f"ambient_o2_percent={req.ambient_o2_percent}% is outside the verified BASS-II PMMA "
            f"experimental range ({O2_MIN}% to {O2_MAX}%)."
        )
    if req.flow_velocity_cms < FLOW_MIN or req.flow_velocity_cms > FLOW_MAX:
        violations.append(
            f"flow_velocity_cms={req.flow_velocity_cms} cm/s is outside the verified BASS-II PMMA "
            f"experimental range ({FLOW_MIN} to {FLOW_MAX} cm/s)."
        )
    return violations


def compute_sustained_flame_score(ambient_o2_percent: float, flow_velocity_cms: float) -> float:
    """
    Pure-Python forward pass matching train.py preprocessing and CombustionResNet weights:
    - Feature 0: raw ambient_o2_percent
    - Feature 1: log10(max(flow_velocity_cms, 1e-6))
    """
    mean = ARTIFACTS["scaler"]["mean"]
    scale = ARTIFACTS["scaler"]["scale"]

    safe_flow = max(float(flow_velocity_cms), 1e-6)
    log10_flow = math.log10(safe_flow)

    x0 = (float(ambient_o2_percent) - mean[0]) / scale[0]
    x1 = (log10_flow - mean[1]) / scale[1]
    x = [x0, x1]

    w = ARTIFACTS["weights"]

    # fc_in + ReLU
    h = [
        max(0.0, sum(w["fc_in"]["weight"][i][j] * x[j] for j in range(2)) + w["fc_in"]["bias"][i])
        for i in range(len(w["fc_in"]["bias"]))
    ]

    # res_fc1 + ReLU
    f_h = [
        max(0.0, sum(w["res_fc1"]["weight"][i][j] * h[j] for j in range(len(h))) + w["res_fc1"]["bias"][i])
        for i in range(len(w["res_fc1"]["bias"]))
    ]

    # res_fc2 (linear)
    f_h = [
        sum(w["res_fc2"]["weight"][i][j] * f_h[j] for j in range(len(f_h))) + w["res_fc2"]["bias"][i]
        for i in range(len(w["res_fc2"]["bias"]))
    ]

    # Residual skip connection: ReLU(h + f_h)
    h_out = [max(0.0, h[i] + f_h[i]) for i in range(len(h))]

    # fc_out + clamped sigmoid
    logit = sum(w["fc_out"]["weight"][0][j] * h_out[j] for j in range(len(h_out))) + w["fc_out"]["bias"][0]
    score = 1.0 / (1.0 + math.exp(-max(min(logit, 60.0), -60.0)))
    return round(score, 6)


def classify_experimental_regime(score: float, flow_velocity_cms: float) -> Dict[str, str]:
    """
    Map the model's sustained-flame score to calibrated experimental regimes grounded in
    NASA BASS-II PMMA rod flammability limits (without overclaiming vehicle-wide fire probability).
    """
    if score < 0.25:
        regime = "Quench / Blowoff Extinction Regime"
        if flow_velocity_cms < 0.45:
            mechanism = "Low-flow radiative heat loss dominates; a PMMA rod flame self-extinguishes in BASS-II tests."
        else:
            mechanism = "High convective stretch rate sweeps fuel vapor faster than reaction kinetics; flame blows off."
    elif score < 0.50:
        regime = "Near-Limit Extinction Boundary"
        mechanism = "Close to the BASS-II flammability boundary; minor increases in O2 or moderate airflow could sustain burning."
    elif score < 0.75:
        regime = "Moderate Flame-Sustainment Regime"
        mechanism = "Crosses the binary threshold (score >= 0.50); convective oxygen supply balances radiative losses for steady spread."
    elif score < 0.90:
        regime = "High Flame-Sustainment Regime"
        mechanism = "Firmly inside the BASS-II sustained-combustion envelope for a 6.35 mm PMMA rod."
    else:
        regime = "Strong Sustained-Combustion Regime"
        mechanism = "Deep inside the stable microgravity burning region observed in NASA BASS-II PMMA stagnation tests."

    return {"regime_label": regime, "physical_interpretation": mechanism}


def build_grounded_fallback(
    o2: float,
    flow: float,
    score: float,
    predicted_state: int,
    regime_info: Dict[str, str],
) -> str:
    """Deterministic, citation-grounded fallback when Groq API is unavailable or invalid."""
    outcome_text = (
        "Sustained flame expected (state = 1) for a 6.35 mm PMMA rod under these test conditions."
        if predicted_state == 1
        else "Self-extinguishing quench or blowoff expected (state = 0) for a 6.35 mm PMMA rod under these test conditions."
    )
    return (
        f"**Experimental Estimate ({regime_info['regime_label']} — Score: {score:.2f}):**\n"
        f"At {o2:.1f}% O2 and {flow:.3f} cm/s forced airflow, {outcome_text} "
        f"{regime_info['physical_interpretation']}\n\n"
        f"**Cited Research Context & Scope:**\n"
        f"- **Benchmark:** Derived from 51 microgravity stagnation-flame data points on 6.35 mm (1/4 in) cast PMMA rods "
        f"in NASA's BASS-II investigation (PSI-25 / NASA NTRS 20160000593).\n"
        f"- **Physical Envelope:** Verified strictly within {O2_MIN}%–{O2_MAX}% O2 and {FLOW_MIN}–{FLOW_MAX} cm/s airflow; "
        f"results do not directly generalize to other polymers, thicknesses, or non-standard cabin pressures."
    )


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "model_version": ARTIFACTS.get("model_version"),
        "groq_configured": bool(GROQ_API_KEY),
        "qwen_model": QWEN_MODEL,
        "supported_envelope": {
            "ambient_o2_percent": [O2_MIN, O2_MAX],
            "flow_velocity_cms": [FLOW_MIN, FLOW_MAX],
            "fuel_baseline_mm": SUPPORTED_FUEL_MM,
        },
    }


@app.get("/api/model")
async def get_model_metadata() -> Dict[str, Any]:
    """Expose supported bounds, units, provenance, and evaluation metrics to the frontend."""
    return {
        "model_name": ARTIFACTS.get("model_name"),
        "model_version": ARTIFACTS.get("model_version"),
        "architecture": ARTIFACTS.get("architecture"),
        "raw_inputs": ARTIFACTS.get("raw_inputs"),
        "feature_transforms": ARTIFACTS.get("feature_transforms"),
        "fuel_baseline_mm": SUPPORTED_FUEL_MM,
        "fuel_reference_description": ARTIFACTS.get("fuel_reference_description"),
        "telemetry_bounds": ARTIFACTS.get("telemetry_bounds"),
        "evaluation_metrics": ARTIFACTS.get("evaluation_metrics"),
        "provenance": {
            "investigation": "Burning and Suppression of Solids - II (BASS-II)",
            "psi_id": "PSI-25",
            "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25",
            "ntrs_citation": "https://ntrs.nasa.gov/citations/20160000593",
            "limitations": (
                "Two-input experimental classifier trained on 51 digitized points from 6.35 mm PMMA rod "
                "stagnation flame tests in microgravity. Outputs represent an experimental flame-sustainment "
                "score, not a calibrated whole-vehicle cabin fire probability."
            ),
        },
    }


@app.get("/api/investigations")
async def list_investigations(
    q: Optional[str] = Query(default=None, description="Keyword search across title, fuels, and findings"),
    fuel: Optional[str] = Query(default=None, description="Filter by fuel material (e.g., PMMA, SIBAL, Heptane)"),
    sort_by: str = Query(default="relevance", pattern="^(relevance|min_o2|max_flow)$"),
) -> Dict[str, Any]:
    """Curated NASA PSI combustion investigation catalog with search, filtering, and ranking."""
    results = list(PSI_INVESTIGATIONS)

    if q:
        needle = q.strip().lower()
        results = [
            item
            for item in results
            if needle in item["title"].lower()
            or needle in item["key_findings"].lower()
            or needle in item["flow_regime"].lower()
            or any(needle in f.lower() for f in item["fuels"])
        ]

    if fuel:
        f_needle = fuel.strip().lower()
        results = [item for item in results if any(f_needle in f.lower() for f in item["fuels"])]

    if sort_by == "min_o2":
        results.sort(key=lambda x: x["oxygen_range_percent"][0])
    elif sort_by == "max_flow":
        results.sort(key=lambda x: x["flow_velocity_range_cms"][1], reverse=True)
    else:
        results.sort(key=lambda x: x["fire_safety_relevance_score"], reverse=True)

    return {
        "count": len(results),
        "sort_by": sort_by,
        "investigations": results,
    }


@app.get("/api/investigations/{psi_id}")
async def get_investigation_detail(psi_id: str) -> Dict[str, Any]:
    target = psi_id.strip().upper()
    for item in PSI_INVESTIGATIONS:
        if item["psi_id"].upper() == target:
            return item
    raise HTTPException(status_code=404, detail=f"Investigation '{psi_id}' not found in curated PSI catalog.")


@app.post("/api/predict")
async def predict_endpoint(req: TelemetryRequest) -> Dict[str, Any]:
    violations = validate_supported_envelope(req)
    if violations:
        return {
            "status": "outside_supported_conditions",
            "supported": False,
            "reasons": violations,
            "supported_envelope": {
                "ambient_o2_percent": {"min": O2_MIN, "max": O2_MAX, "unit": "%"},
                "flow_velocity_cms": {"min": FLOW_MIN, "max": FLOW_MAX, "unit": "cm/s"},
                "fuel_thickness_mm": {"exact": SUPPORTED_FUEL_MM, "unit": "mm"},
            },
        }

    score = compute_sustained_flame_score(req.ambient_o2_percent, req.flow_velocity_cms)
    predicted_state = 1 if score >= 0.5 else 0
    regime_info = classify_experimental_regime(score, req.flow_velocity_cms)

    return {
        "status": "supported",
        "supported": True,
        "flame_hazard_state": predicted_state,
        "sustained_flame_score": score,
        "regime_label": regime_info["regime_label"],
        "physical_interpretation": regime_info["physical_interpretation"],
        "inputs": {
            "ambient_o2_percent": req.ambient_o2_percent,
            "flow_velocity_cms": req.flow_velocity_cms,
            "log10_flow_velocity_cms": round(math.log10(req.flow_velocity_cms), 6),
            "fuel_baseline_mm": SUPPORTED_FUEL_MM,
        },
        "scope_note": (
            "Experimental flame-sustainment estimate for a 6.35 mm cast PMMA rod based on NASA BASS-II "
            "microgravity stagnation data (PSI-25). Not a validated whole-cabin fire probability."
        ),
    }


@app.post("/api/briefing")
async def briefing_endpoint(req: TelemetryRequest) -> Dict[str, Any]:
    violations = validate_supported_envelope(req)
    if violations:
        return {
            "status": "outside_supported_conditions",
            "supported": False,
            "reasons": violations,
            "briefing": (
                "**Outside Supported Experimental Conditions:**\n"
                + "\n".join(f"- {v}" for v in violations)
                + "\n\nAdjust inputs back within the NASA BASS-II 6.35 mm PMMA rod envelope "
                f"({O2_MIN}%–{O2_MAX}% O2, {FLOW_MIN}–{FLOW_MAX} cm/s airflow) for an experimental estimate."
            ),
            "source": "envelope_guard",
        }

    score = compute_sustained_flame_score(req.ambient_o2_percent, req.flow_velocity_cms)
    predicted_state = 1 if score >= 0.5 else 0
    regime_info = classify_experimental_regime(score, req.flow_velocity_cms)
    fallback_text = build_grounded_fallback(
        req.ambient_o2_percent, req.flow_velocity_cms, score, predicted_state, regime_info
    )

    if not GROQ_API_KEY:
        logger.info("GROQ_API_KEY not configured; serving grounded deterministic fallback.")
        return {
            "status": "supported",
            "supported": True,
            "flame_hazard_state": predicted_state,
            "sustained_flame_score": score,
            "regime_label": regime_info["regime_label"],
            "briefing": fallback_text,
            "source": "local_fallback_no_key",
        }

    system_prompt = (
        "You are a concise scientific research interpreter explaining microgravity combustion test results "
        "from NASA's Burning and Suppression of Solids-II (BASS-II, PSI-25) experiment.\n"
        "Strict rules:\n"
        "1. Present the model output strictly as an experimental flame-sustainment estimate for a 6.35 mm (1/4 in) "
        "cast PMMA rod—never claim it is a validated whole-spacecraft cabin fire probability.\n"
        "2. Do NOT invent operational spacecraft emergency commands (such as shutting down fans or depressurizing modules), "
        "because a two-input single-material classifier does not model vehicle ECLSS hardware.\n"
        "3. Explain the physical mechanism in plain English using only NASA BASS-II findings: low airflow causes radiative "
        "quenching, intermediate airflow sustains steady flame spread down to 13.6% O2, and high airflow causes convective blowoff.\n"
        "4. Avoid ML buzzwords (no 'logits', 'tensors', 'sigmoid', 'weights', or 'CSV').\n"
        "5. Format in two short sections: 'Experimental Interpretation' and 'BASS-II Research Context'."
    )

    user_prompt = (
        f"Test Conditions (within verified 6.35 mm PMMA rod envelope):\n"
        f"- Ambient O2: {req.ambient_o2_percent}%\n"
        f"- Forced Airflow Velocity: {req.flow_velocity_cms} cm/s\n"
        f"- Experimental Sustained-Flame Score: {score:.4f} (Binary State: {predicted_state})\n"
        f"- Classified Regime: {regime_info['regime_label']}\n"
        f"- Reference Mechanism: {regime_info['physical_interpretation']}\n"
        f"Provide a clear, grounded 2-section summary."
    )

    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 350,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices") or []
        if not choices:
            logger.warning("Groq API returned empty choices list; falling back.")
            raise ValueError("Empty choices in Groq response")

        choice = choices[0]
        finish_reason = choice.get("finish_reason")
        content = (choice.get("message") or {}).get("content", "").strip()

        if not content or finish_reason == "length":
            logger.warning("Groq output empty or truncated (finish_reason=%s); falling back.", finish_reason)
            raise ValueError(f"Invalid LLM output (finish_reason={finish_reason})")

        return {
            "status": "supported",
            "supported": True,
            "flame_hazard_state": predicted_state,
            "sustained_flame_score": score,
            "regime_label": regime_info["regime_label"],
            "briefing": content,
            "source": f"groq:{QWEN_MODEL}",
        }

    except Exception as exc:
        logger.error("Groq briefing request failed (%s); serving deterministic fallback.", exc)
        return {
            "status": "supported",
            "supported": True,
            "flame_hazard_state": predicted_state,
            "sustained_flame_score": score,
            "regime_label": regime_info["regime_label"],
            "briefing": fallback_text,
            "source": "local_fallback_error",
            "fallback_reason": str(exc),
        }
