"""
生平自动生成引擎
从结构化数据（关系 + 事件）自动生成人物传记
纯模板规则，零 LLM 消耗
"""

from typing import Optional


# ============================================================
# 关系模板（双向视角）
# key: (关系类型, subtype, 性别) → (A视角模板, B视角模板)
# {other} = 对方名字, {year} = 年份, {other_gender} = 对方性别
# ============================================================

RELATIONSHIP_TEMPLATES = {
    "parent_child": {
        # 父亲视角（我是父亲，对方是我的孩子）
        "father": {
            "male": "儿子{other}出生。",
            "female": "女儿{other}出生。",
            "unknown": "孩子{other}出生。",
        },
        # 母亲视角
        "mother": {
            "male": "儿子{other}出生。",
            "female": "女儿{other}出生。",
            "unknown": "孩子{other}出生。",
        },
        # 孩子视角（我是孩子，对方是我的父亲/母亲）
        "_child_of_father": "父亲是{other}。",
        "_child_of_mother": "母亲是{other}。",
    },
    "spouse": {
        # 有日期
        "male": "与{other}结婚。",
        "female": "与{other}结婚。",
        # 无日期
        "_default": "配偶是{other}。",
    },
    "sibling": {
        # 兄 → 弟/妹
        "elder_brother_to_younger_brother": "有弟弟{other}。",
        "elder_brother_to_younger_sister": "有妹妹{other}。",
        # 姐 → 弟/妹
        "elder_sister_to_younger_brother": "有弟弟{other}。",
        "elder_sister_to_younger_sister": "有妹妹{other}。",
        # 弟 → 兄/姐
        "younger_brother_to_elder_brother": "有哥哥{other}。",
        "younger_brother_to_elder_sister": "有姐姐{other}。",
        # 妹 → 兄/姐
        "younger_sister_to_elder_brother": "有哥哥{other}。",
        "younger_sister_to_elder_sister": "有姐姐{other}。",
        # fallback
        "_default": "有兄弟姐妹{other}。",
    },
    "grandparent_grandchild": {
        "grandfather": "祖父是{other}。",
        "grandmother": "祖母是{other}。",
        "grandson": "{year}年，孙子{other}出生。",
        "granddaughter": "{year}年，孙女{other}出生。",
        "_default": "与{other}有祖孙关系。",
    },
    "cousin": {
        "_default": "堂/表兄弟姐妹中有{other}。",
    },
    "aunt_uncle_niece_nephew": {
        "uncle": "叔/伯是{other}。",
        "aunt": "姑/姨是{other}。",
        "nephew": "侄子是{other}。",
        "niece": "侄女是{other}。",
        "_default": "与{other}有叔侄关系。",
    },
    "adopted_parent_child": {
        "_default": "与{other}有过继关系。",
    },
    "godparent_godchild": {
        "_default": "与{other}是干亲。",
    },
    "in_law": {
        "_default": "与{other}是姻亲。",
    },
}


# ============================================================
# 事件模板
# key: 事件类型 → 模板
# ============================================================

EVENT_TEMPLATES = {
    "birth": "出生于{location}。",
    "death": "于{location}去世。",
    "marriage": "与{name}结婚。",
    "divorce": "与{name}离婚。",
    "adoption": "{description}。",
    "illness": "{description}。",
    "relocation": "迁居至{location}。",
    "education": "{description}。",
    "career": "{description}。",
    "recognition": "{description}。",
    "other": "{description}。",
}


def _extract_year(date_str: Optional[str]) -> Optional[str]:
    """从日期字符串提取年份"""
    if not date_str:
        return None
    # 支持 "1995"、"1995-06-08"、"1995年" 等格式
    for sep in ["-", "年"]:
        if sep in date_str:
            return date_str.split(sep)[0]
    if date_str.isdigit() and len(date_str) == 4:
        return date_str
    return None


def _get_subtype(rel: dict) -> str:
    """安全获取关系子类型"""
    return rel.get("subtype") or ""


