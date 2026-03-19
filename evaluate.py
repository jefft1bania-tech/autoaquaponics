"""
Fixed evaluation engine for autoaquaponics experiments.
Computes predicted tilapia harvest weight from design parameters.

DO NOT MODIFY THIS FILE. This is the ground truth scoring function.
The agent modifies design.py only.

Usage:
    python evaluate.py                # evaluate current design.py
    python evaluate.py --verbose      # show daily growth simulation detail

Scoring model based on:
    - Red tilapia (Oreochromis sp.) growth curves from aquaculture literature
    - Specific Growth Rate (SGR) model with environmental modifiers
    - Constraint validation for structural/hydraulic feasibility
"""

import math
import sys
import importlib
import importlib.util
import types

# ---------------------------------------------------------------------------
# Constants (fixed, do not modify)
# ---------------------------------------------------------------------------

GROW_OUT_DAYS = 165             # 5.5 months fixed time budget
FINGERLING_WEIGHT_G = 7.0      # starting weight (grams)
MORTALITY_RATE = 0.10           # 10% expected loss

# Structure limits
MAX_LENGTH_MM = 25 * 304.8     # 7620mm
MAX_WIDTH_MM = 12 * 304.8      # 3657.6mm

# Tilapia biology constants
OPTIMAL_TEMP_C = 28.0
MIN_VIABLE_TEMP_C = 18.0
MAX_VIABLE_TEMP_C = 34.0
OPTIMAL_DO_MG_L = 6.0
MIN_DO_MG_L = 2.0
TAN_PER_KG_FEED = 30.0         # grams TAN per kg feed consumed
K1_SURFACE_AREA_M2_PER_M3 = 500
K1_NITRIFICATION_RATE = 0.5    # g NH3/m2/day (conservative)

# Barbosa climate baseline
BARBOSA_AMBIENT_C = 23.0       # average ambient temp
GREENHOUSE_BOOST_C = 4.0       # polycarbonate greenhouse effect

# ---------------------------------------------------------------------------
# Growth model: SGR-based daily simulation
# ---------------------------------------------------------------------------

def sgr_base(weight_g):
    """Size-dependent base Specific Growth Rate (%/day) for red tilapia
    at optimal conditions (28C, high DO, low density, clean water).
    Larger fish have lower SGR — well-established in aquaculture literature.
    Calibrated so that optimal conditions yield ~450g in 165 days,
    while baseline Barbosa conditions yield ~300g.
    Reference: Abdel-Tawwab et al. (2010), El-Sayed (2006).
    """
    if weight_g < 10:
        return 5.0
    elif weight_g < 30:
        return 4.2
    elif weight_g < 80:
        return 3.3
    elif weight_g < 150:
        return 2.5
    elif weight_g < 250:
        return 2.0
    elif weight_g < 350:
        return 1.6
    elif weight_g < 450:
        return 1.3
    elif weight_g < 600:
        return 0.9
    else:
        return 0.5


def temperature_factor(effective_temp_c):
    """Growth modifier for water temperature.
    Optimal: 26-30C. Drops sharply below 22C and above 32C.
    Returns 0.0-1.0 multiplier on SGR.
    """
    if effective_temp_c < MIN_VIABLE_TEMP_C:
        return 0.0
    elif effective_temp_c < 22:
        return 0.15 + (effective_temp_c - MIN_VIABLE_TEMP_C) / (22 - MIN_VIABLE_TEMP_C) * 0.35
    elif effective_temp_c < 26:
        return 0.50 + (effective_temp_c - 22) / (26 - 22) * 0.50
    elif effective_temp_c <= 30:
        return 1.0
    elif effective_temp_c <= 32:
        return 1.0 - (effective_temp_c - 30) / 2.0 * 0.30
    elif effective_temp_c <= MAX_VIABLE_TEMP_C:
        return 0.70 - (effective_temp_c - 32) / 2.0 * 0.50
    else:
        return 0.0


def dissolved_oxygen_factor(do_mg_l):
    """Growth modifier for dissolved oxygen.
    Optimal: >5 mg/L. Critical below 2 mg/L.
    """
    if do_mg_l < MIN_DO_MG_L:
        return 0.10
    elif do_mg_l < 3.0:
        return 0.30 + (do_mg_l - MIN_DO_MG_L) * 0.20
    elif do_mg_l < 5.0:
        return 0.50 + (do_mg_l - 3.0) / 2.0 * 0.40
    elif do_mg_l < 7.0:
        return 0.90 + (do_mg_l - 5.0) / 2.0 * 0.10
    else:
        return 1.0


