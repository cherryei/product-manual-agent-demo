# 下载功能说明

## 问题描述

在某些电脑/浏览器上，批量下载 PDF 功能可能显示"下载成功"，但实际没有下载文件。

## 原因分析

### 1. 浏览器弹窗拦截
- 现代浏览器（Chrome、Firefox、Safari）默认会阻止网页自动触发多个下载
- 特别是使用 `window.open()` 或动态创建的 `<a>` 标签时

### 2. 浏览器下载设置
- 某些浏览器设置为"每次下载前询问保存位置"
- 批量下载时会弹出多个对话框，用户可能没注意到

## 已实施的解决方案

### 后端改进 ✅
```python
# 添加 Content-Disposition: attachment 头
return FileResponse(
    path,
    media_type="application/pdf",
    filename=filename,
    headers={"Content-Disposition": f"attachment; filename={filename}"}
)
```

这会强制浏览器下载文件，而不是在新标签页打开。

### 前端改进 ✅
```javascript
// 使用隐藏的 iframe 触发下载（不会被浏览器阻止）
const iframe = document.createElement("iframe");
iframe.style.display = "none";
iframe.src = data.download_url;
document.body.appendChild(iframe);
```

iframe 方法比 `window.open()` 更不容易被浏览器阻止。

## 用户操作指南

### 方法 1：允许弹窗（推荐）

**Chrome**:
1. 点击地址栏右侧的 🔒 或 ⓘ 图标
2. 找到"弹出式窗口和重定向"
3. 选择"允许"
4. 刷新页面

**Firefox**:
1. 点击地址栏左侧的 🔒 图标
2. 点击"连接安全"旁边的 ▶
3. 找到"阻止弹出式窗口"
4. 取消勾选
5. 刷新页面

**Safari**:
1. Safari 菜单 → 偏好设置 → 网站
2. 左侧选择"弹出式窗口"
3. 找到 `127.0.0.1` 或当前网站
4. 选择"允许"

### 方法 2：单个下载

如果批量下载仍然有问题，可以：
1. 只勾选 1 个文档
2. 点击"Download Selected PDFs"
3. 等待下载完成
4. 重复以上步骤

### 方法 3：直接访问下载链接

1. 打开浏览器开发者工具（F12）
2. 切换到 Console 标签
3. 点击"Download Selected PDFs"
4. 在 Console 中会看到生成的下载链接
5. 右键点击链接 → "在新标签页中打开"或"另存为"

### 方法 4：使用 API 直接下载

```bash
# 1. 生成 PDF
curl -X POST http://127.0.0.1:8000/api/manual/solid-oak-dining-table/pdf \
  -H "Content-Type: application/json" \
  -d '{"languages": ["en", "de", "it"]}' \
  | python3 -m json.tool

# 2. 从返回的 download_url 下载
curl -O http://127.0.0.1:8000/downloads/solid-oak-dining-table-manual-en-de-it.pdf
```

## 验证下载功能

### 后端测试
```bash
# 测试 PDF 生成
curl -X POST http://127.0.0.1:8000/api/manual/solid-oak-dining-table/pdf \
  -H "Content-Type: application/json" \
  -d '{"languages": ["en"]}'

# 测试下载链接
curl -I http://127.0.0.1:8000/downloads/solid-oak-dining-table-manual-en.pdf

# 应该看到：
# HTTP/1.1 200 OK
# content-disposition: attachment; filename=solid-oak-dining-table-manual-en.pdf
```

### 前端测试
1. 打开 http://127.0.0.1:8000
2. 打开浏览器开发者工具（F12）
3. 切换到 Network 标签
4. 勾选一个文档，点击"Download Selected PDFs"
5. 在 Network 标签中应该看到：
   - POST `/api/manual/{id}/pdf` - 状态 200
   - GET `/downloads/{filename}.pdf` - 状态 200

## 面试演示建议

### 提前准备
1. **在演示电脑上提前测试**
   ```bash
   git clone https://github.com/cherryei/product-manual-agent-demo.git
   cd product-manual-agent-demo
   ./run.sh
   ```

2. **配置浏览器允许弹窗**（见上面的方法 1）

3. **准备备用方案**
   - 如果批量下载有问题，演示单个下载
   - 或者直接展示 `outputs/` 目录中已生成的 PDF

### 演示流程
1. **展示功能**："这是批量下载功能，可以一次性下载多个产品的多语言手册"
2. **选择文档**：勾选 1-2 个文档
3. **选择语言**：勾选 2-3 种语言
4. **点击下载**：点击"Download Selected PDFs"
5. **展示结果**：
   - 如果下载成功：展示下载的文件
   - 如果被阻止：说明"浏览器默认会阻止批量下载，这是安全特性，用户可以在设置中允许"
   - 然后演示单个下载或直接展示 `outputs/` 目录

### 话术建议
> "系统支持批量下载多语言 PDF。由于浏览器的安全限制，批量下载可能需要用户允许弹窗。在生产环境中，我们会引导用户进行一次性配置，或者提供打包下载（ZIP）的选项。"

## 未来改进方向

### 短期
- [ ] 添加"打包下载"功能（生成 ZIP 文件）
- [ ] 添加下载进度提示
- [ ] 检测浏览器是否阻止了下载，并显示提示

### 中期
- [ ] 使用 Service Worker 实现后台下载
- [ ] 添加下载队列管理
- [ ] 支持断点续传

### 长期
- [ ] 集成云存储（S3、OSS）
- [ ] 生成分享链接
- [ ] 邮件发送下载链接

---

## 技术细节

### 为什么使用 iframe 而不是 window.open？

1. **iframe 不会被弹窗拦截器阻止**
   - 浏览器认为 iframe 是页面的一部分，不是弹窗
   - `window.open()` 会被识别为弹窗并阻止

2. **iframe 不会打开新标签页**
   - 用户体验更好
   - 不会干扰用户当前的浏览状态

3. **iframe 支持 Content-Disposition: attachment**
   - 浏览器会自动触发下载
   - 不需要用户交互

### 为什么添加 Content-Disposition 头？

```python
headers={"Content-Disposition": f"attachment; filename={filename}"}
```

- **没有这个头**：浏览器会尝试在新标签页中打开 PDF
- **有这个头**：浏览器会直接下载文件到下载目录

这是 HTTP 标准的一部分，所有现代浏览器都支持。

---

**总结**：下载功能在后端是完全正常的，前端也已经使用了最可靠的方法（iframe + Content-Disposition）。如果仍然有问题，通常是浏览器设置导致的，用户需要允许弹窗或调整下载设置。