def _build_sibling_template_key(my_gender: str, other_gender: str, is_older: bool) -> str:
    """构建兄弟姐妹模板 key"""
    if my_gender == "male":
        prefix = "elder_brother" if is_older else "younger_brother"
    elif my_gender == "female":
        prefix = "elder_sister" if is_older else "younger_sister"
    else:
        return "_default"

    if other_gender == "male":
        suffix = "to_younger_brother" if is_older else "to_elder_brother"
    elif other_gender == "female":
        suffix = "to_younger_sister" if is_older else "to_elder_sister"
    else:
        return "_default"

    return f"{prefix}_{suffix}"


def generate_relationship_entry(rel: dict, my_person_id: str, my_gender: str,
                                 other_name: str, other_gender: str,
                                 other_id: str = "") -> Optional[str]:
    """
    为一条关系生成叙事片段（从 my_person_id 的视角）
    返回字符串或 None（无法生成时）
    """
    rel_type = rel.get("type", "")
    subtype = _get_subtype(rel)
    year = _extract_year(rel.get("start_date") or rel.get("attributes", {}).get("year"))

    templates = RELATIONSHIP_TEMPLATES.get(rel_type)
    if not templates:
        return None

    # 用 {{person:ID}} 占位符替代名字，显示时再解析为当前名字
    ref = f"{{{{person:{other_id}}}}}" if other_id else other_name
    ctx = {"other": ref, "year": year or ""}

    # --- parent_child ---
    if rel_type == "parent_child":
        p1_id = rel.get("person1_id", "")
        is_parent_side = (my_person_id == p1_id)  # person1 是父/母方

        if is_parent_side:
            # 我是父/母
            role_key = subtype if subtype in ("father", "mother") else "father"
            gender_templates = templates.get(role_key, {})
            template = gender_templates.get(other_gender) or gender_templates.get("unknown")
            if not template:
                return None
        else:
            # 我是孩子
            if subtype == "father":
                template = templates.get("_child_of_father")
            elif subtype == "mother":
                template = templates.get("_child_of_mother")
            else:
                template = templates.get("_child_of_father")
            if not template:
                return None

        return template.format(**ctx)

    # --- spouse ---
    if rel_type == "spouse":
        # 如果标记为前任
        is_former = rel.get("attributes", {}).get("status") == "former"
        if is_former:
            if my_gender == "male":
                template = "前妻是{other}。"
            elif my_gender == "female":
                template = "前夫是{other}。"
            else:
                template = "前配偶是{other}。"
        elif year:
            template = templates.get(my_gender) or templates.get("_default")
        else:
            template = templates.get("_default")
        return template.format(**ctx)

    # --- sibling ---
    if rel_type == "sibling":
        # 判断长幼
        is_older = "elder" in subtype if subtype else None
        if is_older is None:
            # 没有 subtype 信息，尝试从 attributes 判断
            is_older = rel.get("attributes", {}).get("birth_order") == "elder"

        if is_older is not None:
            key = _build_sibling_template_key(my_gender, other_gender, is_older)
        else:
            key = "_default"

        template = templates.get(key) or templates.get("_default")
        return template.format(**ctx)

    # --- 其他关系类型 ---
    if subtype:
        template = templates.get(subtype) or templates.get("_default")
    else:
        template = templates.get("_default")

    if template:
        return template.format(**ctx)

    return None


def generate_event_entry(event: dict, my_person_id: str, all_people: dict = None) -> Optional[str]:
    """
    为一个事件生成叙事片段（本人视角）
    """
    event_type = event.get("type", "")
    description = event.get("description", "")
    location = event.get("location", "")
    year = _extract_year(event.get("date"))

    template = EVENT_TEMPLATES.get(event_type) or EVENT_TEMPLATES.get("other")

    # 婚姻/离婚事件：从参与者中找到对方名字
    partner_name = ""
    partner_id = ""
    if event_type in ("marriage", "divorce"):
        for p in event.get("participants", []):
            pid = p.get("person_id", "")
            if pid != my_person_id and all_people:
                partner_id = pid
                partner_name = all_people.get(pid, {}).get("name", "")
                break

    # 用 ID 占位符
    partner_ref = f"{{{{person:{partner_id}}}}}" if partner_id else partner_name

    # 格式化模板
    text = template.format(
        year=year or "",
        location=location or "",
        description=description or "",
        name=partner_ref,
    )

    # 清理空字段导致的尴尬文本
    text = text.replace("出生于。", "").replace("于去世。", "").replace("迁居至。", "")
    if not text or text == "。":
        return None

    # 添加年份前缀
    if year:
        text = f"{year}年，{text}"

    return text


