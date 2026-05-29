#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Product Manual Agent — 一键部署 & 启动脚本 (macOS / Linux)
#
# 用法：
#   ./run.sh            首次会自动建虚拟环境 + 装依赖，然后启动服务
#   PORT=9000 ./run.sh  自定义端口
#
# 脚本是「路径无关」的：拷到任何电脑、任何目录，双击/执行都能跑。
# ---------------------------------------------------------------------------
set -euo pipefail

# 永远以脚本所在目录为根，而不是当前工作目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
VENV_DIR="$SCRIPT_DIR/.venv"

# 1. 选择 python（python3 优先）
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "❌ 找不到 Python，请先安装 Python 3.9+：https://www.python.org/downloads/"
  exit 1
fi

echo "▶ 使用 Python: $($PY --version)"

# 2. 没有 .venv 就创建（首次部署）
if [ ! -d "$VENV_DIR" ]; then
  echo "▶ 首次运行，创建虚拟环境 .venv ..."
  "$PY" -m venv "$VENV_DIR"
fi

# 3. 激活虚拟环境
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 4. 安装/更新依赖（用标记文件避免每次都重装，加速二次启动）
STAMP="$VENV_DIR/.deps-installed"
if [ ! -f "$STAMP" ] || [ requirements.txt -nt "$STAMP" ]; then
  echo "▶ 安装依赖 (requirements.txt) ..."
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r requirements.txt
  touch "$STAMP"
else
  echo "▶ 依赖已就绪，跳过安装。"
fi

# 5. 端口被占用就温柔地清理掉旧进程
if command -v lsof >/dev/null 2>&1; then
  OLD_PID="$(lsof -ti "tcp:$PORT" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ]; then
    echo "▶ 端口 $PORT 被占用 (pid $OLD_PID)，正在停止旧服务 ..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
fi

# 6. 启动
echo ""
echo "============================================================"
echo "  ✅ 服务启动中，请在浏览器打开：  http://$HOST:$PORT"
echo "  健康检查： http://$HOST:$PORT/health"
echo "  停止服务： Ctrl + C"
echo "============================================================"
echo ""

exec uvicorn app.main:app --host "$HOST" --port "$PORT"
