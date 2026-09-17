"""pytest 共享夹具:加载 .env 环境变量,供真实 LLM/搜索调用使用。"""

from __future__ import annotations

from pathlib import Path

import pytest
from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def _load_env():
    """session 级自动加载 .env,确保真实凭证可用。"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
