import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from compiler_engine import CompilerEngine
from fact_store import load_facts

def debug_compile(family_id):
    print(f"Debugging compilation for family: '{family_id}'")
    facts = load_facts(family_id)
    print(f"Loaded {len(facts)} facts.")
    
    compiler = CompilerEngine()
    try:
        compiler.compile(facts)
        print("Compilation successful!")
    except Exception as e:
        print(f"Compilation failed: {e}")
        
    print("\nGraph State:")
    print(f"People: {len(compiler.graph.people)}")
    for p in compiler.graph.people.values():
        print(f"  - {p.name} ({p.id}) gender={p.gender.value} placeholder={p.is_placeholder}")
        
    print("\nRelationships:")
    for r in compiler.graph.relationships.values():
        p1 = compiler.graph.get_person(r.person1_id)
        p2 = compiler.graph.get_person(r.person2_id)
        print(f"  - {p1.name if p1 else r.person1_id} --[{r.type.value}]--> {p2.name if p2 else r.person2_id}")

    print("\nParents Index:")
    for cid, pids in compiler.parents_of.items():
        child = compiler.graph.get_person(cid)
        parents = [compiler.graph.get_person(pid).name for pid in pids if compiler.graph.get_person(pid)]
        print(f"  - {child.name if child else cid}: {', '.join(parents)}")

if __name__ == "__main__":
    # Test both empty ID and the one I saw in logs
    debug_compile("")
    print("\n" + "="*50 + "\n")
    debug_compile("family_20260418_175214")
