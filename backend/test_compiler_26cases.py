import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from compiler_engine import CompilerEngine
from fact_store import FactLog
from models import Gender

def create_person(name: str, gender: str) -> FactLog:
    # 使用名字直接作为ID，简化测试
    return FactLog("test", "ADD_NODE", {"id": name, "name": name, "gender": gender})

def create_edge(a: str, b: str, rel_type: str) -> FactLog:
    return FactLog("test", "ADD_EDGE", {"person_a": a, "person_b": b, "type": rel_type})

def generate_facts():
    facts = []
    # 提取人物实体
    people = [
        ("林大明", "male"), ("赵春花", "female"), ("林绿洲", "male"), ("林青海", "male"),
        ("陈桂芳", "female"), ("林小月", "female"), ("林建国", "male"), ("李玉兰", "female"),
        ("朱雪兰", "female"), ("朱世杰", "male"), ("王大锤", "male"), ("孙美玲", "female"),
        ("王小明", "male"), ("王二锤", "male"), ("周小燕", "female"), ("王芳", "female"),
        ("王磊", "male"), ("王富贵", "male"), ("刘翠花", "female"), ("林王联合", "male"),
        ("王林小雨", "female"), ("刘慧兰", "female"), ("林新生", "male"), ("吴丽丽", "female"),
        ("王甜甜", "female"), ("朱世豪", "male"), ("朱小勇", "male")
    ]
    for name, gender in people:
        facts.append(create_person(name, gender))

    # 1. 林大明和妻子赵春花住在杭州
    facts.append(create_edge("林大明", "赵春花", "spouse"))
    # 2. 他们有两个儿子，大的叫林绿洲，小的叫林青海
    facts.append(create_edge("林大明", "林绿洲", "parent_child"))
    facts.append(create_edge("赵春花", "林绿洲", "parent_child"))
    facts.append(create_edge("林大明", "林青海", "parent_child"))
    facts.append(create_edge("赵春花", "林青海", "parent_child"))
    # 3. 林绿洲的爸爸是林大明 (重复添加测试去重)
    facts.append(create_edge("林大明", "林绿洲", "parent_child"))
    # 4. 林大明和前妻陈桂芳还生了一个女儿叫林小月
    facts.append(create_edge("林大明", "陈桂芳", "spouse"))
    facts.append(create_edge("林大明", "林小月", "parent_child"))
    facts.append(create_edge("陈桂芳", "林小月", "parent_child"))
    # 5. 林绿洲的爷爷叫林建国 -> dict 中为 grandfather_paternal
    facts.append(create_edge("林建国", "林绿洲", "grandfather_paternal"))
    # 6. 林建国的妻子叫李玉兰
    facts.append(create_edge("林建国", "李玉兰", "spouse"))
    # 7. 林绿洲的外婆叫朱雪兰 -> dict 中为 grandmother_maternal
    facts.append(create_edge("朱雪兰", "林绿洲", "grandmother_maternal"))
    # 8. 朱雪兰的丈夫叫朱世杰
    facts.append(create_edge("朱世杰", "朱雪兰", "spouse"))
    # 9. 王大锤和妻子孙美玲有一个儿子叫王小明
    facts.append(create_edge("王大锤", "孙美玲", "spouse"))
    facts.append(create_edge("王大锤", "王小明", "parent_child"))
    facts.append(create_edge("孙美玲", "王小明", "parent_child"))
    # 10. 王大锤还有个弟弟叫王二锤 -> dict 中为 brother
    facts.append(create_edge("王大锤", "王二锤", "brother"))
    # 11. 王二锤的妻子叫周小燕
    facts.append(create_edge("王二锤", "周小燕", "spouse"))
    # 12. 王二锤和周小燕有两个孩子，姐姐叫王芳，弟弟叫王磊
    facts.append(create_edge("王二锤", "王芳", "parent_child"))
    facts.append(create_edge("周小燕", "王芳", "parent_child"))
    facts.append(create_edge("王二锤", "王磊", "parent_child"))
    facts.append(create_edge("周小燕", "王磊", "parent_child"))
    # 13. 王芳的爷爷叫王富贵
    facts.append(create_edge("王富贵", "王芳", "grandfather_paternal"))
    # 14. 王富贵的妻子叫刘翠花
    facts.append(create_edge("王富贵", "刘翠花", "spouse"))
    # 15. 林绿洲娶了王芳
    facts.append(create_edge("林绿洲", "王芳", "spouse"))
    # 16. 林绿洲和王芳有一个儿子叫林王联合
    facts.append(create_edge("林绿洲", "林王联合", "parent_child"))
    facts.append(create_edge("王芳", "林王联合", "parent_child"))
    # 17. 林小月嫁给了王小明
    facts.append(create_edge("王小明", "林小月", "spouse"))
    # 18. 林小月和王小明生了个女儿叫王林小雨
    facts.append(create_edge("王小明", "王林小雨", "parent_child"))
    facts.append(create_edge("林小月", "王林小雨", "parent_child"))
    # 19. 赵春花去世后，林大明又娶了刘慧兰
    facts.append(create_edge("林大明", "刘慧兰", "spouse"))
    # 20. 林大明和刘慧兰生了个儿子叫林新生
    facts.append(create_edge("林大明", "林新生", "parent_child"))
    facts.append(create_edge("刘慧兰", "林新生", "parent_child"))
    # 21. 王二锤和周小燕离婚了，又娶了吴丽丽
    facts.append(create_edge("王二锤", "吴丽丽", "spouse"))
    # 22. 王二锤和吴丽丽生了个女儿叫王甜甜
    facts.append(create_edge("王二锤", "王甜甜", "parent_child"))
    facts.append(create_edge("吴丽丽", "王甜甜", "parent_child"))
    # 23. 朱世杰的哥哥叫朱世豪，他是赵春花的舅舅
    facts.append(create_edge("朱世豪", "朱世杰", "brother"))
    facts.append(create_edge("朱世豪", "赵春花", "uncle_maternal"))
    # 24. 朱世豪有个儿子叫朱小勇
    facts.append(create_edge("朱世豪", "朱小勇", "parent_child"))
    # 25. 林绿洲的妈妈叫赵春花
    facts.append(create_edge("赵春花", "林绿洲", "parent_child"))
    # 26. 王芳的爸爸叫王二锤
    facts.append(create_edge("王二锤", "王芳", "parent_child"))

    return facts

def print_graph(graph):
    print(f"Total people: {len(graph.people)}")
    for pid, p in graph.people.items():
        if p.is_placeholder:
            print(f"[Placeholder] {p.name}")
        else:
            print(f"{p.name} ({p.gender.value})")
            
    print(f"\nTotal relations: {len(graph.relationships)}")
    for rid, r in graph.relationships.items():
        p1 = graph.get_person(r.person1_id).name
        p2 = graph.get_person(r.person2_id).name
        print(f"{p1} --[{r.type.value}]--> {p2}")

def test():
    facts = generate_facts()
    engine = CompilerEngine()
    try:
        graph = engine.compile(facts)
        print_graph(graph)
        graph.export_json("test_compiled_graph.json")
        print("\nGraph compiled and saved to test_compiled_graph.json")
    except Exception as e:
        print(f"Compilation failed: {e}")

if __name__ == "__main__":
    test()
