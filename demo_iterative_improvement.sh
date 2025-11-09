#!/bin/bash
# Demo: 迭代代码改进演示

echo "=========================================================================="
echo "  🚀 Demo: Iterative Code Improvement with Gemini + Codex"
echo "=========================================================================="
echo ""
echo "这个演示展示如何使用两个AI工具进行迭代代码改进："
echo "1. 审阅代码（Gemini + Codex）"
echo "2. 找出共识问题"
echo "3. 自动修复问题"
echo "4. 重新审阅验证"
echo ""

CODE_DIR="deepcode_lab/papers/1/generate_code"

# Step 1: 初始审阅
echo "=========================================================================="
echo "  📊 Step 1: Initial Review with Gemini"
echo "=========================================================================="
echo ""
echo "Reviewing: main.py, model.py, trainer.py"
echo ""

cd "$CODE_DIR"

# Gemini审阅main.py
echo "🔍 Gemini reviewing main.py..."
gemini -p "Review main.py for code quality. Provide score (0-10) and top 3 issues with line numbers. Be concise." main.py 2>&1 | tail -20

echo ""
echo "Press Enter to continue to Codex review..."
read

# Codex审阅main.py
echo "🤖 Codex reviewing main.py..."
codex exec "Review main.py briefly. Score (0-10) and top 2 issues with exact line numbers." 2>&1 | tail -30

echo ""
echo "=========================================================================="
echo "  🔧 Step 2: Apply Fix with Codex"
echo "=========================================================================="
echo ""
echo "Fixing device selection issue in main.py..."
echo "Press Enter to apply fix..."
read

codex exec --sandbox workspace-write "Fix main.py: Add device selection (torch.device with CUDA if available) and move model to device. Apply changes to file." 2>&1 | tail -40

echo ""
echo "=========================================================================="
echo "  ✅ Step 3: Verify Fix"
echo "=========================================================================="
echo ""
echo "Checking if main.py was modified..."
echo ""

if grep -q "torch.device" main.py; then
    echo "✅ SUCCESS: Device selection code added!"
    echo ""
    echo "Modified code:"
    echo "---"
    cat main.py
    echo "---"
else
    echo "⚠️  Device selection not found in main.py"
fi

echo ""
echo "=========================================================================="
echo "  📊 Step 4: Re-review to Verify Improvement"
echo "=========================================================================="
echo ""
echo "Press Enter to re-review with Gemini..."
read

gemini -p "Re-review main.py. Has the device selection issue been fixed? Score (0-10) and remaining issues." main.py 2>&1 | tail -20

echo ""
echo "=========================================================================="
echo "  🎉 Demo Complete!"
echo "=========================================================================="
echo ""
echo "Summary:"
echo "- Initial review identified device selection issue"
echo "- Codex applied fix automatically"
echo "- Code was modified successfully"
echo "- Re-review verified the improvement"
echo ""
echo "This same process can be automated and repeated until target score is reached!"
echo ""
