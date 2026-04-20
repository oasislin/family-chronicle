"""
测试用例扩充器：基于基础用例生成变体，达到 500+ 条
"""
import json
import copy
import random

with open("test_cases.json", "r", encoding="utf-8") as f:
    data = json.load(f)

base_cases = data["test_cases"]
expanded = list(base_cases)  # 保留原始

# ============================================================
# 变体生成策略
# ============================================================

def variant(case, input_variants, suffix=""):
    """为一个用例生成多个输入变体"""
    results = []
    for i, v in enumerate(input_variants):
        c = copy.deepcopy(case)
        c["id"] = f"{case['id']}_v{i+1}"
        c["input"] = v
        if suffix:
            c["notes"] = (case.get("notes", "") + " " + suffix).strip()
        results.append(c)
    return results

# ============================================================
# 1. 新增人物变体（扩充表达方式）
# ============================================================

person_create_variants = [
    # 基础格式变体
    ("我表哥叫陈伟", "我有个表哥，叫陈伟"),
    ("陈伟是我的表哥", "表哥陈伟"),
    ("我家表哥名叫陈伟", "表哥名字叫陈伟"),
]

for base_text, *variants_list in person_create_variants:
    for v in variants_list:
        expanded.append({
            "id": f"EXT_p{len(expanded)+1:03d}",
            "category": "新增人物",
            "subcategory": "表达变体",
            "input": v,
            "expected_actions": [{"action": "CREATE_PERSON"}],
            "notes": f"变体: {base_text}",
        })

# ============================================================
# 2. 批量生成：各种亲属称谓 + 新人
# ============================================================

kinship_terms = [
    ("叔叔", "male"), ("阿姨", "female"), ("舅舅", "male"), ("姑姑", "female"),
    ("爷爷", "male"), ("奶奶", "female"), ("外公", "male"), ("外婆", "female"),
    ("哥哥", "male"), ("姐姐", "female"), ("弟弟", "male"), ("妹妹", "female"),
    ("堂哥", "male"), ("堂弟", "male"), ("堂姐", "female"), ("堂妹", "female"),
    ("表哥", "male"), ("表弟", "male"), ("表姐", "female"), ("表妹", "female"),
    ("姐夫", "male"), ("嫂子", "female"), ("弟媳", "female"), ("妹夫", "male"),
    ("儿媳妇", "female"), ("女婿", "male"), ("亲家", "male"), ("亲家母", "female"),
]

surnames = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴", "孙", "马",
            "朱", "胡", "郭", "何", "高", "林", "罗", "郑", "梁", "谢", "宋", "唐"]
given_names_male = ["建国", "建军", "国强", "志强", "伟", "勇", "军", "明", "华", "刚",
                     "磊", "鹏", "超", "浩", "宇", "涛", "鑫", "飞", "波", "杰"]
given_names_female = ["秀英", "桂芳", "丽华", "翠花", "淑芬", "玉兰", "美玲", "小红",
                       "雪梅", "春花", "丽", "静", "敏", "燕", "芳", "霞", "玲", "娟"]

random.seed(42)

for term, gender in kinship_terms:
    # 每个称谓生成2个变体
    for j in range(2):
        surname = random.choice(surnames)
        if gender == "male":
            given = random.choice(given_names_male)
        else:
            given = random.choice(given_names_female)
        full_name = surname + given
        year = random.randint(1950, 2005)

        templates = [
            f"我的{term}叫{full_name}",
            f"我家{term}{full_name}",
            f"{term}{full_name}是{year}年生的",
            f"有个{term}叫{full_name}，{year}年出生",
        ]
        input_text = random.choice(templates)

        expanded.append({
            "id": f"EXT_k{len(expanded)+1:03d}",
            "category": "新增人物",
            "subcategory": f"亲属称谓-{term}",
            "input": input_text,
            "expected_actions": [
                {"action": "CREATE_PERSON", "name": full_name, "gender": gender}
            ],
        })

# ============================================================
# 3. 批量生成：事件变体
# ============================================================

