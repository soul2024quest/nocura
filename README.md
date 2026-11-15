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


## Discovery redesign sandbox

This repository is an isolated redesign copy of the submitted Nocura application at commit `4fdbfbb`. Changes here deploy to the separate `nocura-next` Vercel project. Do not deploy this repository to the submitted `nocura` project.

The discovery homepage has four scroll-driven chapters, the ESA/NASA BASS-II reference photograph, guided scenarios, research context, and a dedicated evidence page. The laboratory retains the existing backend and lazy-loads Three.js only when opened. Reduced-motion users get a static introduction and can open the laboratory directly. Saved scenarios remain local to each site origin.

Run `npm ci` and `npm run dev`. The default API proxy is `http://127.0.0.1:8000`. To use the sandbox backend during frontend development, set `NOCURA_API_TARGET=https://nocura-next-dp.vercel.app` before starting Vite. No Groq key is needed for prediction or the local fallback; add the key server-side in the new Vercel project when ready.

Recorded evaluation on the Evidence page is from `model_artifacts.json`: 8/11 correct classifications, matrix [[2,3],[0,6]]. It is not independent validation. Source code links require repository access while this repository is private.
