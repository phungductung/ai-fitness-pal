from app.rag.graph_rag import FitnessGraphRAG
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

print("Connecting to Neo4j...")
# FitnessGraphRAG automatically reads from NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
graph = FitnessGraphRAG()

if graph.driver:
    print("Building the initial knowledge graph...")
    graph._build_initial_graph()
    print("Done! The database has been populated with the baseline fitness data.")
else:
    print("Error: Could not connect to Neo4j. Check your .env credentials.")

graph.close()
