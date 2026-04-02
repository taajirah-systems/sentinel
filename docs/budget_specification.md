# Sentinel High-Integrity Internal Budget Specification

This document defines the authoritative architecture, schemas, and state transitions for the Sentinel budget-control sub-system.

## 1. Authority Split
To ensure maximum integrity and auditability, authority is split between historical logging and state caching:

- **Economic History (Authoritative)**: `ledger/accounting.jsonl`. This append-only log is the sole source of truth for cumulative balances, spends, and historical hold actions.
- **Current Hold State (Cache)**: `governance.db:holds` table. This table tracks the active lifecycle of budget reservations and validates transitions. It is *advisory* to the ledger but *authoritative* for state-machine enforcement.

## 2. Parent-Child Zero-Sum Semantics
The budget follows a strict tree inheritance model:

- **Org -> Project -> Agent**
- **Funding**: Allocating budget to a child wallet (e.g. Org to Project) reduces the parent's `available_jul`.
- **Enforcement**: A child's `balance_jul` represents a pre-allocated slice of the parent's liquidity. 
- **No Double-Reserving**: A hold at the Agent level reduces the Agent's `available_jul` but does not create a concurrent second hold at the Project/Org level. The parent's budget was already reduced at the moment of child funding.

## 3. Hold State Machine
All budget reservations MUST follow these transition rules:

| State | Allowed Next State | Action |
| :--- | :--- | :--- |
| **active** | **settled** | `settle_hold` (Actual spend recorded) |
| **active** | **released** | `release_hold` (Manual rejection) |
| **active** | **expired** | `release_hold(is_expiry=True)` (TTL limit) |
| **settled** | *None* | Terminal state |
| **released** | *None* | Terminal state |
| **expired** | *None* | Terminal state |

> [!CAUTION]
> Any attempt to transition from a terminal state or skip the **active** state will be rejected and logged as an `integrity_event`.

## 4. Event Schemas

### `budget_shortfall`
Emitted when `actual_spend > estimated_hold` and the wallet's remaining available pool is insufficient.
```json
{
  "event_type": "budget_shortfall",
  "wallet_id": "string",
  "hold_id": "string",
  "amount_jul": "number",
  "shortfall_jul": "number",
  "timestamp": "ISO-8601"
}
```

### `integrity_event`
Emitted when an invalid hold transition is attempted.
```json
{
  "event_type": "integrity_event",
  "actor_id": "string",
  "action": "string",
  "reason": "ERR_INVALID_HOLD_TRANSITION",
  "details": {
    "hold_id": "string",
    "from_state": "string",
    "to_state": "string"
  }
}
```
