# SkillHub Framework V0.1

一个仅使用 Python 标准库实现的最小可扩展 SkillHub Framework 骨架。

## 架构

```text
用户
 ↓
SkillHub Agent
 ↓
Skill Router
 ↓
Skill
 ↓
Knowledge Router / Tools
```

当前 Demo Skill 是纯业务演示，不访问 Knowledge Router 或 Tools。Knowledge 与 Tools 作为独立扩展边界提供，未来应由执行环境或专门服务适配层提供能力，避免 Skill 与存储、文件或外部系统耦合。

## 职责边界

- `SkillHubAgent`：接收、理解和拆解任务；通过 Router 选择并调度 Skill。
- `SkillRouter`：注册和选择 Skill，不调用 Skill 的业务方法。
- `BaseSkill`：定义业务能力接口；具体 Skill 不调用其他 Skill，也不直接导入 Knowledge 或 Tools。
- `KnowledgeRouter`：统一读取 `data/knowledge/INDEX.md` 注册的 Markdown 知识，未来可替换为 RAG。
- `ToolBase`：文件、API 和外部系统能力的抽象接口。

V0.1 不包含 LangChain、LangGraph、RAG、向量数据库、多 Agent 或自动化工作流。

## 目录

```text
002_SkillHub_Framework_V0.1/
├── app/
│   ├── main.py
│   ├── core/
│   ├── skills/
│   ├── knowledge/
│   ├── tools/
│   └── config/
├── data/
├── tests/
├── requirements.txt
└── README.md
```

## 运行 Demo

在本项目目录中执行：

```powershell
python -m app.main
```

输入任意任务后，调用链为：

```text
输入任务 → SkillHubAgent → SkillRouter → DemoSkill → 输出结果
```

## 运行测试

```powershell
python -m unittest discover -s tests -v
```

## 扩展 Skill

1. 在 `app/skills/` 新建 Skill 并继承 `BaseSkill`。
2. 声明唯一 `name`、能力说明和匹配关键词。
3. 实现 `execute(context)`，不调用其他 Skill，不直接访问 Knowledge 或 Tools。
4. 在启动装配层注册到 `SkillRouter`。
