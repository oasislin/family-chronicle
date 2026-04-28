"""
AI NLP引擎 - 规则+模式匹配版
模拟华为DeepSeek的功能，解析中文家族叙事文本
"""
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime


# ==================== 性别推断 ====================
MALE_INDICATORS = {
    '爸', '爹', '爷', '叔', '伯', '舅', '哥', '弟', '兄', '夫', '婿',
    '儿子', '孙子', '侄子', '外甥', '公公', '丈夫', '老公', '表哥', '表弟',
    '堂哥', '堂弟', '姑父', '姨父', '祖父', '外公', '爷爷', '姥爷', '叔叔',
    '伯伯', '舅舅', '大哥', '二哥', '三哥', '大弟', '小弟', '大爷', '大伯',
    '长子', '次子', '幼子', '小子', '男孩', '先生', '师傅', '老汉', '老头',
    '爷爷', '爸爸', '干爹', '义父', '继父', '大爷爷', '二爷爷',
}

FEMALE_INDICATORS = {
    '妈', '娘', '奶', '姑', '姨', '姐', '妹', '嫂', '妻', '媳', '婆',
    '女儿', '孙女', '侄女', '外甥女', '婆婆', '妻子', '老婆', '表姐', '表妹',
    '堂姐', '堂妹', '姑姑', '姨妈', '祖母', '外婆', '奶奶', '姥姥', '阿姨',
    '大姐', '二姐', '三姐', '大妹', '小妹', '长女', '次女', '幼女', '姑娘',
    '女孩', '女士', '太太', '大妈', '大娘', '大婶', '奶奶', '妈妈',
    '干妈', '义母', '继母', '大奶奶', '二奶奶', '婶婶', '伯母',
}


def infer_gender(name: str, context: str = '') -> str:
    """从名字和上下文推断性别"""
    text = name + ' ' + context
    for indicator in FEMALE_INDICATORS:
        if indicator in text:
            return 'female'
    for indicator in MALE_INDICATORS:
        if indicator in text:
            return 'male'
    # 从名字用字推断
    female_chars = '芳兰英华秀梅丽珍娣翠红霞珠巧云娟娣娣婷娜婕婉婷敏静颖蓉燕'
    male_chars = '强建国军伟勇刚明磊峰龙鹏斌杰辉亮超志昊涛浩宇轩'
    for c in name:
        if c in female_chars:
            return 'female'
        if c in male_chars:
            return 'male'
    return 'unknown'


# ==================== 日期提取 ====================
YEAR_PATTERN = re.compile(r'(?:19|20)\d{2}')
DATE_PATTERN = re.compile(r'((?:19|20)\d{2})\s*年?\s*(\d{1,2})?\s*月?\s*(\d{1,2})?\s*日?')
LUNAR_PATTERN = re.compile(r'农历|阴历|旧历')
SOLAR_PATTERN = re.compile(r'公历|阳历|新历|国历')


def extract_date(text: str) -> Tuple[Optional[str], str]:
    """提取日期，返回 (日期字符串, 日历类型)"""
    calendar = 'solar'
    if LUNAR_PATTERN.search(text):
        calendar = 'lunar'
    elif SOLAR_PATTERN.search(text):
        calendar = 'solar'

    m = DATE_PATTERN.search(text)
    if m:
        year = m.group(1)
        month = m.group(2)
        day = m.group(3)
        if month and day:
            return f"{year}-{int(month):02d}-{int(day):02d}", calendar
        elif month:
            return f"{year}-{int(month):02d}", calendar
        else:
            return year, calendar

    m = YEAR_PATTERN.search(text)
    if m:
        return m.group(0), calendar

    return None, calendar


