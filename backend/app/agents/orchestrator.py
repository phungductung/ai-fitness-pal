from typing import TypedDict, Annotated, List, Union
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langchain_tavily import TavilySearch as TavilySearchResults
from langgraph.prebuilt import ToolNode
import json
import os
from app.utils.mcp_client import get_mcp_client


# Define the state for our agents
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    active_agent: str
    planned_agents: List[str] # List of agents to be called in sequence
    data_context: dict  # Stores data retrieved from MCP or RAG
    summary: str  # Condensed history to manage token limits
    intermediate_outputs: List[dict] # Stores raw responses from agents for blending



# --- Tools ---
@tool
def calculate_1rm(weight: float, reps: int):
    """Calculate 1-Rep Max using the Epley formula. Useful for bench press, squat, etc."""
    from app.tools.fitness_formulas import calculate_1rm as _calc_1rm
    return _calc_1rm(weight, reps)

@tool
def calculate_tdee(weight_kg: float, height_cm: float, age: int, gender: str, activity_multiplier: float):
    """Calculate Total Daily Energy Expenditure. Multiplier: 1.2 (sedentary) to 1.9 (extra active)."""
    from app.tools.fitness_formulas import calculate_tdee as _calc_tdee
    return _calc_tdee(weight_kg, height_cm, age, gender, activity_multiplier)

@tool
def suggest_macros(tdee: float, goal: str):
    """Suggest protein, fat, and carb macros based on TDEE and goal ('bulk', 'cut', 'maintain')."""
    from app.tools.fitness_formulas import suggest_macros as _suggest_macros
    return _suggest_macros(tdee, goal)


@tool
def visualize_progress(exercise: str):
    """Generates a progress chart for a specific exercise and returns the file path."""
    from app.tools.visualization import generate_progress_chart

    # Using the correct path relative to the backend directory
    csv_path = "../fitness_mcp/data/prs.csv"
    output_filename = f"static/{exercise.lower().replace(' ', '_')}_progress.png"
    result = generate_progress_chart(csv_path, exercise, output_path=output_filename)
    
    if "successfully" in result:
        # Return markdown so the Chat UI can render it immediately
        return f"Chart generated successfully! ![Progress](http://localhost:8000/{output_filename})"
    return result


@tool
def query_knowledge_graph(query: str):
    """Query the internal knowledge graph for relationships between supplements, biological effects, and fitness goals.
    Use this for high-level relationships (e.g., 'What are the biological effects of X?').
    """
    from app.rag.graph_rag import FitnessGraphRAG
    rag = FitnessGraphRAG()
    # Basic logic: if query contains a supplement name, query it
    supplements = ["Whey Protein", "Creatine Monohydrate", "Beta-Alanine", "Ashwagandha"]
    for s in supplements:
        if s.lower() in query.lower():
            return json.dumps(rag.query_supplement(s))
    return "No specific supplement found in the knowledge graph for this query. Try searching the research database."

@tool
def search_research_database(query: str):
    """Search the internal vector database for detailed scientific research snippets.
    Use this for specific biological mechanisms or detailed evidence.
    """
    from app.rag.vector_rag import FitnessVectorRAG
    api_key = os.getenv("OPENAI_API_KEY")
    rag = FitnessVectorRAG(api_key)
    
    # Simple hardcoded snippets for demonstration if DB is empty
    snippets = [
        "Ashwagandha (Withania somnifera) is an adaptogen that has been shown to significantly reduce serum cortisol levels in chronically stressed adults.",
        "Clinical trials suggest that Ashwagandha supplementation is associated with muscle mass increase and strength gains in conjunction with resistance training.",
        "The primary bioactive constituents of Ashwagandha are withanolides, which mediate its anti-stress and anti-inflammatory effects."
    ]
    rag.initialize_with_texts(snippets)
    return json.dumps(rag.search(query))


