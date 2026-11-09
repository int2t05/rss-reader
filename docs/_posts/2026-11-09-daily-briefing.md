---
layout: post
title: "每日简报 · 2026-11-09"
date: 2026-11-09 06:32:24 +0800
categories: [简报]
tags: [ai-research, dev-community, research, systems, tech-news]
toc: true
---

# 每日简报 · 2026-11-09

**统计**: 49 条目

## ai-research

### [Ajeya: AI is dramatically accelerating AI research right now](https://www.alignmentforum.org/posts/8tL9f5HZxsTvn2LHp/ajeya-ai-is-dramatically-accelerating-ai-research-right-now)

- **发布**: 11-08
- **分数**: 7.5
- **摘要**: 知名对齐研究者 Ajeya 在 Alignment Forum 发文分析 AI 正显著加速 AI 研究本身,援引 Anthropic S1 中或即将触及 RSP「AI 大幅加速进展」阈值的表态
- **标签: AI 对齐, 负责任扩展政策, AI 加速 AI 研发, Anthropic**

### [基元律动发布NeoHorse-1.5-Flash Preview，Agent模型RSI进入第二轮迭代](https://www.leiphone.com/category/industrynews/tLk5dflVBL8euzAW.html)

- **发布**: 11-09
- **分数**: 7.2
- **摘要**: 基元律动发布Agent原生模型NeoHorse-1.5-Flash Preview（180B总参/6B激活，基于Qwen3.8-Flash），聚焦Agent执行与软件工程能力，并依托多模型差分诊断、对抗式环境进化与群体智能在线学习推进RSI第二轮迭代。
- **标签: 模型发布, Agent, 递归自我改进RSI, 软件工程**

### [\[One Million AI Engineer Special\] How Stanford Teaches AI-Native Engineering — Mihail Eric, Monaco](https://latent.space/p/one_million_ai_engineer_special_how_stanford_teaches_ai-native_engineering_mihail_eric_monaco/)

- **发布**: 11-08
- **分数**: 7.0
- **摘要**: 斯坦福 CS146S 第二期课程专访 Mihail Eric,探讨 AI 原生工程教学法:学生需上手陌生开源仓库并向维护者提交真实改动,反映编码智能体时代工程教育的转型
- **标签: AI 教育, AI 原生工程, 编码智能体, 斯坦福, 开源协作**

## dev-community

### [Unlocking any car from X brand in most of the world](https://shubs.io/unlocking-any-car-from-x-brand-in-most-of-the-world/)

- **发布**: 11-09
- **分数**: 7.5
- **摘要**: 安全研究者披露可远程解锁某品牌全球大部分地区汽车的漏洞,今日在 Hacker News 引发热烈讨论\(206 分、72 条评论\),是值得关注的安全技术发现。
- **标签: 信息安全, 汽车安全, 漏洞披露, Hacker News**

### [Herb Sutter: When a language’s creator and its owners strongly disagree: C++26 post-DIS, historical experience, and paths forward](https://isocpp.org/files/papers/P4454R0.pdf)

- **发布**: 11-08
- **分数**: 7.5
- **摘要**: Herb Sutter 发文探讨 C++26 DIS 之后语言创始人与标准委员会持有者之间的重大分歧,结合历史经验分析 C++ 治理的未来走向,Lobsters 社区热议中。
- **标签: C++26, Herb Sutter, 语言标准化, 社区讨论**

### [Outlook.com is rejecting email from domains without DMARC](https://mailroute.net/blog/outlook-rejecting-email-without-dmarc)

- **发布**: 11-08
- **分数**: 7.5
- **摘要**: 微软 Outlook.com 开始拒绝未配置 DMARC 域名的邮件,这一强认证政策变化对大量自建邮件域名影响重大,在 HN 引发 255 条热议。
- **标签: 邮件系统, DMARC, Outlook, 邮件投递**

### [Llama-modchip: 284B DeepSeek on 64GB RAM, no GPU](https://github.com/synchopate/llama-modchip)

- **发布**: 11-08
- **分数**: 7.5
- **摘要**: 开源项目 Llama-modchip 实现在 64GB 内存、无 GPU 环境下运行 284B 参数的 DeepSeek 模型,以 402 分登上 Hacker News 热榜并引发 180 条讨论
- **标签: LLM本地推理, 低资源部署, DeepSeek, 开源项目**

