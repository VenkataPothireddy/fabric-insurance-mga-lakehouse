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