# ==================== 人物提取 ====================
# 称谓 -> (关系类型, 性别推断)
TITLE_MAP = {
    '爷爷': ('grandfather', 'male'), '祖父': ('grandfather', 'male'), '外公': ('grandfather', 'male'), '姥爷': ('grandfather', 'male'),
    '奶奶': ('grandmother', 'female'), '祖母': ('grandmother', 'female'), '外婆': ('grandmother', 'female'), '姥姥': ('grandmother', 'female'),
    '爸爸': ('father', 'male'), '爹': ('father', 'male'), '父亲': ('father', 'male'),
    '妈妈': ('mother', 'female'), '娘': ('mother', 'female'), '母亲': ('mother', 'female'),
    '哥哥': ('brother', 'male'), '大哥': ('brother', 'male'), '二哥': ('brother', 'male'), '三哥': ('brother', 'male'),
    '弟弟': ('brother', 'male'), '大弟': ('brother', 'male'), '小弟': ('brother', 'male'),
    '姐姐': ('sister', 'female'), '大姐': ('sister', 'female'), '二姐': ('sister', 'female'), '三姐': ('sister', 'female'),
    '妹妹': ('sister', 'female'), '大妹': ('sister', 'female'), '小妹': ('sister', 'female'),
    '儿子': ('son', 'male'), '大儿子': ('son', 'male'), '二儿子': ('son', 'male'), '小儿子': ('son', 'male'),
    '长子': ('son', 'male'), '次子': ('son', 'male'), '幼子': ('son', 'male'),
    '女儿': ('daughter', 'female'), '大女儿': ('daughter', 'female'), '二女儿': ('daughter', 'female'), '小女儿': ('daughter', 'female'),
    '长女': ('daughter', 'female'), '次女': ('daughter', 'female'), '幼女': ('daughter', 'female'),
    '老婆': ('wife', 'female'), '妻子': ('wife', 'female'), '媳妇': ('wife', 'female'),
    '老公': ('husband', 'male'), '丈夫': ('husband', 'male'), '先生': ('husband', 'male'),
    '孙子': ('grandson', 'male'), '孙女': ('granddaughter', 'female'),
    '侄子': ('nephew', 'male'), '侄女': ('niece', 'female'),
    '外甥': ('nephew', 'male'), '外甥女': ('niece', 'female'),
    '舅舅': ('uncle', 'male'), '叔叔': ('uncle', 'male'), '伯伯': ('uncle', 'male'), '伯父': ('uncle', 'male'),
    '大伯': ('uncle', 'male'), '大爷': ('uncle', 'male'), '大舅': ('uncle', 'male'),
    '姑姑': ('aunt', 'female'), '姑妈': ('aunt', 'female'), '姨妈': ('aunt', 'female'), '姨姨': ('aunt', 'female'),
    '阿姨': ('aunt', 'female'), '大姨': ('aunt', 'female'),
    '表哥': ('cousin', 'male'), '表弟': ('cousin', 'male'), '堂哥': ('cousin', 'male'), '堂弟': ('cousin', 'male'),
    '表姐': ('cousin', 'female'), '表妹': ('cousin', 'female'), '堂姐': ('cousin', 'female'), '堂妹': ('cousin', 'female'),
    '姑父': ('uncle_in_law', 'male'), '姨父': ('uncle_in_law', 'male'),
    '公公': ('father_in_law', 'male'), '岳父': ('father_in_law', 'male'),
    '婆婆': ('mother_in_law', 'female'), '岳母': ('mother_in_law', 'female'),
    '大爷爷': ('granduncle', 'male'), '二爷爷': ('granduncle', 'male'),
    '大奶奶': ('grandaunt', 'female'), '二奶奶': ('grandaunt', 'female'),
    '婶婶': ('aunt', 'female'), '伯母': ('aunt', 'female'),
    '干爹': ('godfather', 'male'), '干妈': ('godmother', 'female'),
    '义父': ('godfather', 'male'), '义母': ('godmother', 'female'),
    '继父': ('stepfather', 'male'), '继母': ('stepmother', 'female'),
    '师傅': ('mentor', 'male'), '师父': ('mentor', 'male'),
    '儿媳妇': ('daughter_in_law', 'female'), '女婿': ('son_in_law', 'male'),
    '大嫂': ('sister_in_law', 'female'), '弟妹': ('sister_in_law', 'female'),
    '姐夫': ('brother_in_law', 'male'), '妹夫': ('brother_in_law', 'male'),
}

# 从文本提取"称谓+名字"的模式
NAME_WITH_TITLE = re.compile(
    r'(我)?(的)?(' + '|'.join(sorted(TITLE_MAP.keys(), key=len, reverse=True)) + r')'
    r'(?:叫|是)?\s*([^\s，。、；！？,.;!?]{2,4})'
)

SIMPLE_NAME_PATTERN = re.compile(
    r'(?:叫|名叫|名字叫|名字是)\s*([^\s，。、；！？,.;!?]{2,4})'
)

PERSON_INTRO_PATTERN = re.compile(
    r'(?:有|来了|认识|介绍)\s*(?:个|一位)?\s*'
    r'(?:(男|女|大|小|老|年轻)的?)?\s*'
    r'(?:人|朋友|亲戚|邻居|同事|同学)?\s*'
    r'(?:叫|名叫)?\s*([^\s，。、；！？,.;!?]{2,4})'
)


