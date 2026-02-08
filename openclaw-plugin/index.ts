import { Type } from "@sinclair/typebox";

// Sentinel OpenClaw Plugin
// Calls the Python Sentinel server for full ADK/LLM semantic analysis

const SENTINEL_SERVER_URL = process.env.SENTINEL_SERVER_URL || "http://localhost:8765";

interface AuditResult {
  allowed: boolean;
  risk_score: number;
  reason: string;
  stdout?: string;
  stderr?: string;
  returncode?: number | null;
}

async function auditCommand(command: string): Promise<AuditResult> {
  try {
    const response = await fetch(`${SENTINEL_SERVER_URL}/audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command }),
    });

    if (!response.ok) {
      // Server error - fail closed
      return {
        allowed: false,
        risk_score: 10,
        reason: `Sentinel server error: ${response.status}`,
      };
    }

    return await response.json() as AuditResult;
  } catch (error: any) {
    // Connection error - fail closed
    return {
      allowed: false,
      risk_score: 10,
      reason: `Sentinel server unavailable: ${error.message}. Start with: python sentinel_server.py`,
    };
  }
}

export default function (api: any) {
  api.registerTool({
    name: "sentinel_exec",
    description: "Execute a shell command with Sentinel security auditing. Commands are checked against deterministic blocklists AND LLM semantic analysis for maximum security.",
    parameters: Type.Object({
      command: Type.String({ description: "The shell command to execute" }),
    }),
    async execute(_id: string, params: { command: string }) {
      const { command } = params;
      
      // Call Python Sentinel server for full ADK analysis
      const result = await auditCommand(command);
      
      if (!result.allowed) {
        return {
          content: [{
            type: "text",
            text: `🛡️ SENTINEL BLOCKED\n\nCommand: ${command}\nRisk Score: ${result.risk_score}/10\nReason: ${result.reason}\n\nThis command violates the security policy.`,
          }],
        };
      }
      
      // Command was approved and executed by the server
      const output = result.stdout || result.stderr || "(no output)";
      const status = result.returncode === 0 ? "✅ Success" : `⚠️ Exit code: ${result.returncode}`;
      
      return {
        content: [{
          type: "text",
          text: `🛡️ SENTINEL APPROVED\n\nCommand: ${command}\nRisk Score: ${result.risk_score}/10\nStatus: ${status}\n\nOutput:\n${output.slice(0, 4000)}`,
        }],
      };
    },
  });
}
