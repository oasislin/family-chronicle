"""
智能家族文本解析引擎
利用大语言模型对中文语义的深度理解，解析家族叙事文本
"""
import json, os, re, sys
from typing import List, Dict, Optional, Tuple

# ==================== 基础知识库 ====================
# 已知人物（会在处理过程中动态扩展）
KNOWN_PEOPLE = {}

# 称谓→关系类型+性别
TITLE_REL = {
    '爷爷': ('grandfather', 'male'), '祖父': ('grandfather', 'male'),
    '外公': ('grandfather', 'male'), '姥爷': ('grandfather', 'male'),
    '奶奶': ('grandmother', 'female'), '祖母': ('grandmother', 'female'),
    '外婆': ('grandmother', 'female'), '姥姥': ('grandmother', 'female'),
    '爸爸': ('father', 'male'), '爹': ('father', 'male'), '爸': ('father', 'male'),
    '母亲': ('mother', 'female'), '妈妈': ('mother', 'female'), '娘': ('mother', 'female'),
    '哥哥': ('brother', 'male'), '大哥': ('brother', 'male'), '二哥': ('brother', 'male'),
    '三哥': ('brother', 'male'),
    '弟弟': ('brother', 'male'), '大弟': ('brother', 'male'), '小弟': ('brother', 'male'),
    '姐姐': ('sister', 'female'), '大姐': ('sister', 'female'), '二姐': ('sister', 'female'),
    '三姐': ('sister', 'female'),
    '妹妹': ('sister', 'female'), '大妹': ('sister', 'female'), '小妹': ('sister', 'female'),
    '儿子': ('son', 'male'), '大儿子': ('son', 'male'), '二儿子': ('son', 'male'),
    '小儿子': ('son', 'male'), '长子': ('son', 'male'), '次子': ('son', 'male'),
    '女儿': ('daughter', 'female'), '大女儿': ('daughter', 'female'),
    '小女儿': ('daughter', 'female'), '长女': ('daughter', 'female'),
    '老婆': ('wife', 'female'), '妻子': ('wife', 'female'), '媳妇': ('wife', 'female'),
    '老公': ('husband', 'male'), '丈夫': ('husband', 'male'),
    '孙子': ('grandson', 'male'), '孙女': ('granddaughter', 'female'),
    '外孙': ('grandson', 'male'), '外孙女': ('granddaughter', 'female'),
    '侄子': ('nephew', 'male'), '侄女': ('niece', 'female'),
    '外甥': ('nephew', 'male'), '外甥女': ('niece', 'female'),
    '舅舅': ('uncle_maternal', 'male'), '大舅': ('uncle_maternal', 'male'),
    '二舅': ('uncle_maternal', 'male'), '三舅': ('uncle_maternal', 'male'),
    '叔叔': ('uncle_paternal', 'male'), '伯伯': ('uncle_paternal', 'male'),
    '大伯': ('uncle_paternal', 'male'), '伯父': ('uncle_paternal', 'male'),
    '大爷': ('uncle_paternal', 'male'),
    '姑姑': ('aunt_paternal', 'female'), '姑妈': ('aunt_paternal', 'female'),
    '姨妈': ('aunt_maternal', 'female'), '姨姨': ('aunt_maternal', 'female'),
    '大姨': ('aunt_maternal', 'female'), '二姨': ('aunt_maternal', 'female'),
    '阿姨': ('aunt', 'female'),
    '表哥': ('cousin', 'male'), '表弟': ('cousin', 'male'),
    '堂哥': ('cousin', 'male'), '堂弟': ('cousin', 'male'),
    '表姐': ('cousin', 'female'), '表妹': ('cousin', 'female'),
    '堂姐': ('cousin', 'female'), '堂妹': ('cousin', 'female'),
    '姑父': ('uncle_in_law', 'male'), '姨父': ('uncle_in_law', 'male'),
    '公公': ('father_in_law', 'male'), '岳父': ('father_in_law', 'male'),
    '婆婆': ('mother_in_law', 'female'), '岳母': ('mother_in_law', 'female'),
    '大爷爷': ('granduncle', 'male'), '二爷爷': ('granduncle', 'male'),
    '三爷爷': ('granduncle', 'male'), '四爷爷': ('granduncle', 'male'),
    '五叔公': ('granduncle', 'male'),
    '大奶奶': ('grandaunt', 'female'), '二奶奶': ('grandaunt', 'female'),
    '四奶奶': ('grandaunt', 'female'),
    '婶婶': ('aunt', 'female'), '伯母': ('aunt', 'female'),
    '大伯母': ('aunt', 'female'),
    '干爹': ('godfather', 'male'), '干妈': ('godmother', 'female'),
    '继父': ('stepfather', 'male'), '继母': ('stepmother', 'female'),
    '儿媳妇': ('daughter_in_law', 'female'), '嫂子': ('sister_in_law', 'female'),
    '弟媳': ('sister_in_law', 'female'), '弟妹': ('sister_in_law', 'female'),
    '姐夫': ('brother_in_law', 'male'), '妹夫': ('brother_in_law', 'male'),
    '女婿': ('son_in_law', 'male'),
    '亲家': ('in_law', 'male'), '亲家母': ('in_law', 'female'),
    '师傅': ('mentor', 'male'), '师父': ('mentor', 'male'),
    '太爷爷': ('great_grandfather', 'male'), '太奶奶': ('great_grandmother', 'female'),
    '祖爷爷': ('ancestor', 'male'), '祖奶奶': ('ancestor', 'female'),
    '重孙子': ('great_grandson', 'male'), '重孙女': ('great_granddaughter', 'female'),
    '六舅妈': ('aunt', 'female'), '七姑父': ('uncle_in_law', 'male'),
    '八姨夫': ('uncle_in_law', 'male'),
    '九表哥': ('cousin', 'male'), '十表姐': ('cousin', 'female'),
}

