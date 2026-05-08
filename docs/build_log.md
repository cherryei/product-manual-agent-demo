# 产品说明书 Agent Demo 搭建记录

## 1. 需求理解

用户要的是一个可演示的“产品说明书 Agent”，核心目标不是单纯生成一份 PDF，而是把跨境电商场景中的产品资料、向量知识库、问答 Agent、多语言说明书生成串起来。

我将需求拆成 5 个交付物：

1. Agent：用户可以针对不同产品说明书提问。
2. 多语言：默认识别用户输入语言，并用同语种回答。
3. 知识库：本地 Milvus 数据库，Docker 启动，存储产品说明书切块。
4. PDF 说明书：一份 PDF 中展示 EN、DE、IT、FR、ES、JP、CN 七国语言，包含产品说明和安装说明。
5. 搭建记录：记录需求理解、技术选型、实现过程、遇到的问题和解决方案。

本 demo 选择家具类产品作为样例，包括实木餐桌、五层书架、人体工学办公椅、双门储物柜。素材参考电商平台常见结构：标题、五点卖点、尺寸、材质、安装、保养、安全提示。为降低版权和页面稳定性风险，示例文案是根据公开电商商品格式重写后的 demo 数据，不整段复制具体 Amazon listing。

## 2. 技术选型

### 后端：FastAPI

选择原因：

- demo 启动快，API 和页面可以放在一个轻量服务里。
- Pydantic 数据模型适合定义问答请求、响应和产品摘要。
- 后续可平滑扩展成真实后端服务，例如用户上传 PDF、产品 SKU 管理、权限和日志。

### 向量数据库：Milvus Standalone

选择原因：

- 用户明确提到本地 Milvus，且本机有 Docker。
- Milvus 适合承载多产品、多语言说明书切块检索。
- 使用 Docker Compose 启动 etcd、MinIO、Milvus，接近真实部署方式。

### 检索与 embedding：本地哈希向量

选择原因：

- demo 不依赖 OpenAI、DeepSeek 或其他外部 API key，任何本地环境都能运行。
- 使用固定维度哈希向量，能完成基础相似度检索，适合演示 RAG 流程。
- 后续可以替换为真实 embedding 模型，例如 `text-embedding-3-small`、BGE、E5 或本地 sentence-transformers。

当前实现中的 `app/services/embedding.py` 是可替换层。

### Agent 生成：规则化回答 + 可选 LLM

选择原因：

- 为了 demo 稳定可复现，默认不依赖外部 LLM。
- 回答会先识别语言，再检索对应语言说明书切块，并拼装成同语种回答。
- 已预留 OpenAI-compatible Chat Completions 配置。`.env` 中配置 `MANUAL_AGENT_MODEL_PROVIDER`、`MANUAL_AGENT_MODEL_BASE_URL`、`MANUAL_AGENT_MODEL_NAME`、`MANUAL_AGENT_MODEL_API_KEY` 后，Agent 会用检索出的说明书上下文调用模型。
- 未配置模型或模型调用失败时，系统自动回退到本地检索模板回答。

### PDF 生成：ReportLab

选择原因：

- Python 内直接生成 PDF，适合服务端接口。
- 支持自定义字体。这里优先注册 macOS 的 `Arial Unicode.ttf`，覆盖英文、欧洲语言和日文。
- 可控性高，便于后续加入页眉页脚、页码、表格、条码、SKU 信息。

## 3. 系统结构

```text
product-manual-agent-demo/
  app/
    main.py                    FastAPI 路由和页面
    models.py                  API 数据模型
    services/
      answer_engine.py         语言识别 + 检索 + 回答拼装
      embedding.py             本地哈希 embedding
      language.py              语言识别
      llm.py                   可选 OpenAI-compatible 模型调用
      pdf_manual.py            七国语言 PDF 生成
      products.py              产品数据加载和切块
      vector_store.py          Milvus 与本地 fallback
    static/                    页面 CSS 和产品示意图
    templates/index.html       Demo UI
  data/products.json           餐桌多语言产品资料
  data/furniture_products.json 书架、办公椅、储物柜多语言产品资料
  docker-compose.yml           本地 Milvus
  scripts/seed.py              初始化向量库
  tests/test_demo.py           基础测试
```

## 4. 搭建过程

### 4.1 准备产品资料

产品资料按 `product_id -> aliases -> languages -> sections` 组织。`aliases` 用于多产品自动匹配，例如用户问“书架怎么安装防倾倒”，系统会优先命中 `five-tier-bookshelf`。每种语言都包含：

- `name`
- `title`
- `summary`
- `bullets`
- `specs`
- `installation`
- `safety`
- `care`
- `faq`

这样做的好处是 PDF 和 Agent 共用同一份结构化数据，避免说明书和问答知识库内容不一致。

### 4.2 文档切块

`product_chunks()` 会将产品资料切为：

- overview
- specs
- installation
- safety
- care
- faq

每个 chunk 带上 `product_id`、`language`、`section` 和 `text`，写入 Milvus 或本地 fallback。为了改善中文检索，`embedding.py` 会把中文字符和二元片段加入 token。

### 4.3 初始化 Milvus

执行：

```bash
docker compose up -d
python scripts/seed.py
```

如果 Milvus 可用，脚本会创建 `product_manual_chunks` collection，并写入所有家具、所有语言的说明书切块。

如果 Milvus 不可用，系统会打印原因并使用本地 fallback；这保证 demo 页面仍然能演示。换句话说：当前说明书并不一定已经保存到 Milvus，取决于 Docker/Milvus 是否启动并成功执行 seed。

