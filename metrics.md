## Model Evaluation Metrics (`CombustionResNet`)

Evaluated on the held-out test split of the 51-run NASA BASS-II (`PSI-25`) 6.35 mm PMMA rod stagnation-flame dataset (100 training epochs, exported in `model_artifacts.json`):

| Metric | Score | Percentage |
| :--- | :--- | :--- |
| **Recall (Fire Sensitivity)** | `0.8333` | 83.33% |
| **F1 Score** | `0.6250` | 62.50% |
| **Precision** | `0.5000` | 50.00% |
| **Accuracy** | `0.4545` | 45.45% |

**Safety Calibration Note:** The decision threshold and class weighting deliberately prioritize **Recall (83.33%)** over raw accuracy. In a microgravity spacecraft cabin, missing a self-sustaining flame (a false negative) is a severe crew hazard, whereas flagging a borderline condition (a false positive) triggers a  ventilation and hardware check.
