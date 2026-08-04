# SkillHub Framework Constitution：架构总纲

状态：强制执行
适用版本：SkillHub Framework V0.1 及后续兼容版本

## 1. 目标

本 Constitution 固化 SkillHub Framework 的底层职责边界。任何新代码、Skill、Knowledge、Tool 或基础设施扩展都必须遵循本文及同目录专项规范；局部实现不得绕开架构以换取短期便利。

## 2. 标准调用链

```text
用户
 ↓
SkillHub Agent
 ↓
Skill Router
 ↓
Skill
 ↓
Service Layer
 ↓
Knowledge Router / Tools
```

依赖只能沿箭头向下。下层不得反向依赖、调用或控制上层。

## 3. 强制职责边界

### SkillHub Agent

只负责理解用户任务、拆解任务、请求 Router 选择能力、调度 Skill、汇总结果。Agent 不得直接读取文件、访问 Knowledge、调用 Tool、连接外部系统或实现领域业务。

### Skill Router

只负责 Skill 注册、能力发现和任务分发。Router 可以依据显式元数据匹配 Skill，但不得执行 Skill、实现业务流程、访问 Knowledge 或调用 Tool。

### Skill

负责一个可审计的业务流程。Skill 不得调用其他 Skill，不得直接访问 Knowledge Router、知识文件、Tool 或外部系统。需要知识或外部能力时，只能通过显式注入的 Service Layer 接口。

### Service Layer

是 Skill 与基础设施之间的唯一适配边界。Service 将业务请求转换为 Knowledge Router 查询或 Tool 调用，并将结果转换为稳定数据。Service 不负责 Skill 路由，不得隐藏新的 Agent 或跨 Skill 编排。

### Knowledge Router

是全部知识访问的统一入口。当前实现支持 Markdown + INDEX；调用方不得绕过 Router 直接读取知识文件。未来可在保持查询契约的前提下替换或扩展为 RAG。

### Tools

只提供文件、API、数据库或外部系统能力，不保存业务流程、不选择 Skill、不解释用户意图。Tool 必须显式声明输入、输出、副作用与失败行为。

### MCP Server Registry

MCP Server Registry 是基础设施目录，只管理可连接 MCP Server 的稳定描述、启用状态、Transport 配置引用和 Tool 白名单。它与 Skill Registry 职责分离：Skill Registry 管理 Skill Descriptor 与能力元数据，MCP Server Registry 不保存 Skill、不参与 Skill 路由、不执行业务逻辑，也不执行 Tool。

V0.2 统一登记以下 Server：

```text
knowledge-server
filesystem-server
```

对应关系：

| Server | Service入口 | 固定Tool范围 |
|---|---|---|
| Knowledge MCP Server | KnowledgeService | `knowledge.*`固定Tool |
| FileSystem MCP Server | FileSystemService | `filesystem.*`固定Tool |

每个 Server Descriptor 至少包含：

- `server_name`：全局稳定、非随机标识；
- `server_version`：Server契约版本；
- `transport_name`：受控Transport类型；
- `enabled`：是否允许连接；
- `allowed_tools`：固定Tool白名单；
- `connect_timeout`与`max_request_timeout`：配置引用；
- `capabilities`：Tools、Resources、Prompts支持状态；
- `health_status`：连接准备状态，不包含业务健康判断；
- `metadata`：不含密钥的审计元数据。

依赖关系固定为：

```text
Service
 ↓ 使用受控server_name与tool_name
MCP Client
 ↓ 查询
MCP Server Registry
 ↓ 返回Server Descriptor
Connection Manager / Transport
```

Server Descriptor 必须由 Composition Root 显式装配。用户、Agent和Skill不得注册Server、修改Transport、覆盖endpoint或扩展Tool白名单。Knowledge MCP Server与FileSystem MCP Server不得互相调用；新增Server必须经过配置、权限、安全和架构审核。

MCP Server Registry不得保存连接对象、Transport实例、认证密钥或运行中的Server进程。连接生命周期仍由Connection Manager负责，密钥仍由环境或受控秘密系统注入。

