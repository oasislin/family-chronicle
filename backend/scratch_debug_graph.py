
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from backend.main import load_family_graph
from backend.fact_store import load_facts
from backend.compiler_engine import CompilerEngine

family_id = ""
facts = load_facts(family_id)
print(f"Loaded {len(facts)} facts for family '{family_id}'")

engine = CompilerEngine()
graph = engine.compile(facts)

print(f"Graph has {len(graph.people)} people")
for pid, p in graph.people.items():
    print(f"  - {p.name} (ID: {pid})")

print(f"Graph has {len(graph.relationships)} relationships")
for rid, r in graph.relationships.items():
    print(f"  - {r.person1_id} -> {r.person2_id} ({r.type})")