### [Claude Code Leaked 2,539 Secrets Onto GitHub. I Checked My Own Repos the Same Morning](https://dev.to/aheadkit/claude-code-leaked-2539-secrets-onto-github-i-checked-my-own-repos-the-same-morning-l39)

- **发布**: 11-09
- **分数**: 7.5
- **摘要**: Apiiro 扫描发现 10 万余个公开 GitHub 仓库中的 Claude Code 本地设置文件泄露 2,539 个密钥\(含数据库密码、AWS key 等\),其中 215 个绕过了 TruffleHog 和 GitHub Secret Scanning,作者提醒开发者自查仓库。
- **标签: Claude Code, 密钥泄露, GitHub 安全**

### [A new Go API for JSON](https://www.reddit.com/r/golang/comments/1xqtk9i/a_new_go_api_for_json/)

- **发布**: 11-08
- **分数**: 7.5
- **摘要**: Go 官方博客发布全新的 JSON v2 API,Reddit r/golang 社区热议该标准库重大更新
- **标签: Go, JSON, 标准库更新**

### [GitHub Trending 日报 · 2026-11-08](https://int2t05.github.io/auto-trend/daily/2026-11-08.html)

- **发布**: 11-08
- **分数**: 6.8
- **摘要**: GitHub 日报聚焦 agent 工程化：上下文压缩插件省 5 倍 token、Anthropic SKILL.md 跨厂商规范、Meta 开源 Astryx、Vercel 无障碍树等，主线是给 agent 修路而非比拼模型
- **标签: GitHub Trending, AI Agent, 上下文压缩, 工程实践**

### [gobwas/ws v1.5.0: Go 1.27 flate fix, OOM vuln fix, 4x faster masking with asm](https://www.reddit.com/r/golang/comments/1xq6zuj/gobwasws_v150_go_127_flate_fix_oom_vuln_fix_4x/)

- **发布**: 11-07
- **分数**: 6.5
- **摘要**: 热门 Go WebSocket 库 gobwas/ws 发布 v1.5.0,修复 Go 1.27 flate 兼容性问题与一个可致 OOM 的安全漏洞\(含 GHSA 公告\),并借助 NEON/SSE2/AVX2 SIMD 将 payload masking 性能提升至多 4 倍
- **标签: Go, WebSocket, 安全修复, 性能优化, 开源发布**

### [Proposal Accepted: Generic Sets](https://www.reddit.com/r/golang/comments/1xoe261/proposal_accepted_generic_sets/)

- **发布**: 11-05
- **分数**: 6.0
- **摘要**: Go 官方正式接受泛型集合\(Generic Sets\)提案,未来版本将为语言引入该特性
- **标签: Go, 泛型, 语言提案**

### [The future of Software Engineering is boring](https://www.reddit.com/r/golang/comments/1xqzijp/the_future_of_software_engineering_is_boring/)

- **发布**: 11-08
- **分数**: 5.0
- **摘要**: 观点文章称软件工程的未来将趋于"无聊"\(回归稳健工程实践\),在 r/golang 社区引发讨论
- **标签: 软件工程, 观点, Go 社区, 行业趋势**

### [libtmux-go 0.1: tmux client library, mcp, workspace manager for golang](https://www.reddit.com/r/golang/comments/1xpv4kk/libtmuxgo_01_tmux_client_library_mcp_workspace/)

- **发布**: 11-07
- **分数**: 5.0
- **摘要**: libtmux 的 Go 语言移植版 0.1 alpha 发布,支持 tmux 会话/窗口/窗格的类型化查询、工作区管理,并内置 MCP 服务器便于 AI 代理操作终端
- **标签: Go, tmux, MCP, 开源库**

## research

### [Two-Layer Evolutionary Scheduling for Machine Learning Jobs in Multi-Cluster Environments](https://arxiv.org/abs/2611.09093)

- **发布**: 11-09
- **分数**: 9.5
- **摘要**: 研究相关:提出 EVO-GP 双层进化在线调度方法,将多集群 GPU 环境下的大规模 ML 作业调度建模为在线多目标优化,分层解耦全局作业到集群分配与集群内 GPU 资源分配,直接命中进化计算与双网建模调度两大核心研究方向。
- **标签: 进化计算, 双层调度, 多集群GPU调度, 在线多目标优化, arXiv cs.DC**

### [The k-Clique hypothesis is dead, for good](https://arxiv.org/abs/2611.09764)

