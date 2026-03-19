# autoaquaponics

Autonomous optimization of a closed-loop RAS tilapia aquaponics system.
Instead of minimizing validation loss on a neural network, you are
**maximizing predicted tilapia harvest weight** (target: 450g in 5.5 months).

## Setup

To set up a new experiment run:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar16`). The branch `autoaquaponics/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autoaquaponics/<tag>` from current main.
3. **Read the in-scope files**: The repo is small. Read these for full context:
   - `README.md` — repository context and project overview.
   - `evaluate.py` — fixed scoring model (growth simulation + constraint validation). **Do not modify.**
   - `design.py` — the file you modify. All design parameters + CadQuery CAD model.
4. **Initialize results.tsv**: Create `results.tsv` with just the header row. The baseline will be recorded after the first run.
5. **Confirm and go**: Confirm setup looks good, then kick off experimentation.

## The System

A closed-loop Recirculating Aquaculture System (RAS) for red tilapia, enclosed in a 25ft x 12ft lean-to greenhouse in Barbosa, Antioquia, Colombia (1,300m ASL).

**Components (fixed set — do not add or remove component types):**
- 1x round HDPE fish tank (on elevated stand)
- 1x biofilter system (MBBR barrels with K1 media, in series)
- 1x sump tank (at grade)
- 1x water pump (lifts water from sump to fish tank)
- 1x air pump (aeration for tank + biofilter)
- PVC plumbing (supply, drain, inter-barrel, overflow)
- Lean-to greenhouse structure (posts, rafters, purlins, polycarbonate roof)

**Water pathway:** Fish Tank → Biofilter (gravity) → Sump (gravity) → Pump → Fish Tank

**NO grow beds. NO hydroponics. NO bell siphons.** This is pure RAS.

## Experimentation

Each experiment modifies `design.py` and evaluates the result.

**What you CAN do:**
- Modify `design.py` — this is the only file you edit. Everything is fair game:
  - Tank dimensions (diameter, height, volume)
  - Stand height (affects hydraulic grade line)
  - Biofilter configuration (barrel count, fill ratio, media specs)
  - Stocking count (fewer fish = lower density = bigger individual fish)
  - Pump and air pump specifications
  - Temperature management (insulation boost, greenhouse parameters)
  - Component positions (within the 25x12ft envelope)
  - Pipe dimensions
  - Any parameter in the PARAMS dict

**What you CANNOT do:**
- Modify `evaluate.py`. It is read-only. It contains the fixed growth model.
- Add grow beds, hydroponics, or any banned components.
- Exceed the 25ft x 12ft structural envelope.
- Install new packages beyond what's in `pyproject.toml`.

**The goal: maximize `predicted_weight_g`.** The current baseline produces ~300g.
The target is 450g. All constraints must pass.

## Scoring

Run the evaluation:
```bash
python design.py > run.log 2>&1
```

Extract the key metric:
```bash
grep "^predicted_weight_g:" run.log
```

The scoring model simulates daily tilapia growth over 165 days (5.5 months)
using these factors:
- **Temperature** — optimal 26-30°C, Barbosa ambient is 23°C + greenhouse effect
- **Dissolved Oxygen** — depends on aeration capacity vs. biomass
- **Stocking Density** — lower density = less stress = bigger fish
- **Water Quality** — biofilter TAN removal capacity vs. ammonia production
- **Turnover Rate** — pump flow / tank volume, optimal 1-2x/hour

Each factor multiplies the base Specific Growth Rate (SGR). The product
determines daily weight gain. Small improvements compound over 165 days.

## Key optimization levers

Think about these when proposing changes:

1. **Reduce stocking count** — Fewer fish = lower density at harvest = less growth
   suppression. But: fewer fish to sell. The scoring function only cares about
   individual weight, not total yield.

2. **Increase biofilter capacity** — More barrels, higher fill ratio, or better
   media = more TAN removal = cleaner water = better growth factor.

3. **Boost aeration** — Higher air pump flow = higher DO = better growth.
   Especially impactful at high biomass.

4. **Temperature management** — Insulation boost, greenhouse improvements.
   Each degree closer to 28°C helps significantly at Barbosa's altitude.

5. **Tank volume** — Larger tank = lower density at same fish count. But must
   fit within structure and maintain gravity cascade.

6. **Pump sizing** — Better turnover rate improves water mixing and quality
   distribution. Optimal is 1-2 turnovers/hour.

7. **Stand height** — Affects hydraulic grade line. Higher stand = more gravity
   head for biofilter cascade, but pump must push water higher.

## Constraints that MUST pass

- Structure ≤ 25ft x 12ft (7620 x 3657.6mm)
- Tank fits inside structure with clearance
- Gravity cascade works (tank rim > biofilter top > sump inlet)
- Pump TDH ≤ 3.0m
- Density at 450g target < 60 kg/m³
- At least 1 biofilter barrel
- Pump flow > 5 LPM
- Air pump flow > 5 LPM

If constraints fail, the experiment is marked as `crash` regardless of weight.

## Output format

The script prints a summary:
```
---
predicted_weight_g:     312.45
total_harvest_kg:       7.81
surviving_fish:         25
final_density_kg_m3:    15.6
effective_temp_c:       28.0
effective_do_mg_l:      6.2
biofilter_cap_g_day:    37.5
turnovers_per_hour:     8.0
constraints_pass:       True
```

## Logging results

Log each experiment to `results.tsv` (tab-separated):

```
commit	predicted_weight_g	constraints	status	description
```

1. git commit hash (short, 7 chars)
2. predicted_weight_g (e.g. 312.45) — use 0.00 for crashes
3. constraints: `pass` or `fail`
4. status: `keep`, `discard`, or `crash`
5. short description of what this experiment tried

Example:
```
commit	predicted_weight_g	constraints	status	description
a1b2c3d	312.45	pass	keep	baseline
b2c3d4e	328.10	pass	keep	reduce stocking from 28 to 20
c3d4e5f	0.00	fail	crash	tank too large for structure
```

## The experiment loop

LOOP FOREVER:

1. Look at git state and results.tsv history
2. Propose a design change in `design.py` by modifying parameters
3. git commit the change
4. Run: `python design.py > run.log 2>&1`
5. Read results: `grep "^predicted_weight_g:\|^constraints_pass:" run.log`
6. If grep is empty, the run crashed. Read `tail -n 30 run.log` for the error.
7. Record results in results.tsv
8. If predicted_weight_g improved AND constraints pass → keep (advance branch)
9. If weight is equal/worse OR constraints fail → git reset back
10. Think about what to try next based on the full history of experiments

**Timeout**: Each evaluation takes <10 seconds (no ML training). If it hangs for >60 seconds, kill and treat as crash.

**NEVER STOP**: Once the loop begins, do NOT pause to ask the human. Run indefinitely until manually stopped. If you run out of ideas, re-read the scoring factors, try combinations, try edge cases, try optimizing multiple parameters at once.

## Science hints

- Red tilapia grow fastest at 28°C with DO >6 mg/L
- At Barbosa (1,300m ASL), ambient is 23°C — greenhouse adds ~4°C
- DO saturation at 1,300m is ~7.5 mg/L (lower than sea level)
- K1 media: 500 m²/m³ surface area, ~0.5 g NH3/m²/day nitrification
- Tilapia SGR (Specific Growth Rate) decreases as fish grow larger
- Optimal stocking density for growth: <15 kg/m³
- TAN production: ~30g per kg feed consumed
- Feed rate: 1.5-5% body weight/day depending on fish size
- The growth factors multiply — improving multiple factors compounds gains
