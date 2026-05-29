# 产品手册智能问答系统 — 面试演示文档

## 项目概述

这是一个基于 **RAG (Retrieval-Augmented Generation)** 架构的跨境电商产品手册智能问答系统。支持 7 种语言（EN/DE/IT/FR/ES/JP/CN），用户可以用任意语言提问，系统自动匹配产品并返回同语言答案。

**核心价值**：
- 跨境电商卖家可以为每个产品生成多语言 PDF 手册，一键覆盖全球市场
- 买家可以用母语提问产品安装、维护、规格等问题，获得即时准确的答案
- 支持上传自定义产品手册，自动索引并加入问答库

---

## 技术栈

### 后端
- **FastAPI** — 高性能异步 Web 框架
- **Anthropic Claude API** — LLM 推理（问答生成、语言检测、产品匹配）
- **Sentence Transformers** — 文本向量化（all-MiniLM-L6-v2，384 维）
- **Milvus / 本地向量库** — 向量检索（支持两种后端，自动降级）
- **ReportLab** — PDF 生成（多语言排版、中日文字体支持）
- **PyPDF2** — PDF 文本提取

### 前端
- **原生 JavaScript** — 无框架依赖，轻量高效
- **Jinja2 模板** — 服务端渲染
- **响应式 CSS** — 移动端适配

### 开发工具
- **pytest** — 单元测试（26 个测试用例，100% 通过）
- **uvicorn** — ASGI 服务器
- **Git** — 版本控制

---

## 核心功能演示

### 1. 智能问答（多语言自动匹配）

**演示步骤**：
1. 打开首页 `http://127.0.0.1:8000`
2. 在问题框输入：`How do I assemble the table?`（英文）
3. 点击 **Ask Agent**，系统自动：
   - 检测语言为英文
   - 匹配产品为 `solid-oak-dining-table`（实木餐桌）
   - 从向量库检索相关段落
   - 用 Claude 生成英文答案

**技术亮点**：
- **语言检测**：基于 Unicode 字符集分布 + 关键词匹配，无需额外模型
- **产品匹配**：向量相似度 + 关键词匹配双重策略，准确率高
- **上下文增强**：检索 Top-3 相关段落，拼接为 Prompt 上下文

**代码位置**：
- `app/services/answer_engine.py:answer_question()` — 主流程
- `app/services/language.py:detect_language()` — 语言检测
- `app/services/products.py:match_product_id()` — 产品匹配

---

### 2. 文档管理中心（多语言 PDF 生成）

**演示步骤**：
1. 滚动到页面底部 **Document Center** 区域
2. 选择任意产品（如 Five-Tier Bookshelf）
3. 取消勾选部分语言（如只保留 EN、CN、JP）
4. 点击 **Generate & Download PDF**
5. 浏览器自动下载 `five-tier-bookshelf-manual-en-cn-jp.pdf`

**技术亮点**：
- **动态语言选择**：前端多选框 → 后端 `resolve_languages()` 求交集
- **文件名语义化**：包含产品 ID 和语言列表，避免覆盖
- **中日文字体支持**：自动注册 Noto Sans CJK，无乱码
- **分页排版**：每种语言独立分页，目录 + 页眉 + 页脚

**代码位置**：
- `app/services/pdf_manual.py:generate_manual_pdf()` — PDF 生成
- `app/services/pdf_manual.py:resolve_languages()` — 语言交集计算
- `app/templates/index.html` — 文档管理 UI（第 90-110 行）

---

### 3. 上传自定义手册

**演示步骤**：
1. 准备一个 PDF 或 TXT 文件（如产品说明书）
2. 在 **Upload manual** 区域点击 **Choose File**
3. 输入产品标题（可选）
4. 点击 **Upload**
5. 系统自动：
   - 提取文本内容
   - 分段并向量化
   - 存入向量库
   - 同步到文档管理中心

**技术亮点**：
- **多格式支持**：PDF（PyPDF2）、TXT（UTF-8）
- **自动分段**：按标题（Installation、Safety 等）智能切分
- **即时索引**：上传后立即可问答，无需重启服务
- **持久化存储**：`data/uploaded_manuals.json` + `uploads/` 目录

**代码位置**：
- `app/services/upload_manual.py:upload_manual()` — 上传主流程
- `app/services/upload_manual.py:process_uploaded_manual()` — 文本提取 + 分段
- `app/main.py:upload_manual_endpoint()` — API 端点

---

### 4. 删除上传文档

**演示步骤**：
1. 在文档管理中心找到上传的文档（标记为 **Uploaded**）
2. 点击 **Delete** 按钮
3. 确认删除
4. 系统自动：
   - 删除 JSON 记录
   - 删除源文件
   - 从向量库移除所有相关向量
   - 删除已生成的 PDF

**技术亮点**：
- **级联删除**：一键清理所有关联数据
- **安全防护**：内置产品不可删除（前端 + 后端双重校验）
- **原子操作**：删除失败不影响其他数据