- **发布**: 11-09
- **分数**: 9.5
- **摘要**: 提出运行时间为 n^\(\(ω/3−c\)k\) 的算法解决加权 k-Clique 计数问题,推翻细粒度复杂性领域长期成立的 k-Clique 猜想,属重大理论突破
- **标签: 细粒度复杂性, 图算法, k-Clique, 矩阵乘法指数, 理论突破**

### [As Easy as Rank One: Optimal Algorithms for Matroid Secretary and Single-Sample Matroid Prophet](https://arxiv.org/abs/2611.08869)

- **发布**: 11-09
- **分数**: 9.0
- **摘要**: 论文以强形式解决了悬置多年的拟阵秘书猜想,给出达到最优竞争比 e 与 2 的算法,并同时解决单样本拟阵先知不等式问题,是在线算法与组合优化领域的重要理论突破
- **标签: 拟阵秘书问题, 先知不等式, 在线算法, 组合优化, 理论计算机科学**

### [Online Causal Configuration for Networked Systems via Doubly Robust Steady-State Learning](https://arxiv.org/abs/2611.09665)

- **发布**: 11-09
- **分数**: 9.0
- **摘要**: 研究相关:提出 CAUSAL-UCB 算法,通过干扰感知的截断双重稳健评估实现网络化系统在线因果配置与稳态学习,并给出极小极大推断误差下界,直接契合网络化系统调度研究兴趣
- **标签: 网络化系统调度, 因果推断, 双重稳健, 在线学习, arXiv-stat.ML**

### [OMCDE: Opposition-based Multi-Stage Matrix-Based Competitive Differential Evolution](https://arxiv.org/abs/2611.09167)

- **发布**: 11-09
- **分数**: 8.5
- **摘要**: 研究相关:提出 OMCDE,一种基于矩阵的竞争性差分进化算法,融合竞争驱动搜索、阶段自适应行为与对抗式初始化,在 CEC 2017 基准上达到领先性能且保持计算高效与可并行性。
- **标签: 差分进化, 进化计算, 全局优化, CEC 2017**

### [Evolutionary Architecture Search through Grammar-Based Sequence Alignment](https://arxiv.org/abs/2512.04992)

- **发布**: 11-09
- **分数**: 8.5
- **摘要**: 研究相关:提出基于文法的进化神经架构搜索方法,通过改进 Smith-Waterman 局部序列对齐算法计算架构编辑距离,实现高效交叉算子、架构损失景观分析与种群多样性追踪
- **标签: 进化计算, 神经架构搜索, 序列对齐, 交叉算子**

### [Byzantine-Robust Distributed Sparse Softmax Regression](https://arxiv.org/abs/2611.09110)

- **发布**: 11-09
- **分数**: 8.5
- **摘要**: 研究相关:提出通信高效的拜占庭鲁棒分布式稀疏 softmax 回归算法,采用坐标级 trimmed mean/median 鲁棒聚合,在亚高斯稀疏假设下 Byzantine 比例 α~1/√m 时达到与中心化 oracle 一致的收敛率。
- **标签: 分布式优化, 拜占庭容错, 高维稀疏统计, 鲁棒聚合, 收敛率理论**

### [A hierarchy of physics-embedded neural operators for structural dynamic surrogate modeling](https://arxiv.org/abs/2611.07059)

- **发布**: 11-09
- **分数**: 8.0
- **摘要**: 研究相关:提出物理嵌入神经算子层级方法\(MR/PGMON/MOSAIC\)用于结构动力学代理建模,以远低于 FEA 的成本逼近其精度,服务于大规模设计优化等昂贵优化场景,与代理辅助/数据驱动优化方向高度契合。
- **标签: 代理模型, 物理嵌入神经网络, 结构动力学, 算子学习, 昂贵优化**

### [Quasipolynomial-Time Planning for Decodable POMDPs](https://arxiv.org/abs/2611.09778)

- **发布**: 11-09
- **分数**: 7.5
- **摘要**: 提出针对 ρ-可解码 POMDP 的拟多项式时间近似规划算法,证明可解码性严格弱于可观测性且可被 ℓ1/ℓ2 可观测性蕴含,并给出最优可解码常数的多项式时间计算方法。
- **标签: POMDP, 规划算法, 计算复杂性, 强化学习理论**

### [On Lipschitz Explosion in Deep Neural Networks with Normalization: Consequences for Optimization and Adversarial Robustness](https://arxiv.org/abs/2611.08775)

