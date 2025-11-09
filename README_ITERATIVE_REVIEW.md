# 迭代代码审阅和改进工作流

## 🎯 功能说明

使用Gemini CLI和Codex CLI进行交叉审阅和迭代改进代码，直到达到目标质量分数。

### 工作流程

1. **交叉审阅** - 两个AI工具独立审阅代码
2. **共识分析** - 找出两个AI都发现的问题（优先修复）
3. **自动修复** - 根据两个AI的建议进行代码修改
4. **验证改进** - 重新审阅验证修改效果
5. **迭代直到达标** - 重复1-4直到分数达标

## 📦 可用工具

### 1. `iterative_code_improvement.py` - 完整版

**特点：**
- 全面审阅所有Python文件
- 详细的JSON格式报告
- 完整的审阅历史记录

**适用场景：**
- 小型项目（<10个文件）
- 需要详细报告的场景
- 有充足时间的完整审阅

**使用方法：**
```bash
python iterative_code_improvement.py <目录> [目标分数] [最大迭代次数]

# 示例
python iterative_code_improvement.py deepcode_lab/papers/1/generate_code 8.0 5
```

### 2. `quick_cross_review_and_fix.py` - 快速版

**特点：**
- 只审阅核心文件（main.py, model.py等）
- 更快的审阅速度
- 聚焦关键问题

**适用场景：**
- 大型项目（避免超时）
- 快速迭代改进
- 聚焦核心代码质量

**使用方法：**
```bash
python quick_cross_review_and_fix.py <目录> [目标分数] [最大迭代次数]

# 示例
python quick_cross_review_and_fix.py deepcode_lab/papers/1/generate_code 8.0 3
```

## 🚨 已知限制

### Codex CLI超时问题

**原因：**
- 审阅多个文件时，Codex需要更多时间进行深度分析
- 包含推理过程，执行时间较长

**解决方案：**

1. **使用Gemini单独审阅**（推荐）
   ```bash
   # Gemini速度快，不会超时
   python review_code.py deepcode_lab/papers/1/generate_code
   ```

2. **手动使用Codex审阅单个文件**
   ```bash
   cd deepcode_lab/papers/1/generate_code
   codex exec "Review main.py for code quality issues"
   ```

3. **使用交叉审阅脚本**（推荐用于核心文件）
   ```bash
   # 只审阅核心文件，避免超时
   python quick_cross_review_and_fix.py deepcode_lab/papers/1/generate_code
   ```

## ✅ 推荐工作流

### 方案A：仅使用Gemini（最稳定）

```bash
# 1. 快速审阅并生成报告
python review_code.py deepcode_lab/papers/1/generate_code

# 2. 查看报告
cat deepcode_lab/papers/1/code_review_report.md

# 3. 根据报告手动修复或使用AI辅助修复
```

### 方案B：手动交叉验证（最可靠）

```bash
# 1. Gemini自动审阅
python review_code.py deepcode_lab/papers/1/generate_code

# 2. 手动使用Codex审阅关键文件
cd deepcode_lab/papers/1/generate_code
codex exec "Review main.py, model.py, and trainer.py"

# 3. 比较两个报告，找出共识问题
# 4. 手动修复或使用Codex辅助修复
```

### 方案C：自动化迭代（实验性）

```bash
# 使用快速版本，避免超时
python quick_cross_review_and_fix.py deepcode_lab/papers/1/generate_code 8.0 3
```

## 📊 输出文件

审阅结果保存在：
- `<paper_dir>/code_reviews/` - 各种审阅报告
- `<paper_dir>/iterative_reviews/` - 迭代改进历史

## 💡 使用建议

1. **首次审阅**
   - 使用Gemini快速全面审阅
   - 获得代码质量基线

2. **关键问题验证**
   - 对Gemini发现的严重问题
   - 使用Codex进行第二意见验证

3. **代码修复**
   - 优先修复两个AI都发现的问题（共识问题）
   - 这些问题最可能是真实存在的

4. **迭代改进**
   - 修复后重新审阅
   - 验证改进效果
   - 继续迭代直到达标

## 🎯 目标分数参考

- **8.0-10.0** - 优秀（生产级代码）
- **7.0-7.9** - 良好（需要小幅改进）
- **6.0-6.9** - 中等（需要中等改进）
- **<6.0** - 需要大幅改进

## 🔧 故障排除

### Codex超时
- 减少待审阅文件数量
- 增加timeout值（在脚本中修改）
- 或只使用Gemini

### JSON解析失败
- 查看原始输出文件（*_raw.txt）
- 检查AI的实际输出
- 手动提取审阅结果

### 修复未生效
- 检查文件权限
- 验证Codex Plus订阅状态
- 查看Codex执行日志

