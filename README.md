# Nocura — Orbital Laboratory

An interactive microgravity combustion research interface built with React, TypeScript, Vite, Motion for React, custom CSS, and Three.js. The frontend calls the existing FastAPI model on the same origin.

## Local development

1. Install Python dependencies: `pip install -r requirements.txt`.
2. Start the API: `uvicorn main:app --reload --port 8000`.
3. Install frontend dependencies: `npm ci`.
4. Start the frontend: `npm run dev`. Vite proxies `/api` and `/health` to port 8000.
5. Production validation: `npm run build`.

## Features

- Interactive conceptual PMMA visualization with drag, zoom, pause and reduced-motion support.
- Model inputs, supported-envelope validation, prediction results and on-demand scientific briefings.
- Searchable research catalog, browser-local saved scenarios and JSON export.
- Responsive phone layout and a bounded startup loader with a WebGL fallback.

The orange and blue particles are a conceptual illustration, not simulated flame geometry or measured temperature. Model scores are research outputs, not safety certification.

## Vercel deployment

Deploy the repository root using the Vite preset. `vercel.json` serves the frontend and routes API requests to `api/index.py`, which imports the existing FastAPI application. Backend model logic is unchanged.

The backend works without a provider key and labels its local briefing fallback. To enable provider-generated briefings, configure `GROQ_API_KEY` and optionally `QWEN_MODEL` in Vercel's server-side environment. Never put these secrets in `VITE_` variables.