- **发布**: 11-09
- **分数**: 7.5
- **摘要**: 理论证明带归一化层\(如 BatchNorm\)的深度网络即使每层范数严格受控,输入与参数 Lipschitz 常数仍可随深度指数增长,对优化保证、泛化界与对抗鲁棒性证书均有重要影响。
- **标签: Lipschitz 常数, 归一化层, 深度学习理论, 对抗鲁棒性, 优化保证**

### [Linear Bandits on Ellipsoids: Minimax Optimal Algorithms](https://arxiv.org/abs/2502.17175)

- **发布**: 11-09
- **分数**: 7.5
- **摘要**: 针对动作集为椭球体的线性随机赌博机问题,首次给出极小极大最优算法,并推导了匹配的信息论遗憾下界
- **标签: 线性赌博机, 极小极大最优, 遗憾下界**

### [Quantum-enabled measurement of gravitational forces at the milligram scale](https://arxiv.org/abs/2611.08619)

- **发布**: 11-09
- **分数**: 7.5
- **摘要**: arXiv 量子物理新论文:在毫克量级质量尺度上实现量子增强的引力测量,探索广义相对论与量子力学交汇的微观引力实验前沿
- **标签: 量子物理, 引力测量, 量子引力, arXiv**

### [Reflexive polytopes can have doubly exponentially many vertices](https://arxiv.org/abs/2611.08819)

- **发布**: 11-09
- **分数**: 7.5
- **摘要**: arXiv 数学论文通过反例推翻 2004 年关于 d 维反射多胞体顶点数上界为 6^{d/2} 的猜想,证明在 d≥8 时顶点数可达理论最大值即双指数级,且结果由 GPT-6.1 Sol 辅助发现
- **标签: 组合数学, 反射多胞体, AI辅助数学发现**

### [Jaeger conjecture and Jaeger-Zhang conjecture](https://arxiv.org/abs/2611.08862)

- **发布**: 11-09
- **分数**: 7.5
- **摘要**: arXiv 数学论文:借助 circular flow 与生成树上的小修正引理,证明负围长足够大的带符号平面图的圆色数上界,进而解决平面图情形的 Jaeger 猜想与 Jaeger-Zhang 猜想。
- **标签: 图论, 圆染色, 带符号平面图**

### [Macdonald intersections and the $N!/k$ conjecture](https://arxiv.org/abs/2611.09638)

- **发布**: 11-09
- **分数**: 7.5
- **摘要**: arXiv math.CO 组合数学论文证明 Garsia–Haiman 模交集的 Frobenius 特征公式,从而解决长期悬而未决的 N!/k 猜想,证明基于 Haiman 发展的平面点 Hilbert scheme 几何理论
- **标签: 组合数学, N!/k猜想, Macdonald多项式, Hilbert scheme, 纯数学研究**

## systems

### [从“能写代码”到“能交付”：腾讯轻量云 LoopForge 多 Agent 编排实践｜AICon北京](https://www.infoq.cn/article/wUArox9MHiAoyWPgRxpp?utm_source=rss&utm_medium=article)

- **发布**: 11-09
- **分数**: 8.5
- **摘要**: 研究相关：腾讯轻量云在 AICon 北京分享 LoopForge 多智能体编排实践，聚焦从代码生成到可交付的工程化落地路径，命中 multi-agent 核心主题并获研究兴趣加权。
- **标签: 多智能体编排, 腾讯云, AICon, 工程实践**

### [Chris van Eijk: json vs jsonb in PostgreSQL: size and speed, measured](https://postgr.es/p/9Bl)

- **发布**: 11-08
- **分数**: 7.5
- **摘要**: Chris van Eijk 在 PostgreSQL 17/18 上实测六种文档形态的 json 与 jsonb 差异:何时 jsonb 更小 23% 或更大 41%、读取速度与 GIN 索引表现
- **标签: PostgreSQL, jsonb, 数据库性能, GIN索引**

### [2.5小时一个零日，400多个root提权：Linux被AI挖成了筛子，人类逆向几周才看懂一个](https://www.infoq.cn/article/6kuDZAK0IFkKviGrGzIR?utm_source=rss&utm_medium=article)

