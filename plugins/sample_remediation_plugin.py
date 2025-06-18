from plugins.base_plugin import BasePlugin
import os
import subprocess


class SampleRemediationPlugin(BasePlugin):
    """
    Sample plugin that adds a custom remediation action: clear Windows event logs.
    """

    def register(self, system_context):
        orchestrator = system_context.get("orchestrator")
        config = system_context.get("config")
        # Register the custom action with RemediatorAgent if present
        remediator = orchestrator.agents.get("remediator")
        if remediator:
            # Add the action to the agent (monkey-patch for demo)
            remediator.clear_event_logs = self.clear_event_logs
            if hasattr(remediator, "custom_actions"):
                remediator.custom_actions.append("clear_event_logs")
            else:
                remediator.custom_actions = ["clear_event_logs"]
            remediator.logger.info(
                "SampleRemediationPlugin: Registered clear_event_logs action."
            )
        else:
            print(
                "[SampleRemediationPlugin] RemediatorAgent not found; action not registered."
            )

    def get_config(self):
        return self.config

    async def clear_event_logs(self):
        """Clear Windows event logs (requires admin)."""
        try:
            if os.name != "nt":
                return False
            logs = [
                "Application",
                "System",
                "Security",
                "Setup",
                "ForwardedEvents",
            ]
            for log in logs:
                result = subprocess.run(
                    ["wevtutil", "cl", log], capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    print(
                        f"[SampleRemediationPlugin] Failed to clear {log}: {result.stderr}"
                    )
            print("[SampleRemediationPlugin] Cleared Windows event logs.")
            return True
        except Exception as e:
            print(f"[SampleRemediationPlugin] Error clearing event logs: {e}")
            return False
