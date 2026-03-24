# 用 DreamAxis 做一个真正可执行的本地 Repo Copilot：从启动到 verify / troubleshoot 实战

> 构建日志 + 教程草稿  
> 项目：DreamAxis  
> 定位：local-first、no-signup by default、runtime-centric、self-hosted AI workflow platform

---

## 一、这篇文章想解决什么问题

这几年我们已经看过太多“AI coding 工具演示”：

- 看起来像聊天框
- 回答很流畅
- 但真正落到本地仓库时，经常不清楚：
  - 它到底跑了什么命令
  - 为什么失败
  - 失败属于哪一类
  - 下一步应该修哪里

DreamAxis 想做的不是“再做一个聊天框”，而是把聊天入口变成一个**可观测、可审计、可执行**的本地 repo copilot。

这篇文章会用 DreamAxis 当前的 v0.2 工作流，演示一条真实链路：

1. 本地启动
2. 配置模型
3. 进入 chat-first repo copilot
4. 跑一次 verify
5. 跑一次 troubleshoot
6. 看 execution bundle、runtime evidence、failure summary

如果你平时在用 Codex、Claude Code、OpenClaw 这类桌面 AI 助手，你会很容易理解 DreamAxis 想对齐什么；如果你更在意本地可控、执行证据和可追溯性，那 DreamAxis 的差异点会更明显。

---

## 二、DreamAxis 是什么，为什么不是“又一个聊天框”

DreamAxis 当前更准确的定义是：

> **A local-first agent execution platform for solo developers.**

它的核心不是“模型回答”，而是下面这条链路：

**Chat → Skill routing → CLI / Browser Runtime → Evidence → Next step**

也就是说，Chat 只是入口，不是终点。

DreamAxis 当前已经落地的核心面：

- **Chat**
  - understand / inspect / verify / propose_fix 四种可见模式
- **CLI Runtime**
  - 面向本地仓库的只读命令执行
- **Browser Runtime**
  - 用 Playwright 跑本地页面打开、抓取、截图
- **Knowledge**
  - 用于文档、架构、说明增强，不替代执行层
- **Environment Doctor**
  - 检查 Git / Node.js / pnpm / Python / Docker / Browser readiness

所以 DreamAxis 的重点不是：

- 多会聊天
- 多像一个通用助手

而是：

- **能不能真实执行**
- **能不能把失败讲清楚**
- **能不能把执行轨迹留下来**

---

## 三、本地启动：默认免注册、默认本地优先

DreamAxis 不是 SaaS 首发形态，默认模式是：

```env
AUTH_MODE=local_open
```

这意味着：

- 默认不需要公开注册
- 启动后自动进入本地 owner 体验
- 用户数据保存在你自己的部署环境中

### 数据放在哪里？

DreamAxis 当前的数据落点很明确：

- 用户 / workspace / provider / runtime / skill / knowledge 元数据：**PostgreSQL**
- Provider API key：**加密后存储在 provider_connections**
- 文档原文件：**本地持久目录**
- Web token：**浏览器 localStorage**

换句话说：

> DreamAxis 默认不是“把你的账号和 key 交给官方托管”，而是“你自己部署、你自己持有数据和密钥”。

### 推荐本地基线

DreamAxis 现在明确采用 Desktop AI Assistant Standard v1：

- 必需：
  - Git
  - Node.js
  - pnpm / npm
  - Python
- 增强：
  - Docker
  - Browser Runtime / Playwright

这套标准本质上和 Codex / Claude Code / OpenClaw 的桌面使用前提是对齐的，但 DreamAxis 更进一步：它会把这些依赖做成 **Doctor 可观测能力层**。

### 启动方式

```powershell
git clone https://github.com/DREAMVFIAUNION/dreamaxis.git
cd dreamaxis
pnpm install
Copy-Item .env.example .env
docker compose -f infrastructure/docker/docker-compose.yml up --build
```

启动后打开：

