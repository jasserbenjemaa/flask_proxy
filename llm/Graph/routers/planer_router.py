from Graph.state import GraphState
from Graph.const import SQL_EXEC, FORMATER


def planer_router(state: GraphState) -> str:
  """
  Router function that determines the next node based on planner's decision.
  FIXED: Handles both direct constants and semantic routing
  """

  # Get the planner's decision from state
  next_step = state.get("next_step")

  # Check for errors first
  if state.get("error"):
    print("🚨 ROUTER: Error detected, ending workflow")
    return FORMATER

  # Default to formatter if no decision was made
  if not next_step:
    print("⚠️  ROUTER: No next_step found in state, defaulting to FORMATER")
    return FORMATER

  # FIXED: Handle semantic routing (planner uses semantic names)
  routing_map = {
    # Direct constants
    SQL_EXEC: SQL_EXEC,
    FORMATER: FORMATER,

    # Semantic mappings (from planner)
    "run_sql": SQL_EXEC,
    "finalize": FORMATER,
    "format": FORMATER,
  }

  # Route based on mapping
  if next_step in routing_map:
    target = routing_map[next_step]
    print(f"🔄 ROUTER: Routing '{next_step}' to {target}")
    return target
  else:
    print(f"⚠️  ROUTER: Unknown next_step '{next_step}', defaulting to FORMATER")
    return FORMATER