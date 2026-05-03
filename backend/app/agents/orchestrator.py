from typing import TypedDict, Annotated, List, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from langchain_core.tools import tool
from langchain_tavily import TavilySearch as TavilySearchResults
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
import json
import os
import re
from app.utils.mcp_client import get_mcp_client
from app.tools.schemas import (
    Calculate1RMInput,
    CalculateTDEEInput,
    SuggestMacrosInput,
    VisualizeProgressInput,
    QueryKnowledgeGraphInput,
    SearchLatestFitnessResearchInput,
    QueryFitnessDiaryInput,
    AddPersonalRecordInput,
    AddDiaryEntryInput,
)

# --- Semantic LLM Cache ---
# Caches exact prompt→response pairs in a local SQLite DB.
# If the user asks the exact same question twice, the answer is returned
# instantly without hitting OpenAI — saving money and latency.
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

_cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".cache")
os.makedirs(_cache_dir, exist_ok=True)
_cache_db = os.path.join(_cache_dir, "llm_cache.db")
set_llm_cache(SQLiteCache(database_path=_cache_db))
print(f"[LLM Cache] SQLite semantic cache enabled at {_cache_db}")


# --- Structured Output Model for Orchestrator Routing ---
class OrchestratorDecision(BaseModel):
    """Routing decision from the orchestrator — which specialist agents to invoke."""

    agents: List[Literal["coach", "nutrition"]] = Field(
        description="Ordered list of specialist agents to invoke. "
        "Put the most relevant agent first. "
        "Options: 'coach' (training/exercise/recovery) or 'nutrition' (diet/calories/supplements)."
    )


# --- Destructive tool names that require human confirmation ---
DESTRUCTIVE_TOOLS = {"add_personal_record", "add_diary_entry"}


# --- Safety / Medical Guard Constants ---
# High-risk keywords that strongly indicate a medical/emergency situation
MEDICAL_KEYWORDS_HIGH = [
    r"\bchest pain\b",
    r"\bheart attack\b",
    r"\bstroke\b",
    r"\bsuicid",
    r"\bself[- ]?harm\b",
    r"\bwant to die\b",
    r"\bkill myself\b",
    r"\boverdos",
    r"\banorexia\b",
    r"\bbulimi",
    r"\bpurging\b",
    r"\bstarving myself\b",
    r"\bbleeding\b",
    r"\bfracture\b",
    r"\bbroken bone\b",
    r"\bsevere pain\b",
    r"\bcan'?t breathe\b",
    r"\bshortness of breath\b",
    r"\bblood in\b",
    r"\bconcussion\b",
    r"\bseizure\b",
    r"\bfaint(ed|ing)?\b",
    r"\bunconscious\b",
]

# Medium-risk keywords that need LLM confirmation
MEDICAL_KEYWORDS_MEDIUM = [
    r"\binjur(y|ed|ies)\b",
    r"\bdiagnos",
    r"\bprescription\b",
    r"\bmedication\b",
    r"\bdoctor\b",
    r"\bhospital\b",
    r"\bsurgery\b",
    r"\btreat(ment|ing)?\b",
    r"\bdisorder\b",
    r"\bswollen\b",
    r"\btorn\b",
    r"\bherniat",
    r"\bdisloc",
    r"\bmental health\b",
    r"\bdepression\b",
    r"\banxiety disorder\b",
    r"\beating disorder\b",
    r"\blaxativ",
    r"\bdosage\b",
    r"\bside effect\b",
    r"\bsteroid\b",
    r"\binjection\b",
]

SAFETY_DISCLAIMER = """**Important Health & Safety Notice**

I appreciate you trusting me with this, but this question touches on a **medical or mental health topic** that falls outside my scope as a fitness assistant. Providing guidance here could be harmful, so I want to be responsible.

**What I recommend:**
- **For emergencies:** Call your local emergency number (911 in the US) immediately.
- **For medical concerns:** Please consult a licensed healthcare professional or physician.
- **For mental health support:** Reach out to the [988 Suicide & Crisis Lifeline](https://988lifeline.org/) (call/text 988 in the US) or contact a mental health professional.
- **For eating disorders:** Contact the [National Eating Disorders Association](https://www.nationaleatingdisorders.org/) helpline at 1-800-931-2237.

> **Disclaimer:** I am an AI fitness assistant, not a medical professional. I cannot diagnose, treat, or provide medical advice. Always seek qualified professional guidance for health concerns.

I'm here to help with your **training, nutrition, and fitness goals** whenever you're ready! 💪"""


