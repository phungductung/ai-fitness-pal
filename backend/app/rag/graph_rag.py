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
        MERGE (w:Supplement {name: 'Whey Protein'}) ON CREATE SET w.effect = 'Muscle Protein Synthesis', w.dosage = '20-30g post-workout'
        MERGE (c:Supplement {name: 'Creatine Monohydrate'}) ON CREATE SET c.effect = 'ATP Production, Cell Volumization', c.dosage = '5g daily'
        MERGE (b:Supplement {name: 'Beta-Alanine'}) ON CREATE SET b.effect = 'Buffer Lactic Acid', b.dosage = '3.2-6.4g daily'
        MERGE (a:Supplement {name: 'Ashwagandha'}) ON CREATE SET a.effect = 'Adaptogen, Cortisol Reduction', a.dosage = '300-600g KSM-66'
        
        // Additional Supplements
        MERGE (caf:Supplement {name: 'Caffeine'}) ON CREATE SET caf.effect = 'CNS Stimulation, Alertness', caf.dosage = '100-200mg'
        MERGE (the:Supplement {name: 'L-Theanine'}) ON CREATE SET the.effect = 'Anxiolytic, Focus', the.dosage = '100-200mg'
        MERGE (cit:Supplement {name: 'Citrulline Malate'}) ON CREATE SET cit.effect = 'Nitric Oxide Production, Vasodilation', cit.dosage = '6-8g'
        MERGE (fo:Supplement {name: 'Fish Oil'}) ON CREATE SET fo.effect = 'Inflammation Reduction, Heart Health', fo.dosage = '1-2g EPA/DHA'
        MERGE (vd:Supplement {name: 'Vitamin D3'}) ON CREATE SET vd.effect = 'Calcium Absorption, Hormone Support', vd.dosage = '2000-5000 IU'
        MERGE (vk:Supplement {name: 'Vitamin K2'}) ON CREATE SET vk.effect = 'Bone Health, Cardiovascular Health', vk.dosage = '100-200mcg'
        MERGE (mg:Supplement {name: 'Magnesium'}) ON CREATE SET mg.effect = 'Muscle Relaxation, CNS Recovery', mg.dosage = '200-400mg'
        MERGE (zn:Supplement {name: 'Zinc'}) ON CREATE SET zn.effect = 'Immune Support, Testosterone Support', zn.dosage = '10-30mg'
        MERGE (mel:Supplement {name: 'Melatonin'}) ON CREATE SET mel.effect = 'Circadian Rhythm Regulation', mel.dosage = '1-3mg'
        MERGE (rho:Supplement {name: 'Rhodiola Rosea'}) ON CREATE SET rho.effect = 'Anti-fatigue, Adaptogen', rho.dosage = '300-500mg'
        MERGE (ber:Supplement {name: 'Berberine'}) ON CREATE SET ber.effect = 'AMPK Activation, Blood Sugar Regulation', ber.dosage = '500mg 3x daily'
        MERGE (cur:Supplement {name: 'Curcumin'}) ON CREATE SET cur.effect = 'Potent Anti-inflammatory', cur.dosage = '500mg with Piperine'
        MERGE (pip:Supplement {name: 'Piperine'}) ON CREATE SET pip.effect = 'Bioavailability Enhancer', pip.dosage = '5-20mg'
        MERGE (agp:Supplement {name: 'Alpha-GPC'}) ON CREATE SET agp.effect = 'Choline Source, Cognitive Power', agp.dosage = '300-600mg'
        MERGE (coq:Supplement {name: 'CoQ10'}) ON CREATE SET coq.effect = 'Mitochondrial Health, Antioxidant', coq.dosage = '100-200mg'
        
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
        MERGE (ch:Goal {name: 'Cognitive Health'})
        MERGE (lo:Goal {name: 'Longevity'})
        MERGE (mb:Goal {name: 'Mobility'})
        
        // Biological Effects
        MERGE (cm:BiologicalEffect {name: 'Cortisol Management'})
        MERGE (mps:BiologicalEffect {name: 'Muscle Protein Synthesis'})
        MERGE (vas:BiologicalEffect {name: 'Vasodilation'})
        MERGE (inf:BiologicalEffect {name: 'Inflammation Reduction'})
        MERGE (atp:BiologicalEffect {name: 'ATP Production'})
        MERGE (neu:BiologicalEffect {name: 'Neuroprotection'})
        MERGE (ampk:BiologicalEffect {name: 'AMPK Activation'})
        MERGE (bsr:BiologicalEffect {name: 'Blood Sugar Regulation'})
        
        // Side Effects
        MERGE (wr:SideEffect {name: 'Water Retention'})
        MERGE (gi:SideEffect {name: 'Gastrointestinal Distress'})
        MERGE (ins:SideEffect {name: 'Insomnia'})
        MERGE (jit:SideEffect {name: 'Jitters'})
        MERGE (tin:SideEffect {name: 'Paraesthesia (Tingling)'})
        MERGE (cra:SideEffect {name: 'Muscle Cramps'})
        MERGE (wg:SideEffect {name: 'Weight Gain (Water)'})
        
        // Precautions
        MERGE (p_caf:Precaution {name: 'Avoid late in the day to prevent sleep disruption'})
        MERGE (p_cr:Precaution {name: 'Ensure adequate hydration'})
        MERGE (p_ber:Precaution {name: 'Consult doctor if on blood sugar medication'})
        
        // Food Sources
        MERGE (milk:FoodSource {name: 'Dairy/Milk'})
        MERGE (eggs:FoodSource {name: 'Eggs'})
        MERGE (fish:FoodSource {name: 'Fatty Fish'})
        MERGE (meat:FoodSource {name: 'Red Meat'})
        MERGE (tur:FoodSource {name: 'Turmeric Root'})
        
        // Conditions
        MERGE (hyp:Condition {name: 'Hypertension'})
        MERGE (diab:Condition {name: 'Diabetes'})
        
        // Relationships: SUPPORTS
        MERGE (w)-[:SUPPORTS {weight: 0.9}]->(h)
        MERGE (w)-[:SUPPORTS {weight: 0.8}]->(rec)
        MERGE (c)-[:SUPPORTS {weight: 1.0}]->(s)
        MERGE (c)-[:SUPPORTS {weight: 0.8}]->(h)
        MERGE (c)-[:SUPPORTS {weight: 0.7}]->(ch)
        MERGE (b)-[:SUPPORTS {weight: 0.9}]->(e)
        MERGE (a)-[:SUPPORTS {weight: 0.95}]->(sr)
        MERGE (a)-[:SUPPORTS {weight: 0.8}]->(rec)
        MERGE (caf)-[:SUPPORTS {weight: 1.0}]->(fe)
        MERGE (caf)-[:SUPPORTS {weight: 0.7}]->(e)
        MERGE (the)-[:SUPPORTS {weight: 0.9}]->(fe)
        MERGE (the)-[:SUPPORTS {weight: 0.8}]->(sr)
        MERGE (cit)-[:SUPPORTS {weight: 0.9}]->(e)
        MERGE (cit)-[:SUPPORTS {weight: 0.8}]->(h)
        MERGE (fo)-[:SUPPORTS {weight: 0.9}]->(jh)
        MERGE (fo)-[:SUPPORTS {weight: 0.8}]->(ch)
        MERGE (vd)-[:SUPPORTS {weight: 0.9}]->(rec)
        MERGE (mg)-[:SUPPORTS {weight: 0.9}]->(sq)
        MERGE (mg)-[:SUPPORTS {weight: 0.8}]->(rec)
        MERGE (zn)-[:SUPPORTS {weight: 0.8}]->(rec)
        MERGE (mel)-[:SUPPORTS {weight: 1.0}]->(sq)
        MERGE (rho)-[:SUPPORTS {weight: 0.9}]->(fe)
        MERGE (rho)-[:SUPPORTS {weight: 0.8}]->(e)
        MERGE (ber)-[:SUPPORTS {weight: 0.9}]->(fl)
        MERGE (ber)-[:SUPPORTS {weight: 0.8}]->(lo)
        MERGE (cur)-[:SUPPORTS {weight: 1.0}]->(jh)
        MERGE (cur)-[:SUPPORTS {weight: 0.9}]->(rec)
        MERGE (agp)-[:SUPPORTS {weight: 1.0}]->(ch)
        MERGE (coq)-[:SUPPORTS {weight: 0.9}]->(lo)
        
        // Relationships: AFFECTS (Biological)
        MERGE (w)-[:AFFECTS {weight: 1.0}]->(mps)
        MERGE (c)-[:AFFECTS {weight: 1.0}]->(atp)
        MERGE (a)-[:AFFECTS {weight: 1.0}]->(cm)
        MERGE (cit)-[:AFFECTS {weight: 0.9}]->(vas)
        MERGE (fo)-[:AFFECTS {weight: 0.9}]->(inf)
        MERGE (fo)-[:AFFECTS {weight: 0.8}]->(neu)
        MERGE (ber)-[:AFFECTS {weight: 1.0}]->(ampk)
        MERGE (ber)-[:AFFECTS {weight: 1.0}]->(bsr)
        
        // Relationships: CAUSES (Side Effects)
        MERGE (c)-[:CAUSES]->(wr)
        MERGE (c)-[:CAUSES]->(gi)
        MERGE (c)-[:CAUSES]->(cra)
        MERGE (c)-[:CAUSES]->(wg)
        MERGE (b)-[:CAUSES]->(tin)
        MERGE (caf)-[:CAUSES]->(ins)
        MERGE (caf)-[:CAUSES]->(jit)
        
        // Relationships: HAS_PRECAUTION
        MERGE (caf)-[:HAS_PRECAUTION]->(p_caf)
        MERGE (c)-[:HAS_PRECAUTION]->(p_cr)
        MERGE (ber)-[:HAS_PRECAUTION]->(p_ber)
        
        // Relationships: SYNERGY_WITH
        MERGE (caf)-[:SYNERGY_WITH]->(the)
        MERGE (vd)-[:SYNERGY_WITH]->(vk)
        MERGE (zn)-[:SYNERGY_WITH]->(mg)
        MERGE (cur)-[:SYNERGY_WITH]->(pip)
        
        // Relationships: FOUND_IN
        MERGE (w)-[:FOUND_IN]->(milk)
        MERGE (fo)-[:FOUND_IN]->(fish)
        MERGE (c)-[:FOUND_IN]->(meat)
        MERGE (cur)-[:FOUND_IN]->(tur)
        
        // Relationships: CONTRAINDICATED_FOR
        MERGE (caf)-[:CONTRAINDICATED_FOR]->(hyp)
        MERGE (ber)-[:CONTRAINDICATED_FOR]->(diab)
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
        RETURN s.name as supplement, r.weight as strength, s.effect as effect, s.dosage as dosage
        ORDER BY strength DESC
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, goal=goal)
                recs = [{"supplement": record["supplement"], "strength": record["strength"], "effect": record["effect"], "dosage": record["dosage"]} for record in result]
                if not recs:
                    return f"Goal '{goal}' not found or has no recommendations."
                return recs
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return f"Error querying database."

    def query_side_effects(self, supplement_name: str):
        """Find side effects and precautions for a supplement."""
        if not self.driver:
            return "Neo4j not connected."
            
        query = """
        MATCH (s:Supplement {name: $supplement_name})
        OPTIONAL MATCH (s)-[:CAUSES]->(se:SideEffect)
        OPTIONAL MATCH (s)-[:HAS_PRECAUTION]->(p:Precaution)
        RETURN s.name as name, collect(distinct se.name) as side_effects, collect(distinct p.name) as precautions
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, supplement_name=supplement_name)
                record = result.single()
                if not record or not record["name"]:
                    return f"Supplement '{supplement_name}' not found."
                return {
                    "supplement": record["name"],
                    "side_effects": record["side_effects"],
                    "precautions": record["precautions"]
                }
        except Exception as e:
            logger.error(f"Error querying side effects: {e}")
            return f"Error querying database."

    def find_synergies(self, supplement_name: str):
        """Find supplements that work well with the given supplement."""
        if not self.driver:
            return "Neo4j not connected."
            
        query = """
        MATCH (s:Supplement {name: $supplement_name})-[:SYNERGY_WITH]-(other:Supplement)
        RETURN other.name as synergy, other.effect as effect
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, supplement_name=supplement_name)
                synergies = [{"supplement": record["synergy"], "effect": record["effect"]} for record in result]
                return synergies
        except Exception as e:
            logger.error(f"Error finding synergies: {e}")
            return f"Error querying database."

    def find_food_sources(self, supplement_name: str):
        """Find whole food sources for a supplement."""
        if not self.driver:
            return "Neo4j not connected."
            
        query = """
        MATCH (s:Supplement {name: $supplement_name})-[:FOUND_IN]->(f:FoodSource)
        RETURN f.name as food_source
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, supplement_name=supplement_name)
                sources = [record["food_source"] for record in result]
                return sources
        except Exception as e:
            logger.error(f"Error finding food sources: {e}")
            return f"Error querying database."

    def check_contraindications(self, condition: str):
        """Find supplements that are contraindicated for a specific condition."""
        if not self.driver:
            return "Neo4j not connected."
            
        query = """
        MATCH (s:Supplement)-[:CONTRAINDICATED_FOR]->(c:Condition {name: $condition})
        RETURN s.name as supplement, s.effect as effect
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, condition=condition)
                contras = [{"supplement": record["supplement"], "effect": record["effect"]} for record in result]
                return contras
        except Exception as e:
            logger.error(f"Error checking contraindications: {e}")
            return f"Error querying database."
