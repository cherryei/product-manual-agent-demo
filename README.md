# Product Manual Agent Demo

跨境电商产品说明书 Agent demo。用户可以用任意语言提问，Agent 会检索本地产品说明书知识库，并尽量使用用户输入语言回答。系统支持多个家具产品，并可生成 EN/DE/IT/FR/ES/JP/CN 七国语言 PDF 说明书。

## 功能

- 本地产品资料知识库：示例包含实木餐桌、五层书架、人体工学办公椅、双门储物柜。
- 本地 Milvus 向量数据库：通过 `docker-compose.yml` 启动。
- 无密钥可运行 fallback：Milvus 不可用时使用本地 JSON + 哈希向量检索。
- 自动产品匹配：用户不指定产品时，Agent 会从全库检索并选择最相关家具说明书。
- 可选 LLM：默认是本地检索模板回答；配置 OpenAI-compatible 模型后会用检索上下文调用模型生成回答。
- 多语言问答：根据用户问题语言自动回答，默认同语种输出。
- PDF 说明书生成：输出七国语言产品说明、安装、安全、维护和售后章节。
- 搭建文档：见 [docs/build_log.md](docs/build_log.md)。

## 快速启动

如果项目已经在这台机器上安装过依赖，直接运行：

```bash
cd product-manual-agent-demo
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

或者使用一键启动脚本：

```bash
# macOS/Linux
./run.sh

# Windows
run.bat
```

打开 `http://127.0.0.1:8000`。

如果提示端口被占用，先停止旧服务：

```bash
lsof -ti tcp:8000 | xargs kill
```

再重新执行上面的启动命令。

## 首次安装

只有第一次运行或 `.venv` 不存在时，才需要执行：

```bash
cd product-manual-agent-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Milvus 不是启动 demo 的必要条件。Docker/Milvus 没启动时，系统会自动使用本地检索 fallback。

## Milvus 与模型状态

当前 demo 的说明书数据保存在 `data/products.json` 和 `data/furniture_products.json`。只有在 Docker Desktop 已启动、`docker compose up -d` 成功、并执行 `python scripts/seed.py` 后，说明书切块才会写入本地 Milvus collection：`product_manual_chunks`。

如果 Milvus 没启动，Agent 不会报错，会自动使用本地 fallback 检索。

需要把说明书写入 Milvus 时，再执行：

```bash
cd product-manual-agent-demo
docker compose up -d
source .venv/bin/activate
python scripts/seed.py
```

默认没有配置外部大模型。要启用 OpenAI-compatible Chat Completions 模型，可创建 `.env`：

```bash
MANUAL_AGENT_MODEL_PROVIDER=openai-compatible
MANUAL_AGENT_MODEL_BASE_URL=https://api.openai.com/v1
MANUAL_AGENT_MODEL_NAME=gpt-4o-mini
MANUAL_AGENT_MODEL_API_KEY=你的 API Key
```

重启服务后，`/health` 中的 `llm_enabled` 会变为 `true`。

## 常用 API

```bash
curl -X POST http://127.0.0.1:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"书架怎么安装防倾倒？"}'

curl -X POST http://127.0.0.1:8000/api/manual/solid-oak-dining-table/pdf
```

生成的 PDF 位于 `outputs/`。
