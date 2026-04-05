# CLAUDE.md

## Project Overview

**autoaquaponics** is an autonomous aquaculture design optimization system. An AI agent iterates on a parametric CadQuery 3D model of a tilapia RAS (Recirculating Aquaculture System), maximizing predicted harvest weight. Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

**Target:** Increase red tilapia harvest weight from 300g to 450g in 5.5 months (165 days).

## Repository Structure

```
autoaquaponics/
├── design.py          # Design parameters + CadQuery 3D model (AI-editable)
├── evaluate.py        # Growth simulation & scoring (READ-ONLY, do not modify)
├── optimize.py        # Claude API integration & experiment loop
├── program.md         # Instructions for the AI optimization agent
├── results.tsv        # Experiment history log
├── pyproject.toml     # Python package config
├── README.md          # Project overview
└── .github/workflows/
    └── optimize.yml   # Hourly GitHub Actions workflow
```

## Key Rules

- **NEVER modify `evaluate.py`** — it is the fixed scoring model / ground truth.
- **`design.py` is the primary file the AI agent edits** — all design parameters live here.
- **`program.md` is edited by humans** — it guides the AI agent's optimization strategy.
- **`optimize.py` orchestrates the loop** — calls Claude API, applies changes, evaluates, commits/discards.

## Architecture

### The Optimization Loop

1. Claude reads `design.py` (current params), `results.tsv` (history), `program.md` (instructions)
2. Proposes parameter changes to `design.py`
3. `evaluate.py` simulates 165 days of tilapia growth using multiplicative SGR factors
4. If weight improves and constraints pass → keep. Otherwise → discard and git reset.
5. Result appended to `results.tsv`
6. Runs hourly on GitHub Actions (up to 3 experiments per invocation)

### Scoring Model (`evaluate.py`)

Growth factors that multiply the base Specific Growth Rate (SGR) daily:

| Factor | Optimal Range | Notes |
|--------|--------------|-------|
| Temperature | 26-30C | Barbosa baseline 23C + greenhouse/insulation boosts |
| Dissolved Oxygen | >6 mg/L | Aeration efficiency vs. fish biomass O2 demand |
| Stocking Density | <15 kg/m3 | Lower density = better individual growth |
| Water Quality | Biofilter > 2x TAN production | MBBR K1 media removal capacity |
| Turnover Rate | 2.5-4.0 turnovers/hr | >4.0 is penalized |

Small factor improvements compound exponentially over 165 days.

### Hard Constraints (must all pass)

- Structure fits within 25ft x 12ft footprint
- Gravity cascade works (tank → biofilter → sump elevation)
- Pump TDH (total dynamic head) is adequate
- Final stocking density within acceptable range

## Development

### Prerequisites

- Python 3.10+
- `ANTHROPIC_API_KEY` environment variable (for optimization runs)

### Commands

```bash
# Install dependencies
pip install anthropic cadquery

# Run baseline evaluation (no API key needed)
python design.py

# View 3D CAD model in VSCode OCP CAD Viewer
pip install ocp-vscode
python design.py --render

# Run one optimization experiment
export ANTHROPIC_API_KEY="your-key-here"
python optimize.py

# Run multiple experiments
python optimize.py --max-experiments 5
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes (for optimize.py) | Claude API authentication |
| `AUTOAQUAPONICS_TARGET` | No (default: 450) | Target harvest weight in grams |
| `AUTOAQUAPONICS_PARAMS_ONLY` | No | Skip CAD rendering in CI |

## Code Conventions

- **No test suite** — `evaluate.py` serves as the validation. If constraints pass and weight improves, the experiment succeeds.
- **No linter or formatter configured** — focus is on functional correctness.
- **Flat structure** — no subdirectories for source code. All core files at root.
- **`design.py` exports a `PARAMS` dict** — consumed by `evaluate.py` for scoring.
- **Parameters are Python constants** at the top of `design.py` (e.g., `STOCKING_COUNT = 10`, `FISH_TANK_DIA = 1300`).
- **Multi-tank support** — `NUM_TANKS` parameter scales the system (1, 2, or 3 tanks sharing infrastructure).

## CI/CD

GitHub Actions workflow (`.github/workflows/optimize.yml`):
- **Trigger:** Cron every hour (`0 * * * *`) + manual dispatch
- **Branch strategy:** Creates daily branches (`autoaquaponics/YYYY-MM-DD`)
- **Steps:** Checkout → install deps → run `optimize.py --max-experiments 3` → commit results → push
- **Secret:** `ANTHROPIC_API_KEY` in repository secrets
- **Bot identity:** `autoaquaponics-bot <autoaquaponics-bot@users.noreply.github.com>`

## Current Design State

As of the latest commit (`24efe5b`):
- `STOCKING_COUNT = 10` fish per tank
- `FISH_TANK_DIA = 1300mm`, `FISH_TANK_H = 900mm` (~633L practical volume)
- `BIO_BARREL_COUNT = 4`, `BIO_FILL_RATIO = 0.60`
- `PUMP_FLOW_LPM = 35` (~3.3 turnovers/hr per tank)
- `AIR_PUMP_FLOW_LPM = 95`
- `NUM_TANKS = 2` (two tanks sharing infrastructure)

## Optimization Levers

Key strategies documented in `program.md`:
1. Reduce stocking count (lower density stress)
2. Increase tank volume (more space per fish)
3. Add biofilter capacity (better water quality)
4. Boost aeration (higher DO)
5. Optimize temperature (greenhouse + insulation gains)
6. Tune pump flow for optimal turnover rate
7. Scale to multiple tanks sharing infrastructure
