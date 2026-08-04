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

### KnowledgeResult 元数据

每个命中项至少包含：

- `document_id`：稳定文档标识，不得使用本机路径或相对文件路径作为对外标识；
- `version`：实际命中文档版本；
- `timestamp`：来源记录或引用形成时间，使用带时区的时间值；
- `source`：可核验的正式来源；
- `fragment_id`：可回溯到原文的片段标识；
- `knowledge_type`：只能是 `DOMAIN` 或 `STANDARD`；
- `relevance_score: float | None`：可信相关性分数，不具备可信评分时返回 `None`；
- `last_updated: datetime | None`：来源内容最后更新时间，未知时返回 `None`。

V0.2 不使用向量检索，`relevance_score` 只能来自可解释的确定性匹配规则，不能标记或暗示为向量相似度。`timestamp`、`last_updated` 与实际查询时间必须区分，不得用查询时间覆盖或伪造来源时间。

Domain与Standards的命中结果必须分别保留各自的 `knowledge_type` 和来源信息。发现冲突时，冲突两侧都必须返回完整来源元数据，不得只保留合并后的单一来源。

## 7. MCP 原语边界

V0.2 Knowledge MCP Server 只实现固定Tools：

- `knowledge.query`；
- `knowledge.search`；
- `knowledge.get_document`；
- `knowledge.get_metadata`。

Skill只能通过KnowledgeService调用这些能力，不得直接访问MCP Tool。

MCP Resources仅预留 `standard://xxx` 和 `domain://xxx` 等结构化引用契约，V0.2不实现读取或发现。Agent可以持有资源引用，但不能绕过Skill和KnowledgeService解析资源内容。

MCP Prompts不属于Knowledge MCP Server。规范审查、方案生成等Prompt属于Skill业务层，不得存放在知识Backend中，也不得作为正式知识来源。

## 8. 更新治理

知识更新必须经过来源核验、版本记录和生效状态检查。删除或替换条目时需保留迁移说明；过期标准必须标记失效，不得物理覆盖导致历史任务不可追溯。
