# alchemist · 龙虾知识炼金系统

*[English version →](README.md)*

一个**可自部署的多智能体知识系统**，把 CODE 方法论（捕获 → 组织 → 提炼 → 表达，
Capture → Organize → Distill → Express）跑在一个聊天群和一套 PARA Markdown 工作区之上。
你把四个机器人拉进同一个群，它们就会把你随手丢进去的东西，变成有条理的笔记、被浮现出来的
洞察，以及成型的内容。

架构参考 [nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent)：
一个与平台无关的**网关（gateway）**、可替换的 **LLM 提供方**、一个 **cron 调度器**，以及
YAML 配置——在此被特化为产品 PRD 中的四智能体 CODE 流水线。

## 四个智能体

| 机器人 | CODE 阶段 | 职责 |
|-----|-----------|------|
| `@scout` | **捕获（Capture）** | 接收一切，归档到 PARA，最多问一个意图问题。 |
| `@librarian` | **组织（Organize）** | 守护 PARA 结构；唯一能移动/归档的智能体。每周推送一张知识地图。 |
| `@alchemist` | **提炼（Distill）** | 扫描所有笔记寻找跨笔记的模式；推送洞察候选（周三/周五）；学习你的口味。 |
| `@publisher` | **表达（Express）** | 把洞察 + 项目笔记变成草稿（小红书/公众号/Twitter/备忘/书籍章节……）；永远对论点做反向校验。 |

四个智能体挂载的是**同一个** PARA 工作区（`Projects / Areas / Resources / Archives`）。
笔记都是纯 Markdown（`YYYYMMDD-source-tag.md`）——归你所有，随时可备份、可迁移。

## 安装

```bash
git clone <this repo> alchemist && cd alchemist
./install.sh
```

这会创建一个 venv，安装 `alchemist` 命令行工具，并运行 `alchemist init`（它会写出
`~/.alchemist/config.yaml` 和 PARA 工作区）。

## 配置

编辑 `~/.alchemist/config.yaml`：

1. **提供方（Provider）** —— 默认是 OpenRouter。设置 `provider.api_key`，或导出环境变量
   `OPENROUTER_API_KEY`。改 `provider.name` 即可切换到 Anthropic/OpenAI。
2. **Telegram** —— 用 [@BotFather](https://t.me/BotFather) 创建四个机器人，每个智能体填一个
   token（或使用 `TELEGRAM_TOKEN_SCOUT` 等环境变量）。把四个都拉进同一个群。
   **关闭 @scout 的隐私模式**（`/setprivacy → Disable`），这样它才能看到每一条消息。

密钥始终可以用环境变量代替配置文件——环境变量优先。

## 不用 Telegram 也能试

每个智能体只要有一个提供方密钥，就能在终端里跑：

```bash
alchemist capture "https://example.com/an-article"   # scout 归档它
alchemist chat librarian "我的知识库现在什么状态?"
alchemist chat alchemist "帮我提炼最近关于定价的笔记"
alchemist draft "@publisher 用我的知识管理笔记写第三章，主题是信息过载"
alchemist scan    # 跑一次洞察扫描
alchemist map     # 生成一次每周知识地图
```

## 正式上线

```bash
alchemist run     # 启动所有机器人 + 调度器
```

调度器会自动把**每周知识地图**（周一 9:00）和**洞察候选**（周三/周五 10:00）发进群里。
时间可在 `schedule:` 下配置。

### 部署到服务器

```bash
cd docker && docker compose up -d --build
```

`restart: unless-stopped` 提供了 PRD 要求的自动重启保障；`./data` 卷保存你的配置和工作区
——记得备份。

## 定制智能体行为

- **人格（Personas）**：放一个 `<workspace>/.souls/<agent>.md` 覆盖打包的默认 SOUL。
- **模板（Templates）**：放一个 `<workspace>/.templates/<name>.md` 覆盖/新增 publisher 输出格式。
- **按智能体配模型**：设置 `agents.<id>.model`（例如给 `alchemist` 配一个更强的模型）。

## 开发

```bash
pip install -e ".[dev]"
pytest                      # 全套测试（无需联网）
pytest tests/test_scheduler.py::test_weekly_map_fires_monday_morning_once
```

## 项目结构

```
alchemist/
  cli.py            入口（init/run/chat/capture/draft/scan/map）
  config.py         YAML + 环境变量配置
  constants.py      智能体名册、PARA 目录、消息前缀
  providers/        openrouter（默认）| anthropic | openai
  workspace/        PARA 文件系统 + Note 模型（权限模型在这里）
  agents/           scout / librarian / alchemist / publisher
  souls/            每个智能体打包的 SOUL.md（最高优先级指令）
  templates/        publisher 输出格式
  channels/         ChatAdapter + telegram + 网关路由
  scheduler/        类 cron 的例行任务运行器
```

## 状态

MVP（v0.5）。已实现：四个智能体、PARA 工作区、Telegram 网关、调度器、publisher 模板、
本地 CLI，以及洞察 accept/reject 闭环（回复一条被推送的洞察，就能教会 `@alchemist`
你的口味）。尚未实现：语音转写、更多聊天平台（`ChatAdapter` 接口已就绪）、知识地图图片导出。
完整路线图见 PRD。
