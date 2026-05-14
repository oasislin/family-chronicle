"""
家族编年史智能族谱系统 - 配置管理
Family Chronicle Intelligent Genealogy System - Configuration
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基本配置
    APP_NAME: str = "家族编年史 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    SECRET_KEY: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # 数据目录
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Optional[Path] = Field(default=None, env="DATA_DIR")
    
    def __init__(self, **values):
        super().__init__(**values)
        if self.DATA_DIR is None:
            self.DATA_DIR = self.BASE_DIR / "data"
    
    # AI服务配置
    AI_PROVIDER: str = Field(default="deepseek", env="AI_PROVIDER")  # deepseek, zhipu, openai, claude
    DEEPSEEK_API_KEY: str = Field(default="", env=["HUAWEI_API_KEY", "DEEPSEEK_API_KEY"])
    DEEPSEEK_BASE_URL: str = Field(default="https://api.modelarts-maas.com/openai", env="DEEPSEEK_BASE_URL")
    ZHIPU_API_KEY: str = Field(default="", env="ZHIPU_API_KEY")
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")
    
    # 隐私设置
    PRIVACY_MODE: str = Field(default="local_only", env="PRIVACY_MODE")  # local_only, cloud_desensitized, cloud_full
    ENABLE_DESENSITIZATION: bool = Field(default=True, env="ENABLE_DESENSITIZATION")
    
    # 文件上传配置
    MAX_UPLOAD_SIZE_MB: int = Field(default=50, env="MAX_UPLOAD_SIZE_MB")
    ALLOWED_EXTENSIONS: list = Field(default=[".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx"])
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[Path] = Field(default=None, env="LOG_FILE")

    # 默认家族配置
    DEFAULT_FAMILY_ID: str = "default_family"

    def post_init_logic(self):
        if self.LOG_FILE is None:
            self.LOG_FILE = self.BASE_DIR / "logs" / "app.log"
        
        # 读取本地 server_config.json
        config_path = self.BASE_DIR / "backend" / "server_config.json"
        if config_path.exists():
            try:
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "default_family_id" in data:
                        self.DEFAULT_FAMILY_ID = data["default_family_id"]
            except Exception as e:
                print(f"警告: 无法读取 server_config.json: {e}")
        
        # 手动检查环境变量，确保系统级变量优先
        import os
        if not self.DEEPSEEK_API_KEY:
            # 优先检查 HUAWEI_API_KEY
            huawei_key = os.environ.get("HUAWEI_API_KEY")
            if huawei_key:
                self.DEEPSEEK_API_KEY = huawei_key
            # 其次检查 DEEPSEEK_API_KEY
            elif os.environ.get("DEEPSEEK_API_KEY"):
                self.DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
    
    # CORS配置
    CORS_ORIGINS: list = Field(default=["*"], env="CORS_ORIGINS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局设置实例
settings = Settings()
settings.post_init_logic()

# 确保必要的目录存在
settings.DATA_DIR.mkdir(exist_ok=True, parents=True)
settings.LOG_FILE.parent.mkdir(exist_ok=True, parents=True)


def get_ai_provider_config() -> Dict[str, Any]:
    """获取当前AI提供商的配置"""
    if settings.AI_PROVIDER == "deepseek":
        return {
            "api_key": settings.DEEPSEEK_API_KEY,
            "base_url": settings.DEEPSEEK_BASE_URL,
            "model": "deepseek-v3.2"
        }
    elif settings.AI_PROVIDER == "zhipu":
        return {
            "api_key": settings.ZHIPU_API_KEY,
            "model": "glm-4"
        }
    elif settings.AI_PROVIDER == "openai":
        return {
            "api_key": settings.OPENAI_API_KEY,
            "model": "gpt-4"
        }
    elif settings.AI_PROVIDER == "claude":
        return {
            "api_key": settings.ANTHROPIC_API_KEY,
            "model": "claude-3-sonnet-20240229"
        }
    else:
        raise ValueError(f"不支持的AI提供商: {settings.AI_PROVIDER}")