event_types_variants = {
    "结婚": [
        ("{a}和{b}结婚了", "marriage"),
        ("{a}娶了{b}", "marriage"),
        ("{a}嫁给了{b}", "marriage"),
        ("{a}与{b}喜结连理", "marriage"),
        ("{a}跟{b}成亲了", "marriage"),
        ("{a}和{b}办了喜事", "marriage"),
    ],
    "出生": [
        ("{a}出生了", "birth"),
        ("{a}降生了", "birth"),
        ("{a}来到这个世界", "birth"),
        ("家里添了{a}", "birth"),
    ],
    "去世": [
        ("{a}去世了", "death"),
        ("{a}走了", "death"),
        ("{a}过世了", "death"),
        ("{a}不在了", "death"),
        ("{a}老了（去世）", "death"),
        ("送走了{a}", "death"),
    ],
    "搬家": [
        ("{a}搬到了{loc}", "relocation"),
        ("{a}从{loc}迁走了", "relocation"),
        ("{a}一家搬到{loc}去了", "relocation"),
    ],
    "生病": [
        ("{a}生了一场大病", "illness"),
        ("{a}住院了", "illness"),
        ("{a}病了好几个月", "illness"),
    ],
}

people_names = ["王建国", "李梅", "王大强", "赵大爷", "李菊花"]
places = ["县城", "省城", "北京", "王家村", "李家村", "镇上"]

for event_cat, variants_list in event_types_variants.items():
    for template, etype in variants_list:
        a = random.choice(people_names)
        b = random.choice([n for n in people_names if n != a])
        loc = random.choice(places)
        year = random.randint(1980, 2025)

        input_text = template.format(a=a, b=b, loc=loc, year=year)

        expanded.append({
            "id": f"EXT_e{len(expanded)+1:03d}",
            "category": "事件",
            "subcategory": f"事件变体-{event_cat}",
            "input": input_text,
            "expected_actions": [
                {"action": "CREATE_EVENT", "type": etype}
            ],
        })

# ============================================================
# 4. 批量生成：干扰项
# ============================================================

noise_inputs = [
    "今天天气真好", "明天要下雨了", "午饭吃什么好呢", "这电视真没意思",
    "村口那棵老槐树还在", "今年收成不错", "隔壁村的路修好了",
    "手机没电了", "快递到了", "该理发了", "玉米该收了",
    "狗又跑出去了", "屋顶漏雨了", "井水不甜了", "菜地该浇水了",
    "电视机坏了", "洗衣机漏水了", "电费该交了", "门口路灯不亮",
    "集市上白菜便宜了", "猪肉又涨价了", "种子买好了",
    "清明要上坟了", "过年要杀猪了", "中秋要买月饼",
    "孩子该上学了", "作业还没写完", "老师打电话来了",
    "银行排队好多人", "医院挂号太难了", "公交改线了",
    "邻居家盖新房了", "村长换届了", "修路封道了",
    "听说要拆迁了", "补贴发下来了", "低保办好了",
    "驾照考下来了", "新买的电动车", "手机该换了",
    "天气预报说有暴雨", "山上有野猪了", "河里鱼少了",
    "广场舞开始了", "下棋输了三盘", "钓鱼空军了",
]

for i, noise in enumerate(noise_inputs):
    expanded.append({
        "id": f"EXT_n{i+1:03d}",
        "category": "干扰项",
        "subcategory": "纯噪音",
        "input": noise,
        "expected_actions": [{"action": "NO_ACTION"}],
    })

# ============================================================
# 5. 批量生成：关系变体（不同表达）
# ============================================================

rel_templates = {
    "parent_child": [
        "{a}是{b}的儿子", "{a}是{b}的女儿", "{b}是{a}的父亲", "{b}是{a}的母亲",
        "{a}生了{b}", "{b}是{a}的孩子", "{a}是{b}的爹", "{a}是{b}的妈",
    ],
    "spouse": [
        "{a}是{b}的老婆", "{a}是{b}的丈夫", "{a}和{b}是两口子",
        "{a}和{b}结婚了", "{b}是{a}的媳妇", "{b}是{a}的老公",
    ],
    "sibling": [
        "{a}是{b}的哥哥", "{a}是{b}的弟弟", "{a}是{b}的姐姐", "{a}是{b}的妹妹",
        "{a}和{b}是亲兄弟", "{a}和{b}是亲姐妹", "{a}和{b}是兄妹",
    ],
}

