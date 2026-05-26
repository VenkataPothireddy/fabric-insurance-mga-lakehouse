"""
Citadel MGA Lakehouse — Synthetic Data Generator
=================================================
Generates six CSVs simulating a specialty insurance MGA's operational data:
    programs, carriers, agents, policies, claims, commission_payouts

Output: data-generation/output/*.csv
Run from repo root:  python data-generation/generate_data.py

Design notes
------------
- programs.csv mirrors Citadel's actual specialty verticals
- commission_payouts.csv simulates the "VBA tool output" — silver notebook
  will later replicate this calculation from scratch, proving we can retire
  the legacy Excel workbook
- 2–3% intentional bad data is seeded into policies.csv so DQ checks in
  silver have something to catch (don't clean it here — that's silver's job)
"""

import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SEED = 42                          # deterministic regeneration
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_PROGRAMS  = 10
N_CARRIERS  = 20
N_AGENTS    = 200
N_POLICIES  = 10_000
N_CLAIMS    = 2_000
N_PAYOUTS   = 5_000

DATE_START = datetime(2024, 1, 1)
DATE_END   = datetime(2026, 1, 1)   # 24-month window

random.seed(SEED)
np.random.seed(SEED)
fake = Faker("en_US")
Faker.seed(SEED)


# ---------------------------------------------------------------------------
# 1. PROGRAMS  (10 rows — Citadel's actual verticals)
# ---------------------------------------------------------------------------
def generate_programs() -> pd.DataFrame:
    """
    TODO (Venkata):
    - Fill the `programs` list with Citadel's 10 specialty verticals from the
      handoff: dietary supplements, environmental, healthcare providers,
      energy, life sciences, contingency, manufacturers, property, umbrella,
      business professionals.
    - For each, decide a realistic base_premium_min / base_premium_max.
      Hint: healthcare providers & energy run high ($25K–$300K).
      Dietary supplements & business professionals run lower ($2K–$50K).
    - loss_ratio_target is the expected claims/premium ratio per program.
      Healthcare providers ~0.65, contingency ~0.20, manufacturers ~0.55.
      This drives claims.csv generation downstream.
    """
    programs = [
        # (program_code, program_name, base_premium_min, base_premium_max, loss_ratio_target)
        ("DIET", "Dietary Supplements",       2000,   50000, 0.35),
        ("ENV",  "Environmental",            10000,  250000, 0.50),
        ("HCP",  "Healthcare Providers",     25000,  300000, 0.65),
        ("ENRG", "Energy",                   30000,  400000, 0.55),
        ("LIFE", "Life Sciences",            15000,  200000, 0.45),
        ("CONT", "Contingency",               5000,  150000, 0.20),
        ("MFG",  "Manufacturers",            10000,  175000, 0.55),
        ("PROP", "Property",                  5000,  100000, 0.50),
        ("UMB",  "Umbrella",                  3000,   80000, 0.40),
        ("BIZ",  "Business Professionals",    2000,   40000, 0.30),
    ]
    return pd.DataFrame(
        programs,
        columns=["program_code", "program_name",
                 "base_premium_min", "base_premium_max", "loss_ratio_target"],
    )


# ---------------------------------------------------------------------------
# 2. CARRIERS  (20 rows)
# ---------------------------------------------------------------------------
def generate_carriers() -> pd.DataFrame:
    """
    TODO (Venkata):
    - Generate 20 fake carrier names. Faker doesn't have insurance carriers,
      so use fake.company() + " Insurance Group" / " Specialty" / " Casualty".
    - AM Best rating distribution — weight toward A and A-:
        A++ (5%), A+ (15%), A (40%), A- (25%), B++ (10%), B+ (5%)
      Use np.random.choice with the `p` parameter.
    - admitted flag: 70% admitted, 30% non-admitted (typical MGA mix).
    """
    rows = []

    name_suffixes = [" Insurance Group", " Specialty", " Casualty",
                     " Underwriters", " Insurance Company"]

    for i in range(N_CARRIERS):
        one_carrier = {
            "carrier_id": f"CAR-{i+1:03d}",
            "carrier_name": fake.company() + random.choice(name_suffixes),
            "am_best_rating": np.random.choice(
                ["A++", "A+", "A", "A-", "B++", "B+"],
                p=[0.05, 0.15, 0.40, 0.25, 0.10, 0.05]
            ),
            "admitted": np.random.choice([True, False], p=[0.7, 0.3]),
        }
        rows.append(one_carrier)

    return pd.DataFrame(
        rows,
        columns=["carrier_id", "carrier_name", "am_best_rating", "admitted"],
    )

