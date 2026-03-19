# autoaquaponics

Autonomous optimization of a parametric aquaponics system design.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — instead of optimizing an LLM's validation loss, this project optimizes **tilapia harvest weight** in a closed-loop RAS (Recirculating Aquaculture System).

An AI agent autonomously modifies the design parameters of a CadQuery 3D model, evaluates the predicted tilapia growth using an aquaculture science scoring model, keeps improvements, and discards regressions. It runs every hour on GitHub Actions.

## The idea

Give an AI agent a parametric aquaponics design and let it experiment autonomously. It modifies design parameters, evaluates the predicted harvest weight, checks if the result improved, keeps or discards, and repeats. You check back later to find an optimized system design and a log of experiments.

**Current target:** Increase red tilapia harvest weight from **300g → 450g** in 5.5 months.

## How it works

Three files that matter:

- **`evaluate.py`** — fixed scoring model. Simulates daily tilapia growth over 165 days using environmental factors (temperature, DO, density, water quality, flow rate). Not modified.
- **`design.py`** — the file the agent edits. Contains all design parameters + CadQuery 3D model. Everything is fair game: tank size, biofilter config, stocking density, aeration, temperature management.
- **`program.md`** — instructions for the AI agent. Edited by humans to guide the optimization strategy.

Supporting files:
- **`optimize.py`** — automation script that calls Claude API, proposes changes, evaluates, and commits.
- **`.github/workflows/optimize.yml`** — runs `optimize.py` every hour via GitHub Actions.

## The system

A closed-loop RAS for red tilapia in Barbosa, Antioquia, Colombia (1,300m ASL):

| Component | Specification |
|-----------|---------------|
| Structure | 25ft x 12ft lean-to greenhouse |
| Fish tank | 1x round HDPE (500L baseline) |
| Biofilter | MBBR barrels with K1 media |
| Sump | Rectangular HDPE at grade |
| Water pump | Lifts from sump to fish tank |
| Air pump | Aeration for tank + biofilter |
| Water path | Tank → Biofilter (gravity) → Sump (gravity) → Pump → Tank |

## Quick start

```bash
# 1. Install dependencies
pip install anthropic cadquery

# 2. Run baseline evaluation (no API key needed)
python design.py

# 3. Run one optimization experiment (needs ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY="your-key-here"
python optimize.py

# 4. View the CAD model in VSCode (needs OCP CAD Viewer extension)
pip install ocp-vscode
python design.py --render
```

## GitHub Actions setup

1. Fork this repo
2. Go to Settings → Secrets → Actions
3. Add `ANTHROPIC_API_KEY` as a repository secret
4. The workflow runs automatically every hour, or trigger manually from Actions tab

Each run:
- Creates/continues a daily experiment branch (`autoaquaponics/YYYY-MM-DD`)
- Runs up to 3 experiments per invocation
- Pushes improvements to the branch
- Uploads run logs as artifacts

## Scoring model

The `evaluate.py` scoring function simulates 165 days of tilapia growth using:

| Factor | How it affects growth | Optimal value |
|--------|----------------------|---------------|
| Temperature | SGR multiplier 0-1.0 | 26-30°C |
| Dissolved Oxygen | SGR multiplier 0-1.0 | >6 mg/L |
| Stocking Density | SGR multiplier 0-1.0 | <15 kg/m³ |
| Water Quality | TAN removal ratio | Biofilter > 2x TAN production |
| Flow Rate | Turnover rate | 1-2 turnovers/hour |

Factors multiply the size-dependent base SGR (Specific Growth Rate). Small improvements compound exponentially over 165 days.

## Design choices

- **Single metric.** Predicted harvest weight in grams. Higher is better. Simple.
- **Science-based scoring.** Growth model uses established aquaculture parameters (SGR curves, TAN production rates, K1 media specs, altitude DO correction).
- **Constraint validation.** Structure must fit 25x12ft, gravity cascade must work, pump must be adequate. Failed constraints = crashed experiment.
- **CadQuery CAD output.** The design isn't just numbers — it generates a real 3D model viewable in OCP CAD Viewer. Design changes are visible.

## Viewing the model

In VSCode with the [OCP CAD Viewer](https://marketplace.visualstudio.com/items?itemName=niclas-2-ocp-viewer) extension:

```bash
pip install ocp-vscode
python design.py --render
```

This renders 14 toggleable layers (posts, framing, roof, fish tank, biofilter, plumbing, aeration, etc.) to the OCP CAD Viewer panel on port 3939.

## License

MIT
