import os
from typing import TypedDict, Literal
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

class PipelineState(TypedDict):
    commit_hash: str
    test_logs: str
    test_passed: bool
    human_approved: bool
    deployment_status: str
    error_rate: float
    rollback_performed: bool

@tool
def run_unit_tests(commit_hash: str) -> str:
    """Executes code testing suites and parses console output logs."""
    return f"Logs for {commit_hash}: 120 tests run. 0 failures. Exit code 0."

@tool
def execute_db_migration(commit_hash: str) -> str:
    """Executes database schema migrations safely."""
    return f"Migration applied successfully for {commit_hash}."

@tool
def deploy_container(commit_hash: str) -> str:
    """Builds Docker image and deploys to production."""
    return f"Container deployed for {commit_hash}."

@tool
def trigger_rollback(commit_hash: str) -> str:
    """Rolls back the deployment to the previous stable release state."""
    return f"ROLLBACK SUCCESS: Restored to state prior to {commit_hash}."

def guard_agent(state: PipelineState):
    logs = run_unit_tests.invoke({"commit_hash": state["commit_hash"]})
    passed = "0 failures" in logs
    return {"test_logs": logs, "test_passed": passed}

def human_approval_gate(state: PipelineState):
    print(f"\n[HUMAN GATE REQUIRED]: Approve database migration for commit {state['commit_hash']}?")
    user_input = input("Enter 'yes' to approve or 'no' to abort: ").strip().lower()
    return {"human_approved": user_input == "yes"}

def infra_agent(state: PipelineState):
    if not state.get("human_approved"):
        return {"deployment_status": "ABORTED_UNAPPROVED"}
    execute_db_migration.invoke({"commit_hash": state["commit_hash"]})
    deploy_container.invoke({"commit_hash": state["commit_hash"]})
    return {"deployment_status": "LIVE"}

def watchman_agent(state: PipelineState):
    simulated_error_rate = 8.5
    if simulated_error_rate > 5.0:
        trigger_rollback.invoke({"commit_hash": state["commit_hash"]})
        return {"error_rate": simulated_error_rate, "rollback_performed": True, "deployment_status": "ROLLED_BACK"}
    return {"error_rate": simulated_error_rate, "rollback_performed": False, "deployment_status": "HEALTHY"}

def route_after_guard(state: PipelineState) -> Literal["human_approval_gate", "__end__"]:
    if state["test_passed"]:
        return "human_approval_gate"
    return END

def route_after_human(state: PipelineState) -> Literal["infra_agent", "__end__"]:
    if state["human_approved"]:
        return "infra_agent"
    return END

workflow = StateGraph(PipelineState)
workflow.add_node("guard_agent", guard_agent)
workflow.add_node("human_approval_gate", human_approval_gate)
workflow.add_node("infra_agent", infra_agent)
workflow.add_node("watchman_agent", watchman_agent)
workflow.set_entry_point("guard_agent")
workflow.add_conditional_edges("guard_agent", route_after_guard)
workflow.add_conditional_edges("human_approval_gate", route_after_human)
workflow.add_edge("infra_agent", "watchman_agent")
workflow.add_edge("watchman_agent", END)
app = workflow.compile()

if __name__ == "__main__":
    initial_state = {
        "commit_hash": "a1b2c3d",
        "test_logs": "",
        "test_passed": False,
        "human_approved": False,
        "deployment_status": "PENDING",
        "error_rate": 0.0,
        "rollback_performed": False
    }
    print("=== Starting Event-Driven Agentic Pipeline ===")
    final_state = app.invoke(initial_state)
    print("\n=== Pipeline Execution Completed ===")
    print(f"Final Deployment Status: {final_state.get('deployment_status')}")
    print(f"Rollback Performed: {final_state.get('rollback_performed')}")