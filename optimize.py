"""
Autonomous optimization loop for autoaquaponics.
Calls Claude API to propose design changes, evaluates them, keeps or discards.

This is the GitHub Actions entry point. Runs one experiment per invocation.
The workflow calls this every hour via cron.

Usage:
    python optimize.py                    # run one experiment
    python optimize.py --max-experiments 5  # run up to 5 experiments
    python optimize.py --dry-run          # propose change but don't commit

Requires:
    ANTHROPIC_API_KEY environment variable
"""

import os
import sys
import subprocess
import time
import re
import argparse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DESIGN_FILE = "design.py"
EVALUATE_FILE = "evaluate.py"
PROGRAM_FILE = "program.md"
RESULTS_FILE = "results.tsv"
RUN_LOG = "run.log"
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 16384
TIMEOUT_SECONDS = 120


def run_cmd(cmd, timeout=TIMEOUT_SECONDS, capture=True):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def read_file(path):
    """Read file contents, return empty string if not found."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def write_file(path, content):
    """Write content to file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_git_hash():
    """Get current short git commit hash."""
    rc, out, _ = run_cmd("git rev-parse --short HEAD")
    return out.strip() if rc == 0 else "unknown"


def git_commit(message):
    """Stage design.py and commit."""
    run_cmd(f'git add {DESIGN_FILE}')
    rc, _, err = run_cmd(f'git commit -m "{message}"')
    return rc == 0


def git_reset_last():
    """Revert the last commit (discard failed experiment).
    Falls back to restoring just design.py if HEAD~1 doesn't exist
    (e.g., only one commit in the repo).
    """
    rc, _, _ = run_cmd("git rev-parse --verify HEAD~1")
    if rc == 0:
        run_cmd("git reset --hard HEAD~1")
    else:
        # Only 1 commit exists — can't reset further.
        # Restore design.py from HEAD (undo uncommitted changes at minimum).
        print("  WARNING: Cannot reset HEAD~1 (only 1 commit). Restoring design.py from HEAD.")
        run_cmd(f"git checkout HEAD -- {DESIGN_FILE}")


def init_results_tsv():
    """Create results.tsv with header if it doesn't exist."""
    if not os.path.exists(RESULTS_FILE):
        write_file(RESULTS_FILE, "commit\tpredicted_weight_g\tconstraints\tstatus\tdescription\n")


def append_result(commit, weight, constraints, status, description):
    """Append one row to results.tsv."""
    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{commit}\t{weight:.2f}\t{constraints}\t{status}\t{description}\n")


def parse_run_log(log_content):
    """Extract predicted_weight_g and constraints_pass from run log."""
    weight = 0.0
    constraints = "fail"
    for line in log_content.split("\n"):
        if line.startswith("predicted_weight_g:"):
            try:
                weight = float(line.split(":")[1].strip())
            except ValueError:
                pass
        if line.startswith("constraints_pass:"):
            val = line.split(":")[1].strip()
            constraints = "pass" if val == "True" else "fail"
    return weight, constraints


def get_best_weight():
    """Get the best predicted_weight_g from results.tsv (kept experiments only)."""
    best = 0.0
    content = read_file(RESULTS_FILE)
    for line in content.strip().split("\n")[1:]:  # skip header
        parts = line.split("\t")
        if len(parts) >= 4 and parts[3] == "keep":
            try:
                w = float(parts[1])
                best = max(best, w)
            except ValueError:
                pass
    return best


# ---------------------------------------------------------------------------
# Claude API integration
# ---------------------------------------------------------------------------

def call_claude(prompt):
    """Call Claude API to get a design modification proposal.
    Returns the proposed new design.py content.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print("Installing anthropic SDK...")
        run_cmd(f"{sys.executable} -m pip install anthropic -q")
        import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract the text response
    response_text = ""
    for block in message.content:
        if hasattr(block, "text"):
            response_text += block.text

    return response_text


def build_prompt(design_content, results_content, program_content, best_weight):
    """Build the prompt for Claude to propose a design change."""
    return f"""You are an autonomous aquaponics design optimizer. Your goal is to