# Define the state for our agents
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    active_agent: str
    planned_agents: List[str]  # List of agents to be called in sequence
    data_context: dict  # Stores data retrieved from MCP or RAG
    summary: str  # Condensed history to manage token limits
    intermediate_outputs: List[dict]  # Stores raw responses from agents for blending
    pending_tool_calls: List[dict]  # Tool calls awaiting human approval


# --- Tools ---
@tool(args_schema=Calculate1RMInput)
def calculate_1rm(weight: float, reps: int):
    """Calculate 1-Rep Max using the Epley formula. Useful for bench press, squat, etc."""
    from app.tools.fitness_formulas import calculate_1rm as _calc_1rm

    return _calc_1rm(weight, reps)


@tool(args_schema=CalculateTDEEInput)
def calculate_tdee(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_multiplier: float,
):
    """Calculate Total Daily Energy Expenditure. Multiplier: 1.2 (sedentary) to 1.9 (extra active)."""
    from app.tools.fitness_formulas import calculate_tdee as _calc_tdee

    return _calc_tdee(weight_kg, height_cm, age, gender, activity_multiplier)


@tool(args_schema=SuggestMacrosInput)
def suggest_macros(tdee: float, goal: str):
    """Suggest protein, fat, and carb macros based on TDEE and goal ('bulk', 'cut', 'maintain')."""
    from app.tools.fitness_formulas import suggest_macros as _suggest_macros

    return _suggest_macros(tdee, goal)


@tool(args_schema=VisualizeProgressInput)
def visualize_progress(exercise: str):
    """Generates a progress chart for a specific exercise and returns the file path."""
    from app.tools.visualization import generate_progress_chart
    import pandas as pd

    # Using the correct path relative to the backend directory
    csv_path = "../fitness_mcp/data/prs.csv"
    output_filename = f"static/{exercise.lower().replace(' ', '_')}_progress.png"
    result = generate_progress_chart(csv_path, exercise, output_path=output_filename)

    if "successfully" in result:
        # Include actual data points in the context so the LLM response can be grounded
        try:
            df = pd.read_csv(csv_path)
            ex_data = df[df["Exercise"].str.lower() == exercise.lower()]
            if not ex_data.empty:
                records = ex_data.tail(5).to_dict(orient="records")
                data_summary = json.dumps(records)
                return (
                    f"Chart generated for {exercise}. "
                    f"![Progress](http://localhost:8000/{output_filename}). "
                    f"Recent data points: {data_summary}"
                )
        except Exception:
            pass
        return f"Chart generated successfully for {exercise}. ![Progress](http://localhost:8000/{output_filename})"
    return result


@tool(args_schema=QueryKnowledgeGraphInput)
def query_knowledge_graph(topic: str, topic_type: str):
    """Query the internal Neo4j knowledge graph for fitness relationships.
    Use this to find what a supplement does, what supplements to recommend for a specific goal, 
    or check for side effects, precautions, and synergies.
    """
    from app.rag.graph_rag import FitnessGraphRAG

    rag = FitnessGraphRAG()
    try:
        topic_type = topic_type.lower()
        if topic_type == "supplement":
            result = rag.query_supplement(topic)
        elif topic_type == "goal":
            result = rag.get_recommendations_for_goal(topic)
        elif topic_type == "side_effects":
            result = rag.query_side_effects(topic)
        elif topic_type == "synergy":
            result = rag.find_synergies(topic)
        elif topic_type == "food_source":
            result = rag.find_food_sources(topic)
        elif topic_type == "condition":
            result = rag.check_contraindications(topic)
        else:
            return "Invalid topic_type."
        return json.dumps(result)
    finally:
        rag.close()


