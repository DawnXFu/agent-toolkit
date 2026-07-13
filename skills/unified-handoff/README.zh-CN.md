# Unified Handoff 中文说明

`unified-handoff` 是一套跨 Agent 的会话交接 Skill，用同一份 Markdown 协议连接 Claude Code、Codex、OpenCode、Kilo Code 和其他兼容 Agent Skills 的工具。

## 解决的问题

普通“总结上下文”容易遗漏决策理由、失败尝试、验证证据、用户纠正和下一步操作。本 Skill 不依赖某个平台的 session ID，而是把经过校验的 Markdown 文件作为唯一交接事实源。

## 主要能力

- YAML frontmatter，协议版本 `1.0`
- Compact、Standard、Full 三档，阈值分别为 70、80、85
- 草稿优先；校验失败不会覆盖 `HANDOFF.md`
- 独立记录决策、失败尝试、证据、用户约束、用户纠正和知识状态
- 敏感信息扫描，不回显疑似密钥内容
- 自动采集 Git 元数据；普通非 Git 目录也可降级使用
- 检测 handoff 是否过期
- 只读发现并复制迁移 `.claude/handoffs/`
- Python 3.9+，仅使用标准库
- 支持 Windows、WSL/Linux、macOS、中文和空格路径

## 安装

```bash
npx skills add DawnXFu/agent-toolkit --skill unified-handoff
```

Bash：

```bash
bash skills/unified-handoff/install/install.sh --scope user --agent all
```

PowerShell：

```powershell
./skills/unified-handoff/install/install.ps1 -Scope User -Agent All
```

Codex、OpenCode 等共用 `.agents/skills/unified-handoff`；Claude Code 使用 `.claude/skills/unified-handoff`。默认复制，符号链接为可选项。

## 基本使用

初始化可选配置：

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" init
```

创建标准草稿：

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" create auth-timeout \
  --goal "修复并验证登录超时问题" \
  --mode standard \
  --source claude-code \
  --target codex
```

Agent 必须根据真实对话、文件、Git 状态、命令和测试结果填写草稿。完成后校验并定稿：

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" validate \
  .agent-context/handoffs/<文件>.draft.md --finalize
```

在新 Agent 中恢复：

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" resume --target opencode
```

## 文件结构

```text
.agent-context/
├── HANDOFF.md
├── config.json
└── handoffs/
    ├── 2026-07-13-230000-auth-timeout.md
    └── 2026-07-13-231500-auth-timeout-part-2.draft.md
```

只有通过校验的文件才会更新 `HANDOFF.md`。它是最新有效归档的物理副本，而不是符号链接。

## 强制质量规则

以下情况会阻断定稿：

- 检测到密钥、密码、Token、私钥或带凭据的连接串
- Objective 缺失或不完整
- Current State 缺失或不完整
- Immediate Next Steps 缺失、不具体或不可执行

其他缺失项会扣分并给出警告。失败草稿会保留为 `.draft.md`，不会覆盖上一份有效上下文。

## 迁移旧文件

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" list --include-legacy
python "$SKILL_DIR/scripts/unified_handoff.py" migrate
```

原始 `.claude/handoffs/` 不会被修改或删除。迁移副本会标记为 `status: legacy`，不会自动成为最新有效 handoff。

## 测试

```bash
python -m unittest discover -s skills/unified-handoff/tests -v
python -m py_compile \
  skills/unified-handoff/scripts/handoff_lib.py \
  skills/unified-handoff/scripts/handoff_lib_parts/*.py \
  skills/unified-handoff/scripts/unified_handoff.py
```

详细协议和使用约束见 `references/`。本项目基于 `softaworks/agent-toolkit` 的 `session-handoff` 改造，并保留上游 MIT 许可证与来源说明。
