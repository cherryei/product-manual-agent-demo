# 一键部署指南

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/cherryei/product-manual-agent-demo.git
cd product-manual-agent-demo
```

### 2. 初始化数据文件

```bash
# 创建空的上传记录文件
cp data/uploaded_manuals.json.template data/uploaded_manuals.json
```

### 3. 一键启动

**macOS / Linux:**
```bash
chmod +x run.sh
./run.sh
```

**Windows:**
```cmd
run.bat
```

### 4. 访问应用

打开浏览器访问：http://127.0.0.1:8000

---

## 系统要求

- **Python**: 3.10 或更高版本
- **操作系统**: macOS, Windows, Linux
- **内存**: 至少 512MB 可用内存
- **磁盘**: 至少 500MB 可用空间

---

## 字体支持（重要！）

### 问题说明

PDF 生成需要支持多语言（中文、日文、德文等）的字体。如果系统没有合适的字体，会降级到 Helvetica（不支持 CJK 字符），导致 PDF 生成失败。

### 错误症状

如果看到以下错误：
```
✗ Error: solid-oak-dining-table - "handle_pageBegin args=() 'ManualFont'"
```

说明字体注册失败。

### 解决方案

#### macOS

macOS 通常已经包含所需字体，无需额外安装。

如果仍有问题，安装 Arial Unicode：
```bash
# 检查字体是否存在
ls /Library/Fonts/Arial\ Unicode.ttf
ls /System/Library/Fonts/Supplemental/Arial\ Unicode.ttf
```

#### Windows

安装微软雅黑（通常已预装）：

1. 打开 `C:\Windows\Fonts\`
2. 检查是否有 `msyh.ttc`（微软雅黑）
3. 如果没有，从 Windows 设置安装：
   - 设置 → 个性化 → 字体 → 获取更多字体
   - 搜索并安装 "Microsoft YaHei"

或者使用命令行检查：
```cmd
dir C:\Windows\Fonts\msyh.ttc
dir C:\Windows\Fonts\arial.ttf
```

#### Linux (Ubuntu/Debian)

安装 Noto Sans CJK 字体：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install fonts-noto-cjk

# 验证安装
fc-list | grep -i noto
```

或者安装 DejaVu Sans：
```bash
sudo apt-get install fonts-dejavu
```

#### 验证字体安装

启动服务后，查看日志：

```bash
# macOS/Linux
tail -f /tmp/server.log | grep -i font

# Windows
type nohup.out | findstr /i font
```

如果看到：
```
WARNING: No suitable font found. Using Helvetica (CJK characters may not render correctly).
```

说明需要安装字体。

---

## 环境变量配置（可选）

### LLM API 配置

如果需要使用 AI 问答功能，需要配置 LLM API：

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

配置选项：

```bash
# OpenAI API
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选

# 或者使用 Anthropic Claude
ANTHROPIC_API_KEY=your-api-key-here

# 或者使用 Google Gemini
GOOGLE_API_KEY=your-api-key-here
```

**注意**：如果不配置 LLM API，文档管理和下载功能仍然可以正常使用，只是 AI 问答功能会被禁用。

---

## 端口配置

默认端口是 `8000`。如果端口被占用，可以修改：

### 方法 1：修改启动脚本

**run.sh (macOS/Linux):**
```bash
# 找到这一行
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 改为
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

**run.bat (Windows):**
```cmd
REM 找到这一行
uvicorn app.main:app --host 127.0.0.1 --port 8000

REM 改为
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

### 方法 2：手动启动

```bash
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

---

## 故障排查

### 问题 1：下载 PDF 时显示 404 错误

**症状**：
```
✗ Error: solid-oak-dining-table - HTTP 404
```

**可能原因**：
1. 字体问题导致 PDF 生成失败
2. `data/uploaded_manuals.json` 包含旧数据

**解决方案**：

```bash
# 1. 检查字体（见上面的"字体支持"部分）

# 2. 清理旧数据
echo "[]" > data/uploaded_manuals.json

# 3. 重启服务
# macOS/Linux
lsof -ti tcp:8000 | xargs kill
./run.sh