@tool(args_schema=SearchLatestFitnessResearchInput)
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


@tool(args_schema=QueryFitnessDiaryInput)
async def query_fitness_diary(query: str):
    """Execute a SQL query on the user's local fitness diary database.
    The table name is 'diary'. Columns are: date (TEXT), entry (TEXT), calories (INTEGER), protein (INTEGER), weight (REAL).
    Use this to find what the user ate, their calorie intake, weight history, or notes from specific days.
    """
    mcp = get_mcp_client()
    return await mcp.query_diary(query)


@tool(args_schema=AddPersonalRecordInput)
async def add_personal_record(exercise: str, weight: float, reps: int):
    """Log a new personal record (PR) to the user's local fitness logs.
    Use this when the user reports a new best lift or wants to update their history.
    """
    mcp = get_mcp_client()
    return await mcp.add_pr(exercise, weight, reps)


@tool(args_schema=AddDiaryEntryInput)
async def add_diary_entry(
    entry: str, calories: int, protein: int, weight: float = None
):
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
                search_latest_fitness_research,
                get_personal_records,
                query_fitness_diary,
                add_personal_record,
                add_diary_entry,
            ]
        )

    def _detect_medical_keywords(self, text: str):
        """Two-tier keyword detection for medical/safety topics.
        Returns: ('high', matched) | ('medium', matched) | ('safe', None)
        """
        text_lower = text.lower()
        for pattern in MEDICAL_KEYWORDS_HIGH:
            if re.search(pattern, text_lower):
                return ("high", pattern)
        for pattern in MEDICAL_KEYWORDS_MEDIUM:
            if re.search(pattern, text_lower):
                return ("medium", pattern)
        return ("safe", None)

    async def safety_guard(self, state: AgentState):
        """Safety/Medical Guard Agent — pre-routing layer that intercepts
        medical, emergency, or mental-health queries before they reach
        specialist agents.  Uses a two-tier detection strategy:
          1. Regex keyword scan (fast, deterministic)
          2. LLM confirmation for medium-risk matches (avoids false positives)
        """
        last_msg = state["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        severity, matched = self._detect_medical_keywords(content)

        if severity == "high":
            # High-risk: immediately return disclaimer — no LLM call needed
            return {
                "messages": [AIMessage(content=SAFETY_DISCLAIMER, name="safety_guard")],
                "active_agent": "safety_guard",
            }

        if severity == "medium":
            # Medium-risk: ask the LLM to confirm whether this is truly medical
            confirm_prompt = f"""You are a safety classifier for a fitness chatbot.
Determine if the following user message is asking for MEDICAL ADVICE, 
INJURY TREATMENT, MENTAL HEALTH COUNSELING, or involves an EATING DISORDER.

If the message is a general fitness/nutrition question that happens to mention 
a medical term casually (e.g., "my doctor said I'm healthy" or 
"I recovered from an injury, what exercises can I do?"), classify it as SAFE.

User message: "{content}"

Respond with exactly one word: MEDICAL or SAFE."""
            try:
                response = await self.llm.ainvoke(confirm_prompt)
                classification = response.content.strip().upper()

                if "MEDICAL" in classification:
                    return {
                        "messages": [
                            AIMessage(content=SAFETY_DISCLAIMER, name="safety_guard")
                        ],
                        "active_agent": "safety_guard",
                    }
            except Exception as e:
                print(f"Error in safety_guard (medium risk confirmation): {e}")
                return {"active_agent": "error"}

        # LLM-based Guardrail for general relevance and harmfulness
        guard_prompt = f"""You are a strict input filter for a fitness AI.
Determine if the user's message contains ANY questions or statements relevant to fitness, nutrition, health, or using this app.

User message: "{content}"

If the message contains AT LEAST ONE relevant fitness/health topic (even if it also contains off-topic questions), or is a normal conversational greeting, respond with "PASS".
If the message is ENTIRELY off-topic (e.g., ONLY about coding, politics, etc.) or is harmful, respond with a polite, one-sentence refusal explaining that you are a fitness assistant.
"""
        try:
            response = await self.llm.ainvoke(guard_prompt)
            result = response.content.strip()

            if result.upper() != "PASS" and "PASS" not in result.upper():
                return {
                    "messages": [AIMessage(content=result, name="safety_guard")],
                    "active_agent": "safety_guard",
                }
        except Exception as e:
            print(f"Error in safety_guard (general relevance): {e}")
            return {"active_agent": "error"}

        # Safe — pass through to orchestrator (no message added)
        return {"active_agent": "safe"}

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
        """Decides which agents should participate in the conversation.
        Uses structured output (Pydantic model) for guaranteed valid routing."""
        last_msg = state["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        structured_llm = self.llm.with_structured_output(OrchestratorDecision)

        prompt = f"""Analyze the user's message and decide which agents should respond.
You can pick one or both.
- 'coach': For training, exercise, rest, and recovery.
- 'nutrition': For diet, calories, macros, and supplements.

User Message: "{content}"

Priority: If both are needed, put the most relevant one first."""

        try:
            decision: OrchestratorDecision = structured_llm.invoke(prompt)
            planned = decision.agents if decision.agents else ["coach"]
        except Exception as e:
            print(f"Error in orchestrator decision: {e}")
            return {"active_agent": "error"}

        return {"planned_agents": planned}

    def sequencer(self, state: AgentState):
        """Routes to the next agent in the planned sequence."""
        if state.get("active_agent") == "error":
            return "fallback"
        planned = state.get("planned_agents", [])
        if not planned:
            return END
        return planned[0]

    def _get_multimodal_content(self, file_path: str):
        """Processes images or PDFs into base64 for GPT-4o Vision."""
        from app.utils.multimodal import encode_image, pdf_to_base64_images

        if file_path.lower().endswith(".pdf"):
            base64_images = pdf_to_base64_images(file_path)
            content = [
                {
                    "type": "text",
                    "text": "I have attached the pages of the PDF as images below:",
                }
            ]
            for b64 in base64_images:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    }
                )
            return content
        else:
            b64_image = encode_image(file_path)
            return [
                {"type": "text", "text": "I have attached an image for your analysis:"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                },
            ]

    async def coach_agent(self, state: AgentState):
        """Focuses on training, PRs, and workout strategy."""
        messages = state["messages"]
        planned = state.get("planned_agents", [])
        file_path = state.get("data_context", {}).get("file_path")

        system_msg = SystemMessage(
            content="""You are an Expert Strength Coach. Focus ONLY on training, rest times, and recovery. 
            If the user asked about nutrition, your colleague the Nutritionist will handle that next, so do NOT give nutrition advice yourself. 
            If the user asked ANY completely unrelated questions (e.g., coding, politics), explicitly but politely refuse to answer that specific part.
            
            You have access to:
            1. 'get_personal_records': Use this to find the user's lift history and PRs.
            2. 'add_personal_record': Use this to log a NEW record if the user reports a lift.
            3. 'query_fitness_diary': Use this to check the user's weight history or calorie intake.
            4. 'visualize_progress': Use this to generate charts.
            5. 'search_latest_fitness_research': Use this to find performance studies.
            
            Always check the logs with 'get_personal_records' or 'query_fitness_diary' first.
            
            CRITICAL RULES FOR GROUNDED RESPONSES:
            - Your response MUST only contain information present in the tool outputs. Do NOT add general advice, tips, or recommendations beyond what the tools returned.
            - When a tool returns data, report that data directly. Do NOT interpret, extrapolate, or add coaching tips unless the tool output contains them.
            - When logging a PR, confirm EXACTLY what was logged using the tool's confirmation message. Do NOT rephrase or reinterpret the logged data.
            - Format with clear Markdown. Be concise and direct; no conversational fluff or encouragement."""
        )

        input_messages = [system_msg] + messages
        if file_path and os.path.exists(file_path):
            multimodal_content = self._get_multimodal_content(file_path)
            input_messages.append(HumanMessage(content=multimodal_content))

        try:
            response = await self.llm_with_tools.ainvoke(input_messages)
        except Exception as e:
            print(f"Error in coach_agent: {e}")
            return {"active_agent": "error"}

        # If calling a tool, keep the agent active and don't remove from plan
        if response.tool_calls:
            return {
                "messages": [response],
                "active_agent": "coach",
                "planned_agents": planned,
            }

        # If it's a final text response, store it for blending and move to next
        remaining = planned[1:] if planned and planned[0] == "coach" else planned
        new_output = {"sender": "coach", "content": response.content}
        return {
            "intermediate_outputs": state.get("intermediate_outputs", [])
            + [new_output],
            "active_agent": "coach",
            "planned_agents": remaining,
        }

    async def nutrition_agent(self, state: AgentState):
        """Focuses on macros, calories, and supplements."""
        messages = state["messages"]
        planned = state.get("planned_agents", [])
        file_path = state.get("data_context", {}).get("file_path")

        system_msg = SystemMessage(
            content="""You are a Senior Nutritionist. Focus ONLY on diet, calories, and supplements. 
            If the user asked about training, your colleague the Strength Coach will handle that, so do NOT give workout advice yourself. 
            If the user asked ANY completely unrelated questions (e.g., coding, politics), explicitly but politely refuse to answer that specific part.
            
            PRIORITY FOR INFORMATION:
            1. Use 'query_fitness_diary' to find what the user has eaten, their weight history, or other logs.
            2. Use 'add_diary_entry' to log new meals, calories, protein intake, or current body weight.
            3. Use 'query_knowledge_graph' to get exact connections between Supplements, Goals, Side Effects, Precautions, Synergies, Food Sources, and Medical Contraindications.
            4. Use 'search_latest_fitness_research' (Tavily) to search the web for any specific scientific studies or unstructured fitness questions not found in the graph.
            
            CRITICAL RULES FOR GROUNDED RESPONSES:
            - Your response MUST only contain information present in the tool outputs. Do NOT add general nutrition advice or explanations beyond what the tools returned.
            - When reporting supplement data from the knowledge graph, use ONLY the fields returned (name, strength, effect, dosage, side_effects, precautions, food_sources, contraindications). Do NOT elaborate on what these effects mean or add your own interpretation.
            - When reporting diary data, state the exact numbers from the data. Do NOT add analysis or dietary recommendations unless the tool output contains them.
            - Format with clear Markdown. Be concise and direct; no conversational fluff or encouragement."""
        )

        input_messages = [system_msg] + messages
        if file_path and os.path.exists(file_path):
            multimodal_content = self._get_multimodal_content(file_path)
            input_messages.append(HumanMessage(content=multimodal_content))

        try:
            response = await self.llm_with_tools.ainvoke(input_messages)
        except Exception as e:
            print(f"Error in nutrition_agent: {e}")
            return {"active_agent": "error"}

        # If calling a tool, keep active
        if response.tool_calls:
            return {
                "messages": [response],
                "active_agent": "nutrition",
                "planned_agents": planned,
            }

        # Final text response
        remaining = planned[1:] if planned and planned[0] == "nutrition" else planned
        new_output = {"sender": "nutrition", "content": response.content}
        return {
            "intermediate_outputs": state.get("intermediate_outputs", [])
            + [new_output],
            "active_agent": "nutrition",
            "planned_agents": remaining,
        }

    async def aggregator(self, state: AgentState):
        """Blends outputs from multiple agents into a single cohesive response."""
        outputs = state.get("intermediate_outputs", [])
        if not outputs:
            return {
                "messages": [
                    AIMessage(
                        content="I'm not sure how to help with that specifically.",
                        name="assistant",
                    )
                ]
            }

        # Always blend/rewrite to ensure a consistent premium tone and trigger token streaming
        blend_prompt = f"""
        You are the Head AI Fitness Assistant. Your task is to unify the specialist advice below into a single, direct, and expert response.
        
        Specialist Advice:
        {json.dumps(outputs, indent=2)}
        
        Strict Rules for High Faithfulness:
        1. **Stick to the facts**: Only include information provided by the specialists. Do not add outside knowledge or general advice unless it's explicitly mentioned by them.
        2. **No conversational filler**: Do NOT use greetings, sign-offs, or transitions like "According to the coach".
        3. **Concise Refusals**: If a specialist refused an off-topic part of the prompt, include a brief, one-sentence refusal at the end.
        4. **Markdown Formatting**: Use clear headers and lists.
        5. **Direct Answer**: Start with the most important information or the answer to the user's primary question.
        6. **Zero embellishment**: Do NOT add encouragement, motivational phrases (e.g., "Keep up the good work!", "Great job!"), or any text not directly derived from the specialist data above.
        7. **Traceability**: Every claim or number in your response MUST come from the specialist advice above. If the specialists didn't mention it, do NOT include it.
        """

        try:
            response = await self.llm.ainvoke(blend_prompt)
            # Force the name to 'assistant' for consistent UI display
            response.name = "assistant"
            return {
                "messages": [response],
                "intermediate_outputs": [],
            }  # Clear intermediate for next turn
        except Exception as e:
            print(f"Error in aggregator: {e}")
            return {"active_agent": "error"}

    def fallback(self, state: AgentState):
        """Fallback node to handle errors gracefully."""
        error_msg = AIMessage(
            content="I'm sorry, I encountered a technical difficulty while processing your request. Please try again later.",
            name="assistant",
        )
        return {
            "messages": [error_msg],
            "active_agent": "fallback",
            "planned_agents": [],
        }


