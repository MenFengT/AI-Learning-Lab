# Construction AI Agent Platform Architecture

版本：
V2.0

目标：
构建建筑行业AI Agent平台。

项目位置：
`03_Agent智能体/001_建筑企业SkillHub/`

当前阶段：
实现材料计划Agent。

---

# 核心设计原则

## Agent负责决策

Agent只负责：

- 理解用户需求
- 判断任务流程
- 调用Skill
- 汇总结果


Agent禁止：

- 直接解析文件
- 直接计算材料
- 直接生成Excel
- 存储行业规则


---

# Skill负责执行

所有具体能力必须放入Skill。


例如：

skills/

    parser_skill

    progress_skill

    material_skill

    export_skill


Skill负责：

- 文件处理
- 数据转换
- 业务计算
- 输出生成


---

# Knowledge知识库

行业知识必须独立。


knowledge/

    material/

    rules/

    templates/


禁止：

把建筑规则写死在代码。


---

# 当前Agent

## MaterialPlanningAgent

负责：

材料计划生成。

当前采用单 Agent SkillHub 模式，不新增业务 Agent。

未来图纸、成本、质量、安全能力优先扩展为 Drawing Skill、Cost Skill、Quality Skill、Safety Skill，并注册到 SkillHub。


---

# 数据流

用户输入

↓

Agent

↓

Skill Router

↓

Skills

↓

Knowledge

↓

Output


---

# 开发原则

1. 优先保持架构清晰
2. 功能新增优先增加Skill
3. 不随意增加Agent
4. Prompt必须外置
5. 所有修改必须Git提交
