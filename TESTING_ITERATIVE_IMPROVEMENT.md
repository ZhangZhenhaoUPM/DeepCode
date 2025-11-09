# 测试说明：迭代代码改进功能

## 问题诊断

### 发现的问题
用户报告：代码实现完成后，迭代优化过程没有执行。

### 根本原因
1. **Session State 未正确初始化**：当 `enable_iterative` checkbox 未勾选时，`target_score`、`max_iterations` 和 `iteration_mode` 没有默认值
2. **缺少调试日志**：无法判断迭代改进代码是否被执行
3. **Session State 未显式更新**：依赖 Streamlit 的自动 key 绑定，但在某些情况下不可靠

### 已修复的问题
1. ✅ 在 `ui/components.py` 中添加了默认值初始化（400-402行）
2. ✅ 在 `ui/components.py` 中添加了显式 session state 更新（465-468行）
3. ✅ 在 `ui/handlers.py` 中添加了调试日志（1171-1174行，1207-1210行）

## 测试步骤

### 1. 清理缓存（已完成）
```bash
# 停止 Streamlit
pkill -f "streamlit run deepcode.py"

# 清理缓存
rm -rf .streamlit_cache __pycache__ ui/__pycache__
```

### 2. 启动 Streamlit 应用
```bash
python -m streamlit run deepcode.py --server.headless=true --server.port=8501
```

### 3. 在浏览器中测试

#### 步骤 A: 上传论文并生成代码
1. 打开浏览器访问 `http://localhost:8501`
2. 在侧边栏找到 **"🔄 Iterative Improvement"** 部分
3. **勾选** "🔄 Enable Iterative Improvement"
4. 设置参数：
   - Target Quality Score: 8.0
   - Maximum Iterations: 3
   - Iteration Mode: Quick (Core files only)
5. 上传论文 PDF 文件
6. 点击 "Start Processing"

#### 步骤 B: 验证执行流程
在日志输出中，您应该看到以下内容：

**代码实现阶段**：
```
Code implementation completed successfully!
Code directory: /path/to/generate_code
Implementation report saved to /path/to/code_implementation_report.txt
```

**迭代改进阶段**（新增）：
```
🔍 Checking iterative improvement: enable_iterative=True, code_directory=/path/to/generate_code

### 🔄 Iterative Improvement Phase

🎯 Target: 8.0/10 | Max Iterations: 3

🚀 Starting iterative improvement...
Using quick mode (core files only)
Running iterative improvement (this may take a few minutes)...
```

**如果未启用迭代改进**，您会看到：
```
ℹ️  Iterative improvement is DISABLED in session state
```

### 4. 验证输出文件

检查以下文件是否生成：
```bash
# 迭代改进报告目录
ls -la deepcode_lab/papers/1/iterative_reviews/

# 应该包含：
# - complete_history.json
# - iteration_1_consensus.json
# - iteration_1_consensus.md
# - iteration_1_gemini_raw.txt
# - iteration_2_consensus.json（如果有第二次迭代）
```

## 预期行为

### 启用迭代改进时（Enable Iterative Improvement = ✅）
1. 代码实现完成后
2. 自动运行 `quick_cross_review_and_fix.py` 或 `iterative_code_improvement.py`
3. 使用 Gemini CLI 和 Codex CLI 交叉审阅
4. 自动修复共识问题
5. 重新审阅验证
6. 迭代直到达到目标分数或最大迭代次数
7. 生成完整的迭代历史报告

### 未启用迭代改进时（Enable Iterative Improvement = ❌）
1. 代码实现完成后
2. 直接结束，不运行迭代改进
3. 日志显示 "Iterative improvement is DISABLED"

## 调试建议

如果迭代改进仍然没有运行，请检查：

### 1. Session State 值
在 Streamlit 界面中添加调试信息：
```python
# 在 ui/layout.py 或 deepcode.py 中临时添加
st.write("Debug - Session State:")
st.write(f"enable_iterative: {st.session_state.get('enable_iterative', 'NOT SET')}")
st.write(f"target_score: {st.session_state.get('target_score', 'NOT SET')}")
st.write(f"max_iterations: {st.session_state.get('max_iterations', 'NOT SET')}")
```

### 2. 日志输出
查看终端日志：
```bash
# 查找迭代改进相关日志
grep -i "iterative\|Checking iterative\|DISABLED" <streamlit_log_output>
```

### 3. Code Directory 提取
确认 `extract_code_directory_from_result()` 正确提取了代码目录：
```python
# 在 ui/handlers.py 的 1148 行后添加
logger.info(f"DEBUG: Extracted code_directory = {code_directory}")
```

## 依赖工具

确保以下 CLI 工具已安装并可用：

### Gemini CLI
```bash
gemini --version
# 应该显示: v0.1.18 或更高
```

### Codex CLI
```bash
codex --version
# 应该显示: v0.46.0 或更高

# 确认已登录
codex auth status
```

## 常见问题

### Q1: 日志显示 "Iterative improvement is DISABLED"
**原因**：Checkbox 没有被勾选
**解决**：在侧边栏勾选 "🔄 Enable Iterative Improvement"

### Q2: 代码目录未找到
**原因**：`extract_code_directory_from_result()` 返回 None
**解决**：检查 `result` 字典中是否包含 `code_directory` 字段

### Q3: Gemini/Codex 超时
**原因**：项目文件太多或文件太大
**解决**：使用 "Quick (Core files only)" 模式，只审阅核心文件

### Q4: 没有生成 iterative_reviews 目录
**原因**：迭代改进脚本执行失败
**解决**：
1. 手动运行脚本测试：
   ```bash
   python quick_cross_review_and_fix.py deepcode_lab/papers/1/generate_code 8.0 3
   ```
2. 查看错误输出
3. 确认 Gemini CLI 和 Codex CLI 可用

## 测试完成标准

✅ **成功标准**：
1. 勾选 "Enable Iterative Improvement" 后
2. 代码实现完成后自动触发迭代改进
3. 终端显示迭代改进日志
4. 生成 `iterative_reviews/` 目录和报告文件
5. 最终显示 "🎉 Target reached!" 或 "⚠️ Partial improvement"

❌ **失败标准**：
1. 勾选后没有执行迭代改进
2. 日志显示 "DISABLED" 但 checkbox 已勾选
3. 没有生成任何 iterative_reviews 文件

## 下一步

测试完成后，请报告：
1. ✅ 是否成功执行迭代改进
2. 📊 最终质量分数
3. 📝 迭代次数
4. 🐛 遇到的任何错误或问题

---

**修改时间**: 2025-11-09
**修改内容**:
- 修复 session state 初始化问题
- 添加调试日志
- 显式更新 session state
**提交**: e43154b