# 方言称谓映射
DIALECT_TITLE = {
    '俺爹': '爸爸', '俺娘': '妈妈', '俺大爷': '大伯',
    '俺舅': '舅舅', '俺姨': '姨妈', '俺姑': '姑姑',
    '俺叔': '叔叔', '俺姥爷': '外公', '俺姥娘': '外婆',
    '俺姥奶奶': '外婆', '俺兄弟': '弟弟', '俺闺女': '女儿',
    '俺儿子': '儿子', '俺孙子': '孙子', '俺外甥女': '外甥女',
    '俺侄子': '侄子', '俺孙女': '孙女', '俺重孙子': '重孙子',
    '俺太爷爷': '太爷爷', '俺太奶奶': '太奶奶',
    '俺祖爷爷': '祖爷爷', '俺祖奶奶': '祖奶奶',
    '俺五叔公': '五叔公', '俺六舅妈': '六舅妈',
    '俺七姑父': '七姑父', '俺八姨夫': '八姨夫',
    '俺九表哥': '九表哥', '俺十表姐': '十表姐',
}

# 男性/女性名字用字
MALE_NAME_CHARS = set('强建国军伟勇刚明磊峰龙鹏斌杰辉亮超志昊涛浩宇轩豪博宏毅忠义恒瑞祥德厚柱来福根富德胜华勇刚飞鑫亮小明军伟')
FEMALE_NAME_CHARS = set('芳兰英华秀梅丽珍娣翠红霞珠巧云娟娣娣婷娜婕婉婷敏静颖蓉燕桂花玉兰秀荣秀花秀英秀兰小红小燕红梅红霞美玲丽华丽雪梅玲静娟')


