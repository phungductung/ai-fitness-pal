import os
from dotenv import load_dotenv

import json
import asyncio
from app.agents.orchestrator import create_fitness_graph
from langchain_core.messages import HumanMessage, ToolMessage
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from ragas.llms import LangchainLLMWrapper
from ragas.run_config import RunConfig
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from datasets import Dataset
import pandas as pd

load_dotenv()


# Load dataset
def load_eval_dataset(file_path: str):
    with open(file_path, "r") as f:
        return json.load(f)


async def run_evaluation():
    dataset = load_eval_dataset("tests/eval_dataset.json")
    graph = create_fitness_graph(is_eval=True)

    results = []

    # We iterate through the dataset to get responses from our graph
    for i, item in enumerate(dataset):
        print(f"Testing: {item['question']}")

        # Invoke graph with a unique thread_id per question to ensure isolation
        thread_id = f"eval_thread_{i}"
        inputs = {"messages": [HumanMessage(content=item["question"])]}
        config = {"configurable": {"thread_id": thread_id}}

        # We use astream to capture intermediate states if needed,
        # but here we just want the final result.
        final_state = {}
        async for event in graph.astream(inputs, config=config, stream_mode="values"):
            final_state = event

        # The 'values' stream mode yields the full state dictionary
        messages = final_state.get("messages", [])
        if not messages:
            continue
        last_msg = messages[-1]

        # Extract contexts from ToolMessages
        retrieved_contexts = []
        for m in messages:
            if isinstance(m, ToolMessage):
                # Truncate extremely long tool outputs to prevent token overflow
                content = m.content
                if len(content) > 3000:
                    content = content[:3000] + "... [truncated]"
                retrieved_contexts.append(content)

        # If no tools were called, use the data_context as a fallback
        if not retrieved_contexts:
            data_ctx = final_state.get("data_context", {})
            if data_ctx:
                ctx_str = str(data_ctx)
                if len(ctx_str) > 3000:
                    ctx_str = ctx_str[:3000] + "... [truncated]"
                retrieved_contexts.append(ctx_str)
            else:
                retrieved_contexts.append(
                    "No context retrieved (direct LLM knowledge)."
                )

        # Ragas expects: question, answer, contexts, ground_truth (optional)
        results.append(
            {
                "question": item["question"],
                "answer": last_msg.content,
                "contexts": retrieved_contexts,
                "ground_truth": item.get("expected_answer_contains", ""),
                "actual_agent": final_state.get("active_agent"),
                "skip_faithfulness": item.get("skip_faithfulness", False),
            }
        )

    # Convert to Ragas format
    df = pd.DataFrame(results)
    eval_dataset = Dataset.from_pandas(df)

    # Run Ragas evaluation
    print("Running Ragas metrics...")

    # Using ChatOpenAI with explicit max_tokens to prevent InstructorRetryException
    # for long responses that require extensive decomposition (like workout plans).
    llm = ChatOpenAI(model="gpt-4o", max_tokens=4096)
    judge_llm = LangchainLLMWrapper(llm)
    judge_embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))

    metrics = [faithfulness, answer_relevancy]

    # RunConfig helps manage timeouts and prevent rate limits
    run_config = RunConfig(timeout=120, max_retries=2)

    score = evaluate(
        eval_dataset,
        metrics=metrics,
        llm=judge_llm,
        embeddings=judge_embeddings,
        run_config=run_config,
        batch_size=1,
    )

    print("\n--- Evaluation Summary (Raw) ---")
    print(score)

    # Save full results
    df_results = score.to_pandas()

    # Merge skip_faithfulness flag into results for analysis
    df_results["skip_faithfulness"] = df["skip_faithfulness"].values
    df_results.to_csv("tests/eval_results.csv", index=False)
    print("Detailed results saved to tests/eval_results.csv")

    # --- Adjusted Metrics (excluding structurally unfair questions) ---
    df_faithful = df_results[~df_results["skip_faithfulness"]]
    df_relevant = df_results[
        df_results["answer_relevancy"] > 0.0  # exclude guard-rail 0.0s
    ]

    adj_faithfulness = df_faithful["faithfulness"].mean()
    adj_relevancy = df_relevant["answer_relevancy"].mean()

    print("\n--- Adjusted Evaluation Summary ---")
    print(
        f"Faithfulness (adjusted, {len(df_faithful)} questions): {adj_faithfulness:.4f}"
    )
    print(
        f"Answer Relevancy (adjusted, {len(df_relevant)} questions): {adj_relevancy:.4f}"
    )
    print("")
    print(
        f"Excluded from faithfulness: {len(df_results) - len(df_faithful)} questions (skip_faithfulness=True)"
    )
    print(
        f"Excluded from relevancy: {len(df_results) - len(df_relevant)} questions (score=0.0, guard-rail rejections)"
    )

    # Per-question breakdown for faithfulness issues
    low_faith = df_faithful[df_faithful["faithfulness"] < 0.5]
    if not low_faith.empty:
        print("\n--- Low Faithfulness Questions (< 0.5) ---")
        for _, row in low_faith.iterrows():
            print(f"  [{row['faithfulness']:.2f}] {row['user_input'][:80]}")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set. Please ensure it is in your .env file.")
    else:
        asyncio.run(run_evaluation())
