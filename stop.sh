#!/bin/bash
# ECG Diagnosis Suite - 本地停止脚本

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT_CANDIDATES=(8000 5173 5174)
FOUND_PIDS=()

add_pid() {
    local pid="$1"
    if [ -z "$pid" ]; then
        return
    fi

    for existing in "${FOUND_PIDS[@]:-}"; do
        if [ "$existing" = "$pid" ]; then
            return
        fi
    done

    FOUND_PIDS+=("$pid")
}

is_project_process() {
    local pid="$1"
    local cmd

    cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if [ -z "$cmd" ]; then
        return 1
    fi

    if [[ "$cmd" == *"$PROJECT_ROOT"* ]]; then
        return 0
    fi

    if [[ "$cmd" == *"uvicorn"* && "$cmd" == *"app.main:app"* ]]; then
        return 0
    fi

    if [[ "$cmd" == *"vite"* && "$cmd" == *"/frontend"* ]]; then
        return 0
    fi

    return 1
}

collect_port_pids() {
    local port="$1"
    local pid

    while IFS= read -r pid; do
        if is_project_process "$pid"; then
            add_pid "$pid"
        fi
    done < <(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
}

collect_command_pids() {
    local line
    local pid
    local cmd

    while IFS= read -r line; do
        pid="${line%% *}"
        cmd="${line#"$pid"}"
        cmd="${cmd#" "}"

        if [[ "$cmd" == *"$PROJECT_ROOT"* ]]; then
            if [[ "$cmd" == *"uvicorn"* || "$cmd" == *"vite"* ]]; then
                add_pid "$pid"
            fi
        fi
    done < <(ps -ax -o pid= -o command= 2>/dev/null || true)
}

echo "================================"
echo "ECG Diagnosis Suite - 停止"
echo "================================"
echo ""

for port in "${PORT_CANDIDATES[@]}"; do
    collect_port_pids "$port"
done

collect_command_pids

if [ "${#FOUND_PIDS[@]}" -eq 0 ]; then
    echo "未发现当前项目的本地服务进程。"
    exit 0
fi

echo "准备停止以下进程:"
for pid in "${FOUND_PIDS[@]}"; do
    echo "  PID $pid: $(ps -p "$pid" -o command= 2>/dev/null || echo "<unknown>")"
done

kill "${FOUND_PIDS[@]}" 2>/dev/null || true
sleep 2

REMAINING_PIDS=()
for pid in "${FOUND_PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
        REMAINING_PIDS+=("$pid")
    fi
done

if [ "${#REMAINING_PIDS[@]}" -gt 0 ]; then
    echo ""
    echo "以下进程未正常退出，执行强制停止:"
    for pid in "${REMAINING_PIDS[@]}"; do
        echo "  PID $pid"
    done
    kill -9 "${REMAINING_PIDS[@]}" 2>/dev/null || true
fi

echo ""
echo "✅ 本地服务已停止"