def density_factor(density_kg_m3):
    """Growth modifier for stocking density.
    Tilapia tolerate high density but grow faster at lower density.
    Optimal: <15 kg/m3. Stress above 30 kg/m3.
    """
    if density_kg_m3 < 5:
        return 1.0
    elif density_kg_m3 < 15:
        return 1.0 - (density_kg_m3 - 5) / 10.0 * 0.05
    elif density_kg_m3 < 25:
        return 0.95 - (density_kg_m3 - 15) / 10.0 * 0.20
    elif density_kg_m3 < 40:
        return 0.75 - (density_kg_m3 - 25) / 15.0 * 0.30
    elif density_kg_m3 < 60:
        return 0.45 - (density_kg_m3 - 40) / 20.0 * 0.25
    else:
        return 0.20


def water_quality_factor(tan_production_g_day, tan_removal_capacity_g_day):
    """Growth modifier for water quality (ammonia stress).
    Based on ratio of biofilter capacity to TAN production.
    Safety factor >2x = excellent. <1x = toxic.
    """
    if tan_production_g_day <= 0:
        return 1.0
    ratio = tan_removal_capacity_g_day / tan_production_g_day
    if ratio >= 3.0:
        return 1.0
    elif ratio >= 2.0:
        return 0.95 + (ratio - 2.0) * 0.05
    elif ratio >= 1.5:
        return 0.85 + (ratio - 1.5) / 0.5 * 0.10
    elif ratio >= 1.0:
        return 0.60 + (ratio - 1.0) / 0.5 * 0.25
    elif ratio >= 0.5:
        return 0.20 + (ratio - 0.5) / 0.5 * 0.40
    else:
        return 0.05  # toxic ammonia levels


def turnover_factor(turnovers_per_hour):
    """Growth modifier for water circulation rate.
    Optimal: 1-2 turnovers/hour. Too low = poor water mixing.
    """
    if turnovers_per_hour < 0.3:
        return 0.40
    elif turnovers_per_hour < 0.5:
        return 0.60 + (turnovers_per_hour - 0.3) / 0.2 * 0.15
    elif turnovers_per_hour < 1.0:
        return 0.75 + (turnovers_per_hour - 0.5) / 0.5 * 0.20
    elif turnovers_per_hour <= 2.5:
        return 0.95 + min((turnovers_per_hour - 1.0) / 1.5 * 0.05, 0.05)
    elif turnovers_per_hour <= 4.0:
        return 1.0
    else:
        return 0.95  # excessive flow stresses fish


# ---------------------------------------------------------------------------
# Derived parameter calculations
# ---------------------------------------------------------------------------

def compute_effective_temp(params):
    """Effective water temperature from greenhouse design."""
    base = params.get("ambient_temp_c", BARBOSA_AMBIENT_C)
    greenhouse = params.get("greenhouse_boost_c", GREENHOUSE_BOOST_C)
    insulation = params.get("insulation_boost_c", 0.0)
    dark_tank = params.get("dark_tank_boost_c", 1.0)  # black HDPE absorbs solar
    return base + greenhouse + insulation + dark_tank


def compute_do(params):
    """Effective dissolved oxygen from aeration system."""
    air_lpm = params.get("air_pump_flow_lpm", 60)
    tank_vol_l = params.get("tank_volume_l", 500)
    # DO model: base saturation at altitude - consumption + aeration contribution
    # At 1300m ASL, DO saturation ~7.5 mg/L at 28C (vs 7.8 at sea level)
    do_saturation = 7.5
    # Fish consumption reduces DO; aeration restores it
    # More air per liter of water = closer to saturation
    air_per_liter = air_lpm / tank_vol_l  # LPM air per liter water
    # Empirical: at 0.1 LPM/L, DO stays near saturation; at 0.01, drops to ~4
    aeration_efficiency = min(1.0, air_per_liter / 0.12)
    fish_count = params.get("stocking_count", 28)
    fish_weight = 200  # mid-cycle average weight for DO calc
    biomass_kg = fish_count * fish_weight / 1000
    o2_demand_factor = biomass_kg / (tank_vol_l / 1000)  # kg fish per m3
    consumption_drop = min(3.0, o2_demand_factor * 0.15)
    effective_do = do_saturation * aeration_efficiency - consumption_drop
    return max(1.0, min(do_saturation, effective_do))


def compute_biofilter_capacity(params):
    """TAN removal capacity in g/day from biofilter configuration."""
    barrel_count = params.get("bio_barrel_count", 3)
    barrel_volume_l = params.get("bio_barrel_volume_l", 208.2)
    fill_ratio = params.get("bio_fill_ratio", 0.60)
    media_surface_area = params.get("bio_media_surface_m2_per_m3",
                                     K1_SURFACE_AREA_M2_PER_M3)
    nitrification_rate = params.get("bio_nitrification_rate",
                                     K1_NITRIFICATION_RATE)
    total_media_l = barrel_count * barrel_volume_l * fill_ratio
    total_media_m3 = total_media_l / 1000
    total_surface_m2 = total_media_m3 * media_surface_area
    capacity_g_day = total_surface_m2 * nitrification_rate
    return capacity_g_day


