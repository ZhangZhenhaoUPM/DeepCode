# 性能优化：模型切换日志优化

## 问题描述

用户反馈：代码实现阶段出现大量重复的任务路由日志：

```
🔍 TASK ROUTING CHECK:
   - Routing enabled: True
   - Provider: ollama
   - Task type: code_generation
   - Current active_model: qwen3:32b
🔧 CODE GENERATION TASK → Selected model: qwen3-coder:30b
   ✅ SWITCHING MODEL: qwen3:32b → qwen3-coder:30b
   ✅ System message enhanced for code_generation
```

这些日志在每次 LLM 调用时都会输出，导致：
1. 日志量巨大（可能重复800次）
2. 难以找到真正重要的信息
3. 性能损耗（大量 I/O 操作）

## 根本原因分析

### 代码流程

```python
# workflows/code_implementation_workflow.py

while iteration < max_iterations:  # 最多800次迭代
    iteration += 1

    # 每次迭代都调用
    response = await self._call_llm_with_tools(
        client, client_type, current_system_message, messages, tools, task_type=task_type
    )

    # _call_llm_with_tools 内部（旧代码）
    def _call_llm_with_tools(self, ...):
        # ❌ 每次都输出，即使模型没变
        self.logger.warning(f"🔍 TASK ROUTING CHECK:")
        self.logger.warning(f"   - Routing enabled: {routing_enabled}")
        self.logger.warning(f"   - Provider: {self.active_provider}")
        self.logger.warning(f"   - Task type: {task_type}")
        self.logger.warning(f"   - Current model: {self.active_model}")

        if routing_enabled and is_ollama:
            model_for_task = self._select_model_for_task(task_type)
            # ❌ 每次都输出，即使是同一个模型
            self.logger.warning(f"   ✅ Switched model: {original_model} → {model_for_task}")
```

### 问题点

1. **使用 WARNING 级别**：确保可见性，但导致过度输出
2. **无状态检查**：没有检查上次日志的状态，每次都输出
3. **重复信息**：当 task_type 和 model 都不变时，仍然输出相同信息
4. **模型切换时间**：频繁切换模型需要时间（虽然 Ollama 会缓存）

## 优化方案

### 1. 状态追踪

在 `__init__` 中添加状态追踪变量：

```python
def __init__(self, config_path: str = "mcp_agent.secrets.yaml"):
    # ... 其他初始化代码 ...

    # Track last logged state to avoid repetitive logs
    self._last_logged_task_type = None
    self._last_logged_model = None
    self._model_switch_count = 0
```

### 2. 智能日志输出

只在状态改变时输出日志：

```python
async def _call_llm_with_tools(self, client, client_type, system_message, messages, tools, max_tokens=8192, task_type="general"):
    routing_enabled = self.task_model_routing.get("enabled", False)
    is_ollama = self.active_provider == "ollama"

    if routing_enabled and is_ollama:
        model_for_task = self._select_model_for_task(task_type)
        original_model = self.active_model

        # ✅ 只在状态改变时输出
        should_log = (
            task_type != self._last_logged_task_type or
            model_for_task != self._last_logged_model
        )

        if should_log:
            self.logger.info(f"🔄 Task routing: {task_type} → {model_for_task}")

            # 只在模型真正切换时计数和输出
            if original_model != model_for_task:
                self._model_switch_count += 1
                self.logger.info(f"   ✅ Model switch #{self._model_switch_count}: {original_model} → {model_for_task}")

            self._last_logged_task_type = task_type
            self._last_logged_model = model_for_task

        self.active_model = model_for_task
```

### 3. 启动时配置日志

在工作流开始时输出一次完整配置：

```python
async def run_workflow(self, ...):
    # ... 其他日志 ...

    # ✅ 启动时输出一次配置
    if self.task_model_routing.get("enabled", False):
        strategies = self.task_model_routing.get("strategies", {})
        self.logger.info("🔄 Task routing configuration:")
        self.logger.info(f"   - Code generation: {strategies.get('code_generation', 'N/A')}")
        self.logger.info(f"   - Analysis: {strategies.get('analysis', 'N/A')}")
        self.logger.info(f"   - Vision: {strategies.get('vision', 'N/A')}")
        self.logger.info("   ℹ️  Model switches will be logged only when they occur")
    else:
        self.logger.info("🔄 Task routing: DISABLED")
```

### 4. 完成时统计输出

在实现完成时输出统计信息：

```python
if any(keyword in response_content.lower() for keyword in completion_keywords):
    self.logger.info("Code implementation declared complete")

    # ✅ 输出模型切换统计
    if self._model_switch_count > 0:
        self.logger.info(f"📊 Total model switches during implementation: {self._model_switch_count}")
    break
```

## 优化效果

### 优化前（800次迭代）

