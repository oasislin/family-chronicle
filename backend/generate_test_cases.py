"""
家族编年史 - 测试用例生成器
覆盖所有可能对图谱产生变化的场景，含干扰项。
"""

import json
import uuid

# ============================================================
# 基础人物（预置数据库状态）
# ============================================================
BASE_PEOPLE = [
    {"id": "p1", "name": "王大强", "gender": "male", "birth_date": "1950", "tags": ["长辈"]},
    {"id": "p2", "name": "王建国", "gender": "male", "birth_date": "1980", "tags": ["老大"]},
    {"id": "p3", "name": "李梅", "gender": "female", "birth_date": "1982", "tags": ["隔壁村"]},
    {"id": "p4", "name": "赵大爷", "gender": "male", "birth_date": "1945", "tags": ["村长"]},
    {"id": "p5", "name": "李菊花", "gender": "female", "birth_date": None, "tags": ["李梅之妹"]},
]

BASE_RELATIONSHIPS = [
    {"id": "r1", "person1_id": "p1", "person2_id": "p2", "type": "parent_child"},
    {"id": "r2", "person1_id": "p2", "person2_id": "p3", "type": "spouse"},
    {"id": "r3", "person1_id": "p2", "person2_id": "p4", "type": "godparent_godchild"},
]

# ============================================================
# 测试用例定义
# ============================================================

# 预期操作类型
ACTIONS = {
    "CREATE_PERSON": "新建人物",
    "UPDATE_PERSON": "更新人物信息",
    "MATCH_PERSON": "关联已有人员",
    "CREATE_RELATIONSHIP": "新建关系",
    "SKIP_RELATIONSHIP": "跳过重复关系",
    "CREATE_EVENT": "新建事件",
    "UPDATE_STORY": "更新生平故事",
    "ASK_QUESTION": "需用户确认",
    "NO_ACTION": "无有效信息，不操作",
}

test_cases = []
tid = 0

def add(category, subcategory, input_text, expected_actions, notes=""):
    global tid
    tid += 1
    test_cases.append({
        "id": f"T{tid:03d}",
        "category": category,
        "subcategory": subcategory,
        "input": input_text,
        "expected_actions": expected_actions,
        "notes": notes,
    })

# ============================================================
# 1. 新增人物 (CREATE_PERSON)
# ============================================================

# 1.1 简单新增
add("新增人物", "简单新增",
    "我有个表弟叫周小明，2000年出生的",
    [{"action": "CREATE_PERSON", "name": "周小明", "gender": "male", "birth_year": "2000"}],
    "全新人物，无歧义")

add("新增人物", "简单新增",
    "爷爷的哥哥叫王大壮，已经去世了",
    [{"action": "CREATE_PERSON", "name": "王大壮", "gender": "male", "tags": ["爷爷的哥哥"]}])

add("新增人物", "带详细信息",
    "我姑姑叫刘秀英，1955年出生在刘家村，现在住在县城",
    [{"action": "CREATE_PERSON", "name": "刘秀英", "gender": "female", "birth_year": "1955",
      "birth_place": "刘家村", "current_residence": "县城"}])

add("新增人物", "批量新增",
    "我有三个舅舅，大的叫李国强，二的叫李国富，小的叫李国民",
    [{"action": "CREATE_PERSON", "name": "李国强"},
     {"action": "CREATE_PERSON", "name": "李国富"},
     {"action": "CREATE_PERSON", "name": "李国民"}])

add("新增人物", "只知名字",
    "还有一个人叫张伟",
    [{"action": "CREATE_PERSON", "name": "张伟"}],
    "信息最少的情况")

add("新增人物", "带性别暗示",
    "王建国有个妹妹叫王建红",
    [{"action": "CREATE_PERSON", "name": "王建红", "gender": "female"}],
    "从「妹妹」推断性别")

add("新增人物", "带性别暗示",
    "李梅她姐夫叫陈大牛",
    [{"action": "CREATE_PERSON", "name": "陈大牛", "gender": "male"}],
    "从「姐夫」推断性别")

# 1.2 名字含数字排行
add("新增人物", "排行命名",
    "大伯的三儿子叫建国华",
    [{"action": "CREATE_PERSON", "name": "建国华"}])

# ============================================================
# 2. 关联已有人员 (MATCH_PERSON)
# ============================================================

add("关联人员", "精确匹配",
    "王建国今年45岁了",
    [{"action": "MATCH_PERSON", "name": "王建国"},
     {"action": "UPDATE_PERSON", "name": "王建国", "field": "story", "contains": "45岁"}],
    "精确匹配到已有王建国，附加信息更新story")

add("关联人员", "精确匹配",
    "李梅是隔壁村嫁过来的",
    [{"action": "MATCH_PERSON", "name": "李梅"}],
    "精确匹配，无新信息")

