# 一键部署指南 - 适用于任意电脑

## 快速开始（3 步）

### 1. 克隆项目

```bash
git clone https://github.com/cherryei/product-manual-agent-demo.git
cd product-manual-agent-demo
```

### 2. 一键启动

**macOS / Linux**:
```bash
chmod +x run.sh
./run.sh
```

**Windows**:
```cmd
run.bat
```

### 3. 访问应用

打开浏览器访问：http://127.0.0.1:8000

---

## 启动脚本做了什么

`run.sh` / `run.bat` 会自动：

1. ✅ 检查 Python 3.9+ 是否安装
2. ✅ 创建虚拟环境（如果不存在）
3. ✅ 安装依赖（如果需要）
4. ✅ 停止旧服务（如果端口被占用）
5. ✅ 启动 FastAPI 服务器
6. ✅ 显示访问地址

**无需任何手动配置，开箱即用！**

---

## 配置 LLM（可选，启用翻译功能）

1. 打开 http://127.0.0.1:8000
2. 滚动到 **⚙️ LLM Configuration**
3. 填写配置：
   - **Provider**: 选择 `OpenAI-Compatible` 或 `Anthropic (Claude)`
   - **Base URL**: 填写 API 地址（如 `https://api.openai.com/v1`）
   - **API Key**: 填写你的 API Key
4. 点击 **"Test Connection & Get Models"**
5. 从列表中点击选择一个模型
6. 点击 **"Save Configuration"**
7. 重启服务：`./run.sh` 或 `run.bat`

---

## 功能演示流程

### 1. 多语言问答

1. 在 **Ask the manual** 区域输入问题
2. 选择语言（或留空自动检测）
3. 点击 **Ask Agent**
4. 查看答案

**示例问题**：
- EN: "How do I assemble the dining table?"
- DE: "Wie montiere ich den Esstisch?"
- CN: "这个餐桌怎么组装？"

### 2. 上传自定义手册

1. 在 **Upload manual** 区域选择 PDF 或 TXT 文件
2. 可选：填写产品标题
3. 点击 **Upload**
4. 系统自动：
   - 提取文本
   - 检测语言
   - 翻译成 7 种语言（需要配置 LLM）
   - 索引到向量库

### 3. 批量下载 PDF

1. 滚动到 **📚 Document Center**
2. 在 **Select Languages** 区域勾选想要的语言
3. 在表格中勾选想要下载的文档
4. 点击 **"Download Selected PDFs"**
5. 浏览器自动下载所有 PDF

---

## 系统要求

### 必需
- **Python**: 3.9 或更高版本
- **操作系统**: macOS / Linux / Windows
- **内存**: 至少 2GB 可用内存

### 可选（启用向量检索）
- **Docker**: 用于运行 Milvus（如果不安装，自动降级到本地向量库）

---

## 故障排除

### 端口被占用

**macOS / Linux**:
```bash
lsof -ti tcp:8000 | xargs kill
./run.sh
```

**Windows**:
```cmd
netstat -ano | findstr :8000
taskkill /PID <PID> /F
run.bat
```

### Python 版本过低

```bash
# 检查版本
python3 --version

# 如果低于 3.9，请升级
# macOS: brew install python@3.11
# Ubuntu: sudo apt install python3.11
# Windows: 从 python.org 下载安装
```

### 依赖安装失败

```bash
# 手动安装
cd product-manual-agent-demo
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 项目结构

```
product-manual-agent-demo/
├── run.sh / run.bat          # 一键启动脚本
├── app/
│   ├── main.py               # FastAPI 主应用
│   ├── services/
│   │   ├── translation.py    # 自动翻译服务
│   │   ├── upload_manual.py  # 上传服务
│   │   └── ...
│   ├── templates/
│   │   └── index.html        # 前端页面
│   └── static/
│       └── styles.css        # 样式表
├── data/
│   └── manuals/              # 内置产品手册
├── tests/
│   └── test_demo.py          # 29 个测试用例
└── docs/
    ├── DEPLOYMENT.md         # 本文档
    ├── INTERVIEW.md          # 面试演示文档
    └── FINAL_SUMMARY.md      # 技术总结
```

---

## 技术栈

- **后端**: FastAPI + Python 3.9+
- **向量检索**: Milvus / 本地向量库（自动降级）
- **文本向量化**: Sentence Transformers (all-MiniLM-L6-v2)
- **PDF 生成**: ReportLab
- **LLM**: OpenAI-Compatible API / Anthropic Claude
- **前端**: 原生 JavaScript + Jinja2

---

## 测试

```bash
# 运行所有测试
pytest tests/test_demo.py -v

# 运行特定测试
pytest tests/test_demo.py::test_answer_question_in_english -v
```

---

## 生产部署建议

### 1. 使用 Gunicorn + Uvicorn Workers

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2. 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 使用 Docker Compose

```bash
docker compose up -d
```

---

## 常见问题

### Q: 不配置 LLM 可以使用吗？

A: 可以！不配置 LLM 时：
- ✅ 多语言问答正常工作
- ✅ PDF 生成正常工作
- ❌ 上传文档不会自动翻译（只保留源语言）

### Q: 支持哪些 LLM Provider？

A: 支持所有 OpenAI-Compatible API：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic Claude
- Azure OpenAI
- 本地部署的 LLM（Ollama, LM Studio）

### Q: 数据存储在哪里？

A: 
- 向量数据：Milvus（Docker）或本地文件（`data/local_vector_store.json`）
- 上传的文档：`uploads/` 目录
- 文档元数据：`data/uploaded_manuals.json`

### Q: 如何备份数据？

A:
```bash
# 备份上传的文档和元数据
tar -czf backup.tar.gz uploads/ data/uploaded_manuals.json

# 恢复
tar -xzf backup.tar.gz
```

---

## 联系方式

- **GitHub**: https://github.com/cherryei/product-manual-agent-demo
- **演示地址**: http://127.0.0.1:8000（本地启动后）

---

**一键启动，开箱即用！** 🚀
