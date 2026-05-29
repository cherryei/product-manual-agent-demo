# 下载功能故障诊断指南

## 问题现象

在其他电脑上部署后，点击"Download Selected PDFs"显示错误：
```
✗ Error: uploaded-0918feaf3867 - HTTP 404
✗ Error: ergonomic-office-chair - HTTP 404
```

## 诊断步骤

### 1. 检查服务是否正常运行

```bash
curl http://127.0.0.1:8000/health
# 应该返回: {"status":"ok","llm_enabled":...}
```

### 2. 检查文档列表 API

```bash
curl http://127.0.0.1:8000/api/documents | python3 -m json.tool
# 应该返回 4 个内置文档的列表
```

如果返回的文档列表中包含 `uploaded-xxx` 的文档，但实际不存在，说明：
- `data/uploaded_manuals.json` 文件有旧数据
- **解决方案**：删除或清空该文件

```bash
echo "[]" > data/uploaded_manuals.json
# 重启服务
```

### 3. 手动测试 PDF 生成

```bash
# 生成 PDF
curl -X POST http://127.0.0.1:8000/api/manual/solid-oak-dining-table/pdf \
  -H "Content-Type: application/json" \
  -d '{"languages": ["en"]}' | python3 -m json.tool

# 应该返回：
# {
#   "product_id": "solid-oak-dining-table",
#   "path": "/path/to/outputs/solid-oak-dining-table-manual-en.pdf",
#   "download_url": "/downloads/solid-oak-dining-table-manual-en.pdf",
#   "languages": ["en"]
# }
```

### 4. 检查 outputs 目录

```bash
ls -lh outputs/
# 应该看到刚生成的 PDF 文件
```

如果 `outputs/` 目录不存在或为空：
- PDF 生成失败
- 检查服务器日志：`tail -50 /tmp/server.log` 或 `nohup.out`

### 5. 测试下载链接

```bash
# 使用上一步返回的 download_url
curl -I http://127.0.0.1:8000/downloads/solid-oak-dining-table-manual-en.pdf

# 应该返回：
# HTTP/1.1 200 OK
# content-disposition: attachment; filename=solid-oak-dining-table-manual-en.pdf
```

如果返回 404：
- 文件名不匹配
- 检查 `outputs/` 目录中的实际文件名

### 6. 实际下载测试

```bash
curl -o test.pdf http://127.0.0.1:8000/downloads/solid-oak-dining-table-manual-en.pdf
file test.pdf
# 应该显示: test.pdf: PDF document, version 1.4
```

## 常见问题和解决方案

### 问题 1：`uploaded-xxx` 文档不存在

**原因**：`data/uploaded_manuals.json` 包含旧的上传记录

**解决方案**：
```bash
cd product-manual-agent-demo
echo "[]" > data/uploaded_manuals.json
# 重启服务
lsof -ti tcp:8000 | xargs kill
./run.sh
```

### 问题 2：内置文档也返回 404

**可能原因**：
1. PDF 生成失败（字体问题、权限问题）
2. `outputs/` 目录权限问题
3. 路径配置问题

**诊断**：
```bash
# 检查 outputs 目录权限
ls -ld outputs/
# 应该是: drwxr-xr-x

# 手动创建目录
mkdir -p outputs
chmod 755 outputs

# 测试 PDF 生成
python3 -c "
from app.services.pdf_manual import generate_manual_pdf
path = generate_manual_pdf('solid-oak-dining-table', ['en'])
print(f'Generated: {path}')
print(f'Exists: {path.exists()}')
"
```

### 问题 3：浏览器缓存了旧的文档列表

**解决方案**：
1. 清除浏览器缓存（Ctrl+Shift+Delete）
2. 或者硬刷新（Ctrl+Shift+R / Cmd+Shift+R）
3. 或者使用隐私模式/无痕模式

### 问题 4：字体缺失导致 PDF 生成失败

**症状**：服务器日志显示字体相关错误

**解决方案**：
```bash
# macOS
brew install font-noto-sans-cjk

# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk

# 或者使用系统自带字体（已在代码中配置）
```

### 问题 5：权限问题

**症状**：`Permission denied` 错误

**解决方案**：
```bash
# 确保当前用户有写权限
chmod -R 755 outputs/
chmod -R 755 uploads/
chmod -R 755 data/
```

## 调试模式

启用详细日志：

```bash
# 停止服务
lsof -ti tcp:8000 | xargs kill

# 启动调试模式
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level debug

# 在另一个终端测试
curl -X POST http://127.0.0.1:8000/api/manual/solid-oak-dining-table/pdf \
  -H "Content-Type: application/json" \
  -d '{"languages": ["en"]}'
```

查看详细日志，找到错误原因。

## 浏览器开发者工具调试

1. 打开浏览器开发者工具（F12）
2. 切换到 **Network** 标签
3. 勾选一个文档，点击"Download Selected PDFs"
4. 观察网络请求：

**正常流程**：
```
POST /api/manual/solid-oak-dining-table/pdf → 200 OK
GET /downloads/solid-oak-dining-table-manual-en.pdf → 200 OK
```

**异常流程**：
```
POST /api/manual/solid-oak-dining-table/pdf → 404 Not Found
# 或
POST /api/manual/solid-oak-dining-table/pdf → 200 OK
GET /downloads/solid-oak-dining-table-manual-en.pdf → 404 Not Found
```

5. 点击失败的请求，查看：
   - **Request Headers**：确认请求正确
   - **Response**：查看错误详情
   - **Console**：查看 JavaScript 错误

## 完整的端到端测试脚本

```bash
#!/bin/bash
set -e

echo "=== 端到端下载测试 ==="

# 1. 检查服务
echo "1. 检查服务健康状态..."
curl -s http://127.0.0.1:8000/health | python3 -m json.tool

# 2. 清理旧数据
echo "2. 清理旧的上传记录..."
echo "[]" > data/uploaded_manuals.json

# 3. 获取文档列表
echo "3. 获取文档列表..."
DOCS=$(curl -s http://127.0.0.1:8000/api/documents)
echo "$DOCS" | python3 -m json.tool | head -20

# 4. 生成 PDF
echo "4. 生成 PDF..."
RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/manual/solid-oak-dining-table/pdf \
  -H "Content-Type: application/json" \
  -d '{"languages": ["en", "de"]}')
echo "$RESPONSE" | python3 -m json.tool

# 5. 提取下载 URL
DOWNLOAD_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['download_url'])")
echo "下载 URL: $DOWNLOAD_URL"

# 6. 下载文件
echo "5. 下载文件..."
curl -s -o /tmp/test-download.pdf "http://127.0.0.1:8000$DOWNLOAD_URL"

# 7. 验证文件
echo "6. 验证下载的文件..."
if [ -f /tmp/test-download.pdf ]; then
    ls -lh /tmp/test-download.pdf
    file /tmp/test-download.pdf
    echo "✓ 下载测试通过！"
else
    echo "✗ 下载失败"
    exit 1
fi
```

保存为 `test_download.sh`，然后运行：
```bash
chmod +x test_download.sh
./test_download.sh
```

## 联系支持

如果以上步骤都无法解决问题，请提供：

1. 操作系统版本：`uname -a`
2. Python 版本：`python3 --version`
3. 服务器日志：最后 50 行
4. 浏览器 Network 标签的截图
5. 完整的错误信息

---

**最后更新**：2026-05-29