### 4.4 问答流程

1. 用户输入问题。
2. `detect_language()` 识别语言，或使用用户显式选择的语言。
3. 如果用户指定了 `product_id`，按 `product_id + language` 检索说明书切块。
4. 如果用户没有指定产品，则全库检索，并按最高分结果自动选择家具产品。
5. 如果配置了 LLM，用检索结果作为上下文生成回答；否则用本地模板拼装回答。
6. 返回回答、识别出的语言、选中的 `product_id` 和来源 section。

### 4.5 模型配置流程

默认没有启用模型，`/health` 返回：

```json
{"status":"ok","llm_enabled":false}
```

如需启用 OpenAI-compatible 模型，在项目根目录创建 `.env`：

```bash
MANUAL_AGENT_MODEL_PROVIDER=openai-compatible
MANUAL_AGENT_MODEL_BASE_URL=https://api.openai.com/v1
MANUAL_AGENT_MODEL_NAME=gpt-4o-mini
MANUAL_AGENT_MODEL_API_KEY=你的 API Key
```

重启服务后，`answer_engine.py` 会将检索出的说明书片段交给 `llm.py`，由模型生成自然语言回答。

### 4.6 PDF 生成流程

1. 调用 `POST /api/manual/{product_id}/pdf`。
2. 读取产品七国语言资料。
3. 使用 ReportLab 生成封面、语言分节、规格表、安装步骤、安全提示、保养和 FAQ。
4. 输出到 `outputs/{product_id}-manual-7-languages.pdf`。

## 5. 遇到的问题与解决方案

### 问题 1：Amazon 页面素材不稳定且有版权风险

直接抓取 Amazon 页面通常会遇到反爬、地区页面差异、登录弹窗、DOM 结构变化等问题。商品图片和文案也不适合整段复制进 demo。

解决方案：

- 只使用公开电商商品的常见结构作为参考，例如标题、五点卖点、尺寸、易安装、保养、安全提示。
- 示例产品文案全部重写，并在 `products.json` 中记录 `source_notes`。
- 图片采用本地 SVG demo 示意图，不复制平台商品图。

### 问题 2：没有外部 LLM/embedding key 时 demo 难以复现

真实 RAG 系统通常需要 embedding 模型和 LLM。但如果 demo 依赖外部 key，交付后容易因为配置缺失无法启动。

解决方案：

- 用本地哈希 embedding 模拟向量检索。
- 用规则化回答模拟 Agent 输出。
- 保留清晰替换点：`embedding.py` 和 `answer_engine.py`。

### 问题 3：Milvus 启动需要多个组件

Milvus standalone 依赖 etcd 和 MinIO。只启动一个 Milvus 镜像会失败。

解决方案：

- 在 `docker-compose.yml` 中配置 etcd、MinIO、Milvus 三个服务。
- 启动失败时使用本地 fallback，不阻塞 UI 和 PDF demo。

本机验证时还遇到 Docker daemon 未运行：

```text
failed to connect to the docker API at unix:///Users/cherry/.docker/run/docker.sock
```

解决方式是先启动 Docker Desktop，再执行：

```bash
docker compose up -d
python scripts/seed.py
```

在 Docker 未启动期间，`scripts/seed.py` 会明确打印 Milvus 不可用原因，并切换到本地 fallback。

### 问题 4：多语言 PDF 字体支持

默认 PDF 字体无法显示日文，也可能不完整支持欧洲语言字符。

解决方案：

- ReportLab 启动时优先注册系统字体 `Arial Unicode.ttf`。
- 如果字体不存在，再 fallback 到 Helvetica。
- 日文内容放入结构化数据，并通过 Unicode 字体输出。

### 问题 5：短中文问题会命中错误家具

用户反馈“凳子说明书”返回了书架/储物柜说明书。复现后发现：

- `凳子` 没有加入办公椅的中文别名。
- 当前本地哈希 embedding 不是语义模型，对很短的中文问题理解弱。
- 自动选品原来只看全库向量分数，容易被“说明书”“安装”等通用词和哈希碰撞带偏。

解决方案：

- 给办公椅加入 `凳子`、`座椅` 等中文别名。
- 新增 `match_product_id()`，先用产品别名、产品名、标题做确定性产品识别。
- 只有未识别出明确产品词时，才回退到全库向量检索。
- 增加回归测试：`凳子说明书`、`凳子怎么安装？` 必须命中 `ergonomic-office-chair`。

### 问题 6：SVG 直接嵌入 PDF 兼容性

ReportLab 默认不直接支持所有 SVG。引入 svg2rlg 需要额外依赖。

解决方案：

- Web 页面展示 SVG 产品图。
- PDF 中使用 ReportLab 自绘的稳定占位图/示意框，保证生成流程不因 SVG 解析失败中断。
- 如果后续要做正式说明书，可加入 `svglib` 或使用 PNG/JPEG 产品图。

## 6. 后续可扩展方向

- 接入真实 LLM：让 Agent 根据检索结果生成更自然的多语言回答。
- 上传说明书 PDF：解析已有 PDF 并自动切块入库。
- 多产品管理：增加 SKU、品牌、平台、国家合规字段。
- 人工审核流：说明书生成后由运营确认，再发布。
- 图片增强：接入真实产品图、爆炸图、零件编号图。
- 合规模板：针对 EU/US/JP 市场输出不同安全/保修信息。
