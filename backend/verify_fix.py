
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.main import chat_extract, ChatExtractRequest, create_family, chat_commit, ChatCommitRequest, list_families, export_data
from backend.fact_store import load_facts

async def verify():
    # 1. Create Family
    res = await create_family("Verify Family")
    family_id = res.data["family_id"]
    print(f"Created family: {family_id}")
    
    # 2. List Families
    res = await list_families()
    found = False
    for fam in res.data:
        if fam["family_id"] == family_id:
            found = True
            break
    print(f"List families found created family: {found}")
    
    # 3. Chat Extract
    extract_req = ChatExtractRequest(text="林大明是赵春花的丈夫", family_id=family_id)
    res = await chat_extract(extract_req)
    parsed = res.data["parsed_data"]
    print(f"Extracted entities: {len(parsed['entities'])}")
    
    # 4. Chat Commit
    commit_req = ChatCommitRequest(
        family_id=family_id,
        confirmed_entities=parsed["entities"],
        confirmed_relationships=parsed["relationships"],
        confirmed_events=parsed["events"]
    )
    
    # Simulate confirmation where action="CREATE"
    for ent in commit_req.confirmed_entities:
        ent["action"] = "CREATE"
        ent["gender"] = "M" if ent["gender"] == "male" else "F" if ent["gender"] == "female" else "UNKNOWN"
        
    res = await chat_commit(commit_req)
    print(f"Commit success: {res.success}")
    
    # 5. Export Data (Verify graph)
    res = await export_data(family_id)
    graph = res.data
    print(f"Graph has {len(graph['people'])} people and {len(graph['relationships'])} relationships")
    for p in graph['people']:
        print(f"  - {p['name']} ({p['id']})")
    for r in graph['relationships']:
        print(f"  - {r['person1_id']} -> {r['person2_id']} ({r['type']})")

if __name__ == "__main__":
    asyncio.run(verify())