for rel_type, templates in rel_templates.items():
    for tmpl in templates:
        a = random.choice(people_names)
        b = random.choice([n for n in people_names if n != a])
        input_text = tmpl.format(a=a, b=b)

        expanded.append({
            "id": f"EXT_r{len(expanded)+1:03d}",
            "category": "新建关系",
            "subcategory": f"关系表达-{rel_type}",
            "input": input_text,
            "expected_actions": [
                {"action": "CREATE_RELATIONSHIP", "type": rel_type}
            ],
        })

# ============================================================
# 6. 批量生成：更新信息变体
# ============================================================

update_templates = [
    ("补充出生年", "{name}是{year}年出生的", "birth_date"),
    ("补充出生年", "{name}生于{year}年", "birth_date"),
    ("补充出生月", "{name}是{month}月生的", "birth_date"),
    ("补充出生地", "{name}是{place}人", "birth_place"),
    ("补充出生地", "{name}老家在{place}", "birth_place"),
    ("补充出生地", "{name}生在{place}", "birth_place"),
    ("补充现居地", "{name}现在住在{place}", "current_residence"),
    ("补充现居地", "{name}搬到了{place}", "current_residence"),
    ("补充现居地", "{name}在{place}安了家", "current_residence"),
]

for subcat, tmpl, field in update_templates:
    for name in people_names:
        year = random.randint(1940, 2010)
        month = random.randint(1, 12)
        place = random.choice(places)
        input_text = tmpl.format(name=name, year=year, month=month, place=place)

        expanded.append({
            "id": f"EXT_u{len(expanded)+1:03d}",
            "category": "更新信息",
            "subcategory": subcat,
            "input": input_text,
            "expected_actions": [
                {"action": "UPDATE_PERSON", "name": name, "field": field}
            ],
        })

# ============================================================
# 7. 批量生成：生平故事变体
# ============================================================

story_templates = [
    "{name}年轻时吃过不少苦",
    "{name}为人很老实，从不跟人红脸",
    "{name}手艺很好，做的家具远近闻名",
    "{name}脾气不太好，但心地善良",
    "{name}以前当过兵，回来后一直很自律",
    "{name}是村里的能人，什么都会修",
    "{name}特别疼孩子，有什么好吃的都留给娃",
    "{name}年轻时候是十里八乡的美人",
    "{name}念过私塾，识文断字",
    "{name}一辈子没出过远门",
    "{name}在镇上开过小卖部",
    "{name}种地是一把好手",
    "{name}喜欢喝酒，每顿都得来二两",
    "{name}特别勤快，天不亮就起来干活",
    "{name}会唱戏，逢年过节村里表演",
    "{name}养了一辈子牛，是养牛的好手",
    "{name}是个木匠，方圆几十里都有名",
    "{name}很会做饭，村里红白喜事都请她",
    "{name}一辈子省吃俭用，供孩子读书",
    "{name}在矿上干了一辈子，落下一身病",
]

for tmpl in story_templates:
    name = random.choice(people_names)
    input_text = tmpl.format(name=name)

    expanded.append({
        "id": f"EXT_s{len(expanded)+1:03d}",
        "category": "生平故事",
        "subcategory": "性格/经历描述",
        "input": input_text,
        "expected_actions": [
            {"action": "UPDATE_STORY", "name": name}
        ],
    })

# ============================================================
# 8. 混合场景（有效信息+废话）
# ============================================================

mixed_inputs = [
    "今天去赶集了，买了二斤肉。对了，我二叔叫刘大壮，1960年生的",
    "晚饭吃的面条。想起来我姑姑叫张秀兰，是1958年出生的",
    "下雨了收衣服。哦对了，建国的儿子叫王小刚，今年上初中了",
    "电视又没信号了。话说李梅她妈叫刘桂兰，今年应该七十多了",
    "村口修路呢吵死了。差点忘了说，赵大爷有个弟弟叫赵大海",
    "手机又没电了充一下。想起我姥姥叫周玉兰，1930年生的已经走了",
    "明天要赶早集买种子。对了王大强年轻时候当过兵",
    "柴火不够了要去砍点。我表姐叫杨小红，嫁到外省去了",
    "鸡又丢了满村找。王建国他媳妇李梅做饭特别好吃",
    "自来水又停了。我三爷爷叫王德胜，参加过抗美援朝",
]

