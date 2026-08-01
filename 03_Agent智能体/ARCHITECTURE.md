# Construction AI Agent Platform Architecture

版本：
V2.0

目标：
构建建筑行业AI Agent平台。

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

## MaterialAgent

负责：

材料计划生成。


未来扩展：

DrawingAgent

CostAgent

QualityAgent

SafetyAgent


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