- Web: [http://localhost:3000](http://localhost:3000)
- API: [http://localhost:8000](http://localhost:8000)

---

## 四、先看产品核心：Chat 不是闲聊，而是 repo copilot 控制台

DreamAxis 当前最关键的产品方向，是把 `/chat` 做成一个**可执行的 repo copilot 工作台**。

当前 Chat 的四个模式是：

- `understand`
- `inspect`
- `verify`
- `propose_fix`

其中 v0.2 的主轴不是自动写代码，而是两件事：

1. **verify**：帮你验证某条链路、某个页面、某个构建是否正常
2. **troubleshoot / propose_fix**：当它失败时，帮你把失败讲清楚，并给出 grounded 的下一步建议

DreamAxis 现在要求每轮回答都尽量收敛成四段：

- Intent / plan
- What ran
- What was found
- Recommended next step

也就是说，它不是只给你“结论”，而是把**执行过程**一起带回来。

---

## 五、真实演示：一次 verify + troubleshoot 是怎么跑的

下面这次演示，使用的是 DreamAxis 自己仓库上的真实 acceptance 对话素材。

### 1）先跑 verify

典型问题可以是：

> Verify `/dashboard` and capture the result.

DreamAxis 会走的路径不是空想，而是：

- 看 workspace readiness
- 选择安全的只读 probe
- 跑 CLI 检查
- 如有需要，再走 Browser Runtime
- 把 runtime execution 回流到 chat

这时 Chat 页不只是多一段回答，而是会出现：

- inline execution cards
- runtime execution id
- evidence items
- screenshot / extract / stdout / stderr

### 2）当 verify 失败时，进入 troubleshooting summarizer

这是 DreamAxis 这轮实现里我认为最关键的一点：

> 不只是显示失败，而是把失败讲清楚。

当前 troubleshooting summarizer 会把 trace 里的失败信息整理成结构化字段：

- `failure_summary`
- `failure_classification`
- `stderr_highlights`
- `grounded_next_step_reasoning`

首版失败分类包括：

- `dependency_or_install`
- `missing_toolchain`
- `repo_not_ready`
- `script_or_manifest_missing`
- `code_or_config_failure`
- `browser_or_runtime_failure`
- `unknown`

注意这里很重要的一条约束：

> 分类只能基于 runtime evidence 推断，不能脱离证据胡猜。

也就是说，DreamAxis 不应该说“我觉得可能是 XX”，而应该说：

- 这个命令退出码是多少
- 哪一条 stderr 最关键
- 这个错误更像是缺依赖、缺工具链，还是代码 / 配置执行失败

---

## 六、Troubleshooting Summarizer 到底解决了什么问题

很多 AI coding 工具在失败时的问题是：

- 把整段 stderr 原样甩回来
- 建议很泛
- 不知道下一步该修环境、修脚本、修配置，还是修代码

DreamAxis 这轮的处理方式是：

### 1）先做失败摘要

在 `What was found` 里把失败摘要卡放到前面，而不是让你先看大段日志。

例如：

- 失败发生在哪个 probe
- 失败属于哪一类
- 第一条高信号错误是什么

### 2）再给高信号 stderr

不是整页堆日志，而是提炼：

- 第一条关键报错
- 最相关的 1–3 行上下文
- exit code

### 3）最后给 grounded next step

例如：

- 如果是 `missing_toolchain`：先安装缺失工具链
- 如果是 `dependency_or_install`：先 restore/install 依赖
- 如果是 `script_or_manifest_missing`：明确说明 package.json 或 manifest 不存在对应入口
- 如果是 `browser_or_runtime_failure`：回到 screenshot / page extract / current URL 去检查

这一步的价值在于，它把“AI 看起来很聪明的建议”收敛成了**对开发者真正可执行的下一步**。

---

## 七、执行证据长什么样

DreamAxis 的一条 chat turn，现在不是一个纯文本回答，而是一组 execution bundle。

一个 turn 里通常会有：

- 一个 parent chat execution
- 若干个 child runtime executions
  - CLI
  - Browser
  - Doctor

前端可以直接看到：

- step title
- kind
- status
- command / URL
- output excerpt
- evidence items
- runtime link

这意味着：

> 你可以把 DreamAxis 当作“带解释层的本地执行控制台”，而不只是一个生成文字的助手。

---

## 八、和 Codex / Claude Code / OpenClaw 的关系

如果把 DreamAxis 放到桌面 AI assistant 这一类里看，我会这样定位它和现有工具的关系：

### 相同点

- 都依赖本地开发环境基线
  - Git
  - Node.js
  - 包管理器
  - Python
- 都要面对真实 repo、真实命令、真实失败

### DreamAxis 更强调的点

- **local-first**
- **默认免注册**
- **provider key 自托管**
- **CLI + Browser Runtime 双执行面**
- **更强的可观测性**
- **更明确的审计面板**
- **技能 / 知识 / runtime 都可以独立演化**

如果说 Codex / Claude Code 更像是“强 agent CLI”，那么 DreamAxis 当前更像：

> 一个以 Chat 为入口、但以 Runtime / Evidence / Audit 为核心的数据面和执行面产品。

---

## 九、当前边界也必须说清楚

DreamAxis 现在并没有去夸大自己已经做到的事情。

当前明确边界：

- **proposal only**
  - `propose_fix` 只给修复建议，不自动写文件
- **不自动执行高风险动作**
  - 默认只自动执行安全、只读、可解释的路径
- **不是全自动 multi-agent OS**
  - agent role registry 已有基础，但还不是完整多 agent 自动编排系统
- **重点是 verify / troubleshoot**
  - 不是通用闲聊体验

这反而是我觉得它当前比较健康的地方：

> 先把真实开发任务里的“验证、排错、解释失败”做扎实，再谈更强自动化。

---

## 十、这次构建里一个很关键的验收结论

DreamAxis 当前已经有一套版本化 acceptance 跑法，不再靠“感觉还不错”来判断产品是否可用。

最新的 v0.2 chat-first 验收重点是：

- DreamAxis repo
- 一个 Node repo
- 一个 Python repo

检查的不是“模型多会说”，而是：

- mode 选得对不对
- 调用链对不对
- 有没有 evidence
- 有没有 runtime linkage
- 有没有 failure summary
- next step 是否 grounded
- proposal-only 是否真的没写文件

这点很关键，因为它让 DreamAxis 从“demo”更像一个**可演进的本地执行产品**。

---

## 十一、发布前我会怎么建议你体验它

如果你第一次试 DreamAxis，我建议不要先拿它写代码，而是先做下面这条体验链：

1. 打开 `/environment`
2. 看 Doctor 报告是否正常
3. 去 `/settings/providers` 配一个 OpenAI-compatible 模型网关
4. 打开 `/chat`
5. 先跑一个 `understand`
6. 再跑一个 `verify`
7. 故意触发一个失败
8. 看它能不能把失败类型和下一步讲清楚
9. 最后去 `/runtime` 对照 execution log

如果这条链路成立，你会很快明白 DreamAxis 的方向不是“聊天页更花”，而是“执行层更扎实”。

---

## 十二、配图建议

发布到 CSDN 时，建议使用这组图片：

1. 主图：`docs/assets/readme/dreamaxis-chat.png`
2. 辅图：`docs/assets/readme/dreamaxis-runtime.png`
3. 可选第三张：`docs/assets/readme/dreamaxis-dashboard.png`

如果希望更强调这次 troubleshoot workstream，也可以替换为最新 acceptance 图：

- `artifacts/acceptance/dreamaxis-chat.png`
- `artifacts/acceptance/dreamaxis-runtime.png`

---

## 十三、结尾

DreamAxis 现在还远没到“自动把整个仓库修完”的阶段。

但如果你的目标是做一个真正可用的本地 AI repo copilot，我认为比起继续堆“更像聊天”的 UI，更重要的是先把这些事情做好：

- 能运行
- 能验证
- 能解释失败
- 能给 grounded 的下一步
- 能把过程留下来

DreamAxis 正在沿着这条路线继续推进。

如果你也在关注：

- local-first AI tool
- self-hosted provider keys
- runtime-backed repo copilot
- Browser + CLI 双执行面
- open-source agent execution platform

欢迎直接去 GitHub 看项目，也欢迎拿你自己的仓库跑一遍 verify / troubleshoot。

---

## 项目地址

- GitHub: [https://github.com/DREAMVFIAUNION/dreamaxis](https://github.com/DREAMVFIAUNION/dreamaxis)
- README: `README.md`
- Acceptance report: `docs/chat-acceptance-report-v0.2.md`
- Runbook: `docs/repo-copilot-runbook.md`
- Roadmap: `ROADMAP.md`

---

## 可直接配套的发布标题备选

### 偏工程实践

- DreamAxis：把本地 AI Chat 做成可执行的 Repo Copilot
- 我做了一个 local-first 的 DreamAxis，让 AI 先验证、再解释失败
- 从聊天框到执行控制台：DreamAxis 的 verify / troubleshoot 工作流实战

### 偏产品定位

- DreamAxis 不是“又一个聊天框”，而是可观测的本地 Repo Copilot
- 我为什么想做 DreamAxis：一个 local-first 的 agent execution platform
- 对齐 Codex / Claude Code 标准后，DreamAxis 还想多做什么？
