"""LangGraph pipeline for the investigation agent."""

from langgraph.graph import START, StateGraph

from hybrid_sentinel.agent.alerts import log_alert
from hybrid_sentinel.agent.nodes import (
    analyze_patterns,
    gather_context,
    generate_report,
)
from hybrid_sentinel.agent.state import InvestigationState


def build_investigation_graph():
    """Build and compile the linear investigation StateGraph."""
    builder = StateGraph(InvestigationState)
    
    builder.add_node("gather_context", gather_context)
    builder.add_node("analyze_patterns", analyze_patterns)
    builder.add_node("generate_report", generate_report)
    builder.add_node("log_alert", log_alert)
    
    builder.add_edge(START, "gather_context")
    builder.add_edge("gather_context", "analyze_patterns")
    builder.add_edge("analyze_patterns", "generate_report")
    builder.add_edge("generate_report", "log_alert")
    
    return builder.compile()


investigation_graph = build_investigation_graph()