### FileSystem基础契约预留

#### FileReference版本

FileReference 必须增加 `version` 字段，用于标识文件内容修订版本并支持并发校验、审计和来源追溯。`version`不使用随机值，也不使用本机路径；其生成策略由FileSystem基础设施统一管理，对Skill保持稳定字符串契约。

版本规则：

- 首次创建文件时建立初始版本；
- 写入或覆盖导致内容变化时产生新版本；
- 仅移动或重命名且内容未变化时保持原版本；
- 复制文件时记录新`file_id`，同时保留源文件版本与`source_file_id`；
- 删除、恢复或隔离操作不得复用已失效版本冒充当前版本；
- 破坏性写操作应支持`expected_version`，版本不匹配时拒绝执行，避免并发覆盖。

FileReference至少包含：

```text
file_id
version
area
relative_path
name
size
checksum
created_at
last_modified
source_file_id
metadata
```

#### 大文件Stream接口

V0.2 只预留大文件Stream接口，不实现流式Transport、分片持久化或异步任务。未来接口应支持：

```text
open_read_stream(file_reference, range, runtime_context)
read_chunk(stream_id, max_bytes, runtime_context)
open_write_stream(destination, expected_size, expected_version, runtime_context)
write_chunk(stream_id, sequence, content, checksum, runtime_context)
complete_stream(stream_id, final_checksum, runtime_context)
abort_stream(stream_id, runtime_context)
```

Stream必须具备有限生命周期、顺序校验、单块及总大小限制、超时、背压、checksum、显式完成/中止、资源释放和审计。Skill只接触受控`stream_id`与FileReference，不接触文件句柄、Python Path、绝对路径、Socket或Transport对象。是否启用Stream由配置化文件大小阈值决定，不得硬编码。

#### SecurityScanner Protocol

SecurityScanner 是文件安全检查的预留接口，用于病毒扫描和危险文件检测。V0.2 只定义Protocol与扫描结果契约，不实现扫描引擎、不下载病毒库、不连接外部扫描服务，也不得返回未经扫描的伪安全结论。

建议契约：

```text
scan(file_reference, scan_context) -> SecurityScanResult
```

SecurityScanResult至少包含：

- `status`：`CLEAN`、`SUSPICIOUS`、`INFECTED`、`ERROR`、`NOT_SCANNED`；
- `scanner_name`与`scanner_version`；
- `signature_version`；
- `file_id`、`file_version`与`checksum`；
- `threats`：脱敏威胁摘要；
- `scanned_at`；
- `error_code`与审计元数据。

Scanner只能通过依赖注入提供，FileSystemService、MCP Server和Tool不得自行创建具体扫描器。扫描失败策略必须配置化；用户上传、归档解压和外部来源文件在进入可信处理区前应设置扫描检查点。Scanner不执行文件、不解析其中指令、不修改原文件，也不替代WorkspacePolicy、扩展名校验或权限控制。

## 4. Knowledge 分层

Knowledge 必须区分：

- Domain Knowledge：企业经验、项目规则、领域术语与业务知识；
- Standards：法律法规、国家/行业/地方标准及正式规范。

查询顺序固定为：Domain Knowledge 优先回答，Standards 用于补充、校验和约束。两者冲突时不得静默合并，必须返回来源和冲突信息，由上层业务规则决定处理方式。

### 4.1 Knowledge MCP Server 三原语

Knowledge MCP Server 按 MCP 的 Tools、Resources 和 Prompts 三类原语划分能力。三类原语的职责不得混用，也不得改变 Skill、Service Layer 与 Knowledge Router 的既有依赖方向。

#### MCP Tools（V0.2 实现）

V0.2 只实现以下固定 Tool：

- `knowledge.query`：按 Domain Knowledge 优先、Standards 补充的固定顺序执行组合查询；
- `knowledge.search`：按受控条件检索已注册知识条目；
- `knowledge.get_document`：通过稳定 `document_id` 获取已授权文档；
- `knowledge.get_metadata`：获取文档来源、版本、状态和更新时间等元数据。

