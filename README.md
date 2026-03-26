# Sentinel

**Replayable execution-control layer for autonomous agents.**

Sentinel helps govern agent-initiated commands using:
- **Deterministic policy checks**
- **Approval workflows** for review-gated actions
- **Structured audit telemetry**
- **Stage-by-stage replay**
- **OS-enforced sandbox containment** on macOS

Sentinel is designed for agentic systems that operate near sensitive files, developer environments, or infrastructure. Rather than relying on agent behavior alone, Sentinel applies layered controls before and during execution, while preserving traceable evidence of every major decision.

## Current capabilities
- Versioned policy enforcement (v2.4 baseline)
- Allow / block / require-approval decisions
- Approval logging with actor + reason
- Runtime denial classification (Seatbelt/SBPL)
- Structured JSONL traces
- Replay CLI for stage-by-stage forensics
- Failure injection coverage
- Benchmark reporting by execution path
- Malicious and benign regression suites
- Sequence-chain evaluation

## Scope
Sentinel reduces execution risk and improves auditability for agentic workflows. It is currently validated against an internal test corpus and a macOS sandbox-based containment model.

---
*Sentinel is an open-source execution-governance layer.*