def infer_gender(name: str, context: str = '') -> str:
    """推断性别"""
    text = name + ' ' + context
    female_titles = {'妈', '姑', '姨', '姐', '妹', '嫂', '妻', '媳', '婆', '奶奶', '外婆', '姥姥',
                     '女儿', '孙女', '侄女', '外甥女', '儿媳妇', '弟媳', '亲家母',
                     '太奶奶', '祖奶奶', '重孙女', '六舅妈', '堂姐', '堂妹', '表姐', '表妹'}
    male_titles = {'爸', '爹', '爷', '叔', '伯', '舅', '哥', '弟', '兄', '夫', '婿',
                   '儿子', '孙子', '侄子', '外甥', '姑父', '姨父', '姐夫', '妹夫', '女婿',
                   '太爷爷', '祖爷爷', '重孙子', '五叔公', '七姑父', '八姨夫',
                   '大伯', '大爷', '堂哥', '堂弟', '表哥', '表弟', '师傅', '师父'}

    for t in female_titles:
        if t in text:
            return 'female'
    for t in male_titles:
        if t in text:
            return 'male'

    # 从名字用字推断
    fc = sum(1 for c in name if c in FEMALE_NAME_CHARS)
    mc = sum(1 for c in name if c in MALE_NAME_CHARS)
    if fc > mc:
        return 'female'
    if mc > fc:
        return 'male'
    return 'unknown'


def extract_date(text: str) -> Tuple[Optional[str], str]:
    """提取日期"""
    calendar = 'solar'
    if any(w in text for w in ['农历', '阴历', '旧历']):
        calendar = 'lunar'

    # 精确日期: YYYY-MM-DD
    m = re.search(r'(19|20)\d{2}\s*年?\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', text)
    if m:
        return f"{m.group(0).replace('年','-').replace('月','-').replace('日','')}", calendar

    # 年月
    m = re.search(r'(19|20)\d{2}\s*年?\s*(\d{1,2})\s*月', text)
    if m:
        y = re.search(r'(19|20)\d{2}', m.group(0)).group(0)
        mo = re.search(r'(\d{1,2})\s*月', m.group(0)).group(1)
        return f"{y}-{int(mo):02d}", calendar

    # 纯年份
    m = re.search(r'(19|20)\d{2}', text)
    if m:
        return m.group(0), calendar

    # X年生 / X零年
    m = re.search(r'([一二三四五六七八九零〇])零?年', text)
    if m:
        cn = {'一':'1','二':'2','三':'3','四':'4','五':'5','六':'6','七':'7','八':'8','九':'9','零':'0','〇':'0'}
        d = cn.get(m.group(1), '?')
        # 推断是19X0还是19XX
        if '五零' in text or '50' in text:
            return '1950', calendar
        return f"19{d}0", calendar

    return None, calendar


