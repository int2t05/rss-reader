"""环境变量展开:${VAR_NAME} 替换为 os.environ[VAR_NAME],未定义时保留原样。

config.py 与 sources/rss.py 共享,避免重复实现。
"""

from __future__ import annotations

import os
import re

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def expand_env(value: str) -> str:
    """将 ${VAR_NAME} 替换为 os.environ['VAR_NAME'],未定义时保留原样。

    示例:"http://host/feed/${TOKEN}" → "http://host/feed/secret-123"
    """
    return _ENV_VAR_PATTERN.sub(
        lambda m: os.environ.get(m.group(1), m.group(0)).strip(),
        value,
    )