**代码位置**：
- `app/services/upload_manual.py:delete_uploaded_manual()` — 删除逻辑
- `app/services/vector_store.py:remove_product()` — 向量库删除
- `app/main.py:delete_manual()` — API 端点

---

## 架构设计

### RAG 流程图

```
用户提问
   ↓
语言检测 (detect_language)
   ↓
产品匹配 (match_product_id) ← 可选，用户可手动指定
   ↓
向量检索 (vector_store.search) ← Top-3 相关段落
   ↓
Prompt 拼接 (answer_engine)
   ↓
Claude API 生成答案
   ↓
返回 (答案 + 语言 + 产品 ID + 来源)
```

### 数据流

```
产品数据 (JSON)
   ↓
分段 (product_chunks) ← 按 section 切分
   ↓
向量化 (embed_text) ← Sentence Transformers
   ↓
存入向量库 (Milvus / LocalVectorStore)
   ↓
检索时计算余弦相似度
```

### 目录结构

```
product-manual-agent-demo/
├── app/
│   ├── main.py                 # FastAPI 主应用
│   ├── config.py               # 配置（API Key、路径、语言列表）
│   ├── models.py               # Pydantic 数据模型
│   ├── services/
│   │   ├── answer_engine.py    # 问答引擎
│   │   ├── embedding.py        # 向量化
│   │   ├── language.py         # 语言检测
│   │   ├── llm.py              # Claude API 封装
│   │   ├── pdf_manual.py       # PDF 生成
│   │   ├── products.py         # 产品数据加载
│   │   ├── upload_manual.py    # 上传处理
│   │   └── vector_store.py     # 向量库（双后端）
│   ├── static/
│   │   └── styles.css          # 样式表
│   └── templates/
│       └── index.html          # 前端页面
├── data/
│   ├── products.json           # 内置产品数据
│   ├── furniture_products.json # 家具产品数据
│   └── uploaded_manuals.json   # 上传记录
├── tests/
│   └── test_demo.py            # 单元测试（26 个用例）
├── outputs/                    # 生成的 PDF
├── uploads/                    # 上传的文件
├── requirements.txt            # Python 依赖
├── run.sh                      # 一键启动脚本（macOS/Linux）
├── run.bat                     # 一键启动脚本（Windows）
└── README.md                   # 项目说明
```

---

## 一键部署指南

### 前置条件
- Python 3.9+
- 网络连接（首次需下载依赖和模型）

### macOS / Linux

```bash
# 1. 克隆或拷贝项目到目标机器
cd /path/to/project

# 2. 一键启动（自动创建虚拟环境 + 安装依赖 + 启动服务）
./run.sh

# 3. 浏览器打开
open http://127.0.0.1:8000
```

### Windows

```cmd
REM 1. 进入项目目录
cd C:\path\to\project

REM 2. 双击 run.bat 或命令行执行
run.bat

REM 3. 浏览器打开
start http://127.0.0.1:8000
```

### 自定义端口

```bash
# macOS/Linux
PORT=9000 ./run.sh

# Windows（修改 run.bat 第 6 行）
set PORT=9000
```

### 环境变量配置

在项目根目录创建 `.env` 文件（可选）：

```bash
# Claude API Key（必需，用于问答生成）
ANTHROPIC_API_KEY=sk-ant-xxxxx

# 向量库后端（可选，默认 local）
VECTOR_STORE_BACKEND=local  # 或 milvus

# Milvus 连接（仅当 VECTOR_STORE_BACKEND=milvus 时需要）
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

**注意**：
- 如果没有 Claude API Key，系统会使用 Mock 模式（返回固定答案）
- 向量检索功能不依赖 API Key，始终可用

---

## 测试验证

### 运行全部测试

```bash
# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# 运行测试
pytest tests/test_demo.py -v

