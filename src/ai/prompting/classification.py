"""Tier1 分类+打分 prompt 构建:system prompt 注入分类树 + 评分标准(含时效规则),user prompt 注入条目内容与发布时间。"""

from __future__ import annotations

from datetime import datetime

_DEFAULT_MAX_CHARS = 1000


def analysis_system_prompt(category_tree_json: str) -> str:
    """构建 Tier1 system prompt:分类树 + 评分标准 + JSON 输出契约。

    示例:
        prompt = analysis_system_prompt(registry.category_tree_json())
    """
    return f"""你是技术信息分类器。将条目归入以下分类树之一,并打分(0-10)。

## 分类树
{category_tree_json}

## 评分标准(0-10)
- 9-10: 重大突破 / 重要发布(如 GPT-5 发布、arXiv 顶会最佳论文)
- 7-8:  有价值的技术动态 / 研究发现
- 5-6:  一般性更新 / 教程 / 观点
- 3-4:  低价值 / 营销 / 重复
- 0-2:  无关 / 垃圾

## 时效性(结合 user prompt 中的发布时间打分)
简报是「今日」视角,同等内容越新价值越高:
- 距今 ≤1 天:不降分
- 距今 2-3 天:轻度降分(约 -1)
- 距今 >3 天:显著降分,一般性内容应低于 4 分
- 重大发布 / 重要研究可放宽,但仍应随条目年龄递减
例外:命中研究兴趣加权的条目豁免时效降分。

## 研究兴趣加权(优先级高于基础评分与时效降分)
用户重点研究方向为进化计算与分布式优化。条目命中以下任一主题时,分数显著上调
(至少 +2,通常进 8-10 段),并在 summary 开头标注「研究相关：」:
- 进化计算/群智算法:进化计算、遗传算法、粒子群 PSO、蚁群 ACO、差分进化、进化策略、演化计算、群体智能、swarm
- 分布式/多智能体优化:分布式优化、多智能体、multi-agent、共识优化、众包优化、crowdsourcing
- LLM 与 EC 结合:LLM 超参调优、LLM 算法进化、Algorithm Evolution、自动算法设计、元黑盒优化、meta-black-box
- 强化学习+进化:进化引导的策略梯度、Evolution-Guided Policy Gradient、RL 与 EC 结合、reward shaping 进化
- 数据驱动/代理辅助优化:代理模型、surrogate-assisted、classifier-assisted、昂贵优化、数据驱动优化
- 双网建模调度:双层网络、bi-level network、双网调度、双网建模、网络化系统调度、edge-cloud 协同调度
- 关键学者:Wei-Neng Chen、Jun Zhang、Feng-Feng Wei、Xiao-Qi Guo、Tai-You Chen、陈伟能
- 关键学者:Qiuzhen Lin、Yue-Jiao Gong、Jin-Kao Hao
- 关键载体:IEEE TEVC / TSC / IEEE-CAA JAS 上的进化计算论文
判断标准:主题是条目的核心内容(而非顺带提及)才加权。

## 新闻句写法
summary 是日报中唯一显示的新闻句,也会用作原文链接名称和目录标题。
用简体中文写成一句简洁、可独立理解的新闻句,通常 20–45 个汉字,最多 55 字。
- 先写清谁做了什么,再给最关键的结果或影响;只保留一条主信息,不把多个背景、数据和评价挤进一句话。
- 只保留读者理解事件所需的产品名、机构名和技术词;尽量用常见中文表达,不要整句照抄英文标题。
- 使用简体中文标点;专有名词保留官方拼写,不在中英文之间堆叠括号释义。
- 不写“值得关注”“重大动态”“引发热议”等空泛结尾,不复述打分、热度或标签。不要用感叹号制造语气。
- 对尚未证实的消息保留“据称”“可能”等限定,不把推测写成事实。
- 命中研究兴趣时,必须以“研究相关：”开头,后面仍保持一句简洁新闻句。

示例:
- 原文标题:Gemini Robotics 2.5;写法:Google 发布 Gemini Robotics 2.5，提升机器人在真实任务中的操作能力。
- 原文标题:Nvidia allegedly engineered scarcity by funding AI startups to buy its GPUs;
  写法:NVIDIA 被指资助 AI 初创公司购买自家 GPU，以制造供货紧张。

## 源 category hint
条目可能附带源级 category hint(如 "ai-research/ai-vendor")。默认采用 hint,
但如果内容明显跨类,请 override 为更合适的分类。

## 输出格式
输出 JSON 对象,包含以下字段:
{{
  "category": "分类路径,如 ai-research/ai-papers",
  "score": 8.5,
  "summary": "20–45 字的简体中文新闻句",
  "tags": ["标签1", "标签2", "标签3"]
}}

只输出 JSON,不要其他文字。"""


def analysis_user_prompt(
    title: str,
    content: str,
    feed_name: str,
    category_hint: str | None,
    published_at: datetime,
    now: datetime,
    max_chars: int = _DEFAULT_MAX_CHARS,
) -> str:
    """构建 Tier1 user prompt:条目标题 + 内容截取 + 源信息 + 发布时间(含距今天数,供时效打分)。

    content 超过 max_chars 时截取前 max_chars 字符。
    """
    truncated = content[:max_chars] if content else ""
    hint_line = f"类别提示:{category_hint}" if category_hint else "类别提示:(无,AI 自主分类)"
    age_days = max((now - published_at).days, 0)
    return f"""标题:{title}
内容:{truncated}
来源:{feed_name}
发布时间:{published_at:%Y-%m-%d}(距今 {age_days} 天)
{hint_line}"""
