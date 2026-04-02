# Sentinel Ledger Reconciliation Invariants

This document defines the strict invariants and procedures for maintaining consistency between the authoritative append-only ledger and the derived wallet state cache.

## 1. Authoritative Source of Truth
- The file `/Users/taajirah_systems/sentinel/ledger/accounting.jsonl` is the **only** authoritative source of truth for financial balances.
- The file `/Users/taajirah_systems/sentinel/ledger/governance.jsonl` is the authoritative source for compliance states and admin overrides.
- `wallets.json` is a volatile, derived **cache** used for high-performance read-access. It must never be trusted if it conflicts with the ledger streams.

## 2. Invariants

### I1: Append-Only Audit Trail
No record in `.jsonl` files may ever be modified, deleted, or re-ordered. Every line represents a discrete, atomic event in the system's history.

### I2: Event Idempotency
Every event possesses a unique UUID (`correlation_id` or `event_id`). 
A reconciliation engine must ensure that processing the same event ID twice results in **zero** change to the wallet state.

### I3: Balance Positivity
With the exception of designated Treasury wallets, no wallet may have a negative `balance_jul`. The `spend_service_credit` logic must fail-closed if funds are insufficient at the time of the event.

### I4: Order Consistency
Events must be replayed in strict chronological order based on the `_written_at` or `timestamp` fields. Re-ordering events during reconciliation is a violation of the audit trail.

### I5: Multi-Factor Compliance
Settlement eligibility (`fiat_withdrawal`) requires triple-verification:
1. `wallet_type == "contractor"`
2. `kyc_verified == True`
3. `contract_active == True`

## 3. Reconciliation Procedures

### Cache Rebuild (Full Replay)
If the integrity of `wallets.json` is suspected to be compromised:
1. Stop the Sentinel API server.
2. Delete `ledger/wallets.json`.
3. Run the reconciliation script (re-streams all events from `accounting.jsonl` and `governance.jsonl`).
4. Re-calculate all balances and compliance flags from the genesis event.

### Partial Write Recovery
The system uses `tmp.replace()` for all `wallets.json` updates. If the process crashes during a write, the `.tmp` file is discarded, and the last known good state remains valid. The next event processing will naturally recover the missing state.
