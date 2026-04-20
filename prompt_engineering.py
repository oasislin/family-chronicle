"""
家族编年史智能族谱系统 - AI解析提示词工程
Family Chronicle Intelligent Genealogy System - AI Prompt Engineering

提供系统指令和提示词模板，用于将自然语言家族描述解析为结构化JSON数据。
"""

import json
from typing import Dict, Any, List


class FamilyParsingPrompt:
    """家族信息解析提示词管理器"""
    
    def __init__(self):
        self.system_prompt = self._create_system_prompt()
        self.json_schema = self._create_json_schema()
        self.examples = self._create_examples()
    
    def _create_system_prompt(self) -> str:
        """创建系统指令"""
        return """你是一个家族图谱信息提取专家。你的任务是从用户提供的自然语言描述中，准确提取家族成员、关系和事件信息，并严格按照指定的JSON格式输出。

## 核心能力
1. **人物识别**：从描述中识别所有提到的人物，包括称呼、昵称、关系称谓
2. **关系推断**：根据上下文推断人物之间的关系类型
3. **事件提取**：识别描述中的关键事件（出生、死亡、结婚、离婚、认干亲、生病、搬家等）
4. **时间解析**：尽可能提取或推断时间信息，包括农历、公历、相对时间
5. **冲突标记**：识别描述中可能存在的矛盾或模糊信息

## 输出要求
1. **严格遵循JSON格式**：只输出JSON，不要任何解释、问候或额外文字
2. **使用临时ID**：为每个识别的人物和事件分配临时ID（格式：temp_person_001, temp_event_001）
3. **置信度标注**：为每个提取结果标注置信度（高/中/低）
4. **模糊处理**：对于不确定的信息，使用null值并添加到ambiguous_references
5. **引导性问题**：对于需要用户澄清的信息，生成具体的澄清问题

## 特殊处理规则
1. **称呼解析**：理解中文家族称呼系统（如：大伯、二舅、三姑、小姨等）
2. **排行处理**：正确处理排行信息（老大、老二、长子、次子等）
3. **婚姻状态**：区分初婚、二婚、丧偶、离婚等状态
4. **过继/认干亲**：准确识别非血缘关系的家族关系
5. **方言理解**：理解常见的方言表达方式

## 数据质量要求
1. **准确性优先**：宁可少提取，不要错误提取
2. **完整性检查**：确保人物、关系、事件三者之间的关联完整
3. **一致性验证**：检查提取信息之间是否存在逻辑矛盾
4. **可追溯性**：保留原始描述中的关键信息用于验证"""
    
    def _create_json_schema(self) -> Dict[str, Any]:
        """创建JSON输出格式定义"""
        return {
            "type": "object",
            "required": ["entities", "events", "relationships", "metadata"],
            "properties": {
                "entities": {
                    "type": "array",
                    "description": "识别出的人物实体列表",
                    "items": {
                        "type": "object",
                        "required": ["type", "name", "temp_id"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["person"],
                                "description": "实体类型，固定为'person'"
                            },
                            "name": {
                                "type": "string",
                                "description": "人物姓名或称呼"
                            },
                            "temp_id": {
                                "type": "string",
                                "description": "临时ID，格式：temp_person_XXX"
                            },
                            "gender": {
                                "type": "string",
                                "enum": ["male", "female", "unknown"],
                                "description": "性别"
                            },
                            "birth_year": {
                                "type": ["string", "null"],
                                "description": "出生年份，如果可推断"
                            },
                            "death_year": {
                                "type": ["string", "null"],
                                "description": "去世年份，如果可推断"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "标签，如：['长子', '村长', '手艺人']"
                            },
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "识别置信度"
                            },
                            "source_text": {
                                "type": "string",
                                "description": "原始描述中关于此人的关键文本片段"
                            }
                        }
                    }
                },
                "events": {
                    "type": "array",
                    "description": "识别出的事件列表",
                    "items": {
                        "type": "object",
                        "required": ["type", "description", "temp_id"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": [
                                    "birth", "death", "marriage", "divorce",
                                    "adoption", "illness", "relocation", 
                                    "education", "career", "recognition", "other"
                                ],
                                "description": "事件类型"
                            },
                            "description": {
                                "type": "string",
                                "description": "事件描述"
                            },
                            "temp_id": {
                                "type": "string",
                                "description": "临时ID，格式：temp_event_XXX"
                            },
                            "date": {
                                "type": ["string", "null"],
                                "description": "事件日期，尽可能精确"
                            },
                            "date_accuracy": {
                                "type": "string",
                                "enum": ["exact", "year", "approximate", "unknown"],
                                "description": "日期精确度"
                            },
                            "location": {
                                "type": ["string", "null"],
                                "description": "事件发生地点"
                            },
                            "participants": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "temp_id": {
                                            "type": "string",
                                            "description": "参与者临时ID"
                                        },
                                        "role": {
                                            "type": "string",
                                            "description": "在事件中的角色"
                                        }
                                    }
                                },
                                "description": "事件参与者列表"
                            },
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "事件识别置信度"
                            }
                        }
                    }
                },
                "relationships": {
                    "type": "array",
                    "description": "识别出的人物关系列表",
                    "items": {
                        "type": "object",
                        "required": ["person1_temp_id", "person2_temp_id", "type"],
                        "properties": {
                            "person1_temp_id": {
                                "type": "string",
                                "description": "第一个人物临时ID"
                            },
                            "person2_temp_id": {
                                "type": "string",
                                "description": "第二个人物临时ID"
                            },
                            "type": {
                                "type": "string",
                                "enum": [
                                    "parent_child", "spouse", "sibling",
                                    "grandparent_grandchild", "aunt_uncle_niece_nephew",
                                    "cousin", "adopted_parent_child", 
                                    "godparent_godchild", "in_law", "other"
                                ],
                                "description": "关系类型"
                            },
                            "subtype": {
                                "type": ["string", "null"],
                                "description": "关系子类型，如：'father', 'mother', 'elder_brother'"
                            },
                            "attributes": {
                                "type": "object",
                                "description": "关系属性，如：{ 'birth_order': '老二', 'marriage_number': 2 }"
                            },
                            "event_temp_id": {
                                "type": ["string", "null"],
                                "description": "关联的事件临时ID"
                            },
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "关系识别置信度"
                            }
                        }
                    }
                },
                "metadata": {
                    "type": "object",
                    "description": "解析元数据",
                    "properties": {
                        "parsing_confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "整体解析置信度（0-1）"
                        },
                        "ambiguous_references": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "模糊引用列表，如：['大伯 - 需要确认具体人物']"
                        },
                        "suggested_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "建议的澄清问题列表"
                        },
                        "extracted_time_references": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "提取的时间参考信息"
                        }
                    }
                }
            }
        }
    
    def _create_examples(self) -> List[Dict[str, Any]]:
        """创建示例数据"""
        return [
            {
                "input": "大伯的老二建国，95年和李梅二婚了，后来认了村长赵大爷做干爹",
                "output": {
                    "entities": [
                        {
                            "type": "person",
                            "name": "建国",
                            "temp_id": "temp_person_001",
                            "gender": "male",
                            "tags": ["老二", "大伯之子"],
                            "confidence": "medium",
                            "source_text": "大伯的老二建国"
                        },
                        {
                            "type": "person",
                            "name": "李梅",
                            "temp_id": "temp_person_002",
                            "gender": "female",
                            "confidence": "high",
                            "source_text": "李梅"
                        },
                        {
                            "type": "person",
                            "name": "赵大爷",
                            "temp_id": "temp_person_003",
                            "gender": "male",
                            "tags": ["村长"],
                            "confidence": "high",
                            "source_text": "村长赵大爷"
                        }
                    ],
                    "events": [
                        {
                            "type": "marriage",
                            "description": "建国与李梅结婚（二婚）",
                            "temp_id": "temp_event_001",
                            "date": "1995",
                            "date_accuracy": "year",
                            "participants": [
                                {"temp_id": "temp_person_001", "role": "新郎"},
                                {"temp_id": "temp_person_002", "role": "新娘"}
                            ],
                            "confidence": "high"
                        },
                        {
                            "type": "recognition",
                            "description": "建国认赵大爷为干爹",
                            "temp_id": "temp_event_002",
                            "date": None,
                            "date_accuracy": "unknown",
                            "participants": [
                                {"temp_id": "temp_person_001", "role": "干儿子"},
                                {"temp_id": "temp_person_003", "role": "干爹"}
                            ],
                            "confidence": "high"
                        }
                    ],
                    "relationships": [
                        {
                            "person1_temp_id": "temp_person_001",
                            "person2_temp_id": "temp_person_002",
                            "type": "spouse",
                            "attributes": {"marriage_number": 2},
                            "event_temp_id": "temp_event_001",
                            "confidence": "high"
                        },
                        {
                            "person1_temp_id": "temp_person_001",
                            "person2_temp_id": "temp_person_003",
                            "type": "godparent_godchild",
                            "subtype": "godfather_godson",
                            "event_temp_id": "temp_event_002",
                            "confidence": "high"
                        }
                    ],
                    "metadata": {
                        "parsing_confidence": 0.85,
                        "ambiguous_references": ["大伯 - 需要确认具体人物"],
                        "suggested_questions": [
                            "大伯是指哪位家族成员？",
                            "建国与李梅的二婚是否有具体日期？"
                        ],
                        "extracted_time_references": ["95年"]
                    }
                }
            },
            {
                "input": "我爸叫王大强，1950年生的，我是他二儿子，1980年腊八生的，我媳妇李梅是隔壁村的",
                "output": {
                    "entities": [
                        {
                            "type": "person",
                            "name": "我爸",
                            "temp_id": "temp_person_001",
                            "gender": "male",
                            "birth_year": "1950",
                            "confidence": "high",
                            "source_text": "我爸叫王大强，1950年生的"
                        },
                        {
                            "type": "person",
                            "name": "我",
                            "temp_id": "temp_person_002",
                            "gender": "male",
                            "birth_year": "1980",
                            "tags": ["二儿子"],
                            "confidence": "high",
                            "source_text": "我是他二儿子，1980年腊八生的"
                        },
                        {
                            "type": "person",
                            "name": "李梅",
                            "temp_id": "temp_person_003",
                            "gender": "female",
                            "tags": ["隔壁村"],
                            "confidence": "high",
                            "source_text": "我媳妇李梅是隔壁村的"
                        }
                    ],
                    "events": [
                        {
                            "type": "birth",
                            "description": "王大强出生",
                            "temp_id": "temp_event_001",
                            "date": "1950",
                            "date_accuracy": "year",
                            "participants": [
                                {"temp_id": "temp_person_001", "role": "新生儿"}
                            ],
                            "confidence": "high"
                        },
                        {
                            "type": "birth",
                            "description": "我（二儿子）出生",
                            "temp_id": "temp_event_002",
                            "date": "1980-12-08",
                            "date_accuracy": "exact",
                            "participants": [
                                {"temp_id": "temp_person_002", "role": "新生儿"},
                                {"temp_id": "temp_person_001", "role": "父亲"}
                            ],
                            "confidence": "high"
                        }
                    ],
                    "relationships": [
                        {
                            "person1_temp_id": "temp_person_001",
                            "person2_temp_id": "temp_person_002",
                            "type": "parent_child",
                            "subtype": "father",
                            "attributes": {"birth_order": "老二"},
                            "confidence": "high"
                        },
                        {
                            "person1_temp_id": "temp_person_002",
                            "person2_temp_id": "temp_person_003",
                            "type": "spouse",
                            "confidence": "high"
                        }
                    ],
                    "metadata": {
                        "parsing_confidence": 0.95,
                        "ambiguous_references": [],
                        "suggested_questions": [],
                        "extracted_time_references": ["1950年", "1980年腊八"]
                    }
                }
            }
        ]
    
    def get_parsing_prompt(self, user_input: str) -> List[Dict[str, str]]:
        """生成完整的解析提示词"""
        # 构建few-shot examples
        examples_text = ""
        for i, example in enumerate(self.examples, 1):
            examples_text += f"\n### 示例 {i}\n"
            examples_text += f"输入：{example['input']}\n"
            examples_text += f"输出：\n```json\n{json.dumps(example['output'], ensure_ascii=False, indent=2)}\n```\n"
        
        # 构建完整的提示词
        prompt = f"""请解析以下家族描述，并严格按照JSON格式输出结果。

## 输入描述
{user_input}

## 输出格式要求
请严格按照以下JSON schema输出：
```json
{json.dumps(self.json_schema, ensure_ascii=False, indent=2)}
```

## 示例
{examples_text}

## 注意事项
1. 只输出JSON，不要任何其他文字
2. 使用临时ID格式：temp_person_XXX, temp_event_XXX
3. 对于不确定的信息，使用null值并添加到ambiguous_references
4. 生成具体的澄清问题帮助用户完善信息
5. 尽可能提取时间信息，包括农历转换
6. 正确处理中文家族称呼系统

请开始解析："""
        
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
    
    def get_system_prompt(self) -> str:
        """获取系统指令"""
        return self.system_prompt
    
    def get_json_schema(self) -> Dict[str, Any]:
        """获取JSON schema"""
        return self.json_schema
    
    def validate_output(self, output_json: str) -> Dict[str, Any]:
        """验证输出JSON是否符合schema"""
        try:
            data = json.loads(output_json)
            
            # 基本结构检查
            required_keys = ["entities", "events", "relationships", "metadata"]
            for key in required_keys:
                if key not in data:
                    return {"valid": False, "error": f"缺少必需字段: {key}"}
            
            # 检查实体
            for entity in data.get("entities", []):
                if "temp_id" not in entity or "name" not in entity:
                    return {"valid": False, "error": "实体缺少必需字段: temp_id 或 name"}
            
            # 检查事件
            for event in data.get("events", []):
                if "temp_id" not in event or "type" not in event:
                    return {"valid": False, "error": "事件缺少必需字段: temp_id 或 type"}
            
            # 检查关系
            for rel in data.get("relationships", []):
                if "person1_temp_id" not in rel or "person2_temp_id" not in rel:
                    return {"valid": False, "error": "关系缺少必需字段: person1_temp_id 或 person2_temp_id"}
            
            return {"valid": True, "data": data}
            
        except json.JSONDecodeError as e:
            return {"valid": False, "error": f"JSON解析错误: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"验证错误: {str(e)}"}


def test_prompt_with_examples():
    """测试提示词生成"""
    prompt_manager = FamilyParsingPrompt()
    
    # 测试输入
    test_inputs = [
        "大伯的老二建国，95年和李梅二婚了，后来认了村长赵大爷做干爹",
        "我爸叫王大强，1950年生的，我是他二儿子，1980年腊八生的，我媳妇李梅是隔壁村的",
        "爷爷1920年出生，1998年去世，有三个儿子，我爸是老大，二叔在县城当老师，三叔去深圳打工了"
    ]
    
    print("=== 家族信息解析提示词测试 ===\n")
    
    for i, test_input in enumerate(test_inputs, 1):
        print(f"测试 {i}:")
        print(f"输入: {test_input}")
        
        messages = prompt_manager.get_parsing_prompt(test_input)
        print(f"系统指令长度: {len(messages[0]['content'])} 字符")
        print(f"用户提示词长度: {len(messages[1]['content'])} 字符")
        print("-" * 50)
    
    print("\n=== JSON Schema 验证测试 ===")
    schema = prompt_manager.get_json_schema()
    print(f"Schema 包含 {len(schema['properties'])} 个顶级字段")
    
    # 测试验证功能
    test_output = json.dumps(prompt_manager.examples[0]["output"], ensure_ascii=False)
    validation = prompt_manager.validate_output(test_output)
    print(f"示例输出验证: {'通过' if validation['valid'] else '失败'}")
    
    if not validation['valid']:
        print(f"错误: {validation.get('error')}")


if __name__ == "__main__":
    test_prompt_with_examples()