def generate_biography(person_id: str, person_gender: str,
                       relationships: list, events: list,
                       all_people: dict) -> str:
    """
    为一个人物生成完整传记
    """
    entries = []  # [(sort_key, text)]
    partner_names = set()  # 记录已有婚姻事件的配偶名，避免重复

    # 先收集所有婚姻事件涉及的配偶
    for event in events:
        if event.get("type") in ("marriage", "divorce"):
            for p in event.get("participants", []):
                pid = p.get("person_id", "")
                if pid != person_id and all_people:
                    name = all_people.get(pid, {}).get("name", "")
                    if name:
                        partner_names.add(name)

    # 1. 处理关系 → 叙事片段
    for rel in relationships:
        p1_id = rel.get("person1_id", "")
        p2_id = rel.get("person2_id", "")

        # 确定对方
        if p1_id == person_id:
            other_id = p2_id
        elif p2_id == person_id:
            other_id = p1_id
        else:
            continue

        other = all_people.get(other_id)
        if not other:
            continue

        # 配偶关系：如果已有婚姻事件则跳过，避免重复
        if rel.get("type") == "spouse" and other["name"] in partner_names:
            continue

        entry = generate_relationship_entry(
            rel, person_id, person_gender,
            other["name"], other.get("gender", "unknown"),
            other_id=other_id,
        )
        if entry:
            year = _extract_year(rel.get("start_date") or rel.get("attributes", {}).get("year"))
            sort_key = year or "9998"

            # 添加年份前缀（如果模板里没有年份占位符且有年份信息）
            if year and "{year}" not in str(entry):
                entry = f"{year}年，{entry}"
            elif not year and entry.startswith("年，"):
                entry = entry[3:]  # 去掉尴尬的 "年，"

            entries.append((sort_key, entry))

    # 2. 处理事件 → 叙事片段
    for event in events:
        entry = generate_event_entry(event, person_id, all_people)
        if entry:
            year = _extract_year(event.get("date"))
            sort_key = year or "9999"
            entries.append((sort_key, entry))

    # 3. 按时间排序（无日期的放最后）
    entries.sort(key=lambda x: x[0])

    # 4. 去重（同一句话不重复）
    seen = set()
    unique_entries = []
    for _, text in entries:
        if text not in seen:
            seen.add(text)
            unique_entries.append(text)

    return "\n".join(unique_entries)


# ============================================================
# 便捷函数：从 FamilyGraph 直接生成
# ============================================================

def generate_biography_from_graph(graph, person_id: str) -> str:
    """
    从 FamilyGraph 对象直接为某个人物生成传记

    Args:
        graph: FamilyGraph 实例
        person_id: 人物 ID

    Returns:
        传记文本
    """
    person = graph.get_person(person_id)
    if not person:
        return ""

    # 收集该人物的关系
    person_rels = [
        r for r in graph.relationships.values()
        if r.person1_id == person_id or r.person2_id == person_id
    ]

    # 收集该人物的事件
    person_events = [
        e for e in graph.events.values()
        if any(p.get("person_id") == person_id for p in e.participants)
    ]

    # 构建 all_people 字典
    all_people = {}
    for pid, p in graph.people.items():
        all_people[pid] = {
            "name": p.name,
            "gender": p.gender.value if hasattr(p.gender, 'value') else str(p.gender),
        }

    gender = person.gender.value if hasattr(person.gender, 'value') else str(person.gender)

    return generate_biography(
        person_id, gender,
        [r.to_dict() if hasattr(r, 'to_dict') else r for r in person_rels],
        [e.to_dict() if hasattr(e, 'to_dict') else e for e in person_events],
        all_people,
    )