add("关联人员", "昵称→全名",
    "赵大爷的大名叫赵大雷",
    [{"action": "UPDATE_PERSON", "name": "赵大爷", "field": "name", "new_value": "赵大雷"}],
    "昵称升级为全名")

add("关联人员", "包含匹配",
    "王大强老爷子身体还很硬朗",
    [{"action": "MATCH_PERSON", "name": "王大强"},
     {"action": "UPDATE_PERSON", "name": "王大强", "field": "story"}],
    "「王大强」精确匹配，附加信息入story")

# ============================================================
# 3. 更新人物信息 (UPDATE_PERSON)
# ============================================================

# 3.1 出生日期
add("更新信息", "补充出生日期",
    "李菊花是1985年生的",
    [{"action": "UPDATE_PERSON", "name": "李菊花", "field": "birth_date", "new_value": "1985"}])

add("更新信息", "补充出生日期",
    "李刚出生于1987年",
    [{"action": "UPDATE_PERSON", "name": "李刚", "field": "birth_date", "new_value": "1987"}])

# 3.2 出生地
add("更新信息", "补充出生地",
    "李梅是在李家村出生的",
    [{"action": "UPDATE_PERSON", "name": "李梅", "field": "birth_place", "new_value": "李家村"}])

# 3.3 现居地
add("更新信息", "补充现居地",
    "王建国现在住在省城",
    [{"action": "UPDATE_PERSON", "name": "王建国", "field": "current_residence", "new_value": "省城"}])

# 3.4 标签
add("更新信息", "补充标签",
    "王大强以前是生产队长",
    [{"action": "UPDATE_PERSON", "name": "王大强", "field": "tags", "add": "生产队长"}])

# ============================================================
# 4. 生平故事 (UPDATE_STORY)
# ============================================================

add("生平故事", "描述性信息",
    "王建国年轻的时候长得一表人才，读书成绩一直是班上前几名",
    [{"action": "UPDATE_STORY", "name": "王建国", "contains": "一表人才"}],
    "非关系非事件的描述性信息→story")

add("生平故事", "性格描述",
    "赵大爷是村里出了名的热心肠，谁家有事都帮忙",
    [{"action": "UPDATE_STORY", "name": "赵大爷", "contains": "热心肠"}])

add("生平故事", "职业经历",
    "王建国高中毕业后学了木匠手艺，后来在县城开了家具店",
    [{"action": "UPDATE_STORY", "name": "王建国", "contains": "木匠"}])

add("生平故事", "兴趣爱好",
    "李梅从小就喜欢唱歌，是村里文艺队的骨干",
    [{"action": "UPDATE_STORY", "name": "李梅", "contains": "唱歌"}])

add("生平故事", "多段叙事",
    "王大强年轻时当过兵，后来回村务农。他为人正直，村里人都很尊敬他",
    [{"action": "UPDATE_STORY", "name": "王大强", "contains": "当过兵"}])

# ============================================================
# 5. 新建关系 (CREATE_RELATIONSHIP)
# ============================================================

add("新建关系", "亲子关系",
    "王大强还有个大儿子叫王建军",
    [{"action": "CREATE_PERSON", "name": "王建军"},
     {"action": "CREATE_RELATIONSHIP", "type": "parent_child", "from": "王大强", "to": "王建军"}])

add("新建关系", "配偶关系",
    "王大强的老婆叫孙桂芳",
    [{"action": "CREATE_PERSON", "name": "孙桂芳", "gender": "female"},
     {"action": "CREATE_RELATIONSHIP", "type": "spouse", "between": ["王大强", "孙桂芳"]}])

add("新建关系", "兄弟姐妹",
    "李菊花是李梅的妹妹",
    [{"action": "CREATE_RELATIONSHIP", "type": "sibling", "between": ["李菊花", "李梅"]}],
    "两人都已存在")

add("新建关系", "干亲关系",
    "建国认了赵大爷做干爹",
    [{"action": "CREATE_RELATIONSHIP", "type": "godparent_godchild", "between": ["王建国", "赵大爷"]}])

add("新建关系", "祖孙关系",
    "王大强的父亲叫王老太爷",
    [{"action": "CREATE_PERSON", "name": "王老太爷"},
     {"action": "CREATE_RELATIONSHIP", "type": "parent_child", "from": "王老太爷", "to": "王大强"}])

add("新建关系", "姻亲",
    "李梅的弟弟叫李强",
    [{"action": "CREATE_PERSON", "name": "李强"},
     {"action": "CREATE_RELATIONSHIP", "type": "sibling", "between": ["李梅", "李强"]}])

# ============================================================
# 6. 重复关系（应跳过）
# ============================================================

