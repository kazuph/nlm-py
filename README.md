# nlm-py

Command-line interface for Google's NotebookLM, written in Python.

## 特徴

- Google NotebookLMへのアクセスと管理機能
- 既存のChromeセッションから認証情報を取得 (Python実装)
- クロスプラットフォーム対応（macOS, Linux, Windows）

## インストール

### ローカルでの使用
```bash
# リポジトリのクローン
git clone https://github.com/kazuph/nlm-py.git
cd nlm-py

# 依存関係のインストール
pip install .
```

### グローバルインストール

`nlm`コマンドをグローバルにインストールして、どこからでも実行できるようにするには、以下の方法があります。

#### pipを使ったインストール

```bash
# GitHubリポジトリから直接インストール
pip install git+https://github.com/kazuph/nlm-py.git
```

インストール後、以下のコマンドで動作確認できます：

```bash
nlm --help
nlm auth
```

#### 開発モードでのインストール（開発者向け）

ソースコードを編集しながら使いたい場合は、開発モードでインストールします：

```bash
git clone https://github.com/kazuph/nlm-py.git
cd nlm-py
pip install -e .
```

#### pipxを使ったインストール（推奨）

pipxを使うと、グローバル環境を汚さずにPythonアプリケーションをインストールできます：

```bash
# pipxのインストール（まだない場合）
pip install pipx
pipx ensurepath

# nlm-pyのインストール
pipx install git+https://github.com/kazuph/nlm-py.git
```

## 使い方

### 認証

```bash
nlm auth
```

これは、ChromeのデフォルトプロファイルからGoogle認証情報を取得します。特定のプロファイルを使用するには：

```bash
nlm auth ProfileName
```

### ノートブックの一覧表示

```bash
nlm list
```

### ノートブックの作成

```bash
nlm create "My New Notebook"
```

### その他のコマンド

詳細なコマンドリストは以下のコマンドで確認できます：

```bash
nlm --help
```

## 開発

### 前提条件

- Python 3.8以上

### セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/kazuph/nlm-py.git
cd nlm-py

# 依存関係のインストール
pip install -e .

```

## アーキテクチャ

このツールは以下のコンポーネントで構成されています：

1. **Python CLI** - コマンドラインインターフェースとNotebookLM APIクライアント
2. **Python Auth Module** - ブラウザからの認証情報取得

## ライセンス

MIT
