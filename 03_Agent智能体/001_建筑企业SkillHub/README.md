# 001 建筑企业 SkillHub

面向建筑企业的可扩展能力中心。当前由一个 `MaterialPlanningAgent` 通过 Skill Router 编排全部能力，完成：

- 施工进度解析；
- 阶段材料分析；
- 月材料计划生成；
- JSON 结果输出。

## 运行

```powershell
python main.py
```

也可以传入施工计划文件：

```powershell
python main.py "path/to/plan.xlsx"
```

默认测试文件位于 `test_data/`，运行结果写入项目自己的 `outputs/`。

## 架构

```text
MaterialPlanningAgent
  → SkillRouter
    → SkillRegistry
      → FileParserSkill
      → ProgressExtractionSkill
      → MaterialAnalysisSkill
      → MonthlyMaterialSkill
      → JsonExportSkill
```

`MaterialPlanningAgent` 是当前唯一正式业务 Agent。`progress_agent.py`、`material_agent.py` 和 `schedule_material_agent.py` 仅保留 P1/P2 旧接口兼容，不代表多 Agent 架构。

详细说明见 [ARCHITECTURE_V2.1.md](./ARCHITECTURE_V2.1.md)。