# 预期输出
# ====== 26 passed in 4.08s ======
```

### 测试覆盖

- ✅ 语言检测（英文、日文、中文）
- ✅ 产品匹配（自动匹配、同义词）
- ✅ 向量检索（7 种语言）
- ✅ 问答生成（带来源引用）
- ✅ PDF 生成（全语言、语言子集）
- ✅ 上传处理（PDF、TXT）
- ✅ 文档管理（列表、删除）
- ✅ 边界情况（上传产品只有 en、删除内置产品报错）

---

## 面试演示流程建议

### 第一部分：功能演示（5 分钟）

1. **启动服务**（30 秒）
   ```bash
   ./run.sh
   # 展示一键启动，无需手动配置
   ```

2. **多语言问答**（2 分钟）
   - 英文提问：`How do I assemble the table?`
   - 中文提问：`书架怎么安装防倾倒？`
   - 日文提问：`組み立て方法を教えてください`
   - 强调：自动语言检测 + 产品匹配

3. **文档管理**（2 分钟）
   - 选择产品 → 勾选语言（如 EN + CN）→ 生成 PDF
   - 打开 PDF 展示排版质量
   - 强调：动态语言选择、中日文支持

4. **上传自定义手册**（30 秒）
   - 上传一个 TXT 文件
   - 展示自动索引 + 同步到文档中心
   - 删除演示

### 第二部分：技术讲解（5 分钟）

1. **架构设计**（2 分钟）
   - RAG 流程图讲解
   - 向量检索原理（Sentence Transformers + 余弦相似度）
   - 为什么选择 FastAPI（异步高性能）

2. **核心代码走读**（2 分钟）
   - `answer_engine.py` — 问答主流程
   - `pdf_manual.py` — PDF 生成逻辑
   - `vector_store.py` — 双后端设计（Milvus + Local）

3. **工程实践**（1 分钟）
   - 单元测试覆盖率
   - 一键部署脚本设计
   - 错误处理和降级策略

### 第三部分：Q&A（5 分钟）

**常见问题准备**：

**Q1: 为什么不用 LangChain？**
> A: LangChain 对于这个项目来说过重，我们只需要简单的 RAG 流程。直接调用 Claude API + Sentence Transformers 更轻量、可控性更强，依赖更少。

**Q2: 向量库为什么支持两种后端？**
> A: Milvus 是生产级向量库，性能强但部署复杂。本地向量库是纯 Python 实现，零依赖，适合演示和小规模场景。系统会自动检测 Milvus 是否可用，不可用时降级到本地模式。

**Q3: 如何保证多语言答案的准确性？**
> A: 三层保障：
> 1. 语言检测确保用户语言正确识别
> 2. 向量检索时按语言过滤，只检索同语言段落
> 3. Prompt 中明确要求 Claude 用检测到的语言回答

**Q4: 如果用户提问的产品不在库里怎么办？**
> A: 系统会返回最相似的产品答案，并在来源中标注产品 ID。用户可以手动选择产品后重新提问。未来可以加入"未找到匹配产品"的提示。

**Q5: 性能如何？能支持多少并发？**
> A: 单机测试：
> - 向量检索：< 50ms（本地）、< 20ms（Milvus）
> - Claude API 调用：1-3 秒（取决于网络和答案长度）
> - PDF 生成：2-5 秒（7 种语言）
> 
> FastAPI 是异步框架，理论上可以支持数百并发。瓶颈在 Claude API 的 rate limit（需要企业账号提升配额）。

**Q6: 如何扩展到更多语言？**
> A: 三步：
> 1. 在 `config.py` 的 `SUPPORTED_LANGUAGES` 中添加语言代码
> 2. 在 `data/products.json` 中为每个产品添加该语言的内容
> 3. 在 `language.py` 中添加该语言的检测规则（可选，Unicode 范围自动覆盖大部分语言）

---

## 项目亮点总结

### 技术亮点
1. **RAG 架构**：检索增强生成，答案有据可查
2. **多语言支持**：7 种语言无缝切换，自动检测
3. **双向量库**：Milvus + Local 自动降级，部署灵活
4. **动态 PDF**：用户自选语言，实时生成
5. **一键部署**：零配置启动，跨平台兼容

### 工程亮点
1. **测试覆盖**：26 个单元测试，100% 通过
2. **代码质量**：类型注解、文档字符串、模块化设计
3. **错误处理**：API Key 缺失自动降级、向量库连接失败降级
4. **用户体验**：响应式设计、实时反馈、操作可逆（删除前确认）

### 业务价值
1. **降低客服成本**：买家自助查询，减少人工客服压力
2. **提升转化率**：多语言支持覆盖全球市场，降低语言门槛
3. **快速上线**：卖家上传产品手册即可使用，无需技术团队
4. **数据积累**：问答记录可用于优化产品说明、发现常见问题

---

## 后续优化方向

### 短期（1-2 周）
- [ ] 添加问答历史记录（用户可查看过往提问）
- [ ] 支持图片上传（OCR 提取文本）
- [ ] 添加"未找到匹配产品"的友好提示
- [ ] 优化 PDF 排版（添加产品图片、二维码）

### 中期（1-2 月）
- [ ] 多租户支持（每个卖家独立数据）
- [ ] 用户反馈机制（答案点赞/点踩）
- [ ] 问答质量监控（答案准确率统计）
- [ ] 支持更多文件格式（Word、Excel）

### 长期（3-6 月）
- [ ] 语音问答（集成 Whisper）
- [ ] 视频教程生成（根据手册自动生成安装视频）
- [ ] 多模态检索（图片 + 文本混合检索）
- [ ] 知识图谱（产品关系、配件推荐）

---

## 联系方式

- **项目名称**：Product Manual Agent Demo
- **演示地址**：`http://127.0.0.1:8000`（本地启动后）
- **测试命令**：`pytest tests/test_demo.py -v`

---

**祝面试顺利！🎉**