- **发布**: 11-09
- **分数**: 7.5
- **摘要**: AI 系统以平均 2.5 小时一个的速度挖出 400 多个 Linux 内核 root 提权零日漏洞,人类逆向分析远跟不上,凸显 AI 自动化漏洞挖掘对系统安全的冲击。
- **标签: AI 安全, Linux 内核, 漏洞挖掘, 零日漏洞**

### [What should a scheduled job do when the laptop was asleep?](https://dev.to/bestaitool/what-should-a-scheduled-job-do-when-the-laptop-was-asleep-1dc4)

- **发布**: 11-09
- **分数**: 6.5
- **摘要**: 探讨笔记本休眠与任务重叠场景下定时任务的补偿与重叠策略设计,并用约170行 Python+SQLite 复刻 Temporal Schedules 的核心机制
- **标签: 任务调度, cron, Temporal, Python, SQLite**

### [Vadim Yatsenko: The Server-First Reader Pool: Exact Connection Reuse and Hot-Path Performance](https://postgr.es/p/9Bi)

- **发布**: 11-08
- **分数**: 6.5
- **摘要**: Polar Proxy 作者详解其 reader 连接池的精确连接复用与热路径性能优化设计,减少连接处理对查询响应的干扰。
- **标签: PostgreSQL, 连接池, 性能优化**

### [Harness 已经很准了，为什么还需要一个 Agent Native Database](https://www.infoq.cn/article/49JGp1l7v97riBlPpZ1q?utm_source=rss&utm_medium=article)

- **发布**: 11-09
- **分数**: 6.5
- **摘要**: InfoQ 中文文章探讨在 Harness 评测已足够精准的情况下，为何 AI Agent 时代仍需专门的 Agent Native Database，分析其架构动机与技术价值。
- **标签: Agent Native Database, AI 基础设施, 数据库架构, InfoQ**

### [JIT bitmap text rendering for microcontrollers](https://linebender.org/blog/jit-bitmap-text/)

- **发布**: 11-08
- **分数**: 6.0
- **摘要**: Linebender 团队发布技术博客,介绍面向微控制器的 JIT 位图文本渲染方案,探讨嵌入式设备上字形渲染的性能优化,在 Hacker News 获得 96 分关注。
- **标签: 嵌入式, 文本渲染, 微控制器, 图形学, 工程实践**

### [Maki Majima: Two migrations collide: one loud failure, one silent one](https://postgr.es/p/9Bm)

- **发布**: 11-09
- **分数**: 6.0
- **摘要**: 博主在 PostgreSQL 16 上实测两个分支各自新增迁移文件合并后的行为,展示一种报错的显性冲突和一种更危险的静默冲突,论证迁移冲突只能在按环境的 apply 阶段解决。
- **标签: 数据库迁移, PostgreSQL, 工程实践**

### [当 Flutter 遇上鸿蒙：一次“杂志级”混合开发实战](https://www.infoq.cn/article/R6kE7tmckRcxpNj11mBb?utm_source=rss&utm_medium=article)

- **发布**: 11-09
- **分数**: 6.0
- **摘要**: InfoQ 发布 Flutter 与鸿蒙混合开发实战文章,分享杂志级复杂界面在 HarmonyOS 上的工程落地经验
- **标签: Flutter, 鸿蒙, 混合开发**

### [得票最高的功能终于来了，OpenTofu 开始内置代码检查](https://www.infoq.cn/article/jXBV6ib9g8g2Gw6kDaYh?utm_source=rss&utm_medium=article)

- **发布**: 11-09
- **分数**: 5.5
- **摘要**: Terraform 开源分支 OpenTofu 发布社区得票最高的内置代码检查\(lint\)功能,提升 IaC 工程体验。
- **标签: OpenTofu, 基础设施即代码, 代码检查**

## tech-news

### [Nvidia Board of Directors Is Investigating Jensen Huang](https://nvidianews.nvidia.com/news/statement-from-nvidia-board-of-directors)

- **发布**: 11-08
- **分数**: 8.5
- **摘要**: Nvidia 官方宣布董事会正在调查 CEO 黄仁勋,这一重大公司治理事件引发科技界强烈关注
- **标签: NVIDIA, 黄仁勋, 公司治理, AI 芯片**

### [Goldman Sachs is pulling Claude Code from its bankers and traders](https://www.thestateofai.com/news/goldman-sachs-claude-code-traders-bankers)

