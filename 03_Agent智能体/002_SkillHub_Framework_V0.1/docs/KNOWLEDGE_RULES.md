# Knowledge 管理规范

## 1. 知识分类

知识必须在逻辑和目录上区分：

- Domain Knowledge：企业制度、项目经验、业务术语、领域映射和内部规则；
- Standards：法律法规、强制性条文、国家/行业/地方标准及正式技术规范；
- Templates：输出模板，仅定义结构和表达，不作为事实来源。

禁止把 Standards 混入 Domain Knowledge，禁止把 Prompt 或代码当作知识库。

## 2. 统一访问

所有知识查询必须经过 Knowledge Router。Agent、Router、Skill 和 Tool 不得直接读取知识文件。Service Layer 是业务侧唯一允许调用 Knowledge Router 的位置。

## 3. 查询顺序

固定顺序为：

1. 查询 Domain Knowledge，获得业务上下文和企业规则；
2. 查询 Standards，补充合规要求并校验 Domain 结果；
3. 合并时保留来源、版本、命中条目和冲突状态。

Standards 不替代业务上下文，Domain Knowledge 也不得覆盖强制标准。发现冲突必须显式报告。

## 4. MD + INDEX 规则

V0.1 使用 Markdown 文件承载内容，INDEX 维护稳定条目标识、相对路径、类型、版本、来源和状态。知识文件只能通过相对路径注册，必须防止目录穿越；失效条目不得静默返回。

建议元数据至少包含：`id`、`title`、`category`、`version`、`source`、`effective_date`、`status`、`path`。

## 5. RAG 平滑升级

未来引入 RAG 时，必须保持 Knowledge Router 的上层查询契约稳定。向量检索、切片、Embedding 和重排属于 Router 内部实现，不得泄漏到 Skill。MD + INDEX 应继续作为可审计原文和索引元数据来源。

## 6. 来源与审计

每次查询必须可记录：查询条件、Domain/Standards 查询顺序、命中条目、来源版本、引用片段标识、冲突与降级情况。不得把模型生成内容标记为正式知识来源。

## 7. 更新治理

知识更新必须经过来源核验、版本记录和生效状态检查。删除或替换条目时需保留迁移说明；过期标准必须标记失效，不得物理覆盖导致历史任务不可追溯。