# ---------------------------------------------------------------------------
# 3. AGENTS  (200 rows)
# ---------------------------------------------------------------------------
def generate_agents() -> pd.DataFrame:
    """
    TODO (Venkata):
    - Faker for first_name, last_name, agency_name (fake.company()), state.
    - Commission tier: BRONZE (50%), SILVER (30%), GOLD (15%), PLATINUM (5%).
      This drives the commission rate downstream.
    - Tier → commission rate mapping (used later in payout calc):
        BRONZE   = 0.08
        SILVER   = 0.10
        GOLD     = 0.12
        PLATINUM = 0.15
    - hire_date: random date in the past 1–10 years (fake.date_between).
    """
    rows = []

    tier_rates = {
        "BRONZE":   0.08,
        "SILVER":   0.10,
        "GOLD":     0.12,
        "PLATINUM": 0.15,
    }

    for i in range(N_AGENTS):
        tier = np.random.choice(
            ["BRONZE", "SILVER", "GOLD", "PLATINUM"],
            p=[0.50, 0.30, 0.15, 0.05]
        )

        one_agent = {
            "agent_id": f"AGT-{i+1:03d}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "agency_name": fake.company(),
            "state": fake.state_abbr(),
            "tier": tier,
            "commission_rate": tier_rates[tier],
            "hire_date": fake.date_between(start_date='-10y', end_date='-1y'),
        }
        rows.append(one_agent)

    return pd.DataFrame(
        rows,
        columns=["agent_id", "first_name", "last_name", "agency_name",
                 "state", "tier", "commission_rate", "hire_date"],
    )


# ---------------------------------------------------------------------------
# 4. POLICIES  (10,000 rows — the big one)
# ---------------------------------------------------------------------------
def generate_policies(programs: pd.DataFrame,
                      carriers: pd.DataFrame,
                      agents: pd.DataFrame) -> pd.DataFrame:
    """
    TODO (Venkata):
    - For each of 10,000 policies:
        * policy_id = "POL-" + zero-padded 6-digit number
        * program_code = random choice from programs (weight by realism if you want)
        * carrier_id   = random choice from carriers
        * agent_id     = random choice from agents
        * effective_date = random date in DATE_START..DATE_END
        * expiration_date = effective_date + 365 days (annual policies)
        * premium = log-normal distribution.
            mu = log(15000), sigma = 0.9  → mean ~$15K, long tail to ~$500K
            np.random.lognormal(mean=np.log(15000), sigma=0.9)
            Clip to program's base_premium_min/max where reasonable.
        * status: 75% ACTIVE, 15% EXPIRED, 8% CANCELLED, 2% PENDING
        * insured_name = fake.company()
        * insured_state = fake.state_abbr()

    - DIRTY DATA injection (2–3% of rows):
        * 1% → premium = None  (null premium)
        * 0.5% → premium = negative number
        * 0.5% → effective_date stored as malformed string "2025-13-45"
        * 0.5% → carrier_id = None (orphaned FK)
        * 0.5% → agent_id = "AGT-99999" (FK to nonexistent agent)
      These get caught in silver-layer DQ checks — that's the showcase.

    - Return DataFrame. Don't sort, keep insertion order so dirty rows are
      scattered, not clumped.
    """
    rows = []
    days_range = (DATE_END - DATE_START).days

    program_codes = programs["program_code"].tolist()
    carrier_ids = carriers["carrier_id"].tolist()
    agent_ids = agents["agent_id"].tolist()

    for i in range(N_POLICIES):
        # Pick the program first — we need its min/max for premium
        program_code = random.choice(program_codes)
        program_row = programs[programs["program_code"] == program_code].iloc[0]

        carrier_id = random.choice(carrier_ids)
        agent_id = random.choice(agent_ids)

        # Effective date: random day in the 24-month window
        effective_date = DATE_START + timedelta(days=random.randint(0, days_range))
        expiration_date = effective_date + timedelta(days=365)

        # Log-normal premium, clipped to program range
        premium = np.random.lognormal(mean=np.log(15000), sigma=0.9)
        premium = max(premium, program_row["base_premium_min"])
        premium = min(premium, program_row["base_premium_max"])
        premium = round(premium, 2)

        status = np.random.choice(
            ["ACTIVE", "EXPIRED", "CANCELLED", "PENDING"],
            p=[0.75, 0.15, 0.08, 0.02]
        )

        # --- Dirty data injection (2.5% of rows total) ---
        corruption = random.random()
        if corruption < 0.010:
            premium = None
        elif corruption < 0.015:
            premium = -abs(premium) if premium is not None else None
        elif corruption < 0.020:
            effective_date = "2025-13-45"
        elif corruption < 0.025:
            carrier_id = None
        elif corruption < 0.030:
            agent_id = "AGT-99999"

        one_policy = {
            "policy_id": f"POL-{i+1:06d}",
            "program_code": program_code,
            "carrier_id": carrier_id,
            "agent_id": agent_id,
            "effective_date": effective_date,
            "expiration_date": expiration_date,
            "premium": premium,
            "status": status,
            "insured_name": fake.company(),
            "insured_state": fake.state_abbr(),
        }
        rows.append(one_policy)

    return pd.DataFrame(
        rows,
        columns=["policy_id", "program_code", "carrier_id", "agent_id",
                 "effective_date", "expiration_date", "premium", "status",
                 "insured_name", "insured_state"],
    )


