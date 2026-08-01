# 建筑料账Agent架构规范


## 总体原则

采用 Agent + Skill 架构


## Agent职责

Agent负责:

- 理解用户需求
- 制定任务流程
- 调用Skill


禁止:

- 直接处理文件
- 写业务计算代码


## Skill职责

Skill负责:

- 单一能力实现

例如:

progress_skill:
施工进度解析

drawing_skill:
图纸解析

excel_skill:
表格生成


## Prompt规范

所有提示词必须存放:

/prompts

禁止写入Python


## 数据规范

Agent之间使用JSON通信