for i, mixed in enumerate(mixed_inputs):
    expanded.append({
        "id": f"EXT_m{i+1:03d}",
        "category": "混合场景",
        "subcategory": "废话+有效信息",
        "input": mixed,
        "expected_actions": [
            {"action": "CREATE_PERSON"},
            {"action": "MATCH_PERSON"},
        ],
    })

# ============================================================
# 9. 边界情况
# ============================================================

edge_cases = [
    ("", "空输入", [{"action": "NO_ACTION"}]),
    ("。", "只有标点", [{"action": "NO_ACTION"}]),
    ("嗯", "语气词", [{"action": "NO_ACTION"}]),
    ("好的", "应答词", [{"action": "NO_ACTION"}]),
    ("不知道", "否定回答", [{"action": "NO_ACTION"}]),
    ("王王王", "重复字", [{"action": "NO_ACTION"}]),
    ("12345", "纯数字", [{"action": "NO_ACTION"}]),
    ("abc", "纯英文", [{"action": "NO_ACTION"}]),
    ("👨", "emoji", [{"action": "NO_ACTION"}]),
    ("王建国王建国王建国", "重复名字", [{"action": "MATCH_PERSON"}]),
]

for input_text, desc, actions in edge_cases:
    expanded.append({
        "id": f"EXT_b{len(expanded)+1:03d}",
        "category": "边界情况",
        "subcategory": desc,
        "input": input_text,
        "expected_actions": actions,
    })

# ============================================================
# 10. 日期格式变体扩充
# ============================================================

date_variants = [
    "王建国是80年生的",
    "王建国是八零年生的",
    "王建国生于1980年",
    "王建国1980年腊月十八生的",
    "王建国是1980年12月8号出生的",
    "王建国八零年冬天出生的",
    "王建国是庚申年生的",
    "王建国今年46了（按2026算）",
    "李梅是八二年的",
    "李梅生于壬戌年",
    "赵大爷四五年生的",
    "赵大爷1945年属鸡的",
    "王大强五零年生人",
    "王大强1950年",
]

for i, dv in enumerate(date_variants):
    expanded.append({
        "id": f"EXT_d{i+1:03d}",
        "category": "日期格式",
        "subcategory": "日期表达变体",
        "input": dv,
        "expected_actions": [
            {"action": "UPDATE_PERSON"}
        ],
    })

# ============================================================
# 11. 同名/歧义
# ============================================================

ambiguous_cases = [
    ("村里还有个王建国，是开小卖部的", "同名新人", [{"action": "CREATE_PERSON"}, {"action": "ASK_QUESTION"}]),
    ("大伯说建国该结婚了", "代词+已有人员", [{"action": "MATCH_PERSON"}]),
    ("他妈说他小时候很皮", "纯代词", [{"action": "NO_ACTION"}]),
    ("老王家的老大", "模糊指代", [{"action": "NO_ACTION"}]),
    ("那个谁，叫什么来着", "遗忘", [{"action": "NO_ACTION"}]),
    ("好像是姓李还是姓王", "不确定", [{"action": "NO_ACTION"}]),
]

for input_text, desc, actions in ambiguous_cases:
    expanded.append({
        "id": f"EXT_a{len(expanded)+1:03d}",
        "category": "歧义/指代不明",
        "subcategory": desc,
        "input": input_text,
        "expected_actions": actions,
    })

# ============================================================
# 输出
# ============================================================

# 重新统计
categories = {}
for tc in expanded:
    cat = tc["category"]
    categories[cat] = categories.get(cat, 0) + 1

output = {
    "description": "家族编年史测试用例集 v2（扩充版）",
    "version": "2.0",
    "base_people": data["base_people"],
    "base_relationships": data["base_relationships"],
    "total_cases": len(expanded),
    "categories": categories,
    "test_cases": expanded,
}

with open("test_cases.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ 共生成 {len(expanded)} 条测试用例")
print(f"\n分类统计:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count} 条")
