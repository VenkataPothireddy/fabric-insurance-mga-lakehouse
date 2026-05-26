# Commission Calculation — Business Logic Specification

**Document owner:** Venkata Pothireddy
**Last reviewed:** [today's date]
**Status:** Active
**Replaces:** Legacy VBA workbook (`LEGACY_VBA_V3`)

## Purpose

This document defines the formula used to calculate agent commission payouts
on bound policies. It exists to remove the single-person dependency on the
existing Excel VBA tool by making the business logic explicit, version-controlled,
and reproducible in code.

## Formula

commission_amount = (premium × commission_rate × program_modifier) − adjustments

## Inputs

| Field              | Source         | Description 
|--------------------|----------------|------------------------------------------------------|
| `premium`          | `policies`     | Gross written premium on the bound policy            | 
| `commission_rate`  | `agents`       | Base commission rate, derived from agent tier        | 
| `program_modifier` | `programs`     | Strategic multiplier per specialty program           |  
| `adjustments`      | Operational    | Chargebacks, fee corrections, mid-term cancellations | 


## Agent Tier → Commission Rate

| Tier      | Rate  | Population Share |
|-----------|-------|------------------|
| BRONZE    | 8%    | ~50%             |
| SILVER    | 10%   | ~30%             |
| GOLD      | 12%   | ~15%             |
| PLATINUM  | 15%   | ~5%              |

Tier is reviewed annually based on agent volume and persistency.

## Program Modifier

| Program                | Modifier | Rationale                                  |
|------------------------|----------|--------------------------------------------|
| Contingency            | 1.20     | Specialty, low volume, high margin         |
| Healthcare Providers   | 1.15     | Premium product, specialized underwriting  |
| Energy                 | 1.10     | High-value risks                           |
| Life Sciences          | 1.10     | Specialized underwriting                   |
| Environmental          | 1.05     | Specialty line                             |
| Dietary Supplements    | 1.05     | Small but profitable                       |
| Manufacturers          | 1.00     | Baseline                                   |
| Umbrella               | 1.00     | Baseline                                   |
| Property               | 0.95     | Highly competitive, lower margin           |
| Business Professionals | 0.90     | Commodity, low margin                      |

Program modifiers are set annually by leadership and reviewed quarterly
against book performance.

## Adjustments

A row's `adjustments` is non-zero in approximately 10% of cases. Typical
deduction range: $50–$500. Sources include chargebacks on mid-term
cancellations, fee corrections, and producer disputes.

## Worked Example

A GOLD-tier agent (12% base rate) writes a $25,000 Healthcare Providers
policy with no adjustments: 

commission_amount = 25000 × 0.12 × 1.15 − 0 = $3,450.00


## Reproducibility

This formula is implemented in two places:

| Method            | Location                                        | Status      |
|-------------------|-------------------------------------------------|-------------|
| `LEGACY_VBA_V3`   | `commission_payouts.csv` (synthetic source)     | Current     |
| `FABRIC_PYSPARK_V1` | `notebooks/silver/silver_commission.ipynb`    | Forthcoming |

Both methods are expected to produce identical results to the penny on
the same input set. Reconciliation is enforced in
`notebooks/silver/dq_commission_reconciliation.ipynb`.

## Change Management

Any change to this formula requires:
1. Pull request to `docs/business-logic/commission-calculation.md`
2. Review by Director of Data & Analytics + Finance
3. Update to PySpark implementation in lockstep
4. Re-run of reconciliation notebook prior to merge

## Open Questions

- Should mid-term cancellations claw back the full commission or pro-rata?
- Are there carrier-specific commission overrides that aren't captured here?
- How are renewals treated — same rate, or stepped down?

These are intentional placeholders for Citadel's actual business owners
to resolve.
