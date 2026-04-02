# Sentinel Pilot Specification v1: Bounded Code-Generation

This pilot demonstrates Sentinel's high-integrity budget governance and oversight layer on a real-world coding/refactoring workflow. It proves that Sentinel can prevent uncontrolled agentic spend, clamp budget overruns, and route actions for human review before final execution.

## 1. Workflow Overview
- **Name**: Bounded Code-Generation / Review
- **Scope**: Targeted refactoring, bugfixes, and small module generation.
- **Goal**: Minimize 'waste_jul' and verify 'correction_jul' while maintaining budget limits.

## 2. Pilot Task Pack
The pilot uses a fixed task set to ensure deterministic reporting:

| Task ID | Type | Description | Est. JUL | Risk | Review Required |
|---------|------|-------------|----------|------|-----------------|
| T1 | Refactor | Improve branching in `auth.py` | 50.0 | 4 | No |
| T2 | Bugfix | Fix edge case in `parser.py` | 150.0 | 8 | Yes (Threshold) |
| T3 | Generate | Create `utils/logger.ts` | 30.0 | 3 | No |

## 3. Budget & Hold Management
- **Model**: Org (`org_pilot`) funds Project (`proj_pilot`), which funds Agent (`agent_coder`).
- **Hold Logic**: Every task MUST create a budget hold (`create_hold`) before workflow execution.
- **Success Case**: If actual spend <= estimated, `settle_hold` normally.
- **Anomaly Case**: If `actual > (estimated + available)`, enter `failed_shortfall` (CLAMPED).
- **Release Logic**: Surplus funds are returned to project budget via `surplus_released_jul`.

## 4. Human-in-the-Loop Rules
Reviews are triggered if:
- `risk_score > 7`
- `estimated_cost_jul > 100`

### Allowed Operator Actions (Overrides)
- **`release`**: Cancel task, return funds.
- **`fund_and_settle`**: Force settlement of shortfall.
- **`force_settle`**: Settle only reserved amount.

## 5. Metrics & KPIs

### Core Spend KPIs (Liquidity)
- `estimated_jul`: Initial reservation amount.
- `actual_jul`: Realized cost from provider.
- `variance_jul`: `actual - estimated`.
- `clamped_count`: Number of `failed_shortfall` events.

### Outcome KPIs (Quality)
- `task_completed`: Final result produced.
- `output_accepted`: Passed human review.
- `waste_ratio`: `waste_jul / total_jul`.
- `correction_ratio`: `correction_jul / total_jul`.

### Governance KPIs (Oversight)
- `approval_rate`: `% of requests approved`.
- `human_save_rate`: `estimated_cost_avoided / total_spend`.
- `operator_override_count`: Manual resolutions performed.

## 6. Success Criteria
The pilot is successful if:
1.  **Zero Uncontrolled Spend**: No task settles beyond wallet available limits without override.
2.  **Forensic Traceability**: All overrides (7-field) are visible in the ledger.
3.  **Hierarchy Awareness**: Oversight Console correctly flags parent nodes for anomalies.
4.  **Accurate Metering**: `waste_ratio` and `correction_ratio` remain within established limits.
