import os
import re
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
    for origin in os.getenv("CORS_ORIGINS", "https://nocura.vercel.app,http://localhost:5173").split(",")
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
            "flames quench via radiative heat loss below ~0.11-0.38 cm/s and blow off at high stretch rates, "
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
            "under realistic ventilation velocities (20-30 cm/s), bridging small-scale MSG tests and vehicle-scale fire spread."
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
        "primary_sensors": ["Multi-user Droplet Combustion Apparatus (MDCA)", "