# Windows
taskkill /F /IM python.exe
run.bat

# 4. 清除浏览器缓存
# Chrome/Edge: Ctrl+Shift+Delete
# 或者使用隐私模式/无痕模式
```

### 问题 2：端口已被占用

**症状**：
```
ERROR: [Errno 48] Address already in use
```

**解决方案**：

```bash
# macOS/Linux - 查找并杀死占用端口的进程
lsof -ti tcp:8000 | xargs kill

# Windows - 查找并杀死占用端口的进程
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# 或者使用不同的端口（见上面的"端口配置"）
```

### 问题 3：Python 版本不兼容

**症状**：
```
SyntaxError: invalid syntax
```

**解决方案**：

```bash
# 检查 Python 版本
python3 --version

# 需要 Python 3.10 或更高版本
# 如果版本过低，安装新版本：

# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt-get install python3.11

# Windows
# 从 https://www.python.org/downloads/ 下载安装
```

### 问题 4：依赖安装失败

**症状**：
```
ERROR: Could not find a version that satisfies the requirement...
```

**解决方案**：

```bash
# 升级 pip
python3 -m pip install --upgrade pip

# 手动安装依赖
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 如果仍然失败，尝试使用国内镜像（中国用户）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 5：权限问题

**症状**：
```
Permission denied: 'outputs/'
```

**解决方案**：

```bash
# macOS/Linux
chmod -R 755 outputs/ uploads/ data/

# Windows
# 右键文件夹 → 属性 → 安全 → 编辑 → 添加完全控制权限
```

---

## 完整的端到端测试

运行以下脚本验证部署是否成功：

```bash
#!/bin/bash
set -e

echo "=== 端到端部署测试 ==="

# 1. 检查服务健康状态
echo "1. 检查服务..."
curl -s http://127.0.0.1:8000/health | python3 -m json.tool

# 2. 获取文档列表
echo "2. 获取文档列表..."
curl -s http://127.0.0.1:8000/api/documents | python3 -m json.tool | head -20

# 3. 生成 PDF
echo "3. 生成 PDF..."
RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/manual/solid-oak-dining-table/pdf \
  -H "Content-Type: application/json" \
  -d '{"languages": ["en"]}')
echo "$RESPONSE" | python3 -m json.tool

# 4. 下载 PDF
echo "4. 下载 PDF..."
DOWNLOAD_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['download_url'])")
curl -s -o /tmp/test-deployment.pdf "http://127.0.0.1:8000$DOWNLOAD_URL"

# 5. 验证文件
echo "5. 验证文件..."
if [ -f /tmp/test-deployment.pdf ]; then
    ls -lh /tmp/test-deployment.pdf
    file /tmp/test-deployment.pdf
    echo "✓ 部署测试通过！"
else
    echo "✗ 部署测试失败"
    exit 1
fi
```

保存为 `test_deployment.sh`，然后运行：

```bash
chmod +x test_deployment.sh
./test_deployment.sh
```

---

## 生产环境部署建议

### 1. 使用生产级 WSGI 服务器

```bash
# 安装 gunicorn
pip install gunicorn

# 启动（4 个 worker）
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2. 使用反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /downloads/ {
        alias /path/to/product-manual-agent-demo/outputs/;
    }
}
```

### 3. 使用进程管理器（systemd）

创建 `/etc/systemd/system/product-manual.service`：

```ini
[Unit]
Description=Product Manual Agent Demo
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/product-manual-agent-demo
Environment="PATH=/path/to/product-manual-agent-demo/.venv/bin"
ExecStart=/path/to/product-manual-agent-demo/.venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable product-manual
sudo systemctl start product-manual
sudo systemctl status product-manual
```

### 4. 配置日志

```bash
# 创建日志目录
mkdir -p logs

# 修改启动命令
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --log-level info
```

---

## 更多帮助

- **完整文档**: 查看 `docs/` 目录
- **故障诊断**: `docs/DOWNLOAD_DEBUG.md`
- **面试演示**: `docs/INTERVIEW.md`
- **GitHub Issues**: https://github.com/cherryei/product-manual-agent-demo/issues

---

**最后更新**: 2026-05-29
