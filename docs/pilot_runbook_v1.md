# Sentinel Pilot Runbook v1: Bounded Code-Generation

This runbook provides step-by-step instructions for operators to initialize, execute, and monitor the first Sentinel pilot for controlled internal deployment.

## 1. Initializing Pilot Wallet Tree (Org -> Project -> Agent)
To ensure hierarchical budget visibility, you must first create the pilot structure.

1.  **Fund Org**:
    ```bash
    python3 -c "from src.ledger.ledger import fund_wallet_from_treasury; fund_wallet_from_treasury('org_pilot', 5000.0, 'Initial pilot endowment')"
    ```
2.  **Fund Project**:
    ```bash
    python3 -c "from src.ledger.ledger import fund_wallet_from_parent; fund_wallet_from_parent('org_pilot', 'proj_pilot', 1000.0, 'Project Alpha Budget', 'SENT-PLT-01')"
    ```
3.  **Fund Agent**:
    ```bash
    python3 -c "from src.ledger.ledger import fund_wallet_from_parent; fund_wallet_from_parent('proj_pilot', 'agent_coder', 300.0, 'Agent Coder Allocation', 'SENT-PLT-02')"
    ```

## 2. Launching Pilot Task
The pilot is orchestrated via the `pilot_runner.py` script.

```bash
# Run all pilot tasks in sequence
python3 src/sentinel/pilot_runner.py --run-all
```

Expected output:
- `[PILOT] Hold created for task T1 (50.0 JUL)`
- `[PILOT] Settled T1 (Actual: 45.3 JUL) - Surplus released.`
- `[PILOT] Hold created for task T2 (150.0 JUL) - REVIEW REQUIRED.`

## 3. Resolving Exceptions (Clamped Holds)
If an agent overruns its budget beyond limits, it will enter `failed_shortfall`.

1.  **Identify CLAMPED hold** in the Oversight Console's "Exceptions" view.
2.  **Approve/Resolve** using the admin API:
    ```bash
    # Example: Granting budget and settling a shortfall
    curl -X POST "http://localhost:8765/api/admin/holds/{hold_id}/resolve?resolution_mode=fund_and_settle&audit_reason=EmergencyOverride_Pilot&operator_id=admin_01"
    ```

## 4. Monitoring Hierarchy Anomalies
Check the "Budget Navigator" in the Oversight Console.
- Ensure `org_pilot` and `proj_pilot` show `is_flagged: True` when `agent_coder` has a clamped hold.
- Verify `available_jul` and `held_jul` roll-ups reflect the current liquidity state.

## 5. Reviewing Analytics
After the pilot run, pull the final KPIs for the technical evidence pack.

```bash
curl -X GET "http://localhost:8765/api/admin/analytics/spend" | jq .summary
```

Verify:
- `waste_ratio` is correctly calculated based on outcome classification.
- `human_save_rate` reflects avoided costs from rejected/redirected actions.