def extract_persons(text: str, speaker: str = '我') -> List[Dict]:
    """从文本中提取人物信息"""
    persons = []

    # 模式1: "我XX叫名字"
    for m in NAME_WITH_TITLE.finditer(text):
        title = m.group(3)
        name = m.group(4)
        info = TITLE_MAP.get(title, ('relative', 'unknown'))
        persons.append({
            'name': name,
            'gender': info[1] if info[1] != 'unknown' else infer_gender(name, title),
            'relation_to_speaker': info[0],
            'title': title,
            'confidence': 0.9,
        })

    # 模式2: "叫/名叫XXX"
    if not persons:
        for m in SIMPLE_NAME_PATTERN.finditer(text):
            name = m.group(1)
            if len(name) >= 2 and not any(c in '的了是在有和跟与从到把被让给对' for c in name):
                persons.append({
                    'name': name,
                    'gender': infer_gender(name, text),
                    'relation_to_speaker': 'unknown',
                    'title': None,
                    'confidence': 0.7,
                })

    return persons


# ==================== 关系提取 ====================
RELATIONSHIP_PATTERNS = [
    # A是B的XX
    (re.compile(r'(\S{2,4})\s*(?:是|就是)\s*(\S{2,4})\s*的\s*(\S+)'), 'is_of'),
    # A和B是XX
    (re.compile(r'(\S{2,4})\s*(?:和|跟|与)\s*(\S{2,4})\s*(?:是|算|算是)\s*(\S+)'), 'are'),
    # A的XX是B
    (re.compile(r'(\S{2,4})\s*的\s*(\S+)\s*(?:是|叫|名叫)\s*(\S{2,4})'), 'of_is'),
    # A比B大/小X岁
    (re.compile(r'(\S{2,4})\s*比\s*(\S{2,4})\s*(大|小)\s*(\d+)\s*岁'), 'age_diff'),
]


def extract_relationships(text: str) -> List[Dict]:
    """提取关系描述"""
    rels = []
    for pattern, ptype in RELATIONSHIP_PATTERNS:
        for m in pattern.finditer(text):
            if ptype == 'is_of':
                rels.append({'person_a': m.group(1), 'person_b': m.group(2), 'relation': m.group(3), 'pattern': ptype})
            elif ptype == 'are':
                rels.append({'person_a': m.group(1), 'person_b': m.group(2), 'relation': m.group(3), 'pattern': ptype})
            elif ptype == 'of_is':
                rels.append({'person_a': m.group(1), 'person_b': m.group(3), 'relation': m.group(2), 'pattern': ptype})
            elif ptype == 'age_diff':
                rels.append({'person_a': m.group(1), 'person_b': m.group(2), 'relation': f"{m.group(3)}{m.group(4)}岁", 'pattern': ptype})
    return rels


# ==================== 事件提取 ====================
EVENT_KEYWORDS = {
    'born': ['出生', '降生', '落地', '来到世上', '生了', '添了'],
    'death': ['去世', '过世', '走了', '没了', '病逝', '离世', '仙逝', '驾鹤', '老了', '不在了', '死', '病故', '亡故', '故去'],
    'marriage': ['结婚', '成亲', '办喜事', '娶了', '嫁了', '嫁给了', '迎娶', '过门', '完婚'],
    'divorce': ['离婚', '离了', '分手', '分开了'],
    'move': ['搬到', '迁到', '去了', '移居', '定居', '落户'],
    'education': ['上学', '读书', '考上', '毕业', '入学', '进学校', '高考', '中考'],
    'career': ['工作', '上班', '当了', '做了', '开了', '创业', '退休', '参军', '入伍', '当兵'],
    'illness': ['生病', '病了', '住院', '查出', '确诊', '手术'],
    'reunion': ['团聚', '回来', '回老家', '探亲', '重逢', '过年'],
    'building': ['盖了', '建了', '修了', '翻新', '盖房子', '建房'],
}


def extract_events(text: str, persons: List[Dict]) -> List[Dict]:
    """提取事件"""
    events = []
    for event_type, keywords in EVENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                # 尝试关联到人物
                date, cal = extract_date(text)
                event = {
                    'type': event_type,
                    'keyword': kw,
                    'date': date,
                    'calendar': cal,
                    'raw_text': text,
                    'related_persons': [p['name'] for p in persons],
                }
                events.append(event)
                break  # 每种事件类型只匹配一次
    return events


