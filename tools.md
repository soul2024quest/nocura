## Tools & Libraries Used

### Machine Learning & Data Processing
* **PyTorch:** Used to build and train the `CombustionResNet` residual neural network on the NASA BASS-II (`PSI-25`) microgravity combustion dataset.
* **scikit-learn:** Used for feature standardization (`StandardScaler`), train/test splitting, and computing held-out evaluation metrics (recall, precision, F1 score, and accuracy).
* **Pandas & NumPy:** Used for ingesting the experimental CSV data, applying logarithmic ($\log_{10}$) airflow scaling, and exporting model weights to JSON (`model_artifacts.json`).

### Backend & AI Briefing Pipeline
* **Python:** Core language for model training, deterministic pure-Python edge inference, and API routing.
* **FastAPI & Uvicorn:** Used to serve the REST API endpoints (`/api/predict` and `/api/followup`), enforce operational envelope guards, and deliver sub-millisecond inference without GPU dependencies.
* **Groq API (Qwen):** Used to generate plain-English astronaut briefings and answer interactive follow-up "what-if" scenario questions, paired with a deterministic local fallback when disabled.

### Frontend & Visualization
* **React:** Used to build the interactive web interface, telemetry sliders, and NASA PSI investigation explorer (`BASS-II`, `Saffire-II`, `SAME`, `FLEX`).
* **Vite:** Used as the frontend build tool and development server.
* **JavaScript / TypeScript, HTML5 & CSS3:** Used for state management, responsive layout, and the real-time microgravity flame visualizer.

### Development, Hosting & AI Assistance
* **Git & GitHub:** Version control and source code hosting (`soul2024quest/nocura`).
* **Vercel:** Cloud hosting and deployment for the live frontend application (`nocura.vercel.app`).
* **Visual Studio Code:** Local development environment.
* **ChatGPT & Gemini:** Used during development for debugging, code cleanup, and technical documentation.
