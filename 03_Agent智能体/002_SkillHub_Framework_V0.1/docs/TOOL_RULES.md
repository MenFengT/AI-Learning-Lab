# Tool 开发规范

## 1. 定位

Tool 只封装外部能力，包括文件处理、API 调用、数据库访问和第三方系统接口。Tool 不理解用户任务、不选择 Skill、不保存领域业务规则、不编排业务流程。

## 2. 调用边界

标准依赖为：

```text
Skill → Service Layer → Tool
```

Agent、Skill Router 和 Skill 不得直接调用 Tool。Service 负责参数转换、权限判断和结果归一化。

## 3. 接口要求

每个 Tool 必须声明名称、用途、输入输出类型、副作用、超时、重试策略、幂等性和异常。外部失败不得伪装成业务成功。

## 4. 文件保护

文件处理默认遵循非破坏原则：

1. 原文件只读，禁止原地覆盖；
2. 输出写入明确的新路径或临时文件，并采用原子替换策略；
3. 保留原格式、编码、公式、样式、元数据和目录结构，除非任务明确要求改变；
4. 写入前验证目标路径，禁止目录穿越和不受控通配符；
5. 覆盖、删除、移动等破坏性动作必须显式授权并保留审计记录；
6. 失败时清理临时产物，不留下看似成功的半成品。

## 5. API 与外部系统

密钥只能来自受控配置或秘密管理系统，不得写入代码、日志或测试数据。调用必须设置超时，重试只适用于可安全重试的操作；写操作需防止重复提交。

## 6. 审计

记录 Tool 名称和版本、调用方 Service、输入摘要、目标系统、开始/结束时间、结果状态、副作用和错误分类。敏感字段必须脱敏。

## 7. 测试

测试至少覆盖成功、超时、权限失败、外部错误、幂等行为和文件回滚。文件测试使用副本或临时目录，禁止操作真实原文件。

## 8. MCP Server Registry

Knowledge MCP Server与FileSystem MCP Server必须通过统一MCP Server Registry声明。Registry只保存不可执行的Server Descriptor，不保存连接、Transport实例、Skill、业务状态或密钥。

Server Descriptor必须声明：稳定`server_name`、版本、Transport配置引用、启用状态、固定Tool白名单、timeout边界、能力类型和健康状态。MCP Client只能调用Registry中已启用且Tool位于白名单的Server。用户、Agent、Skill和外部响应不得动态注册Server或Tool。

固定边界：

```text
KnowledgeService → knowledge-server → knowledge.*
FileSystemService → filesystem-server → filesystem.*
```

Tool不得跨Server调用其他Tool，不得通过别名或用户参数绕过白名单。新增Server或Tool必须更新契约、权限、审计和测试。

## 9. FileReference版本规范

文件类Tool返回的FileReference必须包含`version`。版本表示内容修订，不表示路径修订：

- 内容写入或覆盖产生新版本；
- 移动和重命名不改变内容版本；
- 复制产生新`file_id`并保留源版本关系；
- 覆盖、移动前可使用`expected_version`进行并发校验；
- 版本冲突必须明确失败，不得静默覆盖。

Tool内部真实路径不得作为`file_id`或`version`返回。每次副作用审计必须记录操作前后版本和checksum。

## 10. 大文件Stream预留

V0.2只预留Stream Protocol，不实现。未来大文件读写必须采用受控stream_id、分块大小限制、序号校验、总大小限制、timeout、checksum、背压、显式完成/中止和可靠资源释放。

Stream接口不得向Skill暴露文件句柄、Path、绝对路径、Transport或底层流对象。中止、超时或校验失败时必须清理临时产物，不得把半成品标记为成功文件。

## 11. SecurityScanner预留

文件Tool应预留SecurityScanner Protocol注入点，用于病毒扫描和危险文件检测。V0.2只定义接口，不实现扫描引擎。

扫描器必须针对明确的`file_id + version + checksum`返回结构化结果；不得执行文件、修改原文件、记录完整文件内容或伪造`CLEAN`结果。`INFECTED`和`SUSPICIOUS`文件不得进入可信processing/output流程，扫描错误必须按配置化安全策略处理并记录审计事件。
