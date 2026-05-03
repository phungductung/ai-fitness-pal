import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.agents.orchestrator import FitnessAgents, AgentState, OrchestratorDecision
from langchain_core.messages import HumanMessage, AIMessage

@pytest.fixture
def fitness_agents():
    # Mock the LLM initialization to avoid API key requirements
    with patch("app.agents.orchestrator.ChatOpenAI") as mock_openai:
        mock_instance = mock_openai.return_value
        mock_instance.ainvoke = AsyncMock()
        mock_instance.with_structured_output = MagicMock()
        return FitnessAgents(model_name="gpt-4o")

@pytest.mark.asyncio
async def test_safety_guard_medical_high_risk(fitness_agents):
    state = {"messages": [HumanMessage(content="I think I'm having a heart attack")]}
    result = await fitness_agents.safety_guard(state)
    assert result["active_agent"] == "safety_guard"
    assert "medical or mental health topic" in result["messages"][0].content

@pytest.mark.asyncio
async def test_safety_guard_pass(fitness_agents):
    # Mock LLM to return PASS
    mock_response = MagicMock()
    mock_response.content = "PASS"
    
    # Access the mock LLM from the agent
    fitness_agents.llm.ainvoke.return_value = mock_response
    
    state = {"messages": [HumanMessage(content="How do I squat better?")]}
    result = await fitness_agents.safety_guard(state)
    assert result["active_agent"] == "safe"

@pytest.mark.asyncio
async def test_orchestrator_routing_coach(fitness_agents):
    # Mock structured output
    mock_decision = OrchestratorDecision(agents=["coach"])
    
    mock_struct_llm = MagicMock()
    mock_struct_llm.invoke.return_value = mock_decision
    fitness_agents.llm.with_structured_output.return_value = mock_struct_llm
    
    state = {"messages": [HumanMessage(content="What's a good leg day workout?")]}
    result = fitness_agents.orchestrator(state)
    assert "coach" in result["planned_agents"]

@pytest.mark.asyncio
async def test_orchestrator_routing_nutrition(fitness_agents):
    mock_decision = OrchestratorDecision(agents=["nutrition"])
    
    mock_struct_llm = MagicMock()
    mock_struct_llm.invoke.return_value = mock_decision
    fitness_agents.llm.with_structured_output.return_value = mock_struct_llm
    
    state = {"messages": [HumanMessage(content="How much protein is in eggs?")]}
    result = fitness_agents.orchestrator(state)
    assert "nutrition" in result["planned_agents"]

@pytest.mark.asyncio
async def test_orchestrator_routing_both(fitness_agents):
    mock_decision = OrchestratorDecision(agents=["coach", "nutrition"])
    
    mock_struct_llm = MagicMock()
    mock_struct_llm.invoke.return_value = mock_decision
    fitness_agents.llm.with_structured_output.return_value = mock_struct_llm
    
    state = {"messages": [HumanMessage(content="Suggest a workout and a meal plan")]}
    result = fitness_agents.orchestrator(state)
    assert "coach" in result["planned_agents"]
    assert "nutrition" in result["planned_agents"]