maximize the predicted tilapia harvest weight by modifying design.py parameters.

## Current best weight: {best_weight:.2f}g (target: 450g)

## Instructions (from program.md):
{program_content}

## Current design.py:
```python
{design_content}
```

## Experiment history (results.tsv):
```
{results_content}
```

## Your task:
1. Analyze the current design parameters and experiment history
2. Identify which growth factors are BELOW 1.0 (these are the bottlenecks)
3. Propose changes to design.py that will improve predicted_weight_g
4. You may change MULTIPLE parameters at once if they work together
5. Explain your reasoning in 2-3 sentences
6. Output the COMPLETE modified design.py file

IMPORTANT RULES:
- Only modify parameter values in the DESIGN PARAMETERS section at the top
- Do NOT modify the PARAMS dict structure, CadQuery code, or evaluate imports
- Do NOT modify evaluate.py (it's read-only)
- All constraints must still pass (structure fits 25x12ft, gravity works, etc.)
- FISH_TANK_VOLUME_L is computed from geometry (diameter and height) - to change volume, change the tank dimensions
- Think about which growth factors have the most room for improvement
- Try changes that are different from what's been tried before

DIAGNOSTIC HINTS (from evaluate.py analysis):
- turnover_factor: optimal at 2.5-4.0 turnovers/hr (pump_flow_lpm * 60 / tank_volume_l). Above 4.0 is penalized to 0.95.
- temperature_factor: optimal 26-30C. Above 30C is sharply penalized. Current ambient+boosts may already be near 30C.
- density_factor: lower density = better. Increasing tank volume (via larger diameter/height) reduces density.
- water_quality_factor: likely already at 1.0 if biofilter capacity >> TAN production.
- dissolved_oxygen_factor: check if DO is already near saturation before boosting air pump.
- Growth factors MULTIPLY. A 5% fix to one factor compounds over 165 days.

Output format:
REASONING: <1-2 sentence explanation of what you're changing and why>
DESCRIPTION: <short tab-safe description for results.tsv, no tabs or commas>

```python
<complete design.py file content>
```
"""


def extract_design_from_response(response):
    """Extract the python code block from Claude's response."""
    # Find the last python code block (the complete file)
    pattern = r"```python\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)
    if matches:
        return matches[-1].strip()
    return None


def extract_description(response):
    """Extract the DESCRIPTION line from Claude's response."""
    for line in response.split("\n"):
        if line.startswith("DESCRIPTION:"):
            desc = line.replace("DESCRIPTION:", "").strip()
            # Remove tabs and commas (break TSV)
            return desc.replace("\t", " ").replace(",", ";")
    return "AI-proposed design change"


# ---------------------------------------------------------------------------
# Main experiment loop
# ---------------------------------------------------------------------------

def run_one_experiment(dry_run=False):
    """Run a single experiment: propose change, evaluate, keep or discard."""
    print(f"\n{'='*60}")
    print(f"  AUTOAQUAPONICS -- Experiment starting...")
    print(f"{'='*60}\n")

    # Safety check: if design.py has uncommitted changes from a crashed prior run,
    # restore the committed version before starting a new experiment.
    rc, diff_out, _ = run_cmd(f"git diff --name-only {DESIGN_FILE}")
    if rc == 0 and DESIGN_FILE in (diff_out or ""):
        print("  WARNING: design.py has uncommitted changes (leftover from crash?). Restoring from HEAD.")
        run_cmd(f"git checkout HEAD -- {DESIGN_FILE}")

    init_results_tsv()

    # Read current state
    design_content = read_file(DESIGN_FILE)
    results_content = read_file(RESULTS_FILE)
    program_content = read_file(PROGRAM_FILE)
    best_weight = get_best_weight()

    # Check if we need a baseline first
    if "keep" not in results_content and "baseline" not in results_content:
        print("Running baseline evaluation first...")
        os.environ["AUTOAQUAPONICS_PARAMS_ONLY"] = "1"
        rc, _, _ = run_cmd(f"{sys.executable} {EVALUATE_FILE} > {RUN_LOG} 2>&1")
        log_content = read_file(RUN_LOG)
        weight, constraints = parse_run_log(log_content)

        if weight > 0 and constraints == "pass":
            git_commit("baseline: initial design")
            commit_hash = get_git_hash()
            append_result(commit_hash, weight, constraints, "keep", "baseline")
            print(f"  Baseline: {weight:.2f}g [KEEP]")
            return {"status": "keep", "weight": weight, "description": "baseline"}
        else:
            print(f"  Baseline FAILED: weight={weight}, constraints={constraints}")
            print(f"  Log tail:\n{log_content[-500:]}")
            return {"status": "crash", "weight": 0, "description": "baseline failed"}

    print(f"  Current best: {best_weight:.2f}g")
    print(f"  Target: 450g")
    print(f"  Calling Claude API for design proposal...")

    # Get AI proposal
    prompt = build_prompt(design_content, results_content, program_content, best_weight)
    response = call_claude(prompt)

    new_design = extract_design_from_response(response)
    description = extract_description(response)

    if not new_design:
        print("  ERROR: Could not extract design.py from Claude response")
        print(f"  Response preview: {response[:500]}")
        return {"status": "crash", "weight": 0, "description": "failed to parse AI response"}

    print(f"  Proposal: {description}")

    if dry_run:
        print("  [DRY RUN] Would write design.py and evaluate")
        print(f"  Design preview (first 200 chars):\n{new_design[:200]}")
        return {"status": "dry_run", "weight": 0, "description": description}

    # Write new design
    write_file(DESIGN_FILE, new_design)

    # Commit the change
    commit_msg = f"experiment: {description}"
    if not git_commit(commit_msg):
        print("  WARNING: git commit failed (no changes?)")

    commit_hash = get_git_hash()

    # Evaluate (use evaluate.py directly — skip CAD build for speed and stability)
    print(f"  Evaluating design...")
    os.environ["AUTOAQUAPONICS_PARAMS_ONLY"] = "1"
    rc, _, _ = run_cmd(f"{sys.executable} {EVALUATE_FILE} > {RUN_LOG} 2>&1")
    log_content = read_file(RUN_LOG)
    weight, constraints = parse_run_log(log_content)

    print(f"  Result: {weight:.2f}g, constraints={constraints}")

    # Decide: keep or discard
    if weight > 0 and constraints == "pass" and weight > best_weight:
        status = "keep"
        print(f"  IMPROVEMENT: {best_weight:.2f}g -> {weight:.2f}g (+{weight-best_weight:.2f}g) [KEEP]")
    elif weight > 0 and constraints == "pass" and weight <= best_weight:
        status = "discard"
        print(f"  No improvement: {weight:.2f}g <= {best_weight:.2f}g [DISCARD]")
        git_reset_last()
    else:
        status = "crash"
        print(f"  CRASH/FAIL: weight={weight}, constraints={constraints} [DISCARD]")
        if log_content:
            print(f"  Log tail:\n{log_content[-300:]}")
        git_reset_last()

    # Log result (results.tsv is untracked, always append)
    append_result(commit_hash, weight, constraints, status, description)

    return {"status": status, "weight": weight, "description": description}


def main():
    parser = argparse.ArgumentParser(description="Autoaquaponics optimization loop")
    parser.add_argument("--max-experiments", type=int, default=1,
                        help="Maximum experiments to run (default: 1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Propose change but don't commit")
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    for i in range(args.max_experiments):
        print(f"\n--- Experiment {i+1}/{args.max_experiments} ---")
        result = run_one_experiment(dry_run=args.dry_run)

        if result["status"] == "crash" and i == 0:
            print("First experiment crashed. Check design.py and evaluate.py.")
            sys.exit(1)

        if result["weight"] >= 450:
            print(f"\n  TARGET REACHED: {result['weight']:.2f}g >= 450g!")
            break

        # Brief pause between experiments
        if i < args.max_experiments - 1:
            time.sleep(2)

    # Print final summary
    print(f"\n{'='*60}")
    print(f"  AUTOAQUAPONICS -- Session complete")
    print(f"  Experiments run: {i+1}")
    print(f"  Best weight: {get_best_weight():.2f}g")
    print(f"  Target: 450g")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
