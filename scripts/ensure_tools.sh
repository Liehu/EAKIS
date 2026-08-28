#!/usr/bin/env bash
# 探活并（可选）安装资产发现/漏洞扫描所需的外部工具二进制。
# 用法:
#   ./scripts/ensure_tools.sh          # 仅探活
#   ./scripts/ensure_tools.sh install  # 缺失时 go install（需 go >= 1.21）
set -u

GO_BIN="$(go env GOPATH 2>/dev/null || echo "$HOME/go")/bin"
export PATH="$GO_BIN:$PATH"
GOPROXY="${GOPROXY:-https://goproxy.cn,direct}"

TOOLS=(
  "subfinder:github.com/projectdiscovery/subfinder/v2/cmd/subfinder"
  "dnsx:github.com/projectdiscovery/dnsx/cmd/dnsx"
  "httpx:github.com/projectdiscovery/httpx/cmd/httpx"
  "naabu:github.com/projectdiscovery/naabu/v2/cmd/naabu"
  "nuclei:github.com/projectdiscovery/nuclei/v3/cmd/nuclei"
)

# 注意: httpx 与 Python httpx CLI 同名，PATH 顺序必须让 go bin 在前。
# 可用 `httpx -version` 验证输出为 ProjectDiscovery ASCII banner。

missing=0
for entry in "${TOOLS[@]}"; do
  name="${entry%%:*}"; pkg="${entry#*:}"
  if command -v "$name" >/dev/null 2>&1; then
    echo "✓ $name ($(command -v "$name"))"
  else
    echo "✗ $name 未安装"
    if [ "${1:-}" = "install" ]; then
      echo "  → go install $pkg@latest (GOPROXY=$GOPROXY)"
      GOPROXY="$GOPROXY" go install "$pkg@latest" && echo "  ✓ 已安装到 $GO_BIN/$name"
    fi
    missing=$((missing+1))
  fi
done

if [ "$missing" -gt 0 ] && [ "${1:-}" != "install" ]; then
  echo "提示: 执行 ./scripts/ensure_tools.sh install 安装缺失工具"
fi
exit 0