def compute_turnovers(params):
    """Tank turnovers per hour from pump and tank specs."""
    pump_flow_lpm = params.get("pump_flow_lpm", 66.5)
    tank_vol_l = params.get("tank_volume_l", 500)
    return (pump_flow_lpm * 60) / tank_vol_l


# ---------------------------------------------------------------------------
# Constraint validation
# ---------------------------------------------------------------------------

def validate_constraints(params):
    """Check hard engineering constraints. Returns (pass, list_of_issues)."""
    issues = []

    # Structure must fit in 25x12 ft
    length = params.get("structure_length_mm", MAX_LENGTH_MM)
    width = params.get("structure_width_mm", MAX_WIDTH_MM)
    if length > MAX_LENGTH_MM + 10:
        issues.append(f"Structure length {length:.0f}mm exceeds 25ft ({MAX_LENGTH_MM:.0f}mm)")
    if width > MAX_WIDTH_MM + 10:
        issues.append(f"Structure width {width:.0f}mm exceeds 12ft ({MAX_WIDTH_MM:.0f}mm)")

    # Tank must fit inside structure with clearance
    tank_dia = params.get("fish_tank_dia_mm", 1117.6)
    if tank_dia > width - 200:
        issues.append(f"Tank diameter {tank_dia:.0f}mm too large for {width:.0f}mm width")

    # Gravity cascade must work
    tank_rim_z = params.get("fish_tank_stand_h_mm", 450) + params.get("fish_tank_h_mm", 762)
    bio_inlet_z = params.get("bio_stand_h_mm", 170) + params.get("bio_h_mm", 880)
    sump_inlet_z = params.get("sump_inlet_z_mm", 200)
    if tank_rim_z < bio_inlet_z + 50:
        issues.append(f"Gravity fail: tank rim {tank_rim_z:.0f}mm must be > biofilter top {bio_inlet_z:.0f}mm")

    # Pump TDH check
    static_head_m = tank_rim_z / 1000
    if static_head_m > 3.0:
        issues.append(f"Pump TDH {static_head_m:.1f}m exceeds practical limit for small pump")

    # Stocking density at harvest must be viable
    tank_vol_l = params.get("tank_volume_l", 500)
    fish_count = params.get("stocking_count", 28)
    # Check at 450g target
    max_biomass = fish_count * 0.450 * (1 - MORTALITY_RATE)
    max_density = max_biomass / (tank_vol_l / 1000)
    if max_density > 60:
        issues.append(f"Density at 450g would be {max_density:.0f} kg/m3 (lethal)")

    # Must have at least 1 biofilter barrel
    if params.get("bio_barrel_count", 3) < 1:
        issues.append("Must have at least 1 biofilter barrel")

    # Pump flow must be positive
    if params.get("pump_flow_lpm", 66.5) < 5:
        issues.append("Pump flow too low (<5 LPM)")

    # Air pump must provide some aeration
    if params.get("air_pump_flow_lpm", 60) < 5:
        issues.append("Air pump flow too low (<5 LPM)")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score_design(params, verbose=False):
    """
    Simulate tilapia growth over GROW_OUT_DAYS and return predicted harvest weight.
    This is the primary metric: higher predicted_weight_g is better.
    Target: 450g. Baseline design produces ~300g.

    Returns dict with all computed metrics.
    """
    # Validate constraints first
    constraints_pass, constraint_issues = validate_constraints(params)

    # Compute environmental factors from design
    effective_temp = compute_effective_temp(params)
    effective_do = compute_do(params)
    biofilter_cap = compute_biofilter_capacity(params)
    turnovers_hr = compute_turnovers(params)

    tank_vol_l = params.get("tank_volume_l", 500)
    tank_vol_m3 = tank_vol_l / 1000
    fish_count = params.get("stocking_count", 28)
    surviving_count = int(fish_count * (1 - MORTALITY_RATE))

    # Daily growth simulation
    weight = FINGERLING_WEIGHT_G
    daily_log = []

    for day in range(GROW_OUT_DAYS):
        # Current biomass and density
        current_biomass_kg = (weight * surviving_count) / 1000
        current_density = current_biomass_kg / tank_vol_m3

        # Feed rate (% body weight, decreasing with size)
        if weight < 20:
            feed_pct = 5.0
        elif weight < 80:
            feed_pct = 4.0
        elif weight < 200:
            feed_pct = 3.0
        elif weight < 350:
            feed_pct = 2.0
        else:
            feed_pct = 1.5

        daily_feed_kg = current_biomass_kg * feed_pct / 100
        tan_production = daily_feed_kg * TAN_PER_KG_FEED

        # Compute all growth factors
        f_temp = temperature_factor(effective_temp)
        f_do = dissolved_oxygen_factor(effective_do)
        f_dens = density_factor(current_density)
        f_wq = water_quality_factor(tan_production, biofilter_cap)
        f_turn = turnover_factor(turnovers_hr)

        # Effective SGR
        base_sgr = sgr_base(weight)
        effective_sgr = base_sgr * f_temp * f_do * f_dens * f_wq * f_turn

        # Daily weight gain
        daily_gain = weight * effective_sgr / 100
        weight += daily_gain

        if verbose and day % 15 == 0:
            daily_log.append({
                "day": day,
                "weight_g": weight,
                "sgr_base": base_sgr,
                "sgr_eff": effective_sgr,
                "f_temp": f_temp,
                "f_do": f_do,
                "f_dens": f_dens,
                "f_wq": f_wq,
                "f_turn": f_turn,
                "density_kg_m3": current_density,
                "tan_g_day": tan_production,
            })

    # Final metrics
    harvest_weight_g = round(weight, 2)
    total_harvest_kg = round(surviving_count * weight / 1000, 2)
    final_density = round(surviving_count * weight / 1000 / tank_vol_m3, 1)

    result = {
        "predicted_weight_g": harvest_weight_g,
        "total_harvest_kg": total_harvest_kg,
        "surviving_fish": surviving_count,
        "final_density_kg_m3": final_density,
        "effective_temp_c": round(effective_temp, 1),
        "effective_do_mg_l": round(effective_do, 1),
        "biofilter_capacity_g_day": round(biofilter_cap, 1),
        "turnovers_per_hour": round(turnovers_hr, 1),
        "constraints_pass": constraints_pass,
        "constraint_issues": constraint_issues,
        "daily_log": daily_log,
    }

    return result