add("重复关系", "完全重复",
    "王建国是王大强的儿子",
    [{"action": "SKIP_RELATIONSHIP", "reason": "已存在亲子关系"}],
    "已有 r1: p1→p2 parent_child")

add("重复关系", "反向表述",
    "王大强是王建国的父亲",
    [{"action": "SKIP_RELATIONSHIP", "reason": "已存在亲子关系"}],
    "方向反了但本质相同")

add("重复关系", "配偶重复",
    "王建国和李梅是两口子",
    [{"action": "SKIP_RELATIONSHIP", "reason": "已存在配偶关系"}],
    "已有 r2: p2↔p3 spouse")

# ============================================================
# 7. 事件 (CREATE_EVENT)
# ============================================================

add("事件", "出生事件",
    "小明是2000年5月出生在县医院的",
    [{"action": "CREATE_PERSON", "name": "小明"},
     {"action": "CREATE_EVENT", "type": "birth", "date": "2000"}])

add("事件", "结婚事件",
    "建国和李梅是1995年9月15号结的婚，在县城办的酒席",
    [{"action": "CREATE_EVENT", "type": "marriage", "date": "1995-09-15", "location": "县城"}])

add("事件", "去世事件",
    "王老太爷是2010年走的",
    [{"action": "CREATE_PERSON", "name": "王老太爷"},
     {"action": "CREATE_EVENT", "type": "death", "date": "2010"}])

add("事件", "搬家事件",
    "2005年王建国一家从王家村搬到了县城",
    [{"action": "CREATE_EVENT", "type": "relocation", "date": "2005"}])

add("事件", "生病事件",
    "2020年李梅生了一场大病",
    [{"action": "CREATE_EVENT", "type": "illness", "date": "2020"}])

add("事件", "认干亲事件",
    "1996年建国认赵大爷做干爹，在赵家村办的",
    [{"action": "CREATE_EVENT", "type": "recognition", "date": "1996", "location": "赵家村"}])

# ============================================================
# 8. 冲突信息 (ASK_QUESTION 或自动处理)
# ============================================================

add("冲突信息", "出生日期冲突",
    "王建国其实是1979年出生的，不是1980年",
    [{"action": "ASK_QUESTION", "type": "date_conflict",
      "message_contains": "1980"}],
    "数据库记1980，新信息1979")

add("冲突信息", "出生地冲突",
    "李梅是李家村人，不是隔壁村的",
    [{"action": "UPDATE_PERSON", "name": "李梅", "field": "birth_place", "new_value": "李家村"}],
    "标签是「隔壁村」，不冲突（标签≠出生地）")

add("冲突信息", "关系冲突",
    "赵大爷其实是王建国的舅舅",
    [{"action": "ASK_QUESTION", "type": "relationship_conflict"}],
    "现有干亲关系，新说舅舅")

# ============================================================
# 9. 指代不明 (ASK_QUESTION)
# ============================================================

add("指代不明", "代词",
    "他小时候很调皮，经常去河里摸鱼",
    [{"action": "NO_ACTION"}],
    "无主语，无法关联")

add("指代不明", "模糊称呼",
    "大伯的老二叫建国",
    [{"action": "ASK_QUESTION", "type": "person_match", "message_contains": "大伯"}],
    "「大伯」可能指王大强，需确认")

add("指代不明", "同名问题",
    "村里还有个建国，是赵大爷的侄子",
    [{"action": "CREATE_PERSON", "name": "建国", "tags": ["赵大爷侄子"]}],
    "新建另一个「建国」，AI应给出区别性信息")

# ============================================================
# 10. 废话/干扰项 (NO_ACTION)
# ============================================================

add("干扰项", "无关内容",
    "今天天气真好啊",
    [{"action": "NO_ACTION"}])

add("干扰项", "无关内容",
    "晚饭吃的是饺子",
    [{"action": "NO_ACTION"}])

add("干扰项", "无关内容",
    "明天要去镇上赶集",
    [{"action": "NO_ACTION"}])

add("干扰项", "半相关",
    "我们村有几百年的历史了",
    [{"action": "NO_ACTION"}],
    "提到村但不涉及具体人物")

add("干扰项", "半相关",
    "老王家在村里住了好几代",
    [{"action": "NO_ACTION"}],
    "提到老王家但无具体人名")

add("干扰项", "混合",
    "今天天气不错，对了，王建国的儿子叫王小明，今年上小学了",
    [{"action": "CREATE_PERSON", "name": "王小明"},
     {"action": "CREATE_RELATIONSHIP", "type": "parent_child", "from": "王建国", "to": "王小明"}],
    "废话+有效信息混合")

# ============================================================
# 11. 复杂场景
# ============================================================

