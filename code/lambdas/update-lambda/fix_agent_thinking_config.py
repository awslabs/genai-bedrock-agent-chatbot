import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Bedrock Agents injects a default ORCHESTRATION reasoning config of
# {"thinking": {"type": "enabled", "budget_tokens": N}} for reasoning-capable
# Claude models. Newer models reject that legacy shape at invoke time with:
#   "thinking.type.enabled" is not supported for this model. Use
#   "thinking.type.adaptive" and "output_config.effort" to control thinking behavior.
# The agent therefore deploys successfully but fails on every InvokeAgent call.
#
# Extend this set when adopting another model that requires adaptive thinking.
ADAPTIVE_THINKING_MODELS = (
    "claude-opus-4-8",
    "claude-fable-5",
)

ADAPTIVE_THINKING_FIELDS = {"thinking": {"type": "adaptive"}}


def requires_adaptive_thinking(foundation_model):
    """
    True when the agent's foundation model rejects the legacy
    "thinking.type.enabled" reasoning configuration.
    """
    return any(m in foundation_model for m in ADAPTIVE_THINKING_MODELS)


def fix_agent_thinking_config(bedrock_agent, agent_id):
    """
    Replace the agent's default ORCHESTRATION reasoning configuration with the
    adaptive form when the foundation model requires it.

    Must run before prepare_agent/create_agent_alias so the resulting agent
    version snapshot carries the corrected configuration -- an alias pointing at
    a version created beforehand keeps serving the broken config.
    """
    agent = bedrock_agent.get_agent(agentId=agent_id)["agent"]
    foundation_model = agent.get("foundationModel", "")

    if not requires_adaptive_thinking(foundation_model):
        logger.info(
            f"Model {foundation_model} does not require adaptive thinking; "
            "leaving the default reasoning configuration in place."
        )
        return

    logger.info(
        f"Model {foundation_model} requires adaptive thinking. "
        "Overriding ORCHESTRATION reasoning configuration."
    )

    # promptCreationMode DEFAULT keeps Bedrock's managed base prompt template and
    # rejects basePromptTemplate / inferenceConfiguration / promptState, so send
    # only the prompt type plus the corrected additional model request fields.
    bedrock_agent.update_agent(
        agentId=agent_id,
        agentName=agent["agentName"],
        foundationModel=foundation_model,
        agentResourceRoleArn=agent["agentResourceRoleArn"],
        instruction=agent["instruction"],
        description=agent.get("description", ""),
        idleSessionTTLInSeconds=agent.get("idleSessionTTLInSeconds", 3600),
        promptOverrideConfiguration={
            "promptConfigurations": [
                {
                    "promptType": "ORCHESTRATION",
                    "promptCreationMode": "DEFAULT",
                    "additionalModelRequestFields": ADAPTIVE_THINKING_FIELDS,
                }
            ]
        },
    )

    # update_agent returns immediately; the agent must leave UPDATING before it
    # can be prepared.
    for _ in range(30):
        status = bedrock_agent.get_agent(agentId=agent_id)["agent"]["agentStatus"]
        if status != "UPDATING":
            logger.info(f"Agent reached status {status} after thinking-config update.")
            return
        # nosemgrep: <arbitrary-sleep Message: time.sleep() call>
        time.sleep(5)  # nosem: arbitrary-sleep

    raise RuntimeError(
        f"Agent {agent_id} did not leave UPDATING after the thinking-config update."
    )