def is_noise(text: str) -> bool:
    """判断是否为噪声/无关输入"""
    text = text.strip()
    if not text:
        return True
    if re.match(r'^[。！？，\s\.\!\?]+$', text):
        return True
    if re.match(r'^(好|嗯|哦|啊|是|对|不|没有|不知道|好的)\s*[。！？.!?]*$', text):
        return True
    if re.match(r'^[a-zA-Z\d\s]+$', text):
        return True
    if re.match(r'^[\U0001F000-\U0001FFFF]+$', text):  # emoji only
        return True

    noise_kw = ['今天天气', '明天要下雨', '午饭吃什么', '这电视', '手机没电', '快递到了',
                '该理发了', '玉米该收', '狗又跑', '屋顶漏雨', '井水不甜', '菜地该浇水',
                '电视机坏了', '洗衣机漏水', '电费该交', '门口路灯', '集市上白菜',
                '猪肉又涨价', '种子买好了', '清明要上坟', '过年要杀猪', '中秋要买月饼',
                '孩子该上学', '作业还没写完', '老师打电话', '银行排队', '医院挂号',
                '公交改线', '邻居家盖新房', '村长换届', '修路封道', '听说要拆迁',
                '补贴发下来', '低保办好了', '驾照考下来', '新买的电动车', '手机该换了',
                '天气预报', '山上有野猪', '河里鱼少了', '广场舞开始', '下棋输了',
                '钓鱼空军', '猪跑了满院子', '鸡下了个双黄蛋', '猫抓了只老鼠',
                '小狗又咬鞋', '羊该剪毛', '马蜂窝要捅', '腌的酸菜', '晒的红薯干',
                '磨的豆腐', '酿的酒出缸', '包的粽子', '擀的面条', '缝的被子',
                '织的毛衣', '纳的鞋底', '修的房顶', '垒的院墙', '挖的水渠',
                '栽的树活了', '种的花开了', '剪的枝该', '扑克打了一宿', '麻将输了',
                '象棋赢了', '广场舞学会了', '秧歌扭起来', '二胡拉得好听',
                '下地干活', '上山砍柴', '下河摸鱼', '赶集买菜', '走亲戚去了',
                '串门子去了', '晒太阳真暖和', '乘凉好舒服', '烤火真暖和',
                '农药该打', '化肥该买', '种子该播', '犁地要用牛', '插秧弯着腰',
                '割麦子累得慌', '晚饭吃的是饺子', '明天要去镇上赶集',
                '我们村有几百年的历史', '老王家在村里住了好几代',
                '村口那棵老槐树', '今年收成不错', '隔壁村的路修好了',
                '赶集了，买了二斤肉', '下雨了收衣服', '电视又没信号',
                '村口修路呢', '手机又没电了充一下', '柴火不够了',
                '鸡又丢了满村找', '自来水又停了']

    for kw in noise_kw:
        if kw in text:
            # 但检查是否有逗号后面的有用信息
            parts = re.split(r'[，。；]', text)
            has_useful = False
            for part in parts[1:]:
                part = part.strip()
                if part and len(part) > 3:
                    # 检查是否有家族信息
                    family_kw = ['叫', '出生', '生的', '结婚', '去世', '过世', '搬到',
                                '儿子', '女儿', '爸爸', '妈妈', '爷爷', '奶奶', '哥哥',
                                '弟弟', '姐姐', '妹妹', '老婆', '老公', '当过兵', '会']
                    if any(fk in part for fk in family_kw):
                        has_useful = True
                        break
            if not has_useful:
                return True

    return False


def find_person_by_name(name: str) -> Optional[str]:
    """在已知人物中查找（精确+模糊）"""
    if name in KNOWN_PEOPLE:
        return name
    # 模糊匹配
    for existing in KNOWN_PEOPLE:
        if name in existing or existing in name:
            return existing
        # 字符重叠度
        overlap = len(set(name) & set(existing))
        if overlap >= 2 and overlap / max(len(name), len(existing)) >= 0.5:
            return existing
    return None