Tool 名称由 KnowledgeService 固定映射，不接受用户输入动态指定，不支持运行时动态注册。Skill 只能通过显式注入的 KnowledgeService 接口调用知识能力，不能直接调用 MCP Tool、MCP Client 或 Knowledge MCP Server。

#### MCP Resources（V0.2 预留）

未来可提供结构化知识资源标识，例如：

```text
standard://xxx
domain://xxx
```

Resources 用于让 Agent 在任务上下文和结果中引用稳定的结构化知识资源，而不是直接读取知识内容。资源解析与内容获取仍必须经过 Skill、KnowledgeService、Knowledge MCP Server 和 Knowledge Router 的受控调用链；Agent 不得直接访问文件、INDEX、Knowledge Backend 或 MCP Resource实现。

V0.2 仅预留资源URI契约，不实现Resource注册、列举、读取、订阅或动态发现能力。任何未来实现都必须保留权限校验、来源追溯、版本信息和审计记录。

#### MCP Prompts（边界说明）

Prompt 属于 Skill 业务层，用于表达特定业务任务的流程和判断，例如：

- 规范审查 Prompt；
- 方案生成 Prompt。

Prompt 不属于 Knowledge MCP Server。Knowledge MCP Server 不保存、不选择、不组合业务 Prompt，也不根据Prompt执行任务拆解、业务判断或Skill路由。Knowledge MCP Server只返回可追溯知识数据，不把Prompt或模型生成内容标记为正式知识来源。

### 4.2 KnowledgeResult Metadata

KnowledgeResult 中每个知识命中项必须携带稳定、可审计的来源元数据。基础字段至少包括：

```text
document_id
version
timestamp
source
fragment_id
knowledge_type
relevance_score
last_updated
```

字段语义：

| 字段 | 类型 | 规则 |
|---|---|---|
| `document_id` | `str` | 稳定知识文档标识，不使用文件路径替代 |
| `version` | `str` | 命中文档的明确版本 |
| `timestamp` | `datetime` | 本次来源记录或引用形成时间，必须包含时区 |
| `source` | `str` | 可核验的正式来源名称 |
| `fragment_id` | `str` | 可定位回原文的稳定片段标识 |
| `knowledge_type` | `DOMAIN \| STANDARD` | 明确区分Domain Knowledge与Standards |
| `relevance_score` | `float \| None` | 可选相关性分数；缺少可信评分时必须为`None` |
| `last_updated` | `datetime \| None` | 来源内容最后更新时间；未知时为`None`，必须包含时区 |

`relevance_score` 不得伪装成向量相似度。V0.2 的 MD + INDEX Backend 可以返回确定性关键词匹配分数，也可以返回 `None`；不得为满足字段而编造评分。`last_updated` 与查询时间分离，不得使用当前查询时间伪装来源更新时间。

`knowledge_type` 是固定枚举：

```text
DOMAIN
STANDARD
```

Templates 不属于 KnowledgeResult 的正式知识类型，不得标记为 `DOMAIN` 或 `STANDARD`。

## 5. 不可违反的架构不变量

1. 系统只有一个 SkillHub Agent，不在 Skill、Service 或 Tool 中伪装子 Agent。
2. Router 选择能力但不执行业务。
3. Skill 之间不存在调用链或隐式依赖。
4. Skill 不直接导入 Knowledge 或 Tools。
5. Knowledge 与 Standards 可追溯到来源和版本。
6. 文件类 Tool 默认保护原文件、格式和元数据。
7. 所有注册、路由、查询和外部调用必须具备可审计信息。

## 6. 审计要求

每次任务至少可追踪：任务标识、原始输入摘要、拆解结果、选择的 Skill、Skill 版本、Service 调用、知识条目及来源、Tool 调用及副作用、最终状态和错误。日志不得记录密钥或不必要的敏感原文。

## 7. 变更治理

违反职责边界的变更不得合并。需要改变本 Constitution 时，必须先更新文档、说明兼容性与迁移方案、增加架构测试，并按 `VERSION_RULES.md` 处理版本升级。
