# SkillHub 开发指南

## 1. 开发前

1. 阅读本目录全部 Constitution 文档；
2. 明确需求属于 Agent、Router、Skill、Service、Knowledge Router 还是 Tool；
3. 优先扩展 Skill，不新增 Agent；
4. 定义输入、输出、错误、副作用、权限与审计事件；
5. 评估是否影响公共契约和版本。

## 2. 新 Skill 流程

1. 建立单一业务目标和稳定名称；
2. 定义类型化输入输出；
3. 将知识/外部能力需求定义为 Service 接口；
4. 实现 Skill，禁止调用其他 Skill 或直接访问 Knowledge/Tools；
5. 在 Composition Root 注册到 Router；
6. 添加业务、失败和架构边界测试；
7. 更新 README、能力清单和版本记录。

## 3. 新 Knowledge 流程

1. 判定为 Domain Knowledge 或 Standards；
2. 核验来源、版本、生效日期和授权；
3. 新增 Markdown 原文并登记 INDEX；
4. 验证 Domain 优先、Standards 补充的查询行为；
5. 测试缺失、冲突、过期和路径越界。

## 4. 新 Tool 流程

1. 明确外部能力和副作用；
2. 继承 Tool 抽象并定义类型契约；
3. 实现超时、权限、幂等、回滚和脱敏；
4. 文件处理使用副本/临时文件，保护原文件与格式；
5. 通过 Service 暴露给 Skill，禁止 Skill 直接调用；
6. 使用 mock、sandbox 或临时目录测试。

## 5. 提交前门禁

- 所有测试通过；
- Agent 仅理解、拆解、调度；
- Router 仅注册与分发；
- Skill 无 Skill-to-Skill 调用；
- Skill 无 Knowledge/Tools 直接依赖；
- Knowledge 分类、查询顺序和来源正确；
- Tool 副作用和文件保护已验证；
- 类型、错误、安全和审计信息完整；
- `git diff --cached --check` 通过；
- 暂存区不包含运行产物、密钥或范围外文件。

## 6. 审查问题

审查者应能回答：任务如何路由、为何选择该 Skill、使用了哪些知识版本、调用了哪些外部能力、产生了什么副作用、失败如何恢复、结果能否复现。

## 7. 完成定义

代码、测试、文档、版本和审计契约同时完成才算交付。任何通过跨层调用实现的“可运行”结果都不满足完成定义。

## 8. README 维护规范

README 是 Project Dashboard（项目驾驶舱），用于呈现项目当前状态和决策所需的稳定信息，不作为开发日志。

重大版本更新和核心模块状态变化必须同步维护 README，至少更新：

- 当前版本；
- 架构状态；
- 模块完成情况；
- 当前开发任务；
- Roadmap；
- Documentation 与 Architecture Freeze 信息。

单个函数修改、Bug 修复、参数调整和内部代码重构不需要逐项写入 README，应通过 Git commit 和 CHANGELOG 管理。

禁止把 README 写成按时间排列的开发日志。详细维护标准见 `README_MAINTENANCE_RULES.md`。

## 9. 代码工程规范

所有 Codex 任务和人工开发必须遵守 `CODING_STANDARDS.md`。开始实现前，应确认 Python 3.11 环境、数据契约、模块职责、配置来源、异常策略、日志字段和测试方案。

### 强制要求

- 为跨模块接口明确 Input Schema 与 Output Schema；
- 未经评审不得增加、删除字段或修改字段类型；
- 文件 I/O、网络、MCP 和 LLM 调用必须包含异常、超时、有限重试和资源释放；
- 使用依赖注入，禁止业务模块硬编码基础设施；
- 日志按 INFO/ERROR 分级，并支持 `trace_id`、`task_id`、`doc_id`、`page`、`skill_name`；
- 文件批处理预留异步执行接口，禁止固化长时间阻塞模式；
- Word、Excel、PDF、CAD 和文本切片参数必须配置化并保留 source metadata；
- API Key、路径和运行参数统一由 config/environment 提供；
- Agent、Skill、Service、MCP Server 必须遵守 Constitution 职责边界。

### 开发任务交付

交付前先说明实现思路、架构影响和限制，再提供完整可运行代码与测试证据。禁止用残缺代码或 Demo 替代要求的正式实现；无法满足的数据契约或环境能力必须明确报告。

### 演进兼容

接口设计应支持 MD → RAG、Local Queue → Redis、Single Agent → Multi Agent 的未来迁移，但不得未经 Constitution 和版本评审提前改变当前冻结架构。