# ---------------------------------------------------------------------------
# 5. CLAIMS  (2,000 rows — subset of policies have claims)
# ---------------------------------------------------------------------------
def generate_claims(policies: pd.DataFrame,
                    programs: pd.DataFrame) -> pd.DataFrame:
    """
    TODO (Venkata):
    - Pick 2,000 policy_ids from policies (only ACTIVE or EXPIRED ones).
    - One policy can have 1–3 claims (most have 1).
    - For each claim:
        * claim_id = "CLM-" + zero-padded 7-digit
        * loss_date = random date between policy effective_date and expiration_date
        * report_date = loss_date + random 0–60 days
        * claim_amount = function of premium × program's loss_ratio_target × random factor
            e.g. premium * loss_ratio_target * np.random.uniform(0.3, 2.5)
            (some claims small, some catastrophic)
        * claim_status: 40% OPEN, 45% CLOSED, 10% LITIGATION, 5% DENIED
        * cause_of_loss: pick from ["Fire", "Water", "Theft", "Liability",
                                    "Professional Negligence", "Product Defect",
                                    "Cyber", "Auto", "Weather", "Other"]
    """
    rows = []
    
    causes = ["Fire", "Water", "Theft", "Liability",
              "Professional Negligence", "Product Defect",
              "Cyber", "Auto", "Weather", "Other"]
    
    # Build a lookup: program_code → loss_ratio_target
    loss_ratio_lookup = dict(zip(
        programs["program_code"],
        programs["loss_ratio_target"]
    ))
    
    # Filter to claimable policies (ACTIVE or EXPIRED only)
    eligible = policies[policies["status"].isin(["ACTIVE", "EXPIRED"])]
    
    # Oversample by 20% to give us room to skip dirty rows
    selected = eligible.sample(n=int(N_CLAIMS * 1.2), replace=True, random_state=SEED)
    
    claim_counter = 0
    for _, policy_row in selected.iterrows():
        if claim_counter >= N_CLAIMS:
            break
        
        # Skip dirty rows
        if pd.isna(policy_row["premium"]) or policy_row["premium"] <= 0:
            continue
        if not isinstance(policy_row["effective_date"], (datetime, pd.Timestamp)):
            continue
        
        # Loss date: random day between effective and expiration
        eff_date = pd.Timestamp(policy_row["effective_date"]).to_pydatetime()
        exp_date = pd.Timestamp(policy_row["expiration_date"]).to_pydatetime()
        policy_days = (exp_date - eff_date).days
        loss_date = eff_date + timedelta(days=random.randint(0, max(policy_days - 1, 1)))
        
        # Report date: 0–60 days after loss
        report_date = loss_date + timedelta(days=random.randint(0, 60))
        
        # Claim amount: premium × loss_ratio × random factor
        loss_ratio = loss_ratio_lookup[policy_row["program_code"]]
        random_factor = np.random.uniform(0.3, 2.5)
        claim_amount = round(
            policy_row["premium"] * loss_ratio * random_factor, 2
        )
        
        claim_status = np.random.choice(
            ["OPEN", "CLOSED", "LITIGATION", "DENIED"],
            p=[0.40, 0.45, 0.10, 0.05]
        )
        
        one_claim = {
            "claim_id": f"CLM-{claim_counter + 1:07d}",
            "policy_id": policy_row["policy_id"],
            "loss_date": loss_date.date(),
            "report_date": report_date.date(),
            "claim_amount": claim_amount,
            "claim_status": claim_status,
            "cause_of_loss": random.choice(causes),
        }
        rows.append(one_claim)
        claim_counter += 1
    
    return pd.DataFrame(
        rows,
        columns=["claim_id", "policy_id", "loss_date", "report_date",
                 "claim_amount", "claim_status", "cause_of_loss"],
    )


