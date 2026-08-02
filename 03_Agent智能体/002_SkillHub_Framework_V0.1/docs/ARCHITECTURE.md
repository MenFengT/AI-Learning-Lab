# SkillHub Framework Constitution：架构总纲

状态：强制执行
适用版本：SkillHub Framework V0.1 及后续兼容版本

## 1. 目标

本 Constitution 固化 SkillHub Framework 的底层职责边界。任何新代码、Skill、Knowledge、Tool 或基础设施扩展都必须遵循本文及同目录专项规范；局部实现不得绕开架构以换取短期便利。

## 2. 标准调用链

```text
用户
 ↓
SkillHub Agent
 ↓
Skill Router
 ↓
Skill
 ↓
Service Layer
 ↓
Knowledge Router / Tools
```

依赖只能沿箭头向下。下层不得反向依赖、调用或控制上层。

## 3. 强制职责边界

### SkillHub Agent

只负责理解用户任务、拆解任务、请求 Router 选择能力、调度 Skill、汇总结果。Agent 不得直接读取文件、访问 Knowledge、调用 Tool、连接外部系统或实现领域业务。

### Skill Router

只负责 Skill 注册、能力发现和任务分发。Router 可以依据显式元数据匹配 Skill，但不得执行 Skill、实现业务流程、访问 Knowledge 或调用 Tool。

### Skill

负责一个可审计的业务流程。Skill 不得调用其他 Skill，不得直接访问 Knowledge Router、知识文件、Tool 或外部系统。需要知识或外部能力时，只能通过显式注入的 Service Layer 接口。

### Service Layer

是 Skill 与基础设施之间的唯一适配边界。Service 将业务请求转换为 Knowledge Router 查询或 Tool 调用，并将结果转换为稳定数据。Service 不负责 Skill 路由，不得隐藏新的 Agent 或跨 Skill 编排。

### Knowledge Router

是全部知识访问的统一入口。当前实现支持 Markdown + INDEX；调用方不得绕过 Router 直接读取知识文件。未来可在保持查询契约的前提下替换或扩展为 RAG。

### Tools

只提供文件、API、数据库或外部系统能力，不保存业务流程、不选择 Skill、不解释用户意图。Tool 必须显式声明输入、输出、副作用与失败行为。

## 4. Knowledge 分层

Knowledge 必须区分：

- Domain Knowledge：企业经验、项目规则、领域术语与业务知识；
- Standards：法律法规、国家/行业/地方标准及正式规范。

查询顺序固定为：Domain Knowledge 优先回答，Standards 用于补充、校验和约束。两者冲突时不得静默合并，必须返回来源和冲突信息，由上层业务规则决定处理方式。

## 5. 不可违反的架构不变量

1. 系统只有一个 SkillHub Agent，不在 Skill、Service 或 Tool 中伪装子 Agent。
2. Router 选择能力但不执行业务。
3. Skill 之间不存在调用链或隐式依赖。
4. Skill 不直接导入 Knowledge 或 Tools。
5. Knowledge 与 Standards 可追溯到来源和版本。
6. 文件类 Tool 默认保护原文件、格式和元数据。
7. 所有注册、路由、查询和外部调用必须具备可审计信息。

## 6. 审计要求

每次任务至少可追踪：任务标识、原始输入摘要、拆解结果、选择的 Skill、Skill 版本、Service 调用、知识条目及来源、Tool 调用及副作用、最终状态和错误。日志不得记录密钥或不必要的敏感原文。

## 7. 变更治理

违反职责边界的变更不得合并。需要改变本 Constitution 时，必须先更新文档、说明兼容性与迁移方案、增加架构测试，并按 `VERSION_RULES.md` 处理版本升级。
