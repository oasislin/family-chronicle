"""
处理全部 502 条测试用例
用内置 NLP 引擎解析每条输入，更新知识图谱，输出完整日志
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ai_engine import KnowledgeGraphEngine


def main():
    # 加载测试用例
    with open('test_cases.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    base_people = data['base_people']
    base_relationships = data.get('base_relationships', [])
    test_cases = data['test_cases']

    print(f"基础人物: {len(base_people)}")
    print(f"基础关系: {len(base_relationships)}")
    print(f"测试用例: {len(test_cases)}")
    print("=" * 60)

    # 初始化引擎
    engine = KnowledgeGraphEngine()
    engine.init_base_data(base_people, base_relationships)

    # 逐条处理
    stats = {
        'total': len(test_cases),
        'noise_skipped': 0,
        'persons_created': 0,
        'persons_updated': 0,
        'events_added': 0,
        'relationships_added': 0,
        'no_action': 0,
        'errors': 0,
    }

    detailed_log = []

    for i, case in enumerate(test_cases):
        case_id = case['id']
        text = case['input']
        category = case.get('category', '?')

        try:
            result = engine.process_input(text, case_id)

            # 统计
            for action in result['actions']:
                if action['type'] == 'SKIP':
                    stats['noise_skipped'] += 1
                elif action['type'] == 'CREATE_PERSON':
                    stats['persons_created'] += 1
                elif action['type'] == 'UPDATE_PERSON':
                    stats['persons_updated'] += 1
                elif action['type'] == 'ADD_EVENT':
                    stats['events_added'] += 1
                elif action['type'] == 'ADD_RELATIONSHIP':
                    stats['relationships_added'] += 1
                elif action['type'] == 'NO_ACTION':
                    stats['no_action'] += 1

            detailed_log.append({
                'id': case_id,
                'category': category,
                'input': text,
                'actions': result['actions'],
                'is_noise': result['is_noise'],
            })

        except Exception as e:
            stats['errors'] += 1
            detailed_log.append({
                'id': case_id,
                'category': category,
                'input': text,
                'actions': [{'type': 'ERROR', 'error': str(e)}],
                'is_noise': False,
            })

        # 进度
        if (i + 1) % 50 == 0:
            print(f"  已处理 {i+1}/{len(test_cases)} ...")

    print("=" * 60)
    print(f"处理完成!")
    print(f"  总用例:     {stats['total']}")
    print(f"  噪声跳过:   {stats['noise_skipped']}")
    print(f"  创建人物:   {stats['persons_created']}")
    print(f"  更新人物:   {stats['persons_updated']}")
    print(f"  添加事件:   {stats['events_added']}")
    print(f"  添加关系:   {stats['relationships_added']}")
    print(f"  无操作:     {stats['no_action']}")
    print(f"  错误:       {stats['errors']}")

    # 保存知识图谱数据
    state = engine.get_state()
    os.makedirs('data', exist_ok=True)

    with open('data/persons.json', 'w', encoding='utf-8') as f:
        json.dump(state['persons'], f, ensure_ascii=False, indent=2)
    print(f"\n已保存 {len(state['persons'])} 个人物 -> data/persons.json")

    with open('data/relationships.json', 'w', encoding='utf-8') as f:
        json.dump(state['relationships'], f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(state['relationships'])} 条关系 -> data/relationships.json")

    with open('data/events.json', 'w', encoding='utf-8') as f:
        json.dump(state['events'], f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(state['events'])} 条事件 -> data/events.json")

    # 保存详细日志
    with open('test_run_log.json', 'w', encoding='utf-8') as f:
        json.dump({
            'stats': stats,
            'cases': detailed_log,
            'final_state': state,
        }, f, ensure_ascii=False, indent=2)
    print(f"已保存处理日志 -> test_run_log.json")

    # 输出每个人物的最终信息
    print("\n" + "=" * 60)
    print("最终知识图谱 - 人物列表:")
    print("=" * 60)
    for p in state['persons']:
        tags_str = ', '.join(p['tags']) if p['tags'] else '-'
        bio_count = len(p.get('biography', []))
        print(f"  [{p['id']}] {p['name']} | {p['gender']} | 生:{p['birth_date'] or '?'} | 卒:{p['death_date'] or '-'} | 标签:{tags_str} | 生平:{bio_count}条")


if __name__ == '__main__':
    main()
