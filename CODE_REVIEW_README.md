# 代码审阅功能使用指南

## 🎯 概述

DeepCode支持使用两个AI模型进行代码交叉审阅：

1. **Gemini 2.5 Pro** - Google最新模型（API自动审阅）
2. **OpenAI Codex CLI** - OpenAI命令行工具（交互式审阅）

## 🚀 快速开始

### 方式1: 仅使用Gemini（推荐新手）

```bash
python review_code.py deepcode_lab/papers/9/generate_code
```

### 方式2: 交叉审阅（最全面）

```bash
python cross_review.py deepcode_lab/papers/9/generate_code
```

---

## ⚙️ 配置

### 1. 配置Gemini API（推荐）

#### 获取API密钥

1. 访问: https://aistudio.google.com/apikey
2. 登录Google账号
3. 点击"Create API key"
4. 复制API密钥

#### 配置

编辑 `mcp_agent.secrets.yaml`:

```yaml
openai:
  api_key: "YOUR_GEMINI_API_KEY_HERE"
  base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"
```

**注意**: Gemini API目前免费，有慷慨的配额。

### 2. 安装Codex CLI（可选，用于交叉审阅）

#### 安装

```bash
# 使用npm
npm install -g @openai/codex

# 或使用Homebrew (macOS)
brew install codex
```

#### 认证

首次运行时会提示登录：
- 使用ChatGPT Plus/Pro/Business/Edu/Enterprise账号
- 或提供OpenAI API密钥

#### 验证安装

```bash
codex --version
```

---

## 📖 使用方法

### 选项1: 单独使用Gemini审阅

```bash
python review_code.py deepcode_lab/papers/9/generate_code
```

**输出**:
- `code_review_report.md` - 详细审阅报告

**优点**:
- ✅ 完全自动化
- ✅ 快速（2-5分钟）
- ✅ 详细的JSON格式报告
- ✅ 免费API配额

### 选项2: 交叉审阅（Gemini + Codex）

```bash
python cross_review.py deepcode_lab/papers/9/generate_code
```

**流程**:

1. **自动运行Gemini审阅**
   - 生成 `gemini_review.md`

2. **启动Codex CLI**
   - 自动打开终端并运行Codex
   - 或手动运行: `cd <directory> && codex`

3. **在Codex中审阅**
   ```
   Codex> Look for vulnerabilities and create a security review report
   Codex> Review code quality and best practices
   Codex> /review
   ```

4. **生成交叉审阅汇总**
   - `CROSS_REVIEW_SUMMARY.md`

**优点**:
- ✅ 两个模型交叉验证
- ✅ Gemini快速自动化
- ✅ Codex深度交互式分析
- ✅ 发现更全面的问题

---

## 📊 审阅内容

### 代码质量 (0-10分)
- 可读性和可维护性
- 编码规范（PEP 8）
- 代码组织

### 正确性 (0-10分)
- 逻辑错误和Bug
- 边界情况处理
- 错误处理

### 性能 (0-10分)
- 算法效率
- 资源使用
- 性能瓶颈

### 安全性 (0-10分)
- 安全漏洞
- 输入验证
- 数据安全

### 最佳实践 (0-10分)
- 设计模式
- Python惯用法
- SOLID原则

### 文档 (0-10分)
- Docstrings质量
- 注释适当性
- API文档

---

## 📁 输出结构

```
deepcode_lab/papers/9/
├── generate_code/              # 生成的代码
│   ├── environment.py
│   ├── heat_equation_2d.py
│   └── setup.py
└── code_reviews/               # 审阅结果
    ├── gemini_review.md        # Gemini审阅报告
    ├── codex_review.md         # Codex审阅报告（手动保存）
    ├── codex_review_prompt.txt # Codex审阅提示
    └── CROSS_REVIEW_SUMMARY.md # 交叉审阅汇总
```

---

## 🎯 使用Codex CLI的技巧

### 基本命令

```bash
# 启动Codex
codex

# 在Codex中
Codex> /review                    # 自动审阅当前目录
Codex> /status                    # 查看状态
Codex> /model gpt-5-codex         # 切换模型
```

### 审阅提示示例

```
Codex> Review all Python files for security vulnerabilities and code quality issues.
       Provide a detailed report with:
       1. Overall score for each file
       2. List of issues by severity
       3. Specific recommendations
```

### 有用的Codex命令

- `Look for vulnerabilities and create a security review report`
- `Review code quality and identify anti-patterns`
- `Check for potential bugs and edge cases`
- `Assess performance issues and suggest optimizations`

---

## 💡 最佳实践

### 1. 何时使用单一审阅

使用Gemini单独审阅当：
- ✅ 需要快速反馈
- ✅ 代码相对简单
- ✅ 想要自动化流程

### 2. 何时使用交叉审阅

使用Gemini + Codex交叉审阅当：
- ✅ 代码关键或复杂
- ✅ 需要深度安全审计
- ✅ 想要最全面的分析
- ✅ 两个模型可以交叉验证

### 3. 审阅工作流

```
1. 生成代码
   └─> python deepcode.py

2. 快速审阅 (Gemini)
   └─> python review_code.py <directory>

3. 如果发现问题，做交叉验证
   └─> python cross_review.py <directory>

4. 修复问题
   └─> 根据审阅建议改进代码

5. 重新审阅验证
   └─> python review_code.py <directory>
```

---

## ❓ 常见问题

### Q: Gemini API是免费的吗？

**A**: 是的！Gemini API目前提供免费配额：
- 每分钟15次请求
- 每天1500次请求
- 对代码审阅足够了

### Q: Codex CLI需要付费吗？

**A**: 需要ChatGPT Plus/Pro或OpenAI API密钥：
- **ChatGPT Plus** ($20/月) - 推荐，已有订阅可直接使用
- **OpenAI API** - 按使用量付费

### Q: 可以只用一个工具吗？

**A**: 可以！
- **仅Gemini**: 完全自动化，免费，快速
- **仅Codex**: 深度交互，需要Plus订阅
- **两者结合**: 最佳，交叉验证

### Q: 审阅需要多长时间？

**A**:
- **Gemini**: 2-5分钟（自动）
- **Codex**: 5-10分钟（交互式）
- **总计**: 约10-15分钟完整交叉审阅

---

## 🛠️ 故障排除

### Gemini API错误

**问题**: "Gemini API key not found"

**解决**:
1. 检查 `mcp_agent.secrets.yaml`
2. 确认API密钥正确
3. 验证base_url设置

### Codex CLI错误

**问题**: "codex: command not found"

**解决**:
```bash
# 重新安装
npm install -g @openai/codex

# 或
brew install codex

# 验证
which codex
```

**问题**: Codex authentication failed

**解决**:
1. 确认有ChatGPT Plus订阅
2. 或配置OpenAI API密钥
3. 运行 `codex` 重新认证

---

## 🔗 相关链接

- **Gemini API**: https://ai.google.dev/docs
- **Gemini API密钥**: https://aistudio.google.com/apikey
- **Codex CLI文档**: https://developers.openai.com/codex/cli/
- **Codex GitHub**: https://github.com/openai/codex
- **项目GitHub**: https://github.com/ZhangZhenhaoUPM/DeepCode

---

## 📞 支持

遇到问题？查看故障排除部分或提交Issue。

**祝审阅顺利！Happy Reviewing! 🎉**
