import networkx as nx

class FitnessGraphRAG:
    def __init__(self):
        self.graph = nx.Graph()
        self._build_initial_graph()

    def _build_initial_graph(self):
        # Adding Supplements
        self.graph.add_node("Whey Protein", type="Supplement", effect="Muscle Protein Synthesis")
        self.graph.add_node("Creatine Monohydrate", type="Supplement", effect="ATP Production")
        self.graph.add_node("Beta-Alanine", type="Supplement", effect="Buffer Lactic Acid")
        self.graph.add_node("Ashwagandha", type="Supplement", effect="Adaptogen, Cortisol Reduction")
        
        # Adding Biological Effects / Goals
        self.graph.add_node("Hypertrophy", type="Goal")
        self.graph.add_node("Strength", type="Goal")
        self.graph.add_node("Endurance", type="Goal")
        self.graph.add_node("Stress Reduction", type="Goal")
        self.graph.add_node("Cortisol Management", type="Biological Effect")
        
        # Linking
        self.graph.add_edge("Whey Protein", "Hypertrophy", weight=0.9)
        self.graph.add_edge("Creatine Monohydrate", "Strength", weight=1.0)
        self.graph.add_edge("Creatine Monohydrate", "Hypertrophy", weight=0.6)
        self.graph.add_edge("Beta-Alanine", "Endurance", weight=0.8)
        self.graph.add_edge("Ashwagandha", "Stress Reduction", weight=0.95)
        self.graph.add_edge("Ashwagandha", "Cortisol Management", weight=1.0)

    def query_supplement(self, supplement_name: str):
        """Find biological effects and goals linked to a supplement."""
        if supplement_name not in self.graph:
            return f"{supplement_name} not found in knowledge graph."
        
        connections = list(self.graph.neighbors(supplement_name))
        details = self.graph.nodes[supplement_name]
        return {
            "name": supplement_name,
            "details": details,
            "linked_to": connections
        }

    def get_recommendations_for_goal(self, goal: str):
        """Find supplements linked to a specific fitness goal."""
        if goal not in self.graph:
            return f"Goal {goal} not found."
        
        recs = []
        for neighbor in self.graph.neighbors(goal):
            edge_data = self.graph.get_edge_data(goal, neighbor)
            recs.append({"supplement": neighbor, "strength": edge_data['weight']})
        return sorted(recs, key=lambda x: x['strength'], reverse=True)