# --- Building the Graph ---

# Module-level checkpointer so it persists across requests
_checkpointer = MemorySaver()


def create_fitness_graph(is_eval: bool = False):
    agents = FitnessAgents()
    workflow = StateGraph(AgentState)
    agents.is_eval = is_eval

    # Define tools node for safe (read-only) tools
    all_tools = [
        calculate_1rm,
        calculate_tdee,
        suggest_macros,
        visualize_progress,
        query_knowledge_graph,
        search_latest_fitness_research,
        get_personal_records,
        query_fitness_diary,
        add_personal_record,
        add_diary_entry,
    ]
    tools_node = ToolNode(all_tools)

    async def safe_tools_node(state: AgentState, config):
        try:
            return await tools_node.ainvoke(state, config)
        except Exception:
            return {"active_agent": "error"}

    # --- Human Review Node (interrupt before destructive actions) ---
    async def human_review(state: AgentState):
        """Intercept destructive tool calls and ask the user for confirmation
        via a LangGraph interrupt.  Non-destructive calls pass through."""
        last_message = state["messages"][-1]

        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {}  # Nothing to review

        destructive_calls = [
            tc for tc in last_message.tool_calls if tc["name"] in DESTRUCTIVE_TOOLS
        ]

        if not destructive_calls:
            return {}  # All calls are safe — skip review

        # Build a human-readable summary of what is about to happen
        descriptions = []
        for tc in destructive_calls:
            if tc["name"] == "add_diary_entry":
                args = tc["args"]
                descriptions.append(
                    f'📝 **Log diary entry:** "{args.get("entry", "")}" '
                    f"({args.get('calories', 0)} kcal, {args.get('protein', 0)}g protein"
                    + (f", {args.get('weight')} kg" if args.get("weight") else "")
                    + ")"
                )
            elif tc["name"] == "add_personal_record":
                args = tc["args"]
                descriptions.append(
                    f"🏋️ **Log PR:** {args.get('exercise', '?')} — "
                    f"{args.get('weight', 0)} kg × {args.get('reps', 0)} reps"
                )

        summary = "\n".join(descriptions)
        confirmation_msg = (
            f"I'm about to make the following changes:\n\n{summary}\n\n"
            "**Do you approve?** Reply `yes` to confirm or `no` to cancel."
        )

        # Interrupt execution — the graph pauses here until the user resumes
        human_response = interrupt(
            {
                "question": confirmation_msg,
                "tool_calls": [tc for tc in destructive_calls],
            }
        )

        # When resumed, human_response is the value passed via Command(resume=...)
        if isinstance(human_response, str) and human_response.lower().strip() in (
            "yes",
            "y",
            "approve",
            "confirm",
        ):
            # Approved — proceed (the tool node will execute next)
            return {}
        else:
            # Rejected — replace the AI message's tool calls with a cancellation
            cancel_msg = AIMessage(
                content="✅ Got it — I've cancelled that action. No changes were made.",
                name="assistant",
            )
            return {
                "messages": [cancel_msg],
                "active_agent": "cancelled",
                "planned_agents": [],
            }

    # Add all nodes — safety_guard is the new entry point
    workflow.add_node("safety_guard", agents.safety_guard)
    workflow.add_node("orchestrator", agents.orchestrator)
    workflow.add_node("coach", agents.coach_agent)
    workflow.add_node("nutrition", agents.nutrition_agent)
    workflow.add_node("aggregator", agents.aggregator)
    workflow.add_node("human_review", human_review)
    workflow.add_node("tools", safe_tools_node)
    workflow.add_node("fallback", agents.fallback)

    # Entry point: every message goes through the safety guard first
    workflow.set_entry_point("safety_guard")

    # Safety guard routing: if flagged → END, otherwise → orchestrator
    def after_safety_guard(state: AgentState):
        if state.get("active_agent") == "error":
            return "fallback"
        if state.get("active_agent") == "safety_guard":
            return END  # Medical/safety topic detected — response already set
        return "orchestrator"  # Safe — proceed to normal routing

    workflow.add_conditional_edges(
        "safety_guard",
        after_safety_guard,
        {END: END, "orchestrator": "orchestrator", "fallback": "fallback"},
    )

    # Orchestrator decides which specialist agents to invoke
    def sequencer_routing(state: AgentState):
        if state.get("active_agent") == "error":
            return "fallback"
        planned = state.get("planned_agents", [])
        if not planned:
            return END
        return planned[0]

    workflow.add_conditional_edges("orchestrator", sequencer_routing)

    # Routing logic after an agent speaks
    def after_agent(state: AgentState):
        if state.get("active_agent") == "error":
            return "fallback"

        last_message = state["messages"][-1]
        # Only AIMessages have tool_calls attribute
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            # Check if any tool call is destructive → route to human review
            has_destructive = any(
                tc["name"] in DESTRUCTIVE_TOOLS for tc in last_message.tool_calls
            )
            if has_destructive and not is_eval:
                return "human_review"
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
            "human_review": "human_review",
            "coach": "coach",
            "nutrition": "nutrition",
            "aggregator": "aggregator",
            "fallback": "fallback",
        },
    )

    workflow.add_conditional_edges(
        "nutrition",
        after_agent,
        {
            "tools": "tools",
            "human_review": "human_review",
            "coach": "coach",
            "nutrition": "nutrition",
            "aggregator": "aggregator",
            "fallback": "fallback",
        },
    )

    # After aggregator, we are definitely done
    def after_aggregator(state: AgentState):
        if state.get("active_agent") == "error":
            return "fallback"
        return END

    workflow.add_conditional_edges(
        "aggregator", after_aggregator, {END: END, "fallback": "fallback"}
    )

    # After human_review: if cancelled → END, otherwise → tools
    def after_human_review(state: AgentState):
        if state.get("active_agent") == "cancelled":
            return END
        return "tools"

    workflow.add_conditional_edges(
        "human_review",
        after_human_review,
        {"tools": "tools", END: END},
    )

    # After tools, go back to the active agent to interpret results
    def after_tools(state: AgentState):
        if state.get("active_agent") == "error":
            return "fallback"
        return state.get("active_agent", "coach")

    workflow.add_conditional_edges("tools", after_tools)

    workflow.add_edge("fallback", END)

    # Compile with checkpointer for persistent memory
    # and interrupt_before for human-in-the-loop on the review node
    return workflow.compile(
        checkpointer=_checkpointer,
    )
