"""
家族编年史智能族谱系统 - AI服务模块
Family Chronicle Intelligent Genealogy System - AI Service Module

提供统一的AI服务接口，支持多种AI提供商（DeepSeek、智谱、OpenAI、Claude）。
"""

import json
import time
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import httpx
from datetime import datetime

# 导入配置
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from config import settings, get_ai_provider_config


class AIProvider(ABC):
    """AI提供商基类"""
    
    @abstractmethod
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """聊天补全接口"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        pass


class DeepSeekProvider(AIProvider):
    """DeepSeek AI提供商"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = "deepseek-v3.2"
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """调用DeepSeek API"""
        url = f"{self.base_url}/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 2000),
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise Exception(f"DeepSeek API错误: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"DeepSeek API调用失败: {str(e)}")
    
    def get_provider_name(self) -> str:
        return "deepseek"


class ZhipuProvider(AIProvider):
    """智谱AI提供商"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "glm-4"
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """调用智谱API"""
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 2000)
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise Exception(f"智谱API错误: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"智谱API调用失败: {str(e)}")
    
    def get_provider_name(self) -> str:
        return "zhipu"


class OpenAIProvider(AIProvider):
    """OpenAI提供商"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gpt-4"
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """调用OpenAI API"""
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 2000)
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise Exception(f"OpenAI API错误: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"OpenAI API调用失败: {str(e)}")
    
    def get_provider_name(self) -> str:
        return "openai"


class ClaudeProvider(AIProvider):
    """Claude提供商"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "claude-3-sonnet-20240229"
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """调用Claude API"""
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        # 转换消息格式为Claude格式
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                # Claude使用system参数而不是消息
                continue
            claude_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # 提取system消息
        system_content = ""
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
                break
        
        payload = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", 2000),
            "temperature": kwargs.get("temperature", 0.1),
            "system": system_content,
            "messages": claude_messages
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise Exception(f"Claude API错误: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"Claude API调用失败: {str(e)}")
    
    def get_provider_name(self) -> str:
        return "claude"


class MockProvider(AIProvider):
    """模拟AI提供商（用于测试）"""
    
    def __init__(self):
        self.model = "mock-model"
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """返回模拟响应"""
        # 解析用户消息
        user_content = ""
        for msg in messages:
            if msg["role"] == "user":
                user_content = msg["content"]
                break
        
        # 生成模拟响应
        mock_response = {
            "id": "mock-response-001",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self._generate_mock_content(user_content)
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(user_content.split()),
                "completion_tokens": 100,
                "total_tokens": len(user_content.split()) + 100
            }
        }
        
        return mock_response
    
    def _generate_mock_content(self, user_content: str) -> str:
        """生成模拟内容"""
        if "大伯的老二建国" in user_content:
            # 返回示例JSON
            return json.dumps({
                "entities": [
                    {
                        "type": "person",
                        "name": "建国",
                        "temp_id": "temp_person_001",
                        "gender": "male",
                        "tags": ["老二", "大伯之子"],
                        "confidence": "medium"
                    },
                    {
                        "type": "person",
                        "name": "李梅",
                        "temp_id": "temp_person_002",
                        "gender": "female",
                        "confidence": "high"
                    },
                    {
                        "type": "person",
                        "name": "赵大爷",
                        "temp_id": "temp_person_003",
                        "gender": "male",
                        "tags": ["村长"],
                        "confidence": "high"
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
                    ]
                }
            }, ensure_ascii=False)
        else:
            # 通用响应
            return json.dumps({
                "entities": [
                    {
                        "type": "person",
                        "name": "示例人物",
                        "temp_id": "temp_person_001",
                        "gender": "unknown",
                        "confidence": "medium"
                    }
                ],
                "events": [],
                "relationships": [],
                "metadata": {
                    "parsing_confidence": 0.5,
                    "ambiguous_references": ["这是模拟数据"],
                    "suggested_questions": ["请提供更详细的家族描述"]
                }
            }, ensure_ascii=False)
    
    def get_provider_name(self) -> str:
        return "mock"


class AIService:
    """AI服务管理器"""
    
    def __init__(self):
        self.provider = self._create_provider()
        self.prompt_manager = None  # 延迟加载
    
    def _create_provider(self) -> AIProvider:
        """创建AI提供商实例"""
        provider_name = settings.AI_PROVIDER.lower()
        
        if provider_name == "deepseek":
            config = get_ai_provider_config()
            if not config["api_key"]:
                print("警告: DeepSeek API密钥未配置，使用模拟提供商")
                return MockProvider()
            return DeepSeekProvider(config["api_key"], config["base_url"])
        
        elif provider_name == "zhipu":
            config = get_ai_provider_config()
            if not config["api_key"]:
                print("警告: 智谱API密钥未配置，使用模拟提供商")
                return MockProvider()
            return ZhipuProvider(config["api_key"])
        
        elif provider_name == "openai":
            config = get_ai_provider_config()
            if not config["api_key"]:
                print("警告: OpenAI API密钥未配置，使用模拟提供商")
                return MockProvider()
            return OpenAIProvider(config["api_key"])
        
        elif provider_name == "claude":
            config = get_ai_provider_config()
            if not config["api_key"]:
                print("警告: Claude API密钥未配置，使用模拟提供商")
                return MockProvider()
            return ClaudeProvider(config["api_key"])
        
        elif provider_name == "mock":
            return MockProvider()
        
        else:
            print(f"警告: 不支持的AI提供商 '{provider_name}'，使用模拟提供商")
            return MockProvider()
    
    def _get_prompt_manager(self):
        """延迟加载提示词管理器"""
        if self.prompt_manager is None:
            from prompt_engineering import FamilyParsingPrompt
            self.prompt_manager = FamilyParsingPrompt()
        return self.prompt_manager
    
    async def parse_family_text(self, text: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """解析家族文本"""
        try:
            # 获取提示词
            prompt_manager = self._get_prompt_manager()
            messages = prompt_manager.get_parsing_prompt(text)
            
            # 调用AI API
            start_time = time.time()
            response = await self.provider.chat_completion(
                messages=messages,
                temperature=options.get("temperature", 0.1) if options else 0.1,
                max_tokens=options.get("max_tokens", 2000) if options else 2000
            )
            elapsed_time = time.time() - start_time
            
            # 解析响应
            content = self._extract_response_content(response)
            
            # 验证JSON格式
            try:
                parsed_data = json.loads(content)
            except json.JSONDecodeError as e:
                # 尝试修复常见的JSON格式问题
                content = self._fix_json_format(content)
                try:
                    parsed_data = json.loads(content)
                except json.JSONDecodeError:
                    raise Exception(f"AI返回的JSON格式无效: {str(e)}")
            
            # 验证数据结构
            validation = prompt_manager.validate_output(json.dumps(parsed_data, ensure_ascii=False))
            if not validation["valid"]:
                raise Exception(f"AI返回的数据结构无效: {validation['error']}")
            
            # 记录解析日志
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "provider": self.provider.get_provider_name(),
                "model": getattr(self.provider, 'model', 'unknown'),
                "input_text": text[:200] + "..." if len(text) > 200 else text,
                "response_time": elapsed_time,
                "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                "success": True
            }
            
            return {
                "parsed_data": parsed_data,
                "raw_response": content,
                "log": log_entry,
                "provider": self.provider.get_provider_name()
            }
            
        except Exception as e:
            # 记录错误日志
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "provider": self.provider.get_provider_name(),
                "input_text": text[:200] + "..." if len(text) > 200 else text,
                "error": str(e),
                "success": False
            }
            
            raise Exception(f"AI解析失败: {str(e)}")
    
    def _extract_response_content(self, response: Dict[str, Any]) -> str:
        """从AI响应中提取内容"""
        # 处理不同提供商的响应格式
        if "choices" in response and len(response["choices"]) > 0:
            # OpenAI/DeepSeek格式
            return response["choices"][0]["message"]["content"]
        elif "content" in response:
            # Claude格式
            if isinstance(response["content"], list):
                return "".join([block["text"] for block in response["content"] if block["type"] == "text"])
            else:
                return response["content"]
        else:
            raise Exception(f"无法从响应中提取内容: {response}")
    
    def _fix_json_format(self, content: str) -> str:
        """修复常见的JSON格式问题"""
        # 移除可能的markdown代码块标记
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        # 移除前后空白
        content = content.strip()
        
        # 尝试找到JSON对象的开始和结束
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            content = content[start_idx:end_idx+1]
        
        return content
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试AI服务连接"""
        try:
            test_messages = [
                {"role": "system", "content": "你是一个测试助手。"},
                {"role": "user", "content": "请回复'连接成功'"}
            ]
            
            start_time = time.time()
            response = await self.provider.chat_completion(test_messages, max_tokens=50)
            elapsed_time = time.time() - start_time
            
            return {
                "success": True,
                "provider": self.provider.get_provider_name(),
                "model": getattr(self.provider, 'model', 'unknown'),
                "response_time": elapsed_time,
                "response": self._extract_response_content(response)
            }
        except Exception as e:
            return {
                "success": False,
                "provider": self.provider.get_provider_name(),
                "error": str(e)
            }


# 创建全局AI服务实例
ai_service = AIService()


# 测试函数
async def test_ai_service():
    """测试AI服务"""
    print("=== 测试AI服务 ===")
    
    # 测试连接
    print("1. 测试连接...")
    connection_test = await ai_service.test_connection()
    print(f"   结果: {connection_test}")
    
    if not connection_test["success"]:
        print(f"   连接失败: {connection_test['error']}")
        return
    
    # 测试解析
    print("\n2. 测试解析...")
    test_text = "大伯的老二建国，95年和李梅二婚了，后来认了村长赵大爷做干爹"
    
    try:
        result = await ai_service.parse_family_text(test_text)
        print(f"   解析成功!")
        print(f"   提供商: {result['provider']}")
        print(f"   响应时间: {result['log']['response_time']:.2f}秒")
        print(f"   使用的tokens: {result['log']['tokens_used']}")
        
        # 打印解析结果摘要
        parsed_data = result["parsed_data"]
        print(f"\n   解析结果摘要:")
        print(f"   - 人物数量: {len(parsed_data.get('entities', []))}")
        print(f"   - 事件数量: {len(parsed_data.get('events', []))}")
        print(f"   - 关系数量: {len(parsed_data.get('relationships', []))}")
        print(f"   - 置信度: {parsed_data.get('metadata', {}).get('parsing_confidence', 0)}")
        
    except Exception as e:
        print(f"   解析失败: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_service())