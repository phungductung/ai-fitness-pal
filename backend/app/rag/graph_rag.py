from neo4j import GraphDatabase
import os
import logging

logger = logging.getLogger(__name__)

class FitnessGraphRAG:
    def __init__(self, uri=None, user=None, password=None):
        # By default, reads from environment variables if not passed explicitly
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test connection
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j Graph Database.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def _build_initial_graph(self):
        """Seed the graph with initial data if empty. Useful for first-time setup."""
        if not self.driver:
            logger.warning("Neo4j driver not initialized. Cannot build initial graph.")
            return
        
        query = """
        // Core Supplements
        MERGE (w:Supplement {name: 'Whey Protein'}) ON CREATE SET w.effect = 'Muscle Protein Synthesis'
        MERGE (c:Supplement {name: 'Creatine Monohydrate'}) ON CREATE SET c.effect = 'ATP Production'
        MERGE (b:Supplement {name: 'Beta-Alanine'}) ON CREATE SET b.effect = 'Buffer Lactic Acid'
        MERGE (a:Supplement {name: 'Ashwagandha'}) ON CREATE SET a.effect = 'Adaptogen, Cortisol Reduction'
        
        // New Supplements
        MERGE (caf:Supplement {name: 'Caffeine'}) ON CREATE SET caf.effect = 'CNS Stimulation, Alertness'
        MERGE (cit:Supplement {name: 'Citrulline Malate'}) ON CREATE SET cit.effect = 'Nitric Oxide Production, Vasodilation'
        MERGE (fo:Supplement {name: 'Fish Oil'}) ON CREATE SET fo.effect = 'Inflammation Reduction'
        MERGE (vd:Supplement {name: 'Vitamin D3'}) ON CREATE SET vd.effect = 'Calcium Absorption, Hormone Support'
        MERGE (mg:Supplement {name: 'Magnesium'}) ON CREATE SET mg.effect = 'Muscle Relaxation, CNS Recovery'
        MERGE (zma:Supplement {name: 'ZMA'}) ON CREATE SET zma.effect = 'Sleep Quality, Recovery'
        MERGE (mel:Supplement {name: 'Melatonin'}) ON CREATE SET mel.effect = 'Circadian Rhythm Regulation'
        MERGE (car:Supplement {name: 'L-Carnitine'}) ON CREATE SET car.effect = 'Lipid Metabolism'
        
        // Goals
        MERGE (h:Goal {name: 'Hypertrophy'})
        MERGE (s:Goal {name: 'Strength'})
        MERGE (e:Goal {name: 'Endurance'})
        MERGE (sr:Goal {name: 'Stress Reduction'})
        MERGE (fl:Goal {name: 'Fat Loss'})
        MERGE (fe:Goal {name: 'Focus & Energy'})
        MERGE (rec:Goal {name: 'Recovery'})
        MERGE (sq:Goal {name: 'Sleep Quality'})
        MERGE (jh:Goal {name: 'Joint Health'})
        
        // Biological Effects
        MERGE (cm:BiologicalEffect {name: 'Cortisol Management'})
        MERGE (mps:BiologicalEffect {name: 'Muscle Protein Synthesis'})
        MERGE (vas:BiologicalEffect {name: 'Vasodilation'})
        MERGE (inf:BiologicalEffect {name: 'Inflammation Reduction'})
        
        // Relationships
        MERGE (w)-[:SUPPORTS {weight: 0.9}]->(h)
        MERGE (w)-[:AFFECTS {weight: 1.0}]->(mps)
        
        MERGE (c)-[:SUPPORTS {weight: 1.0}]->(s)
        MERGE (c)-[:SUPPORTS {weight: 0.6}]->(h)
        
        MERGE (b)-[:SUPPORTS {weight: 0.8}]->(e)
        
        MERGE (a)-[:SUPPORTS {weight: 0.95}]->(sr)
        MERGE (a)-[:AFFECTS {weight: 1.0}]->(cm)
        MERGE (a)-[:SUPPORTS {weight: 0.7}]->(sq)
        
        MERGE (caf)-[:SUPPORTS {weight: 1.0}]->(fe)
        MERGE (caf)-[:SUPPORTS {weight: 0.6}]->(e)
        MERGE (caf)-[:SUPPORTS {weight: 0.5}]->(fl)
        
        MERGE (cit)-[:SUPPORTS {weight: 0.8}]->(e)
        MERGE (cit)-[:SUPPORTS {weight: 0.7}]->(h)
        MERGE (cit)-[:AFFECTS {weight: 0.9}]->(vas)
        
        MERGE (fo)-[:SUPPORTS {weight: 0.8}]->(jh)
        MERGE (fo)-[:SUPPORTS {weight: 0.7}]->(rec)
        MERGE (fo)-[:AFFECTS {weight: 0.9}]->(inf)
        
        MERGE (vd)-[:SUPPORTS {weight: 0.8}]->(rec)
        MERGE (vd)-[:SUPPORTS {weight: 0.6}]->(jh)
        
        MERGE (mg)-[:SUPPORTS {weight: 0.8}]->(sq)
        MERGE (mg)-[:SUPPORTS {weight: 0.9}]->(rec)
        
        MERGE (zma)-[:SUPPORTS {weight: 0.9}]->(sq)
        MERGE (zma)-[:SUPPORTS {weight: 0.8}]->(rec)
        
        MERGE (mel)-[:SUPPORTS {weight: 1.0}]->(sq)
        
        MERGE (car)-[:SUPPORTS {weight: 0.7}]->(fl)
        """
        with self.driver.session() as session:
            session.run(query)
            logger.info("Initial graph built/verified successfully.")

    def add_supplement_relation(self, supplement_name: str, supplement_effect: str, target_name: str, target_label: str = "Goal", relation_type: str = "SUPPORTS", weight: float = 1.0):
        """Dynamically add a supplement and its relation to a goal/effect."""
        if not self.driver:
            return "Neo4j not connected."
        
        # Note: Dynamic labels in Neo4j queries require string formatting or APOC
        query = f"""
        MERGE (s:Supplement {{name: $supplement_name}})
        ON CREATE SET s.effect = $supplement_effect
        MERGE (g:{target_label} {{name: $target_name}})
        MERGE (s)-[r:{relation_type}]->(g)
        SET r.weight = $weight
        RETURN s.name, g.name
        """
        try:
            with self.driver.session() as session:
                session.run(query, supplement_name=supplement_name, supplement_effect=supplement_effect, 
                            target_name=target_name, weight=weight)
                return f"Added relation: {supplement_name} -[{relation_type}]-> {target_name}"
        except Exception as e:
            logger.error(f"Error adding relation: {e}")
            return f"Failed to add relation: {e}"

    def query_supplement(self, supplement_name: str):
        """Find biological effects and goals linked to a supplement."""
        if not self.driver:
            return "Neo4j not connected."
            
        query = """
        MATCH (s:Supplement {name: $supplement_name})-[r]->(target)
        RETURN s, type(r) as relation, labels(target) as target_labels, target
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, supplement_name=supplement_name)
                connections = []
                details = None
                for record in result:
                    if not details:
                        details = dict(record["s"])
                    connections.append({
                        "relation": record["relation"],
                        "target_type": record["target_labels"][0] if record["target_labels"] else "Unknown",
                        "target_details": dict(record["target"])
                    })
                
                if not details:
                    return f"{supplement_name} not found in knowledge graph."
                    
                return {
                    "name": supplement_name,
                    "details": details,
                    "linked_to": connections
                }
        except Exception as e:
            logger.error(f"Error querying supplement: {e}")
            return f"Error querying database."

    def get_recommendations_for_goal(self, goal: str):
        """Find supplements linked to a specific fitness goal."""
        if not self.driver:
            return "Neo4j not connected."
            
        query = """
        MATCH (s:Supplement)-[r:SUPPORTS]->(g:Goal {name: $goal})
        RETURN s.name as supplement, r.weight as strength, s.effect as effect
        ORDER BY strength DESC
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, goal=goal)
                recs = [{"supplement": record["supplement"], "strength": record["strength"], "effect": record["effect"]} for record in result]
                if not recs:
                    return f"Goal '{goal}' not found or has no recommendations."
                return recs
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return f"Error querying database."