@tool
def search_latest_fitness_research(query: str):
    """Search the internet for the latest fitness studies, nutritional news, or athletic performance research.
    Use this tool whenever the user asks about recent studies, 'the latest' information, or specific scientific evidence.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY is not set in the environment. Please add it to your .env file to enable live research."
    
    search = TavilySearchResults(max_results=3)
    return search.invoke(query)


@tool
async def get_personal_records():
    """Fetch the user's personal records (PRs) from their local fitness logs.
    Use this to answer questions about their heaviest lifts, best performances, or historical PR data.
    """
    mcp = get_mcp_client()
    return await mcp.get_prs()

@tool
async def query_fitness_diary(query: str):
    """Execute a SQL query on the user's local fitness diary database.
    The table name is 'diary'. Columns are: date (TEXT), entry (TEXT), calories (INTEGER), protein (INTEGER), weight (REAL).
    Use this to find what the user ate, their calorie intake, weight history, or notes from specific days.
    """
    mcp = get_mcp_client()
    return await mcp.query_diary(query)


@tool
async def add_personal_record(exercise: str, weight: float, reps: int):
    """Log a new personal record (PR) to the user's local fitness logs.
    Use this when the user reports a new best lift or wants to update their history.
    """
    mcp = get_mcp_client()
    return await mcp.add_pr(exercise, weight, reps)

@tool
async def add_diary_entry(entry: str, calories: int, protein: int, weight: float = None):
    """Add a new entry to the user's daily fitness diary.
    Use this when the user reports what they ate, their current weight, or wants to log their nutritional intake.
    """
    mcp = get_mcp_client()
    return await mcp.add_diary(entry, calories, protein, weight)


# --- Agent Nodes ---
class FitnessAgents:
    def __init__(self, model_name="gpt-4o"):
        self.llm = ChatOpenAI(model=model_name)
        self.llm_with_tools = self.llm.bind_tools(
            [
                calculate_1rm,
                calculate_tdee,
                suggest_macros,
                visualize_progress,
                query_knowledge_graph,
                search_research_database,
                search_latest_fitness_research,
                get_personal_records,
                query_fitness_diary,
                add_personal_record,
                add_diary_entry,
            ]
        )

    def summarize_conversation(self, state: AgentState):
        """Condense long conversation history into a concise summary."""
        messages = state["messages"]
        if len(messages) < 10:
            return {"summary": state.get("summary", "")}

        summary_prompt = f"Summarize the following fitness conversation concisely, focusing on current goals, recent PRs, and health metrics: {messages}"
        response = self.llm.invoke(summary_prompt)
        # We keep the summary and clear the messages (rolling window logic)
        return {"summary": response.content, "messages": messages[-4:]}

    def orchestrator(self, state: AgentState):
        """Decides which agents should participate in the conversation."""
        last_msg = state["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        
        prompt = f"""
        Analyze the user's message and decide which agents should respond. 
        You can pick one or both.
        - 'coach': For training, exercise, rest, and recovery.
        - 'nutrition': For diet, calories, macros, and supplements.
        
        User Message: "{content}"
        
        Respond with a JSON list of agent names, e.g., ["coach"] or ["nutrition", "coach"].
        Priority: If both are needed, put the most relevant one first.
        """
        
        response = self.llm.invoke(prompt)
        try:
            cleaned_content = response.content.strip()
            if "```json" in cleaned_content:
                cleaned_content = cleaned_content.split("```json")[1].split("```")[0].strip()
            
            planned = json.loads(cleaned_content)
            if not isinstance(planned, list) or not planned: 
                planned = ["coach"]
        except Exception as e:
            planned = ["coach"]
            
        return {"planned_agents": planned}

    def sequencer(self, state: AgentState):
        """Routes to the next agent in the planned sequence."""
        planned = state.get("planned_agents", [])
        if not planned:
            return END
        return planned[0]

    def _get_multimodal_content(self, file_path: str):
        """Processes images or PDFs into base64 for GPT-4o Vision."""
        from app.utils.multimodal import encode_image, pdf_to_base64_images
        
        if file_path.lower().endswith(".pdf"):
            base64_images = pdf_to_base64_images(file_path)
            content = [{"type": "text", "text": "I have attached the pages of the PDF as images below:"}]
            for b64 in base64_images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                })
            return content
        else:
            b64_image = encode_image(file_path)
            return [
                {"type": "text", "text": "I have attached an image for your analysis:"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}
                }
            ]

    async def coach_agent(self, state: AgentState):
        """Focuses on training, PRs, and workout strategy."""
        messages = state["messages"]
        planned = state.get("planned_agents", [])
        file_path = state.get("data_context", {}).get("file_path")
        
        system_msg = SystemMessage(
            content="""You are an Expert Strength Coach. Focus ONLY on training, rest times, and recovery. 
            If the user asked about nutrition, your colleague the Nutritionist will handle that next, so do NOT give nutrition advice yourself. 
            
            You have access to:
            1. 'get_personal_records': Use this to find the user's lift history and PRs.
            2. 'add_personal_record': Use this to log a NEW record if the user reports a lift.
            3. 'query_fitness_diary': Use this to check the user's weight history or calorie intake.
            4. 'visualize_progress': Use this to generate charts.
            5. 'search_latest_fitness_research': Use this to find performance studies.
            
            Always check the logs with 'get_personal_records' or 'query_fitness_diary' first.
            Format with clear Markdown."""
        )
        
        input_messages = [system_msg] + messages
        if file_path and os.path.exists(file_path):
            multimodal_content = self._get_multimodal_content(file_path)
            input_messages.append(HumanMessage(content=multimodal_content))
            
        response = await self.llm_with_tools.ainvoke(input_messages)
        
        # If calling a tool, keep the agent active and don't remove from plan
        if response.tool_calls:
            return {"messages": [response], "active_agent": "coach", "planned_agents": planned}
            
        # If it's a final text response, store it for blending and move to next
        remaining = planned[1:] if planned and planned[0] == "coach" else planned
        new_output = {"sender": "coach", "content": response.content}
        return {
            "intermediate_outputs": state.get("intermediate_outputs", []) + [new_output],
            "active_agent": "coach", 
            "planned_agents": remaining
        }

    async def nutrition_agent(self, state: AgentState):
        """Focuses on macros, calories, and supplements."""
        messages = state["messages"]
        planned = state.get("planned_agents", [])
        file_path = state.get("data_context", {}).get("file_path")
        
        system_msg = SystemMessage(
            content="""You are a Senior Nutritionist. Focus ONLY on diet, calories, and supplements. 
            If the user asked about training, your colleague the Strength Coach will handle that, so do NOT give workout advice yourself. 
            
            PRIORITY FOR INFORMATION:
            1. Use 'query_fitness_diary' to find what the user has eaten, their weight history, or other logs.
            2. Use 'add_diary_entry' to log new meals, calories, protein intake, or current body weight.
            3. Use 'query_knowledge_graph' for high-level relationships and biological effects of supplements.
            4. Use 'search_research_database' for specific scientific snippets and mechanisms.
            5. Use 'search_latest_fitness_research' (Tavily) ONLY if internal tools are insufficient.
            
            Format with clear Markdown."""
        )
        
        input_messages = [system_msg] + messages
        if file_path and os.path.exists(file_path):
            multimodal_content = self._get_multimodal_content(file_path)
            input_messages.append(HumanMessage(content=multimodal_content))
            
        response = await self.llm_with_tools.ainvoke(input_messages)
        
        # If calling a tool, keep active
        if response.tool_calls:
            return {"messages": [response], "active_agent": "nutrition", "planned_agents": planned}
            
        # Final text response
        remaining = planned[1:] if planned and planned[0] == "nutrition" else planned
        new_output = {"sender": "nutrition", "content": response.content}
        return {
            "intermediate_outputs": state.get("intermediate_outputs", []) + [new_output],
            "active_agent": "nutrition", 
            "planned_agents": remaining
        }

    async def aggregator(self, state: AgentState):
        """Blends outputs from multiple agents into a single cohesive response."""
        outputs = state.get("intermediate_outputs", [])
        if not outputs:
            return {"messages": [AIMessage(content="I'm not sure how to help with that specifically.")]}

        if len(outputs) == 1:
            # Only one agent responded, return it as assistant
            return {"messages": [AIMessage(content=outputs[0]["content"], name="assistant")]}


        # Multiple agents, blend them
        blend_prompt = f"""
        You are the Head AI Fitness Assistant. You need to blend advice from your specialists into a single, cohesive, and premium response.
        
        Specialist Advice:
        {json.dumps(outputs, indent=2)}
        
        Strict Rules:
        1. Do NOT use greetings (e.g., 'Hello', 'Hi', 'Dear').
        2. Do NOT use sign-offs or signatures (e.g., 'Best regards', 'Your Fitness Assistant').
        3. Do NOT say 'Coach says X and Nutritionist says Y'. 
        4. Go STRAIGHT to the advice and information.
        5. Create a unified narrative that flows logically.
        6. Use clean Markdown formatting.
        7. Maintain a natural, expert, and direct conversational tone.
        """
        
        response = await self.llm.ainvoke(blend_prompt)
        # Force the name to 'assistant' for consistent UI display
        response.name = "assistant"
        return {"messages": [response], "intermediate_outputs": []} # Clear intermediate for next turn



# --- Building the Graph ---
def create_fitness_graph():
    agents = FitnessAgents()
    workflow = StateGraph(AgentState)

    # Define tools node
    tools_node = ToolNode(
        [
            calculate_1rm,
            calculate_tdee,
            suggest_macros,
            visualize_progress,
            query_knowledge_graph,
            search_research_database,
            search_latest_fitness_research,
            get_personal_records,
            query_fitness_diary,
            add_personal_record,
            add_diary_entry,
        ]
    )

    workflow.add_node("orchestrator", agents.orchestrator)
    workflow.add_node("coach", agents.coach_agent)
    workflow.add_node("nutrition", agents.nutrition_agent)
    workflow.add_node("aggregator", agents.aggregator)
    workflow.add_node("tools", tools_node)


    # Simplified Sequence logic
    workflow.set_entry_point("orchestrator")

    def sequencer_routing(state: AgentState):
        planned = state.get("planned_agents", [])
        if not planned:
            return END
        return planned[0]

    # After planning, go to the first agent
    workflow.add_conditional_edges("orchestrator", sequencer_routing)

    # Routing logic after an agent speaks
    def after_agent(state: AgentState):
        last_message = state["messages"][-1]
        # Only AIMessages have tool_calls attribute
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        
        # If no tool calls, check for next agent in sequence
        planned = state.get("planned_agents", [])
        if not planned:
            return "aggregator"
        return planned[0]

    workflow.add_conditional_edges(
        "coach",
        after_agent,
        {
            "tools": "tools",
            "coach": "coach", 
            "nutrition": "nutrition",
            "aggregator": "aggregator"
        }
    )

    workflow.add_conditional_edges(
        "nutrition",
        after_agent,
        {
            "tools": "tools",
            "coach": "coach",
            "nutrition": "nutrition",
            "aggregator": "aggregator"
        }
    )

    # After aggregator, we are definitely done
    workflow.add_edge("aggregator", END)


    # After tools, go back to the active agent to interpret results
    def after_tools(state: AgentState):
        return state.get("active_agent", "coach")

    workflow.add_conditional_edges("tools", after_tools)

    return workflow.compile()