# ---------------------------------------------------------------------------
# Standalone evaluation (reads design.py and scores it)
# ---------------------------------------------------------------------------

def load_design_params():
    """Import design.py and extract the PARAMS dict."""
    spec = importlib.util.spec_from_file_location("design",
        __file__.replace("evaluate.py", "design.py"))
    design = importlib.util.module_from_spec(spec)
    # We only need the PARAMS dict, not the CAD execution
    # design.py exports PARAMS at module level
    try:
        spec.loader.exec_module(design)
    except SystemExit:
        pass
    except Exception as e:
        print(f"ERROR loading design.py: {e}")
        sys.exit(1)
    if not hasattr(design, "PARAMS"):
        print("ERROR: design.py must define a PARAMS dict")
        sys.exit(1)
    return design.PARAMS


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv

    params = load_design_params()
    result = score_design(params, verbose=verbose)

    if verbose and result["daily_log"]:
        print("\n--- Growth Simulation (every 15 days) ---")
        print(f"{'Day':>4s} {'Weight':>8s} {'SGR_b':>6s} {'SGR_e':>6s} "
              f"{'T':>5s} {'DO':>5s} {'Dens':>5s} {'WQ':>5s} {'Flow':>5s} "
              f"{'kg/m3':>6s} {'TAN':>6s}")
        for entry in result["daily_log"]:
            print(f"{entry['day']:4d} {entry['weight_g']:8.1f} "
                  f"{entry['sgr_base']:6.2f} {entry['sgr_eff']:6.2f} "
                  f"{entry['f_temp']:5.2f} {entry['f_do']:5.2f} "
                  f"{entry['f_dens']:5.2f} {entry['f_wq']:5.2f} "
                  f"{entry['f_turn']:5.2f} "
                  f"{entry['density_kg_m3']:6.1f} {entry['tan_g_day']:6.2f}")

    # Print summary (matches autoresearch output format)
    print("\n---")
    print(f"predicted_weight_g:     {result['predicted_weight_g']:.2f}")
    print(f"total_harvest_kg:       {result['total_harvest_kg']:.2f}")
    print(f"surviving_fish:         {result['surviving_fish']}")
    print(f"final_density_kg_m3:    {result['final_density_kg_m3']:.1f}")
    print(f"effective_temp_c:       {result['effective_temp_c']:.1f}")
    print(f"effective_do_mg_l:      {result['effective_do_mg_l']:.1f}")
    print(f"biofilter_cap_g_day:    {result['biofilter_capacity_g_day']:.1f}")
    print(f"turnovers_per_hour:     {result['turnovers_per_hour']:.1f}")
    print(f"constraints_pass:       {result['constraints_pass']}")
    if result["constraint_issues"]:
        for issue in result["constraint_issues"]:
            print(f"  CONSTRAINT FAIL: {issue}")