add("复杂场景", "一段话多人多关系",
    "我爷爷叫王老根，奶奶叫刘桂花。爷爷有三个儿子，老大王大强是我大伯，老二王大志是我爸，老三王小军是我叔",
    [{"action": "CREATE_PERSON", "name": "王老根"},
     {"action": "CREATE_PERSON", "name": "刘桂花"},
     {"action": "CREATE_PERSON", "name": "王大志"},
     {"action": "CREATE_PERSON", "name": "王小军"},
     {"action": "MATCH_PERSON", "name": "王大强"},
     {"action": "CREATE_RELATIONSHIP", "count": ">=5"}],
    "一段话产生多个人物和多条关系")

add("复杂场景", "婚姻+生子",
    "建国和李梅结婚后第二年生了个女儿叫小芳",
    [{"action": "CREATE_PERSON", "name": "小芳", "gender": "female"},
     {"action": "CREATE_RELATIONSHIP", "type": "parent_child", "from": "王建国", "to": "小芳"},
     {"action": "CREATE_RELATIONSHIP", "type": "parent_child", "from": "李梅", "to": "小芳"}])

add("复杂场景", "过继/改名",
    "王小军的儿子过继给了王大志，改名叫王继志",
    [{"action": "CREATE_PERSON", "name": "王继志"},
     {"action": "CREATE_RELATIONSHIP", "type": "adopted_parent_child", "from": "王大志", "to": "王继志"}])

add("复杂场景", "离婚再婚",
    "王建国和李梅后来离婚了，建国又娶了一个叫张丽的女人",
    [{"action": "CREATE_PERSON", "name": "张丽", "gender": "female"},
     {"action": "CREATE_RELATIONSHIP", "type": "spouse", "between": ["王建国", "张丽"]}])

# ============================================================
# 12. 日期格式变体
# ============================================================

add("日期格式", "年份",
    "赵大爷是45年生的",
    [{"action": "UPDATE_PERSON", "name": "赵大爷"}],
    "已有1945，信息一致")

add("日期格式", "完整日期",
    "李梅是1982年3月15日出生的",
    [{"action": "UPDATE_PERSON", "name": "李梅", "field": "birth_date", "new_value": "1982-03-15"}])

add("日期格式", "年月",
    "王建国是1980年12月出生的",
    [{"action": "UPDATE_PERSON", "name": "王建国", "field": "birth_date", "new_value": "1980-12"}])

add("日期格式", "农历",
    "赵大爷是1945年腊月生的",
    [{"action": "UPDATE_PERSON", "name": "赵大爷"}])

add("日期格式", "模糊",
    "王大强大概是50年代初出生的",
    [{"action": "UPDATE_PERSON", "name": "王大强"}])

# ============================================================
# 13. 地名变体
# ============================================================

add("地名", "村",
    "王大强是王家村土生土长的",
    [{"action": "UPDATE_PERSON", "name": "王大强", "field": "birth_place"}])

add("地名", "省",
    "李梅娘家是山东的",
    [{"action": "UPDATE_PERSON", "name": "李梅"}])

# ============================================================
# 14. 称呼变体
# ============================================================

add("称呼", "正式全名",
    "赵大爷的全名是赵大雷",
    [{"action": "UPDATE_PERSON", "name": "赵大爷→赵大雷"}])

add("称呼", "小名",
    "建国的小名叫狗蛋",
    [{"action": "UPDATE_PERSON", "name": "王建国", "field": "tags", "add": "狗蛋"}])

add("称呼", "职务",
    "赵大爷以前是村长，后来当了支书",
    [{"action": "UPDATE_PERSON", "name": "赵大爷", "field": "tags"}])

# ============================================================
# 15. 死亡信息
# ============================================================

add("死亡", "明确去世",
    "王老太爷2010年去世了",
    [{"action": "CREATE_PERSON", "name": "王老太爷"},
     {"action": "CREATE_EVENT", "type": "death"}])

add("死亡", "委婉表达",
    "我奶奶前年走了",
    [{"action": "CREATE_PERSON", "name": "奶奶"}])

add("死亡", "已有人员",
    "赵大爷去年冬天过世了",
    [{"action": "MATCH_PERSON", "name": "赵大爷"},
     {"action": "UPDATE_PERSON", "name": "赵大爷", "field": "death_date"}])

# ============================================================
# 输出
# ============================================================

output = {
    "description": "家族编年史测试用例集",
    "version": "1.0",
    "base_people": BASE_PEOPLE,
    "base_relationships": BASE_RELATIONSHIPS,
    "total_cases": len(test_cases),
    "categories": {},
    "test_cases": test_cases,
}

# 统计分类
for tc in test_cases:
    cat = tc["category"]
    if cat not in output["categories"]:
        output["categories"][cat] = 0
    output["categories"][cat] += 1

with open("test_cases.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ 生成 {len(test_cases)} 条测试用例")
print(f"\n分类统计:")
for cat, count in sorted(output["categories"].items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count} 条")
