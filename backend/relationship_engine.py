"""
亲属关系推导引擎
核心思想：路径压缩 + 坐标系称谓生成

链式操作分三类：
  1. 纵向 (ascend/descend) - 纯计数器，不增加规则复杂度
  2. 横向血亲 (sibling/cousin) - 在同代内跳转
  3. 横向姻亲 (spouse) - 通过婚姻连接

称谓 = f(辈分差, 对方性别, 血统路径, 姻亲连接点)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from collections import deque
import json


# ═══════════════════════════════════════════════════════════
# 第一层：原子操作定义
# ═══════════════════════════════════════════════════════════

@dataclass
class AtomicLink:
    """一条原子关系边"""
    op: str                           # ascend / descend / sibling / spouse
    label: str = ""                   # 原始标签（"父亲"、"配偶"等）
    gender: str = "unknown"           # 链接终点的性别
    lineage: str = "blood"            # blood / marriage / adoptive

    def __repr__(self):
        return f"--[{self.op}({'♂' if self.gender=='male' else '♀' if self.gender=='female' else '?'})]-->"


@dataclass
class CompressedStep:
    """压缩后的链步骤"""
    op: str          # ascend / descend / sibling / spouse
    count: int       # 连续次数
    gender: str = "unknown"  # 该步终点的性别（关键：父/母、子/女）
    lineage: str = "blood"

    def __repr__(self):
        if self.count == 1:
            return self.op
        return f"{self.op}×{self.count}"


# ═══════════════════════════════════════════════════════════
# 第二层：路径压缩
# ═══════════════════════════════════════════════════════════

def compress_chain(chain: List[AtomicLink]) -> List[CompressedStep]:
    """
    将原始链压缩为压缩链

    规则：相同 op 且相同 gender 才能连续压缩
    ascend(♂) → ascend(♂) → ascend×2
    ascend(♀) → ascend(♂) → ascend(♀), ascend(♂) （不同性别不合并）
    """
    if not chain:
        return []

    compressed = []
    run_op = None
    run_count = 0
    run_gender = "unknown"
    run_lineage = "blood"

    for link in chain:
        compressible = link.op in ("ascend", "descend")

        # 只有 op 和 gender 都相同时才合并
        if compressible and link.op == run_op and link.gender == run_gender:
            run_count += 1
        else:
            if run_op:
                compressed.append(CompressedStep(
                    op=run_op, count=run_count,
                    gender=run_gender, lineage=run_lineage
                ))
            run_op = link.op
            run_count = 1
            run_gender = link.gender
            run_lineage = link.lineage

    if run_op:
        compressed.append(CompressedStep(
            op=run_op, count=run_count,
            gender=run_gender, lineage=run_lineage
        ))

    return compressed


def chain_to_string(chain: List[AtomicLink]) -> str:
    """链转可读字符串"""
    return " → ".join(f"{l.op}({l.gender})" for l in chain)


def compressed_to_string(cchain: List[CompressedStep]) -> str:
    """压缩链转可读字符串"""
    return " → ".join(
        f"{s.op}×{s.count}" if s.count > 1 else s.op
        for s in cchain
    )


# ═══════════════════════════════════════════════════════════
# 第三层：辈分词表（静态，纵向深度无关规则数）
# ═══════════════════════════════════════════════════════════

# 上溯辈分词（generation → (对男性称, 对女性称)）
ANCESTOR_TERMS = {
    1: ("父亲", "母亲"),
    2: ("祖父", "祖母"),
    3: ("曾祖父", "曾祖母"),
    4: ("高祖父", "高祖母"),
    5: ("天祖父", "天祖母"),
    6: ("烈祖父", "烈祖母"),
    7: ("太祖父", "太祖母"),
    8: ("远祖父", "远祖母"),
    9: ("鼻祖父", "鼻祖母"),
}
# 超过9代 → "X世祖"

# 下溯辈分词
DESCENDANT_TERMS = {
    1: ("儿子", "女儿"),
    2: ("孙子", "孙女"),
    3: ("曾孙", "曾孙女"),
    4: ("玄孙", "玄孙女"),
    5: ("来孙", "来孙女"),
    6: ("晜孙", "晜孙女"),
    7: ("仍孙", "仍孙女"),
    8: ("云孙", "云孙女"),
    9: ("耳孙", "耳孙女"),
}
# 超过9代 → "X世孙"


# ═══════════════════════════════════════════════════════════
# 第四层：横向关系映射（静态表）
# ═══════════════════════════════════════════════════════════

def _sibling_term(gen_up: int, sib_gender: str, is_paternal: bool,
                   through_parent_gender: str) -> str:
    """
    同辈兄弟姐妹称谓
    gen_up: 往上几辈到达共同祖先
    sib_gender: 兄弟姐妹性别
    is_paternal: 是否父系
    through_parent_gender: 通过的父亲还是母亲到达共同祖先
    """
    if gen_up == 0:
        # 同父母的兄弟姐妹
        if sib_gender == "male":
            return "哥哥"  # 简化，实际需比年龄
        return "姐姐"

    if gen_up == 1:
        # 父母的兄弟姐妹的孩子 = 堂/表兄弟姐妹
        if is_paternal:
            # 父亲的兄弟的孩子
            if sib_gender == "male":
                return "堂兄弟"
            return "堂姐妹"
        else:
            # 父亲的姐妹 或 母亲的兄弟姐妹 的孩子
            if sib_gender == "male":
                return "表兄弟"
            return "表姐妹"

    # 更远的同辈
    if sib_gender == "male":
        return f"族兄弟(往上{gen_up}辈)"
    return f"族姐妹(往上{gen_up}辈)"


# ═══════════════════════════════════════════════════════════
# 第五层：核心称谓生成引擎
# ═══════════════════════════════════════════════════════════

class KinshipEngine:
    """
    亲属关系推导引擎

    用法：
        engine = KinshipEngine()
        engine.add_link("我", "爸爸", "ascend", "male")
        engine.add_link("爸爸", "爷爷", "ascend", "male")
        engine.add_link("爷爷", "叔爷爷", "sibling", "male")
        engine.add_link("叔爷爷", "叔奶奶", "spouse", "female")

        label = engine.resolve("我", "叔奶奶")
        # → "叔奶奶" (ascend×2 → sibling → spouse)
    """

    def __init__(self):
        # 邻接表: person -> [(target_person, AtomicLink)]
        self.graph: Dict[str, List[Tuple[str, AtomicLink]]] = {}
        # 所有人物信息
        self.persons: Dict[str, Dict] = {}
        # 直接标签缓存
        self.direct_labels: Dict[Tuple[str, str], str] = {}

    def add_person(self, name: str, gender: str = "unknown"):
        """添加人物（已有则仅更新缺失字段）"""
        if name not in self.graph:
            self.graph[name] = []
        if name not in self.persons:
            self.persons[name] = {"name": name, "gender": gender}
        elif gender != "unknown":
            # 仅在提供非默认值时更新
            self.persons[name]["gender"] = gender

    def add_link(self, person_a: str, person_b: str,
                 op: str, gender_b: str = "unknown",
                 label: str = "", lineage: str = "blood"):
        """
        添加一条关系边（自动存储双向）

        op: 从 A 到 B 的方向
            ascend(从A到B，B在上方) / descend(从A到B，B在下方)
            sibling / spouse
        """
        self.add_person(person_a)
        self.add_person(person_b)

        # 正向: A → B
        link_ab = AtomicLink(op=op, label=label, gender=gender_b, lineage=lineage)
        self.graph[person_a].append((person_b, link_ab))

        # 反向: B → A（操作取反，gender 取 A 的性别）
        rev_op = {"ascend": "descend", "descend": "ascend",
                  "sibling": "sibling", "spouse": "spouse"}.get(op, op)
        gender_a = self.persons.get(person_a, {}).get("gender", "unknown")
        link_ba = AtomicLink(op=rev_op, label=label, gender=gender_a, lineage=lineage)
        self.graph[person_b].append((person_a, link_ba))

    def add_direct_label(self, person_a: str, person_b: str, label: str):
        """添加直接称谓（当无法推导时使用）"""
        self.direct_labels[(person_a, person_b)] = label

    # ─────────────────────────────────────────────────
    # BFS 路径查找
    # ─────────────────────────────────────────────────

    def _get_all_adjacent(self, person: str) -> List[Tuple[str, AtomicLink]]:
        """获取某人的所有相邻节点（add_link 已存储双向，直接返回）"""
        return list(self.graph.get(person, []))

    def find_path(self, start: str, end: str,
                  max_depth: int = 10) -> Optional[List[AtomicLink]]:
        """
        找最优路径（语义加权 Dijkstra）

        权重：ascend=1, sibling=2, spouse=3, descend=4
        """
        if start == end:
            return []

        WEIGHTS = {"ascend": 1, "sibling": 2, "spouse": 3, "descend": 4}

        visited = {}
        import heapq
        heap = [(0, 0, start, [])]  # (cost, tiebreaker, node, path)
        counter = [0]

        while heap:
            cost, _, current, path = heapq.heappop(heap)

            if len(path) >= max_depth:
                continue

            if current in visited:
                continue
            visited[current] = True

            if current == end and path:
                return path

            for neighbor, link in self.graph.get(current, []):
                if neighbor in visited:
                    continue
                edge_weight = WEIGHTS.get(link.op, 5)
                new_cost = cost + edge_weight
                new_path = path + [link]
                counter[0] += 1
                heapq.heappush(heap, (new_cost, counter[0], neighbor, new_path))

        return None

    # ─────────────────────────────────────────────────
    # 链路分析
    # ─────────────────────────────────────────────────

    def analyze_chain(self, chain: List[AtomicLink]) -> Dict:
        """
        分析链路特征，增加血统追踪
        """
        compressed = compress_chain(chain)

        num_ascend = sum(s.count for s in compressed if s.op == "ascend")
        num_descend = sum(s.count for s in compressed if s.op == "descend")
        gen_diff = num_ascend - num_descend
        lateral_ops = [s for s in compressed if s.op in ("sibling", "spouse")]
        other_gender = compressed[-1].gender if compressed else "unknown"

        # 血统追踪：从 speaker 出发，沿 ascend 链追踪父系/母系
        # 规则：第一个 ascend 的性别决定血统
        #   ascend(♂) → 父系（去了父亲那边）
        #   ascend(♀) → 母系（去了母亲那边）
        # 后续 ascend 不改变血统（在同一条血统线上）
        lineage = "unknown"
        turning_gen = 0
        ascend_so_far = 0
        for s in compressed:
            if s.op == "ascend":
                prev_ascend = ascend_so_far
                ascend_so_far += s.count
                # 如果之前没有 ascend（prev==0），第一个 ascend 决定血统
                if lineage == "unknown" and prev_ascend == 0:
                    lineage = "paternal" if s.gender == "male" else "maternal"
                # 记录特殊血缘属性（养、干等）
                if s.lineage != "blood":
                    final_lineage_type = s.lineage
            elif s.op == "sibling":
                turning_gen = ascend_so_far
                if lineage == "unknown":
                    lineage = "paternal" if s.gender == "male" else "maternal"
                if s.lineage != "blood":
                    final_lineage_type = s.lineage
            elif s.op == "spouse":
                turning_gen = ascend_so_far

        is_paternal = lineage == "paternal"

        return {
            "gen_diff": gen_diff,
            "compressed": compressed,
            "num_hops": len(chain),
            "num_ascend": num_ascend,
            "num_descend": num_descend,
            "num_lateral": len(lateral_ops),
            "lateral_ops": [s.op for s in lateral_ops],
            "is_paternal": is_paternal,
            "lineage": lineage,
            "turning_gen": turning_gen,
            "other_gender": other_gender,
            "lineage_type": final_lineage_type if 'final_lineage_type' in locals() else "blood"
        }

    # ─────────────────────────────────────────────────
    # 称谓生成
    # ─────────────────────────────────────────────────

    def generate_label(self, chain: List[AtomicLink]) -> str:
        """
        从链路生成中文称谓
        """
        if not chain:
            return "自己"

        # 如果是单跳且有自定义标签，优先使用
        if len(chain) == 1 and chain[0].label:
            return chain[0].label

        analysis = self.analyze_chain(chain)
        compressed = analysis["compressed"]
        gen_diff = analysis["gen_diff"]
        other_gender = analysis["other_gender"]
        num_lateral = analysis["num_lateral"]
        lineage = analysis.get("lineage", "unknown")
        lineage_type = analysis.get("lineage_type", "blood")

        # ── 情况1: 纯纵向链（只有 ascend/descend，无 sibling/spouse）──
        if num_lateral == 0 or (num_lateral > 0 and not any(s.op in ("sibling","spouse") for s in compressed)):
            # 重算 gen_diff（只看 ascend/descend）
            pure_gen_diff = sum(s.count if s.op == "ascend" else -s.count for s in compressed)
            # 对于纯 descend 链，通过首跳性别判断母系
            if pure_gen_diff < 0 and compressed and compressed[0].op == "descend":
                if compressed[0].gender == "female":
                    lineage = "maternal"
            return self._pure_vertical_label(pure_gen_diff, other_gender, lineage, lineage_type)

        # ── 情况2: ascend → sibling（父/母的兄弟姐妹）──
        if (num_lateral == 1 and compressed[-1].op == "sibling"
            and all(s.op == "ascend" for s in compressed[:-1])):
            ascend_n = analysis["num_ascend"]
            sib_gender = compressed[-1].gender
            return self._sibling_label(ascend_n, sib_gender, lineage == "paternal")

        # ── 情况3: ascend → sibling → spouse ──
        if (len(compressed) >= 3
            and compressed[-1].op == "spouse"
            and compressed[-2].op == "sibling"
            and all(s.op == "ascend" for s in compressed[:-2])):
            ascend_n = analysis["num_ascend"]
            sib_gender = compressed[-2].gender
            return self._sibling_spouse_label(ascend_n, sib_gender, lineage == "paternal")

        # ── 情况4: ascend → sibling → descend（堂/表关系）──
        if (len(compressed) == 3
            and compressed[0].op == "ascend"
            and compressed[1].op == "sibling"
            and compressed[2].op == "descend"):
            ascend_n = compressed[0].count
            sib_gender = compressed[1].gender
            descend_n = compressed[2].count
            descend_gender = compressed[2].gender
            is_paternal = lineage == "paternal"

            if ascend_n == descend_n:
                # 上下对称 = 同辈堂/表兄弟姐妹
                if is_paternal and sib_gender == "male":
                    prefix = "堂"
                else:
                    prefix = "表"
                if descend_gender == "male":
                    return f"{prefix}兄弟"
                return f"{prefix}姐妹"
            elif ascend_n == 1 and descend_n == 1:
                # 兄弟的孩子（不对称路径的情况）
                if is_paternal and sib_gender == "male":
                    return "侄子" if descend_gender == "male" else "侄女"
                else:
                    return "外甥" if descend_gender == "male" else "外甥女"
            # 其他 descend 数量
            cousin_prefix = "堂" if (is_paternal and sib_gender == "male") else "表"
            desc_term = self._pure_vertical_label(-descend_n, descend_gender, lineage)
            return f"{cousin_prefix}{desc_term}"

        # ── 情况5: ascend → sibling → ascend（同辈堂/表兄弟姐妹）──
        if (len(compressed) == 3
            and compressed[0].op == "ascend"
            and compressed[1].op == "sibling"
            and compressed[2].op == "ascend"):
            ascend_n = compressed[0].count
            sib_gender = compressed[1].gender
            is_paternal = lineage == "paternal"

            if ascend_n == 1:
                # 叔叔/姑姑/舅舅的子女 = 堂/表兄弟姐妹
                if is_paternal and sib_gender == "male":
                    prefix = "堂"
                else:
                    prefix = "表"
                return f"{prefix}兄弟"  # 简化，实际应区分兄弟/姐妹
            return "族兄弟"

        # ── 情况6: ascend × N → spouse（祖先的配偶）──
        if (len(compressed) == 2
            and compressed[0].op == "ascend"
            and compressed[1].op == "spouse"):
            ascend_n = compressed[0].count
            return self._ancestor_spouse_label(ascend_n, lineage)

        # ── 情况7: ascend → ascend → spouse（爷爷的配偶=奶奶）──
        if (len(compressed) >= 3
            and all(s.op == "ascend" for s in compressed[:-1])
            and compressed[-1].op == "spouse"):
            ascend_n = sum(s.count for s in compressed[:-1])
            return self._ancestor_spouse_label(ascend_n, lineage)

        # ── 情况8: sibling → descend（兄弟姐妹的晚辈）──
        if (len(compressed) == 2
            and compressed[0].op == "sibling"
            and compressed[1].op == "descend"):
            descend_gender = compressed[1].gender
            descend_n = compressed[1].count

            # 关键：sibling 的 gender 是链中"对方"的性别
            # 要判断是兄弟还是姐妹，需要看 lineage
            # 如果 lineage 是 paternal 且 sibling gender 是 male → 爸爸的兄弟 → 叔叔的侄
            # 如果 lineage 是 paternal 且 sibling gender 是 female → 爸爸的姐妹 → 姑姑的外甥
            # lineage unknown 时，用 sibling gender 判断
            is_brother = compressed[0].gender == "male"

            if is_brother:
                if descend_gender == "male":
                    return "侄子" if descend_n == 1 else f"侄{'孙'*(descend_n-1)}"
                return "侄女"
            else:
                if descend_gender == "male":
                    return "外甥"
                return "外甥女"

        # ── 情况9: spouse → descend（配偶的晚辈）──
        if (len(compressed) >= 2
            and compressed[0].op == "spouse"
            and all(s.op == "descend" for s in compressed[1:])):
            descend_n = sum(s.count for s in compressed[1:])
            descend_gender = compressed[-1].gender
            # descend 链首跳性别决定血统
            first_desc_gender = compressed[1].gender if len(compressed) > 1 else "unknown"
            effective_lineage = "maternal" if first_desc_gender == "female" else lineage
            return self._pure_vertical_label(-descend_n, descend_gender, effective_lineage, lineage_type)

        # ── 情况10: spouse → sibling → descend（配偶的兄弟姐妹的子女）──
        if (len(compressed) == 3
            and compressed[0].op == "spouse"
            and compressed[1].op == "sibling"
            and compressed[2].op == "descend"):
            # 配偶的兄弟姐妹的孩子 → 外甥/外甥女
            descend_gender = compressed[2].gender
            return "外甥" if descend_gender == "male" else "外甥女"

        # ── 情况11: descend（纯下溯）──
        if num_lateral == 0 and gen_diff < 0:
            # 判断母系：如果第一个 descend 通过女性
            if compressed and compressed[0].gender == "female":
                lineage = "maternal"
            return self._pure_vertical_label(gen_diff, other_gender, lineage, lineage_type)

        # 兜底
        return self._complex_label(chain, analysis)

    def _pure_vertical_label(self, gen_diff: int, gender: str, lineage: str = "unknown", lineage_type: str = "blood") -> str:
        """纯纵向称谓，区分父系/母系"""
        if gen_diff == 0:
            return "自己"

        prefix = ""
        if lineage_type == "adoptive":
            prefix = "养"
        elif lineage_type == "god":
            prefix = "干"
        elif lineage_type == "step":
            prefix = "继"


        if gen_diff > 0:
            # 对方辈分更高（祖先）
            if gen_diff == 1:
                if gender == "male":
                    return prefix + "父亲" if prefix else "父亲"
                return prefix + "母亲" if prefix else "母亲"
            if gen_diff == 2:
                if lineage == "maternal":
                    return prefix + "外公" if prefix else "外公"
                return prefix + "爷爷" if prefix else "爷爷"
            if gen_diff == 3:
                prefix = "外" if lineage == "maternal" else ""
                if gender == "male":
                    return f"{prefix}曾祖父" if prefix else "曾祖父"
                return f"{prefix}曾祖母" if prefix else "曾祖母"
            terms = ANCESTOR_TERMS.get(gen_diff)
            if terms:
                return terms[0] if gender == "male" else terms[1]
            return f"{'高' * (gen_diff - 4)}祖（{gen_diff}世祖）"

        else:
            # 对方辈分更低（后代）
            n = abs(gen_diff)
            if n == 1:
                return "儿子" if gender == "male" else "女儿"
            if n == 2:
                if lineage == "maternal":
                    return "外孙" if gender == "male" else "外孙女"
                return "孙子" if gender == "male" else "孙女"
            terms = DESCENDANT_TERMS.get(n)
            if terms:
                return terms[0] if gender == "male" else terms[1]
            return f"{'玄' * (n - 4)}孙（{n}世孙）"

    def _ancestor_spouse_label(self, ascend_n: int, lineage: str = "unknown") -> str:
        """
        祖先的配偶称谓
        ascend=2 + spouse = 祖母/外祖母
        ascend=3 + spouse = 曾祖母/外曾祖母
        """
        if ascend_n == 2:
            return "外祖母" if lineage == "maternal" else "祖母"
        if ascend_n == 3:
            return "外曾祖母" if lineage == "maternal" else "曾祖母"
        base = self._pure_vertical_label(ascend_n, "male", lineage)
        return f"{base}的配偶"

    def _sibling_label(self, ascend_n: int, sib_gender: str,
                       is_paternal: bool) -> str:
        """
        上溯N辈后的兄弟姐妹称谓

        ascend=1 + sibling(♂) = 兄弟
        ascend=1 + sibling(♀) = 姐妹
        ascend=2 + sibling(♂) = 如果父系→叔伯，母系→舅
        ascend=2 + sibling(♀) = 如果父系→姑，母系→姨
        """
        male = sib_gender == "male"

        if ascend_n == 0:
            return "哥哥" if male else "姐姐"

        if ascend_n == 1:
            # 父/母的兄弟姐妹
            if is_paternal:
                return "叔叔" if male else "姑姑"
            else:
                return "舅舅" if male else "姨妈"

        if ascend_n == 2:
            # 祖父/祖母的兄弟姐妹
            if is_paternal:
                return ("爷爷的兄弟" if male else "爷爷的姐妹")  # 简化
            else:
                return ("外公的兄弟" if male else "外婆的姐妹")

        # 更远：往上N辈的同辈亲属
        ancestor = self._pure_vertical_label(ascend_n, "male" if is_paternal else "female")
        relation = "兄弟" if male else "姐妹"
        return f"{ancestor}的{relation}"

    def _sibling_spouse_label(self, ascend_n: int, sib_gender: str,
                               is_paternal: bool) -> str:
        """
        上溯N辈 → sibling → spouse

        ascend=1 + sibling(♂) + spouse = 婶婶/伯母/舅妈
        ascend=1 + sibling(♀) + spouse = 姑父/姨父
        """
        male = sib_gender == "male"

        if ascend_n == 1:
            if is_paternal:
                if male:
                    return "婶婶"  # 叔叔的妻子（简化，实际应区分伯母）
                return "姑父"    # 姑姑的丈夫
            else:
                if male:
                    return "舅妈"  # 舅舅的妻子
                return "姨父"    # 姨妈的丈夫

        if ascend_n == 2:
            if is_paternal:
                if male:
                    return "叔奶奶"  # 爷爷的兄弟的妻子
                return "姑爷爷"    # 爷爷的姐妹的丈夫
            else:
                if male:
                    return "舅姥姥"  # 外婆的兄弟的妻子? 外公的兄弟
                return "姨姥姥"    # 外婆的姐妹

        # 更远的
        sib_label = self._sibling_label(ascend_n, sib_gender, is_paternal)
        return f"{sib_label}的配偶"

    def _complex_label(self, chain: List[AtomicLink],
                       analysis: Dict) -> str:
        """
        复杂链的称谓生成

        使用递归分解：
        ascend×N → X → descend×M 可以分解为两段
        """
        compressed = analysis["compressed"]

        # 模式: ascend → sibling → descend (堂/表侄辈)
        if (len(compressed) == 3
            and compressed[0].op == "ascend"
            and compressed[1].op == "sibling"
            and compressed[2].op == "descend"):
            up = compressed[0].count
            sib_g = compressed[1].gender
            down = compressed[2].count
            down_g = compressed[2].gender
            is_pat = compressed[0].gender == "male"

            # 父亲的兄弟的儿子 = 堂兄弟 (已经通过 sibling 处理了)
            # 这里处理: 叔叔的儿子的儿子 = 堂侄
            sib = self._sibling_label(up, sib_g, is_pat)
            desc = self._pure_vertical_label(-down, down_g)
            return f"{sib}的{desc}"

        # 模式: ascend → sibling → spouse → descend (叔奶奶的孙子等)
        if (len(compressed) >= 4
            and compressed[0].op == "ascend"
            and compressed[1].op == "sibling"
            and compressed[2].op == "spouse"):
            up = compressed[0].count
            sib_g = compressed[1].gender
            is_pat = compressed[0].gender == "male"
            sib_sp = self._sibling_spouse_label(up, sib_g, is_pat)

            remaining = compressed[3:]
            if remaining and remaining[0].op == "descend":
                down = remaining[0].count
                down_g = remaining[0].gender
                desc = self._pure_vertical_label(-down, down_g)
                return f"{sib_sp}的{desc}"

        # 兜底：拼接各段
        parts = []
        for s in compressed:
            if s.op == "ascend":
                parts.append(self._pure_vertical_label(s.count, s.gender))
            elif s.op == "descend":
                parts.append(self._pure_vertical_label(-s.count, s.gender))
            elif s.op == "sibling":
                parts.append(s.label if s.label else ("兄弟" if s.gender == "male" else "姐妹"))
            elif s.op == "spouse":
                parts.append(s.label if s.label else "配偶")

        return "的".join(parts) if parts else "亲戚"

    # ─────────────────────────────────────────────────
    # 对外接口
    # ─────────────────────────────────────────────────

    def resolve(self, person_a: str, person_b: str) -> Dict:
        """
        解析 A 对 B 的称谓

        返回:
        {
            "label": "叔奶奶",
            "source": "derived",       # derived / direct / unknown
            "path": [...],             # 原子链路
            "compressed": [...],       # 压缩链路
            "analysis": {...},         # 链路分析
        }
        """
        # 1. 先查直接标签
        if (person_a, person_b) in self.direct_labels:
            label = self.direct_labels[(person_a, person_b)]
            return {
                "label": label,
                "source": "direct",
                "path": [],
                "compressed": [],
                "analysis": {},
            }

        # 2. 找多条候选路径，选最优的
        best_result = self._find_best_path(person_a, person_b)
        if best_result:
            return best_result

        return {
            "label": "未知",
            "source": "unknown",
            "path": [],
            "compressed": [],
            "analysis": {},
        }

    def _find_best_path(self, start: str, end: str) -> Optional[Dict]:
        """
        找最优路径：跑两轮 Dijkstra，选最优

        第一轮：ascend优先（权重 ascend=1, sibling=2, spouse=3, descend=4）
        第二轮：sibling优先（权重 sibling=1, ascend=2, spouse=3, descend=4）
        合并候选，选 descends 最少的
        """
        all_paths = []

        # 第一轮：ascend 优先
        p1 = self.find_path(start, end)
        if p1:
            all_paths.append(p1)

        # 第二轮：sibling 优先（交换权重）
        p2 = self._dijkstra(start, end, weights={"sibling":1,"ascend":2,"spouse":3,"descend":4})
        if p2:
            all_paths.append(p2)

        # 第三轮：直接 DFS 全枚举（限制小图）
        p3_list = self._dfs_all(start, end, max_depth=5, max_paths=30)
        all_paths.extend(p3_list)

        if not all_paths:
            return None

        # 去重（按压缩链去重）
        seen = set()
        unique = []
        for p in all_paths:
            key = tuple((lk.op, lk.gender) for lk in p)
            if key not in seen:
                seen.add(key)
                unique.append(p)

        # 评分
        # 规则：
        # 1. 对于同辈(gen_diff=0)：强烈偏好对称路径（ascend==descend > 0）
        # 2. 对于非同辈：偏好 descend 少的路径
        # 3. 通用：配偶越少越好
        def score(path):
            compressed = compress_chain(path)
            num_descends = sum(s.count for s in compressed if s.op == "descend")
            num_ascends = sum(s.count for s in compressed if s.op == "ascend")
            num_spouses = sum(1 for s in compressed if s.op == "spouse")
            gen_diff = num_ascends - num_descends

            is_peer = gen_diff == 0
            is_symmetric = is_peer and num_ascends == num_descends and num_ascends > 0

            if is_symmetric:
                # 对称路径（堂/表兄弟）：极低分，最优先
                # 用 hops 区分（越短越好）
                return (-1000 + len(path),)
            elif is_peer:
                # 非对称但同辈（如 ascend→sibling→descend，1↑1↓）：
                # 这种路径给出 侄子/外甥，分数比对称路径高
                return (num_descends * 100 + num_spouses * 10, len(path))
            else:
                # 非同辈：正常评分
                return (num_descends * 100 + num_spouses * 10, len(path))

        unique.sort(key=score)
        best_path = unique[0]

        analysis = self.analyze_chain(best_path)
        label = self.generate_label(best_path)

        return {
            "label": label,
            "source": "derived",
            "path": [{"op": l.op, "gender": l.gender, "label": l.label}
                     for l in best_path],
            "compressed": [str(s) for s in analysis["compressed"]],
            "analysis": {
                "gen_diff": analysis["gen_diff"],
                "num_hops": analysis["num_hops"],
                "is_paternal": analysis["is_paternal"],
                "turning_gen": analysis["turning_gen"],
            },
        }

    def _dijkstra(self, start, end, weights=None, max_depth=10):
        """Dijkstra with custom weights"""
        if weights is None:
            weights = {"ascend": 1, "sibling": 2, "spouse": 3, "descend": 4}
        visited = {}
        import heapq
        heap = [(0, 0, start, [])]
        counter = [0]
        while heap:
            cost, _, current, path = heapq.heappop(heap)
            if len(path) >= max_depth:
                continue
            if current in visited:
                continue
            visited[current] = True
            if current == end and path:
                return path
            for nb, lk in self.graph.get(current, []):
                if nb in visited:
                    continue
                w = weights.get(lk.op, 5)
                counter[0] += 1
                heapq.heappush(heap, (cost+w, counter[0], nb, path+[lk]))
        return None

    def _dfs_all(self, start, end, max_depth=5, max_paths=30):
        """DFS 枚举所有路径（允许通过不同路径到达同一节点）"""
        results = []
        def dfs(cur, path, visited):
            if len(results) >= max_paths:
                return
            if len(path) >= max_depth:
                return
            if cur == end and path:
                results.append(list(path))
                return
            visited.add(cur)
            for nb, lk in self.graph.get(cur, []):
                if nb not in visited:
                    path.append(lk)
                    dfs(nb, path, visited)
                    path.pop()
            visited.remove(cur)
        dfs(start, [], set())
        return results

    def resolve_all(self, person: str) -> Dict[str, Dict]:
        """
        解析某人对所有其他人的称谓

        返回: {"王建国": {"label":"堂兄弟", ...}, ...}
        """
        results = {}
        for other in self.persons:
            if other != person:
                results[other] = self.resolve(person, other)
        return results

    # ─────────────────────────────────────────────────
    # 矛盾检测
    # ─────────────────────────────────────────────────

    def detect_conflicts(self, person_a: str, person_b: str,
                         claimed_label: str) -> Optional[Dict]:
        """
        检测声称的关系是否与推导结果矛盾

        返回 None 表示无矛盾，返回 dict 表示有矛盾
        """
        result = self.resolve(person_a, person_b)

        if result["source"] == "unknown":
            return None  # 无法推导，不矛盾

        derived = result["label"]

        # 简单矛盾检测：性别不匹配
        # 比如推导结果是"叔叔"(male)，但声称的是"姑姑"(female)
        MALE_LABELS = {"父亲","爷爷","祖父","曾祖父","叔叔","伯伯","舅舅","哥哥",
                       "弟弟","堂兄弟","表兄弟","侄子","外甥","儿子","孙子","曾孙",
                       "丈夫","老公","姐夫","妹夫","姑父","姨父","女婿","儿媳"}
        FEMALE_LABELS = {"母亲","奶奶","祖母","曾祖母","姑姑","姨妈","姐姐","妹妹",
                         "堂姐妹","表姐妹","侄女","外甥女","女儿","孙女","曾孙女",
                         "妻子","老婆","嫂子","弟媳","舅妈","婶婶","伯母","儿媳","女婿"}

        claimed_is_male = claimed_label in MALE_LABELS
        claimed_is_female = claimed_label in FEMALE_LABELS
        derived_is_male = derived in MALE_LABELS
        derived_is_female = derived in FEMALE_LABELS

        if (claimed_is_male and derived_is_female) or (claimed_is_female and derived_is_male):
            return {
                "type": "gender_mismatch",
                "claimed": claimed_label,
                "derived": derived,
                "detail": f"声称的'{claimed_label}'与推导的'{derived}'性别不匹配"
            }

        # 辈分矛盾
        if result["analysis"]:
            gen_diff = result["analysis"]["gen_diff"]
            # 声称的是长辈但推导是晚辈（或反过来）
            ELDER_LABELS = {"父亲","母亲","爷爷","奶奶","祖父","祖母","叔叔","姑姑",
                            "舅舅","姨妈","伯伯","婶婶","舅妈","姑父","姨父","伯母"}
            YOUNGER_LABELS = {"儿子","女儿","孙子","孙女","侄子","侄女","外甥","外甥女",
                              "曾孙","曾孙女","儿媳","女婿"}

            if claimed_label in ELDER_LABELS and gen_diff < 0:
                return {
                    "type": "generation_mismatch",
                    "claimed": claimed_label,
                    "derived": derived,
                    "detail": f"声称'{claimed_label}'是长辈但推导是晚辈(差{gen_diff}辈)"
                }
            if claimed_label in YOUNGER_LABELS and gen_diff > 0:
                return {
                    "type": "generation_mismatch",
                    "claimed": claimed_label,
                    "derived": derived,
                    "detail": f"声称'{claimed_label}'是晚辈但推导是长辈(差{gen_diff}辈)"
                }

        return None  # 无矛盾

    # ─────────────────────────────────────────────────
    # 导出/导入
    # ─────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        """导出为字典"""
        links = []
        for person_a, edges in self.graph.items():
            for person_b, link in edges:
                links.append({
                    "from": person_a,
                    "to": person_b,
                    "op": link.op,
                    "gender": link.gender,
                    "label": link.label,
                    "lineage": link.lineage,
                })
        return {
            "persons": list(self.persons.values()),
            "links": links,
            "direct_labels": [
                {"from": k[0], "to": k[1], "label": v}
                for k, v in self.direct_labels.items()
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "KinshipEngine":
        """从字典加载"""
        engine = cls()
        for p in data.get("persons", []):
            engine.add_person(p["name"], p.get("gender", "unknown"))
        for link in data.get("links", []):
            engine.add_link(
                link["from"], link["to"], link["op"],
                link.get("gender", "unknown"),
                link.get("label", ""),
                link.get("lineage", "blood"),
            )
        for dl in data.get("direct_labels", []):
            engine.add_direct_label(dl["from"], dl["to"], dl["label"])
        return engine


# ═══════════════════════════════════════════════════════════
# 演示和测试
# ═══════════════════════════════════════════════════════════

def demo():
    """演示：构建一个4代家谱并解析所有关系"""
    engine = KinshipEngine()

    # 构建4代家谱
    #       曾祖父 ─ 曾祖母
    #          │
    #       爷爷 ─ 奶奶          外公 ─ 外婆
    #       ┌─┼─┐                │
    #    大伯 爸爸 姑姑        舅舅─舅妈
    #     │   │                  │
    #   堂哥  我(♂)            表弟

    persons = [
        ("曾祖父", "male"), ("曾祖母", "female"),
        ("爷爷", "male"), ("奶奶", "female"),
        ("大伯", "male"), ("爸爸", "male"), ("姑姑", "female"),
        ("外公", "male"), ("外婆", "female"),
        ("舅舅", "male"), ("舅妈", "female"),
        ("堂哥", "male"), ("我", "male"), ("表弟", "male"),
    ]
    for name, g in persons:
        engine.add_person(name, g)

    # 纵向关系
    links = [
        ("曾祖父", "爷爷", "ascend"),   # 曾祖父 → 爷爷 (爷爷是曾祖父的儿子)
        ("爷爷", "爸爸", "ascend"),      # 简化：用 ascend 表示"上一辈"
        ("爷爷", "大伯", "ascend"),
        ("爷爷", "姑姑", "ascend"),
        ("外公", "舅舅", "ascend"),
        ("爸爸", "我", "descend"),
        ("大伯", "堂哥", "descend"),
        ("舅舅", "表弟", "descend"),
    ]
    for a, b, op in links:
        b_gender = dict(persons).get(b, "unknown")
        engine.add_link(a, b, op, b_gender)

    # 横向关系
    engine.add_link("爷爷", "奶奶", "spouse", "female")
    engine.add_link("外公", "外婆", "spouse", "female")
    engine.add_link("舅舅", "舅妈", "spouse", "female")
    engine.add_link("爸爸", "大伯", "sibling", "male")
    engine.add_link("爸爸", "姑姑", "sibling", "female")

    # 测试
    print("=" * 60)
    print("  4代家谱关系推导演示")
    print("=" * 60)

    test_cases = [
        ("我", "爸爸"),
        ("我", "爷爷"),
        ("我", "曾祖父"),
        ("我", "大伯"),
        ("我", "姑姑"),
        ("我", "舅舅"),
        ("我", "舅妈"),
        ("我", "堂哥"),
        ("我", "表弟"),
        ("我", "奶奶"),
        ("我", "外婆"),
    ]

    for a, b in test_cases:
        result = engine.resolve(a, b)
        path_str = " → ".join(
            f"{p['op']}({'♂' if p['gender']=='male' else '♀'})"
            for p in result["path"]
        )
        compressed = " → ".join(result["compressed"]) if result["compressed"] else "-"
        print(f"\n  {a} → {b}")
        print(f"    称谓: {result['label']}")
        print(f"    来源: {result['source']}")
        print(f"    路径: {path_str or '直接'}")
        print(f"    压缩: {compressed}")
        if result["analysis"]:
            a_info = result["analysis"]
            print(f"    分析: 辈分差={a_info['gen_diff']:+d}, "
                  f"跳数={a_info['num_hops']}, "
                  f"{'父系' if a_info['is_paternal'] else '母系'}")

    # 矛盾检测演示
    print(f"\n{'=' * 60}")
    print("  矛盾检测演示")
    print("=" * 60)

    # 声称"爸爸是妈妈"——性别矛盾
    conflict = engine.detect_conflicts("我", "爸爸", "妈妈")
    print(f"\n  声称: 我→爸爸='妈妈'")
    print(f"  结果: {'矛盾! ' + conflict['detail'] if conflict else '无矛盾'}")

    # 声称"爷爷是孙子"——辈分矛盾
    conflict = engine.detect_conflicts("我", "爷爷", "孙子")
    print(f"\n  声称: 我→爷爷='孙子'")
    print(f"  结果: {'矛盾! ' + conflict['detail'] if conflict else '无矛盾'}")

    # 声称"舅舅是舅舅"——正确
    conflict = engine.detect_conflicts("我", "舅舅", "舅舅")
    print(f"\n  声称: 我→舅舅='舅舅'")
    print(f"  结果: {'矛盾! ' + conflict['detail'] if conflict else '无矛盾 ✓'}")

    # 直接标签（无法推导的情况）
    print(f"\n{'=' * 60}")
    print("  直接标签演示（无法推导时）")
    print("=" * 60)

    engine.add_person("王秀英", "female")
    engine.add_direct_label("我", "王秀英", "舅妈")
    result = engine.resolve("我", "王秀英")
    print(f"\n  我 → 王秀英")
    print(f"    称谓: {result['label']}")
    print(f"    来源: {result['source']}（直接标注，无法推导）")

    # 导出
    print(f"\n{'=' * 60}")
    print("  JSON 导出")
    print("=" * 60)
    data = engine.to_dict()
    print(f"  人物: {len(data['persons'])}")
    print(f"  链接: {len(data['links'])}")
    print(f"  直接标签: {len(data['direct_labels'])}")


if __name__ == "__main__":
    demo()