# ==================== 地点提取 ====================
LOCATION_PATTERN = re.compile(
    r'(?:在|到|去|从|来自|搬到|迁到|住在|老家在|祖籍)\s*'
    r'(\S{2,10}(?:省|市|县|区|镇|村|乡|州|岛|路|街|巷|号|屯|庄|沟|岭|坡|湾))'
)


def extract_locations(text: str) -> List[str]:
    """提取地点"""
    return [m.group(1) for m in LOCATION_PATTERN.finditer(text)]


# ==================== 生平描述提取 ====================
def extract_description(text: str) -> Optional[str]:
    """提取人物描述/生平"""
    # 如果是纯叙述性文字（没有明确的人物或关系提取）
    desc_patterns = [
        r'(.{10,}的?人)', r'(.{10,}性格)', r'(.{10,}脾气)',
        r'(.{10,}手艺)', r'(.{10,}技术)', r'(.{10,}本事)',
        r'(.{10,}经历)', r'(.{10,}故事)', r'(.{10,}一辈子)',
    ]
    for p in desc_patterns:
        m = re.search(p, text)
        if m:
            return m.group(1)
    # 长文本且没有提取到其他结构化信息，整体作为描述
    if len(text) > 15:
        return text
    return None


# ==================== 综合解析 ====================
def parse_family_text(text: str, context_people: List[str] = None) -> Dict:
    """
    综合解析家族叙事文本
    返回结构化数据: persons, relationships, events, locations, description, is_noise
    """
    text = text.strip()

    # 噪声检测
    noise_patterns = [
        r'^今天天气', r'^明天.*天气', r'^(\d+\s*)+$',  # 天气/数字
        r'^[。！？，\s]+$',  # 纯标点
        r'^(好|嗯|哦|啊|是|对|不|没有|不知道)\s*[。！？.!?]*$',  # 简短应答
        r'^(哈哈|呵呵|嘿嘿|嘻嘻)\s*[！!]*$',  # 纯笑声
        r'^(吃饭|睡觉|喝水|上厕所)',  # 日常琐事（无家族信息）
    ]
    for p in noise_patterns:
        if re.match(p, text):
            return {
                'persons': [], 'relationships': [], 'events': [],
                'locations': [], 'description': None, 'is_noise': True,
                'raw_text': text,
            }

    persons = extract_persons(text)
    relationships = extract_relationships(text)
    events = extract_events(text, persons)
    locations = extract_locations(text)
    description = extract_description(text)

    # 如果没有提取到结构化信息但文本较长，可能是故事描述
    if not persons and not relationships and not events and len(text) > 10:
        is_story = True
    else:
        is_story = False

    return {
        'persons': persons,
        'relationships': relationships,
        'events': events,
        'locations': locations,
        'description': description if is_story else None,
        'is_noise': False,
        'is_story': is_story,
        'raw_text': text,
    }