# ---------------------------------------------------------------------------
# 6. COMMISSION PAYOUTS  (5,000 rows — THE VBA LOGIC SHOWCASE)
# ---------------------------------------------------------------------------
def generate_commission_payouts(policies: pd.DataFrame,
                                agents: pd.DataFrame,
                                programs: pd.DataFrame) -> pd.DataFrame:
    """
    >>> THIS IS THE INTERVIEW DIFFERENTIATOR <<<

    This CSV represents the OUTPUT of the legacy VBA tool. The silver-layer
    notebook will replicate this calculation in PySpark from scratch — proving
    the VBA workbook can be retired without losing business logic.

    Document the formula below in plain English. It becomes the first entry
    in docs/business-logic/commission-calculation.md.

    TODO (Venkata):
    - Pick 5,000 ACTIVE policies (newest commission cycle).
    - For each:
        commission_amount = premium
                          × agent.commission_rate   (tier-based)
                          × program_modifier        (see below)
                          - adjustments              (random clawbacks)

      program_modifier (multiplier on top of base rate):
        Healthcare Providers: 1.15  (harder to place, premium product)
        Energy:               1.10
        Environmental:        1.05
        Life Sciences:        1.10
        Contingency:          1.20  (specialty, low volume, high margin)
        Manufacturers:        1.00
        Property:             0.95  (commodity-ish)
        Umbrella:             1.00
        Business Professionals: 0.90
        Dietary Supplements:  1.05

      adjustments:
        10% of rows → random deduction $50–$500 (chargebacks, fee corrections)
        Otherwise 0.

    - payout_date = effective_date + random 30–90 days (typical settlement lag)
    - payout_status: 80% PAID, 15% PENDING, 5% DISPUTED

    Add `calc_method = "LEGACY_VBA_V3"` as a column. This makes it explicit
    in the demo: silver notebook will produce the same column with value
    "FABRIC_PYSPARK_V1" — side-by-side reconciliation proves equivalence.
    """
    rows = []

    # Program modifier: program-specific multiplier on top of base commission rate
    program_modifiers = {
        "DIET": 1.05,
        "ENV":  1.05,
        "HCP":  1.15,
        "ENRG": 1.10,
        "LIFE": 1.10,
        "CONT": 1.20,
        "MFG":  1.00,
        "PROP": 0.95,
        "UMB":  1.00,
        "BIZ":  0.90,
    }

    # Lookup tables built once before the loop
    agent_rate_lookup = dict(zip(
        agents["agent_id"],
        agents["commission_rate"]
    ))

    # Filter to commissionable policies (ACTIVE preferred, also allow EXPIRED)
    eligible = policies[policies["status"].isin(["ACTIVE", "EXPIRED"])]

    # Oversample by 20% to absorb dirty-row skips
    selected = eligible.sample(
        n=int(N_PAYOUTS * 1.2),
        replace=False,
        random_state=SEED
    )

    payout_counter = 0
    for _, policy_row in selected.iterrows():
        if payout_counter >= N_PAYOUTS:
            break

        # Skip dirty rows
        if pd.isna(policy_row["premium"]) or policy_row["premium"] <= 0:
            continue
        if pd.isna(policy_row["agent_id"]) or policy_row["agent_id"] not in agent_rate_lookup:
            continue
        if not isinstance(policy_row["effective_date"], (datetime, pd.Timestamp)):
            continue

        premium = policy_row["premium"]
        commission_rate = agent_rate_lookup[policy_row["agent_id"]]
        program_modifier = program_modifiers[policy_row["program_code"]]

        # Adjustments: 10% of rows get a random deduction $50-$500, else 0
        if random.random() < 0.10:
            adjustments = round(random.uniform(50, 500), 2)
        else:
            adjustments = 0.00

        # THE VBA FORMULA — document this in business-logic/commission-calculation.md
        commission_amount = round(
            (premium * commission_rate * program_modifier) - adjustments,
            2
        )

        # Payout date: 30-90 days after policy effective date
        eff_date = pd.Timestamp(policy_row["effective_date"]).to_pydatetime()
        payout_date = eff_date + timedelta(days=random.randint(30, 90))

        payout_status = np.random.choice(
            ["PAID", "PENDING", "DISPUTED"],
            p=[0.80, 0.15, 0.05]
        )

        one_payout = {
            "payout_id": f"CMP-{payout_counter + 1:07d}",
            "policy_id": policy_row["policy_id"],
            "agent_id": policy_row["agent_id"],
            "program_code": policy_row["program_code"],
            "premium": round(premium, 2),
            "commission_rate": commission_rate,
            "program_modifier": program_modifier,
            "adjustments": adjustments,
            "commission_amount": commission_amount,
            "payout_date": payout_date.date(),
            "payout_status": payout_status,
            "calc_method": "LEGACY_VBA_V3",
        }
        rows.append(one_payout)
        payout_counter += 1

    return pd.DataFrame(
        rows,
        columns=["payout_id", "policy_id", "agent_id", "program_code",
                 "premium", "commission_rate", "program_modifier",
                 "adjustments", "commission_amount", "payout_date",
                 "payout_status", "calc_method"],
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def main():
    print(f"Output directory: {OUTPUT_DIR}\n")

    print("Generating programs...")
    programs = generate_programs()
    programs.to_csv(OUTPUT_DIR / "programs.csv", index=False)
    print(f"  → {len(programs):,} rows")

    print("Generating carriers...")
    carriers = generate_carriers()
    carriers.to_csv(OUTPUT_DIR / "carriers.csv", index=False)
    print(f"  → {len(carriers):,} rows")

    print("Generating agents...")
    agents = generate_agents()
    agents.to_csv(OUTPUT_DIR / "agents.csv", index=False)
    print(f"  → {len(agents):,} rows")

    print("Generating policies...")
    policies = generate_policies(programs, carriers, agents)
    policies.to_csv(OUTPUT_DIR / "policies.csv", index=False)
    print(f"  → {len(policies):,} rows")

    print("Generating claims...")
    claims = generate_claims(policies, programs)
    claims.to_csv(OUTPUT_DIR / "claims.csv", index=False)
    print(f"  → {len(claims):,} rows")

    print("Generating commission payouts...")
    payouts = generate_commission_payouts(policies, agents, programs)
    payouts.to_csv(OUTPUT_DIR / "commission_payouts.csv", index=False)
    print(f"  → {len(payouts):,} rows")

    print("\nDone.")


if __name__ == "__main__":
    main()
