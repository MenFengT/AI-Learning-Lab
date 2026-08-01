# Construction AI Agent Framework Architecture

版本：`v2.1-agent-framework`

基线版本：`v2.0-agent-skill`

## 目标

将静态 Agent + Skill 调用升级为可注册、可路由、可扩展的 Agent Framework，同时保持材料计划现有调用流程与输出不变。

## 核心原则

### Agent

Agent 负责：

- 理解任务和决定执行顺序；
- 通过 `SkillRouter` 调用能力；
- 传递上下文并汇总结果。

Agent 禁止：

- 导入或实例化具体 Skill；
- 直接解析文件或调用模型；
- 编写业务计算和输出逻辑；
- 保存行业知识。

### Skill

所有 Skill 必须：

- 继承 `BaseSkill`；
- 声明唯一且稳定的 `name`；
- 通过 `run()` 提供单一能力；
- 由装配层注册，不能由 Agent 直接创建。

### Registry 与 Router

`SkillRegistry` 负责：

- 注册 Skill 实例；
- 校验 Skill 类型和名称；
- 阻止重复注册；
- 按名称查找 Skill。

`SkillRouter` 负责：

- 接收 Agent 的能力名称与参数；
- 从 Registry 查找 Skill；
- 调用 Skill 并返回原始结果。

Router 不修改业务数据，不改变 Skill 输出。

## 组件结构

```text
03_Agent智能体/
├── agents/
│   ├── material_planning_agent.py
│   ├── progress_agent.py
│   ├── material_agent.py
│   └── schedule_material_agent.py
├── skills/
│   ├── base.py
│   ├── registry.py
│   ├── router.py
│   ├── bootstrap.py
│   ├── parser_skill.py
│   ├── progress_skill.py
│   ├── material_skill.py
│   ├── schedule_skill.py
│   └── export_skill.py
├── knowledge/
├── prompts/
├── outputs/
└── tests/
```

## 运行时数据流

```text
main.py
  → create_skill_registry(client)
  → SkillRouter(registry)
  → MaterialPlanningAgent(router)
      → router.route("file_parser")
      → router.route("progress_extraction")
      → router.route("material_analysis")
      → router.route("monthly_material")
      → router.route("json_export")
```

当前结果结构保持为：

```json
{
  "progress": {},
  "material_plan": {},
  "monthly_material_plan": ""
}
```

月材料计划继续保留 v2.0 的原始文本返回类型，P2 不处理数据契约升级。

## 当前 Skill 注册表

| Skill name | 实现 | 职责 |
|---|---|---|
| `file_parser` | `FileParserSkill` | 文件内容提取 |
| `progress_extraction` | `ProgressExtractionSkill` | 施工进度结构化 |
| `material_analysis` | `MaterialAnalysisSkill` | 阶段材料分析 |
| `monthly_material` | `MonthlyMaterialSkill` | 月材料计划生成 |
| `json_export` | `JsonExportSkill` | 保持现有 JSON 输出 |

## 扩展新 Skill

1. 新 Skill 继承 `BaseSkill`。
2. 设置不重复的 `name`。
3. 实现 `run()`。
4. 在 `skills/bootstrap.py` 的装配函数中注册。
5. Agent 只通过 Router 使用名称调用。
6. 增加 Registry、Router 和业务流程测试。

示例：

```python
class DrawingParseSkill(BaseSkill):
    name = "drawing_parse"

    def run(self, file_path):
        ...
```

## 扩展新 Agent

DrawingAgent、CostAgent 等新 Agent 必须通过构造参数接收 `SkillRouter`。为兼容旧调用方式，可以委托装配函数创建 Router，但 Agent 文件中不得引用具体 Skill 类。

推荐调用形式：

```python
router = create_skill_router(client)
agent = DrawingAgent(router=router)
result = agent.run(task)
```

## 兼容策略

- 保留 P1 的三个兼容 Agent 类及 `run()` 参数；
- 保留 `MaterialPlanningAgent(client)` 的兼容构造方式；
- 保留现有 Skill 的业务实现；
- 保留输出文件名、写入顺序和返回类型；
- Framework 只改变能力发现与调用方式，不改变业务结果。

## 后续边界

以下内容不属于 P2：

- JSON Schema 和领域模型；
- LLM Gateway；
- 动态意图识别；
- 自动扫描或插件加载；
- 月材料计划字符串到对象的迁移；
- DrawingAgent、CostAgent 的具体业务实现。