# ==================== 知识图谱更新引擎 ====================
class KnowledgeGraphEngine:
    """模拟后端auto-import逻辑"""

    def __init__(self):
        self.persons = {}  # name -> person_data
        self.relationships = []
        self.events = []
        self.next_id = 1
        self.log = []  # 处理日志

    def init_base_data(self, base_people: List[Dict], base_relationships: List[Dict]):
        """初始化基础数据"""
        id_to_name = {}
        for p in base_people:
            pid = p.get('id', f"p{self.next_id}")
            self.persons[p['name']] = {
                'id': pid,
                'name': p['name'],
                'gender': p.get('gender', 'unknown'),
                'birth_date': p.get('birth_date', ''),
                'death_date': p.get('death_date', ''),
                'tags': p.get('tags', []),
                'biography': [],
                'description': p.get('description', ''),
            }
            id_to_name[pid] = p['name']
            num = int(pid.replace('p', '')) if pid.startswith('p') else self.next_id
            self.next_id = max(self.next_id, num + 1)

        for r in base_relationships:
            pa = r.get('person_a', r.get('person1_id', ''))
            pb = r.get('person_b', r.get('person2_id', ''))
            # 如果是 ID 引用，转换为名字
            pa_name = id_to_name.get(pa, pa)
            pb_name = id_to_name.get(pb, pb)
            self.relationships.append({
                'id': r.get('id', f"r{len(self.relationships)+1}"),
                'person_a': pa_name,
                'person_b': pb_name,
                'type': r.get('type', 'relative'),
                'description': r.get('description', ''),
            })

    def fuzzy_match(self, name: str, threshold: float = 0.6) -> Optional[str]:
        """模糊匹配现有人员"""
        if name in self.persons:
            return name

        best_match = None
        best_score = 0
        for existing_name in self.persons:
            score = self._similarity(name, existing_name)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = existing_name
        return best_match

    def _similarity(self, a: str, b: str) -> float:
        """简单的字符重叠相似度"""
        if a == b:
            return 1.0
        set_a = set(a)
        set_b = set(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0

    def process_input(self, text: str, case_id: str = '') -> Dict:
        """处理一条输入文本"""
        parsed = parse_family_text(text)
        result = {
            'case_id': case_id,
            'input': text,
            'actions': [],
            'is_noise': parsed['is_noise'],
        }

        if parsed['is_noise']:
            result['actions'].append({'type': 'SKIP', 'reason': '噪声/无效输入'})
            self.log.append(result)
            return result

        # 处理人物
        for p in parsed['persons']:
            matched = self.fuzzy_match(p['name'])
            if matched:
                # 更新已有人员
                person = self.persons[matched]
                actions = []
                if not person['gender'] or person['gender'] == 'unknown':
                    person['gender'] = p['gender']
                    actions.append(f"设置性别={p['gender']}")
                if p.get('title'):
                    person['tags'].append(p['title'])
                    actions.append(f"添加标签={p['title']}")
                result['actions'].append({
                    'type': 'UPDATE_PERSON',
                    'name': matched,
                    'details': actions,
                })
            else:
                # 创建新人物
                person_data = {
                    'id': f"p{self.next_id}",
                    'name': p['name'],
                    'gender': p['gender'],
                    'birth_date': '',
                    'death_date': '',
                    'tags': [p['title']] if p.get('title') else [],
                    'biography': [],
                    'description': '',
                }
                self.persons[p['name']] = person_data
                self.next_id += 1
                result['actions'].append({
                    'type': 'CREATE_PERSON',
                    'name': p['name'],
                    'gender': p['gender'],
                    'id': person_data['id'],
                })

        # 处理事件（附带日期）
        for e in parsed['events']:
            event_record = {
                'id': f"e{len(self.events)+1}",
                'type': e['type'],
                'date': e['date'],
                'related_persons': e['related_persons'],
                'raw_text': e['raw_text'],
            }
            self.events.append(event_record)
            result['actions'].append({
                'type': 'ADD_EVENT',
                'event_type': e['type'],
                'date': e['date'],
                'persons': e['related_persons'],
            })

            # 如果事件关联到人物，更新人物信息
            for pname in e['related_persons']:
                matched = self.fuzzy_match(pname)
                if matched and e['date']:
                    person = self.persons[matched]
                    if e['type'] == 'born' and not person['birth_date']:
                        person['birth_date'] = e['date']
                    elif e['type'] == 'death' and not person['death_date']:
                        person['death_date'] = e['date']

        # 处理关系
        for r in parsed['relationships']:
            rel_record = {
                'id': f"r{len(self.relationships)+1}",
                'person_a': r['person_a'],
                'person_b': r['person_b'],
                'type': r['relation'],
                'description': '',
            }
            self.relationships.append(rel_record)
            result['actions'].append({
                'type': 'ADD_RELATIONSHIP',
                'person_a': r['person_a'],
                'person_b': r['person_b'],
                'relation': r['relation'],
            })

        # 处理地点
        for loc in parsed['locations']:
            result['actions'].append({
                'type': 'ADD_LOCATION',
                'location': loc,
            })

        # 处理描述
        if parsed['description']:
            # 尝试关联到最近创建/更新的人物
            for p in parsed['persons']:
                matched = self.fuzzy_match(p['name'])
                if matched:
                    self.persons[matched]['biography'].append(parsed['description'])
                    result['actions'].append({
                        'type': 'ADD_BIOGRAPHY',
                        'person': matched,
                        'text': parsed['description'][:100],
                    })
                    break

        if not result['actions']:
            result['actions'].append({'type': 'NO_ACTION', 'reason': '未提取到有效信息'})

        self.log.append(result)
        return result

    def get_state(self) -> Dict:
        """获取当前知识图谱状态"""
        return {
            'persons': list(self.persons.values()),
            'relationships': self.relationships,
            'events': self.events,
            'stats': {
                'total_persons': len(self.persons),
                'total_relationships': len(self.relationships),
                'total_events': len(self.events),
            }
        }


if __name__ == '__main__':
    # 测试
    engine = KnowledgeGraphEngine()
    result = engine.process_input("我爷爷叫王大强，1950年出生的，今年身体不太好")
    print(json.dumps(result, ensure_ascii=False, indent=2))
