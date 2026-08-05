# 编码规范

## 1. 基础要求

- 使用 Python 和明确的模块边界；
- 公共函数、方法、字段和返回值必须使用类型注解；
- 中文注释解释设计意图和业务边界，不复述显而易见的代码；
- 单个模块保持单一职责，禁止循环依赖和隐式全局状态；
- 新增第三方依赖必须说明必要性、许可证、版本约束和安全影响。

## 2. 依赖方向

允许：

```text
Agent → Router / Context
Router → BaseSkill / Skill metadata
Skill → Context / Domain types / Service interfaces
Service → Knowledge Router / Tool interfaces
Knowledge Router → Knowledge storage adapter
Tool → External system adapter
```

禁止反向依赖、跨层快捷导入和运行时猴子补丁。启动装配应集中在 Composition Root，不在业务模块中创建具体基础设施。

## 3. 可审计设计

关键组件必须使用稳定名称和版本。重要决策不得只存在于自由文本；路由选择、知识命中、Service 与 Tool 调用应产生结构化事件。审计标识应贯穿一次任务，但不得泄漏密钥或完整敏感数据。

## 4. 错误处理

使用明确异常表达输入、路由、业务、知识、工具和安全错误。禁止裸 `except`、静默失败和用 `None` 模糊表示多种状态。用户错误与内部错误应分层呈现。

## 5. 测试与质量门禁

新代码必须包含单元测试；跨层契约需要集成测试；架构边界需用静态扫描或测试防回归。提交前至少执行语法检查、测试、格式/空白检查和暂存范围审计。

## 6. 兼容性

公共接口、Skill 名称、Knowledge 条目标识和 Tool 名称视为契约。修改前评估调用方；破坏性变化必须提供迁移路径并按版本规范升级。
