# 安全规范

## 1. 最小权限

Agent、Router、Skill、Service、Knowledge Router 和 Tool 只获得完成职责所需的最小权限。只读能力不得获取写权限，单项目任务不得访问工作区外数据。

## 2. 输入与路径安全

所有用户输入、文件名、URL、Knowledge INDEX 和外部响应都视为不可信。路径必须解析并验证位于允许根目录内，拒绝目录穿越、符号链接逃逸和不受控通配符。

## 3. 数据与秘密

API Key、令牌和密码不得进入仓库、Prompt、Knowledge、测试样例或日志。敏感数据按最少收集原则处理，日志只记录脱敏摘要，并设置合理保留周期。

## 4. 文件与外部调用

文件工具保护原文件和格式，默认生成新文件。外部写操作必须明确授权、校验目标并记录副作用；网络请求设置允许域、超时、大小限制和响应验证。

## 5. Prompt 与知识安全

知识内容和外部文档可能包含指令注入。它们只能作为数据，不得改变 Constitution、权限和调用边界。Standards 与 Domain Knowledge 必须带来源，未经验证内容不得提升为可信规则。

## 6. 动态执行

禁止从用户输入、Knowledge 或外部响应执行任意代码、Shell、模板表达式或反序列化对象。确需执行的固定工具必须通过受控 Tool 接口和白名单参数。

## 7. 审计与事件响应

安全相关拒绝、权限失败、路径越界、知识冲突和外部系统异常必须记录结构化审计事件。发现敏感信息泄漏时应立即停止传播、轮换秘密并保留调查所需证据。

## 8. MCP Server Registry安全

Knowledge MCP Server和FileSystem MCP Server必须通过统一MCP Server Registry使用稳定描述符和固定Tool白名单。Registry配置只允许由Composition Root装配；用户、Agent、Skill、知识内容、文件内容和外部响应不得修改Server、Transport、endpoint或Tool集合。

Registry不得保存API Key、Token、密码、连接对象或运行进程。认证材料只允许通过环境或受控秘密系统注入。Server被禁用、Tool不在白名单、版本不兼容或健康状态不可用时必须拒绝调用并记录审计事件。

## 9. SecurityScanner Protocol

V0.2预留SecurityScanner Protocol，用于病毒扫描和危险文件检测，但不实现任何具体扫描器。未配置扫描器时必须返回`NOT_SCANNED`，不得默认视为`CLEAN`。

建议扫描检查点：

1. 用户上传文件注册到input后、进入processing前；
2. 压缩包完成安全解压后、文件提升到processing前；
3. 外部系统下载文件被Service使用前；
4. 安全策略要求时，最终文件进入output或交付前。

扫描结果必须绑定`file_id`、`version`和checksum，文件发生变化后原扫描结果立即失效。`INFECTED`文件必须隔离，`SUSPICIOUS`文件必须按策略阻断或进入人工审核；`ERROR`与`NOT_SCANNED`的处理必须配置化并遵循失败安全原则。

Scanner不得执行待扫描文件、运行宏、跟随不受控链接、修改原文件或记录完整内容。Scanner是补充控制，不能替代WorkspacePolicy、权限、文件类型、大小、归档安全和路径边界检查。

## 10. FileReference版本与Stream安全

FileReference必须包含内容`version`和checksum。破坏性操作应校验`expected_version`，避免检查与执行之间发生并发覆盖。仅移动或重命名不改变内容版本，内容变化必须产生新版本并使旧扫描结果、缓存和确认令牌失效。

未来Stream接口必须使用短期、不可猜测且绑定task_id、skill_id、file_id和操作类型的stream_id。每个Stream必须限制块大小、总大小、持续时间和并发数，并校验块序号及checksum。

Stream超时、中止、断连或校验失败时必须关闭资源并清理临时产物。Stream不得暴露本机路径、文件句柄、Socket或底层Transport，也不得允许跨任务恢复或复用。
