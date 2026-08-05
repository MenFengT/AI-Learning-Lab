# Development Guide


## 技术栈

Python


## 项目规则

本项目采用单 Agent SkillHub 模式。`MaterialPlanningAgent` 是当前唯一正式业务 Agent；新能力优先新增 Skill，不新增业务 Agent。


### 文件职责

agents:

负责唯一正式 Agent 的流程决策与 Skill Router 调用。旧 Agent 文件仅用于接口兼容，禁止增加业务逻辑。


skills:

负责具体能力。


knowledge:

负责行业数据。


prompts:

负责提示词。


outputs:

负责结果。


---

## 新增功能流程


1.
判断是否属于Skill


2.
创建新的Skill


3.
Agent调用Skill


4.
增加测试


5.
Git提交


---

## 禁止事项


禁止：

- 在Agent中写大量业务代码

- 在Prompt中硬编码规则

- 在代码中写死路径


---

## Git规范


提交信息：

feat:
新增功能


refactor:
架构调整


fix:
问题修复


docs:
文档修改