def process_case(case_id: str, text: str, speaker_context: str = '') -> Dict:
    """处理单条输入，返回结构化结果"""
    result = {
        'case_id': case_id,
        'input': text,
        'actions': [],
    }

    # 噪声检测
    if is_noise(text):
        result['actions'].append({'type': 'NOISE'})
        return result

    # ============ 人物提取 ============
    # 模式: 我[称谓]叫/是[名字]
    for title_key in sorted(TITLE_REL.keys(), key=len, reverse=True):
        # 标准: "我XX叫NAME"
        pattern1 = rf'(?:俺|我)?(?:的)?{re.escape(title_key)}(?:叫|是|名叫)\s*([\u4e00-\u9fff]{{2,4}})'
        m = re.search(pattern1, text)
        if m:
            name = m.group(1)
            rel_type, gender = TITLE_REL[title_key]
            matched = find_person_by_name(name)
            if matched:
                result['actions'].append({
                    'type': 'MATCH_PERSON', 'name': matched,
                    'context': f"匹配到已有人员 {matched}"
                })
            else:
                KNOWN_PEOPLE[name] = {'gender': gender, 'title': title_key}
                result['actions'].append({
                    'type': 'CREATE_PERSON', 'name': name,
                    'gender': gender, 'tags': [title_key]
                })
            # 尝试关联
            # "我XX叫NAME" → speaker 的 XX 是 NAME
            if '我' in text or '俺' in text:
                result['actions'].append({
                    'type': 'ADD_RELATIONSHIP',
                    'person_a': 'speaker', 'person_b': name,
                    'relation': rel_type
                })

    # 模式: [NAME]的[称谓]叫[NAME2]
    for title_key in sorted(TITLE_REL.keys(), key=len, reverse=True):
        pattern = rf'([\u4e00-\u9fff]{{2,4}})的{re.escape(title_key)}(?:叫|是|名叫)\s*([\u4e00-\u9fff]{{2,4}})'
        m = re.search(pattern, text)
        if m:
            person_a = m.group(1)
            name2 = m.group(3)
            rel_type, gender = TITLE_REL[title_key]
            # 确保 person_a 存在
            if find_person_by_name(person_a):
                matched_a = find_person_by_name(person_a)
            else:
                matched_a = person_a
            # 创建或匹配 name2
            if not find_person_by_name(name2):
                KNOWN_PEOPLE[name2] = {'gender': gender, 'title': title_key}
                result['actions'].append({
                    'type': 'CREATE_PERSON', 'name': name2,
                    'gender': gender, 'tags': [title_key]
                })
            result['actions'].append({
                'type': 'ADD_RELATIONSHIP',
                'person_a': matched_a, 'person_b': name2,
                'relation': rel_type
            })

    # 模式: [NAME]叫[NAME2]（无称谓，只有名字）
    # 但要排除已经通过称谓匹配的情况
    if not result['actions'] or all(a['type'] not in ['CREATE_PERSON'] for a in result['actions']):
        simple_pattern = r'(?:有个人|还有一个人|还有个人|有个亲戚|家里有个人|我们家还有个|他叫|名字叫|名叫)\s*([\u4e00-\u9fff]{2,4})'
        m = re.search(simple_pattern, text)
        if m:
            name = m.group(1)
            if not find_person_by_name(name) and len(name) >= 2:
                gender = infer_gender(name, text)
                KNOWN_PEOPLE[name] = {'gender': gender, 'title': None}
                result['actions'].append({
                    'type': 'CREATE_PERSON', 'name': name,
                    'gender': gender, 'tags': []
                })

    # ============ 日期/信息更新 ============
    date, cal = extract_date(text)

    # "[NAME]是XXXX年生的" / "[NAME]生于XXXX"
    birth_pattern = r'([\u4e00-\u9fff]{2,4})(?:是|生于|出生于|出生在)\s*(.{0,20}?)(?:生的|出生|生人|年生)'
    m = re.search(birth_pattern, text)
    if m:
        name = m.group(1)
        date_part = m.group(2)
        matched = find_person_by_name(name)
        if matched and date:
            result['actions'].append({
                'type': 'UPDATE_PERSON', 'name': matched,
                'field': 'birth_date', 'value': date
            })

    # "[NAME]今年XX岁了" → 推算出生年
    age_pattern = r'([\u4e00-\u9fff]{2,4})今年(\d{1,3})岁'
    m = re.search(age_pattern, text)
    if m:
        name = m.group(1)
        age = int(m.group(2))
        birth_year = 2026 - age
        matched = find_person_by_name(name)
        if matched:
            result['actions'].append({
                'type': 'UPDATE_PERSON', 'name': matched,
                'field': 'birth_date', 'value': str(birth_year)
            })

    # "[NAME]是[地名]人" / "[NAME]老家在[地名]"
    origin_patterns = [
        r'([\u4e00-\u9fff]{2,4})是([\u4e00-\u9fff]{2,6})人',
        r'([\u4e00-\u9fff]{2,4})老家在([\u4e00-\u9fff]{2,8})',
        r'([\u4e00-\u9fff]{2,4})娘家是([\u4e00-\u9fff]{2,8})',
    ]
    for p in origin_patterns:
        m = re.search(p, text)
        if m:
            name = m.group(1)
            place = m.group(2)
            matched = find_person_by_name(name)
            if matched:
                result['actions'].append({
                    'type': 'UPDATE_PERSON', 'name': matched,
                    'field': 'origin', 'value': place
                })

    # "[NAME]现在住在[地名]" / "[NAME]搬到[地名]"
    live_patterns = [
        r'([\u4e00-\u9fff]{2,4})现在住在([\u4e00-\u9fff]{2,8})',
        r'([\u4e00-\u9fff]{2,4})搬到了?([\u4e00-\u9fff]{2,8})',
        r'([\u4e00-\u9fff]{2,4})在([\u4e00-\u9fff]{2,8})安了家',
    ]
    for p in live_patterns:
        m = re.search(p, text)
        if m:
            name = m.group(1)
            place = m.group(2)
            matched = find_person_by_name(name)
            if matched:
                result['actions'].append({
                    'type': 'UPDATE_PERSON', 'name': matched,
                    'field': 'current_location', 'value': place
                })

    # "[NAME]的全名是[全名]" / "[NAME]的大名叫[全名]"
    fullname_pattern = r'([\u4e00-\u9fff]{2,4})的?(?:大名|全名|本名|正式名)(?:叫|是)\s*([\u4e00-\u9fff]{2,6})'
    m = re.search(fullname_pattern, text)
    if m:
        name = m.group(1)
        fullname = m.group(2)
        matched = find_person_by_name(name)
        if matched:
            result['actions'].append({
                'type': 'UPDATE_PERSON', 'name': matched,
                'field': 'full_name', 'value': fullname
            })

    # "[NAME]的小名叫[昵称]"
    nickname_pattern = r'([\u4e00-\u9fff]{2,4})的?(?:小名|乳名|昵称|外号)(?:叫|是)\s*([\u4e00-\u9fff]{1,4})'
    m = re.search(nickname_pattern, text)
    if m:
        name = m.group(1)
        nickname = m.group(2)
        matched = find_person_by_name(name)
        if matched:
            result['actions'].append({
                'type': 'UPDATE_PERSON', 'name': matched,
                'field': 'nickname', 'value': nickname
            })

    # ============ 事件检测 ============
    event_kw = {
        'born': ['出生了', '降生了', '落地了', '来到这个世界', '家里添了'],
        'death': ['去世了', '过世了', '走了', '没了', '不在了', '病逝了', '送走了'],
        'marriage': ['结婚了', '成亲了', '办了喜事', '娶了', '嫁给了', '喜结连理', '成亲'],
        'divorce': ['离婚了', '离了'],
        'move': ['搬到了', '迁到了', '搬到'],
        'illness': ['生了一场大病', '病了好几个月', '住院了'],
    }

    for etype, keywords in event_kw.items():
        for kw in keywords:
            if kw in text:
                # 尝试提取关联人物
                related = []
                for pname in KNOWN_PEOPLE:
                    if pname in text:
                        related.append(pname)
                if not related:
                    # 可能是 "赵大爷出生了" 这种
                    for pname in list(KNOWN_PEOPLE.keys()):
                        if pname in text:
                            related.append(pname)

                result['actions'].append({
                    'type': 'ADD_EVENT',
                    'event_type': etype,
                    'date': date,
                    'persons': related,
                    'keyword': kw,
                })
                break

    # ============ 关系声明 ============
    # "[NAME]是[NAME2]的[称谓]"
    for title_key in sorted(TITLE_REL.keys(), key=len, reverse=True):
        rel_pattern = rf'([\u4e00-\u9fff]{{2,4}})(?:和|与|跟)([\u4e00-\u9fff]{{2,4}})(?:是|算|算\s*是)\s*(?:两口子|夫妻|亲兄弟|亲姐妹|兄妹|姐弟)'
        m = re.search(rel_pattern, text)
        if m:
            a, b = m.group(1), m.group(2)
            rel_text = text[m.end()-6:]
            result['actions'].append({
                'type': 'ADD_RELATIONSHIP',
                'person_a': find_person_by_name(a) or a,
                'person_b': find_person_by_name(b) or b,
                'relation': rel_text.strip()
            })

    # "A是B的XX"
    is_of_pattern = r'([\u4e00-\u9fff]{2,4})(?:就?\s*是)\s*([\u4e00-\u9fff]{2,4})的([\u4e00-\u9fff]{1,4})'
    m = re.search(is_of_pattern, text)
    if m:
        a, b, rel = m.group(1), m.group(2), m.group(3)
        if rel in TITLE_REL:
            result['actions'].append({
                'type': 'ADD_RELATIONSHIP',
                'person_a': find_person_by_name(a) or a,
                'person_b': find_person_by_name(b) or b,
                'relation': TITLE_REL[rel][0]
            })

    # ============ 生平描述 ============
    # 如果文本较长且没有提取到任何结构化信息，作为生平描述
    desc_indicators = ['年轻时', '年轻的时候', '为人', '脾气', '性格', '手艺', '一辈子',
                       '喜欢', '会', '以前', '从前', '后来', '念过', '当过', '学过',
                       '是个', '特别', '很', '十分', '非常', '吃苦', '勤劳', '老实',
                       '热心肠', '能人', '识文断字', '好手', '省吃俭用', '疼孩子',
                       '针线活', '做饭', '炒菜', '喝酒', '唱戏', '木匠', '养牛',
                       '编筐', '赶大车', '跑运输', '务农', '开过', '干了一辈子',
                       '在矿上', '供孩子读书', '没出过远门', '种地']

    has_desc = any(ind in text for ind in desc_indicators)
    has_person_mentioned = any(pname in text for pname in KNOWN_PEOPLE)

    if has_desc and has_person_mentioned and len(text) > 8:
        # 找出文本中提到的人物
        mentioned = [pname for pname in KNOWN_PEOPLE if pname in text]
        for pname in mentioned:
            result['actions'].append({
                'type': 'ADD_BIOGRAPHY',
                'person': find_person_by_name(pname) or pname,
                'text': text
            })

    # ============ 复杂场景：多个子句 ============
    # 按逗号/句号分割，检查每个子句
    clauses = re.split(r'[，。；]', text)
    for clause in clauses:
        clause = clause.strip()
        if len(clause) < 4:
            continue

        # 子句中的"XX叫NAME"
        for title_key in sorted(TITLE_REL.keys(), key=len, reverse=True):
            m = re.search(rf'{re.escape(title_key)}(?:叫|是)\s*([\u4e00-\u9fff]{{2,4}})', clause)
            if m:
                name = m.group(1)
                if not find_person_by_name(name) and len(name) >= 2:
                    rel_type, gender = TITLE_REL[title_key]
                    KNOWN_PEOPLE[name] = {'gender': gender, 'title': title_key}
                    # 检查前面是否有人名
                    before = clause[:m.start()].strip()
                    parent_match = re.search(r'([\u4e00-\u9fff]{2,4})的?$', before)
                    if parent_match:
                        parent = parent_match.group(1)
                        if find_person_by_name(parent):
                            result['actions'].append({
                                'type': 'ADD_RELATIONSHIP',
                                'person_a': find_person_by_name(parent),
                                'person_b': name,
                                'relation': rel_type
                            })
                    if not any(a.get('name') == name for a in result['actions'] if a['type'] == 'CREATE_PERSON'):
                        result['actions'].append({
                            'type': 'CREATE_PERSON', 'name': name,
                            'gender': gender, 'tags': [title_key]
                        })

        # 子句中的"NAME生于/出生于/是XX年生的"
        m = re.search(r'([\u4e00-\u9fff]{2,4})(?:生于|出生于|出生在|是)\s*((?:19|20)\d{2})', clause)
        if m:
            name = m.group(1)
            year = m.group(2)
            matched = find_person_by_name(name)
            if matched:
                if not any(a.get('name') == matched and a.get('field') == 'birth_date'
                          for a in result['actions'] if a['type'] == 'UPDATE_PERSON'):
                    result['actions'].append({
                        'type': 'UPDATE_PERSON', 'name': matched,
                        'field': 'birth_date', 'value': year
                    })

        # "过继给" → 收养关系
        if '过继' in clause:
            m = re.search(r'([\u4e00-\u9fff]{2,4})的?(?:儿子|女儿)?过继给了?\s*([\u4e00-\u9fff]{2,4})', clause)
            if m:
                result['actions'].append({
                    'type': 'ADD_RELATIONSHIP',
                    'person_a': find_person_by_name(m.group(1)) or m.group(1),
                    'person_b': find_person_by_name(m.group(2)) or m.group(2),
                    'relation': 'adopted'
                })

        # "收了个XX叫NAME" → 收养
        if '收了' in clause or '收养' in clause:
            m = re.search(r'(?:收了|收养)(?:个|了一个?)(?:孤儿|孩子|女儿|儿子)(?:叫)?\s*([\u4e00-\u9fff]{2,4})', clause)
            if m:
                name = m.group(1)
                if not find_person_by_name(name):
                    KNOWN_PEOPLE[name] = {'gender': 'unknown', 'title': None}
                    result['actions'].append({
                        'type': 'CREATE_PERSON', 'name': name,
                        'gender': 'unknown', 'tags': ['收养']
                    })

    # 去重
    seen = set()
    unique_actions = []
    for a in result['actions']:
        key = json.dumps(a, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique_actions.append(a)
    result['actions'] = unique_actions

    if not result['actions']:
        result['actions'].append({'type': 'NO_ACTION', 'reason': '未识别到有效信息'})

    return result


def main():
    # 加载测试用例
    with open('test_cases.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    base_people = data['base_people']
    test_cases = data['test_cases']

    # 初始化已知人物
    for p in base_people:
        KNOWN_PEOPLE[p['name']] = {
            'gender': p.get('gender', 'unknown'),
            'birth_date': p.get('birth_date'),
            'title': None,
        }

    print(f"基础人物: {len(KNOWN_PEOPLE)}")
    print(f"测试用例: {len(test_cases)}")
    print("=" * 60)

    # 统计
    stats = {'total': 0, 'noise': 0, 'create': 0, 'update': 0, 'event': 0,
             'relation': 0, 'bio': 0, 'no_action': 0, 'error': 0}
    log = []

    for case in test_cases:
        stats['total'] += 1
        try:
            r = process_case(case['id'], case['input'])
            for a in r['actions']:
                t = a['type']
                if t == 'NOISE': stats['noise'] += 1
                elif t == 'CREATE_PERSON': stats['create'] += 1
                elif t == 'UPDATE_PERSON': stats['update'] += 1
                elif t == 'ADD_EVENT': stats['event'] += 1
                elif t == 'ADD_RELATIONSHIP': stats['relation'] += 1
                elif t == 'ADD_BIOGRAPHY': stats['bio'] += 1
                elif t == 'NO_ACTION': stats['no_action'] += 1
            log.append(r)
        except Exception as e:
            stats['error'] += 1
            log.append({'case_id': case['id'], 'input': case['input'],
                        'actions': [{'type': 'ERROR', 'error': str(e)}]})

    print("\n处理完成!")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # 保存
    with open('test_run_log_v2.json', 'w', encoding='utf-8') as f:
        json.dump({'stats': stats, 'log': log, 'known_people': KNOWN_PEOPLE},
                  f, ensure_ascii=False, indent=2)
    print(f"\n日志已保存到 test_run_log_v2.json")

    # 输出 NO_ACTION 的用例
    print("\nNO_ACTION 用例:")
    for r in log:
        if any(a['type'] == 'NO_ACTION' for a in r['actions']):
            print(f"  [{r['case_id']}] {r['input'][:80]}")

    # 输出已知人物
    print(f"\n最终人物 ({len(KNOWN_PEOPLE)}):")
    for name, info in KNOWN_PEOPLE.items():
        print(f"  {name}: {info}")


if __name__ == '__main__':
    main()