```
🔍 TASK ROUTING CHECK:
   - Routing enabled: True
   - Provider: ollama
   - Task type: general
   - Current model: qwen3:32b
🔍 TASK ROUTING CHECK:
   - Routing enabled: True
   - Provider: ollama
   - Task type: general
   - Current model: qwen3:32b
... (重复798次)
🔧 CODE GENERATION TASK → Selected model: qwen3-coder:30b
   ✅ SWITCHING MODEL: qwen3:32b → qwen3-coder:30b
🔧 CODE GENERATION TASK → Selected model: qwen3-coder:30b
   ✅ SWITCHING MODEL: qwen3:32b → qwen3-coder:30b
... (重复多次)
```

**日志行数**：~3200 行（每次调用4行日志）

### 优化后（800次迭代）

```
================================================================================
🚀 STARTING CODE IMPLEMENTATION WORKFLOW
================================================================================
📄 Plan file: /path/to/plan.txt
📂 Plan file parent: /path/to/parent
🎯 Code directory (MCP workspace): /path/to/code
⚙️  Read tools: ENABLED
🔄 Task routing configuration:
   - Code generation: qwen3-coder:30b
   - Analysis: qwen3:32b
   - Vision: qwen3-vl:4b
   ℹ️  Model switches will be logged only when they occur
================================================================================

... (代码实现过程中，只在task_type或model变化时输出)

🔄 Task routing: code_generation → qwen3-coder:30b
   ✅ Model switch #1: qwen3:32b → qwen3-coder:30b

... (更多实现过程)

🔄 Task routing: analysis → qwen3:32b
   ✅ Model switch #2: qwen3-coder:30b → qwen3:32b

... (实现完成)

Code implementation declared complete
📊 Total model switches during implementation: 15
```

**日志行数**：~20 行（只在变化时输出）

**减少比例**：99.4%（从3200行减少到20行）

## 性能影响

### 1. I/O 性能

**优化前**：
- 每次 LLM 调用写入 4-5 行日志
- 800 次迭代 × 5 行 × 平均 100 字节 = ~400KB 日志数据
- 频繁的磁盘写入操作

**优化后**：
- 只在状态变化时写入（假设20次变化）
- 20 次 × 2 行 × 100 字节 = ~4KB 日志数据
- 减少 99% 的磁盘 I/O

### 2. 模型切换开销

**Ollama 模型切换特性**：
- Ollama 会缓存最近使用的模型
- 同一模型重复调用：几乎无开销
- 不同模型切换：需要加载新模型（几秒钟）

**优化效果**：
- 不会减少实际的模型切换次数
- 但清晰显示切换发生的时机
- 便于分析是否有不必要的切换

### 3. 调试便利性

**优化前**：
- 难以找到重要信息（被重复日志淹没）
- 不知道模型切换了多少次
- 日志文件巨大，难以分析

**优化后**：
- 清晰显示每次状态变化
- 统计信息一目了然
- 日志文件小巧，易于分析

## 配置建议

### 如果需要详细调试

可以临时启用详细日志（修改代码）：

```python
# 在 _call_llm_with_tools 中
if should_log or True:  # 临时启用所有日志
    self.logger.info(f"🔄 Task routing: {task_type} → {model_for_task}")
```

或者设置日志级别为 DEBUG：

```python
# 在 main() 或启动脚本中
logging.getLogger("workflows.code_implementation_workflow").setLevel(logging.DEBUG)
```

### 如果不需要任何路由日志

可以完全禁用任务路由：

```yaml
# mcp_agent.config.yaml
task_model_routing:
  enabled: false  # 禁用多模型路由
```

## 最佳实践

### 1. 日志级别选择

- **INFO**：正常状态变化（推荐）
- **WARNING**：异常情况（不要用于正常流程）
- **DEBUG**：详细调试信息（开发时使用）

### 2. 状态追踪模式

对于频繁调用的函数，应该：
```python
# ✅ 好的做法
if state_changed:
    log_state_change()

# ❌ 不好的做法
log_state_every_time()
```

### 3. 统计信息

在长时间运行的流程中，提供统计摘要：
```python
# 开始时
log_configuration()

# 过程中
if state_changed:
    log_change()

# 结束时
log_statistics()
```

## 相关 Commit

```
commit 70b0fc8
Author: Claude Code
Date: 2025-11-09

Optimize: Reduce repetitive task routing logs during code implementation

- Track last logged state to avoid repetition
- Only log when task type or model actually changes
- Count and report total model switches at completion
- Move detailed routing config to workflow start
- Change from WARNING to INFO level
```

## 总结

### 问题
- 重复日志输出（800次迭代 × 4-5行 = 3200+行）
- 使用 WARNING 级别导致过度可见性
- 无法快速找到重要信息

### 解决方案
- 状态追踪：记录上次日志的状态
- 智能输出：只在状态改变时输出
- 统计摘要：在开始和结束时输出汇总信息

### 效果
- 日志量减少 99.4%
- 重要信息更清晰
- 便于调试和性能分析
- 模型切换统计一目了然

---

**优化时间**: 2025-11-09
**优化内容**: 任务路由日志优化
**性能提升**: 日志 I/O 减少 99%+
