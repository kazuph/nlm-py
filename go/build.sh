#!/bin/bash
set -e

# スクリプトが存在するディレクトリに移動
cd "$(dirname "$0")"

# ビルド対象のOSとアーキテクチャ
OS_ARCH_PAIRS=(
  "darwin/amd64"
  "darwin/arm64"
  "linux/amd64"
  "linux/arm64"
  "windows/amd64"
)

# バイナリの出力先ディレクトリを作成
BIN_DIR="../nlm/bin"
mkdir -p "$BIN_DIR"

echo "Building nlm-auth binaries..."

# 各OSとアーキテクチャでビルド
for os_arch in "${OS_ARCH_PAIRS[@]}"; do
  OS="${os_arch%%/*}"
  ARCH="${os_arch##*/}"
  
  # バイナリ名の設定（Windowsの場合は.exeを付ける）
  if [ "$OS" = "windows" ]; then
    BINARY_NAME="nlm-auth-${OS}-${ARCH}.exe"
  else
    BINARY_NAME="nlm-auth-${OS}-${ARCH}"
  fi
  
  echo "Building for ${OS}/${ARCH}..."
  
  # クロスコンパイル
  GOOS=$OS GOARCH=$ARCH go build -o "${BIN_DIR}/${BINARY_NAME}" ./cmd/nlm-auth
  
  # 実行権限を付与（Windows以外）
  if [ "$OS" != "windows" ]; then
    chmod +x "${BIN_DIR}/${BINARY_NAME}"
  fi
done

echo "Build completed successfully!"
echo "Binaries available in ${BIN_DIR}:"
ls -la "$BIN_DIR"
