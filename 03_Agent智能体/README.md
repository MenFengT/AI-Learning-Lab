# Agent 智能体项目

本目录用于承载多个相互独立的 Agent 项目。

## 项目列表

| 编号 | 项目 | 架构 | 状态 |
|---|---|---|---|
| 001 | [建筑企业 SkillHub](./001_建筑企业SkillHub/) | 单 Agent + SkillHub | 开发中 |
| 002 | [SkillHub Framework V0.1](./002_SkillHub_Framework_V0.1/) | Framework 工程骨架 | 可运行 Demo |

每个项目独立管理自己的 Agent、Skills、Knowledge、Prompts、测试数据和输出。

## SkillHub Framework Constitution

`002_SkillHub_Framework_V0.1/docs/` 固化 Framework 的架构宪章与开发规范，后续 Agent、Skill、Knowledge、Service 和 Tool 开发必须遵守：

- [架构总纲](./002_SkillHub_Framework_V0.1/docs/ARCHITECTURE.md)
- [Skill 规范](./002_SkillHub_Framework_V0.1/docs/SKILL_RULES.md)
- [Knowledge 规范](./002_SkillHub_Framework_V0.1/docs/KNOWLEDGE_RULES.md)
- [Tool 规范](./002_SkillHub_Framework_V0.1/docs/TOOL_RULES.md)
- [编码规范](./002_SkillHub_Framework_V0.1/docs/CODING_RULES.md)
- [安全规范](./002_SkillHub_Framework_V0.1/docs/SECURITY_RULES.md)
- [版本规范](./002_SkillHub_Framework_V0.1/docs/VERSION_RULES.md)
- [开发指南](./002_SkillHub_Framework_V0.1/docs/DEVELOPMENT_GUIDE.md)

根目录 `outputs/` 是目录迁移前保留的历史运行产物，不属于新的项目代码结构。