- **发布**: 11-08
- **分数**: 7.5
- **摘要**: 高盛决定从银行家与交易员处撤下 Claude Code 编程工具,这一头部金融机构对 AI 编程工具的收紧政策引发广泛讨论\(HN 684 分、384 评论\)
- **标签: Claude Code, 高盛, 企业AI政策, Anthropic**

### [Nvidia is investigating Jensen Huang’s relationship with a Chinese spy](https://www.theverge.com/ai-artificial-intelligence/1029562/nvidia-investigating-jensen-huang-relationship-chinese-spy)

- **发布**: 11-08
- **分数**: 7.5
- **摘要**: 英伟达董事会宣布就 CEO 黄仁勋与被中国国安部招募的 Megaspeed 高管 Alice Huang 的关系启动独立调查,涉及重大企业治理与地缘政治风险。
- **标签: Nvidia, 黄仁勋, 商业间谍, 董事会调查, 地缘政治**

### [Edge AI Daily 早报（11月9日）](https://www.tmtpost.com/8197806.html)

- **发布**: 11-09
- **分数**: 7.0
- **摘要**: AI 行业日报:美国46项数据中心公投否决扩张标志 AI 基建进入许可时代,纳指单日暴跌引发亚洲熔断,Anthropic 斥34亿美元购燃气发电机、OpenAI 算力支出预估上调至6140亿美元。
- **标签: AI基础设施, 市场行情, 行业日报, 政策监管**

### [Apple is racing to make Siri more agentic](https://www.theverge.com/ai-artificial-intelligence/1029552/apple-siri-ai-agentic)

- **发布**: 11-08
- **分数**: 6.5
- **摘要**: 彭博 Mark Gurman 爆料:苹果 CEO John Ternus 正施压 Craig Federighi 加速 Siri 的 agentic 化,打造可抗衡 OpenAI 与 Meta 的 AI 智能体。
- **标签: Apple, Siri, AI Agent, 科技新闻**

### [英伟达在韩举办 AI Day 活动，韩国政府、三星、LG 电子、现代汽车集团等排队合作](https://www.ithome.com/1/024/217.htm)

- **发布**: 11-09
- **分数**: 6.5
- **摘要**: 英伟达在首尔举办 AI Day，宣布与韩国政府、三星、SK 电信等围绕主权 AI 生态、NVLink Fusion 及基础模型推理优化的多项合作
- **标签: 英伟达, 主权AI, NVLink Fusion, 韩国**

### [IDC：2026 年全球灵巧手出货量约 2.5 万台，中国厂商占比超 85%](https://www.ithome.com/1/024/146.htm)

- **发布**: 11-09
- **分数**: 6.5
- **摘要**: IDC 发布报告预计 2026 年全球灵巧手出货量约 2.5 万台、中国厂商占比超 85%,行业竞争正从硬件参数转向精细操作、感知控制及与具身智能模型的协同能力。
- **标签: 灵巧手, 人形机器人, 具身智能, IDC 报告, 市场分析**

### [M6 MacBook Pro 体验：38 块的灵魂，一万五的身体](https://www.ifanr.com/1688127?utm_source=rss&utm_medium=rss&utm_campaign=)

- **发布**: 11-09
- **分数**: 6.0
- **摘要**: 爱范儿发布 M6 MacBook Pro 上手体验，认为苹果下一阶段的战略重点是面向创作人群构筑生态围城。
- **标签: 苹果, M6 MacBook Pro, 产品评测, 消费电子**

### [Apple capped engineers at a $200 daily AI budget](https://www.stork.ai/newsletter/2026-11-08-apple-capped-engineers-at-a-200-daily-ai-budget#story-1)

- **发布**: 11-09
- **分数**: 5.5
- **摘要**: 苹果将工程师每日 AI 工具使用预算上限设为 200 美元,反映大型科技公司对 AI 使用成本的管控策略,属一般性行业动态
- **标签: Apple, AI 成本管控, 企业 AI 政策**

### [乘联分会：10 月新能源乘用车出口 58.2 万辆同比增长 144.7%，比亚迪、奇瑞、吉利前三](https://www.ithome.com/1/024/215.htm)

- **发布**: 11-09
- **分数**: 5.5
- **摘要**: 乘联分会发布 10 月新能源乘用车出口数据:58.2 万辆、同比增长 144.7%,比亚迪、奇瑞、吉利位列前三,新能源占乘用车出口 62.8%。
- **标签: 新能源汽车, 汽车出口, 乘联分会, 行业数据**
