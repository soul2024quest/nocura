# nocura
Fire behaves completely differently in zero gravity. On Earth, hot air rises and pulls fresh oxygen into a flame. In space, there is no buoyancy, so cabin ventilation fans decide whether a fire suffocates on its own, burns steadily, or gets blown out.

NOCURA is a microgravity combustion hazard dashboard and edge inference engine built for the NASA Space Apps Challenge. It takes spacecraft cabin oxygen and airflow readings, runs a lightweight neural network trained on real ISS fire experiments, and translates the result into plain-English cabin physics and immediate crew actions.

Live App: https://nocura.vercel.app

## Why We Built It This Way

- Real ISS Data: Trained on 51 microgravity stagnation-flame runs from NASA's Burning and Suppression of Solids - II (BASS-II / PSI-25) experiment using 6.35 mm (1/4 in) cast PMMA rods.
- Why BASS-II? Unlike FLEX (which tested liquid fuel droplets) or Saffire-II (high-speed 20-30 cm/s duct flows), BASS-II mapped solid plastic flammability across low-to-moderate spacecraft cabin airflows (0.106 to 16.298 cm/s) and reduced oxygen levels (13.5% to 21.9%). That captures both ways a microgravity fire dies out: suffocating at near-zero airflow and blowing off at high airflow.
- Edge-Ready Inference: Spacecraft hardware and serverless deployments can't carry multi-gigabyte ML frameworks just to check two sensor numbers. I trained the residual network (CombustionResNet) offline in PyTorch, exported the weights and log10 airflow scaler stats into model_artifacts.json, and wrote the live forward pass in pure math. Inference runs in under a millisecond with zero heavy dependencies.
- Plain-English Astronaut Briefings: Instead of dumping raw numbers or research jargon on a crew member, /api/briefing uses Qwen (via Groq) to explain what is physically happening in the cabin and what actions to take, with a built-in local fallback if the API is unreachable.
- NASA PSI Research Catalog: Includes a searchable, sortable catalog comparing BASS-II (PSI-25), Saffire-II (PSI-99), SAME, and FLEX directly from NASA's Physical Sciences Informatics archive.

## Scope & Guardrails

- Experimental Estimate, Not Whole-Cabin Probability: The output (0.000 to 1.000) is a flame-sustainment score for a 6.35 mm PMMA rod under specific oxygen and airflow conditions, not a calibrated probability of a whole-spacecraft fire.
- Strict Envelope Checks: The API blocks predictions outside the verified BASS-II bounds (13.5% to 21.9% O2 and 0.106 to 16.298 cm/s airflow) instead of guessing beyond real experimental data.

## Project Structure

- main.py: FastAPI backend, pure-Python inference, PSI catalog, and Groq briefing route
- model_artifacts.json: Exported CombustionResNet weights, Z-score scaler, and telemetry bounds
- train.py: Offline PyTorch training, 5-fold cross-validation, and Logistic Regression baseline comparison
- bass2_pmma_flammability_data-v3.csv: Digitized NASA BASS-II 6.35 mm PMMA rod flammability dataset
- DATASET_PROVENANCE.md: Source citations and physical limits for the training dataset
- requirements.txt: Lean runtime dependencies for serverless deployment
- requirements-train.txt: Full ML dependencies for offline training
