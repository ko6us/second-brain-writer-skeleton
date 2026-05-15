# 初期セットアップガイド：Second Brain Writer Skeleton

このガイドでは、本リポジトリを導入し、AIエージェントと協調して「第二の脳」を運用し始めるための手順を説明します。

---

## 1. リポジトリの準備

### 1.1 リポジトリのクローン
まずは、GitHubからリポジトリを自分のローカル環境にクローンします。

```bash
git clone https://github.com/ko6us/second-brain-writer-skeleton.git my-second-brain
cd my-second-brain
```

### 1.2 依存関係のインストール（スクリプト利用者のみ）
`scripts/` 内のPythonスクリプト（Gist連携や画像化）を使用する場合は、必要なライブラリをインストールします。

```bash
pip install pandas matplotlib japanize-matplotlib requests
```

---

## 2. エディタ（Obsidian）の設定

本リポジトリは **Obsidian** での閲覧・編集を推奨しています。

1. **Vaultとして開く**: Obsidianを起動し、「Open folder as vault」からクローンしたディレクトリを選択します。
2. **推奨プラグインのインストール**: 以下のプラグインを導入すると、運用がよりスムーズになります。
   - **Obsidian Git**: GitHubとの同期用。
   - **Templater**: 記事テンプレート（`knowledge/template/`）の適用。
   - **Dataview**: ノートや記事のステータス一覧表示。

---

## 3. AIエージェント（Gemini CLI / Antigravity）の導入

AIを「執筆パートナー」として機能させるために、AIエージェントをセットアップします。

1. **Gemini CLIのインストール**: 
   ```bash
   npm install -g @google/gemini-cli
   ```
2. **プロジェクトの読み込み**:
   リポジトリルートで `gemini` を起動します。エージェントは自動的に `GEMINI.md` を読み込み、このプロジェクトのルール（Roleやフォルダ構成）を理解します。

---

## 4. 最初の「思想のライフサイクル」を回す

セットアップが完了したら、以下の手順で実際に使ってみましょう。

### Step 1: 生素材の投入 (Ingest)
何か気になるWeb記事のURLや、自分の走り書きメモを `knowledge/raw/` フォルダにMarkdownファイル（例: `memo.md`）として保存します。

### Step 2: AIによる構造化
AIエージェントを起動し、以下のように依頼します。
> 「`knowledge/raw/memo.md` を読んで、適切な `knowledge/concepts/memos/` に構造化ノートを作成して」

### Step 3: スタンスの抽出 (Distill)
いくつかのメモが溜まってきたら、自分の考えをまとめます。
> 「`knowledge/concepts/memos/` にある最近のノートから、私の共通する『スタンス（主張）』を抽出して `stances/` にまとめて」

### Step 4: 記事の執筆 (Write)
抽出したスタンスを元に、記事のドラフトを作成します。
> 「〇〇というスタンスに基づいて、noteに投稿する記事の構成案を作って」

---

## 5. 高度な設定（Gist連携）

記事内の表をGistで公開し、note等に埋め込みたい場合は、`scripts/config.json.example` を `scripts/config.json` にリネームし、GitHubトークンを設定してください。

```json
{
  "github_token": "your_github_pat_here"
}
```

設定後、以下のコマンドで表のGist同期が可能になります。
```bash
python scripts/md-to-gist.py articles/YYYYMMDD-slug/article.md
```

---

これでお手元の「第二の脳」は、AIと共に進化を続ける準備が整いました。
より詳細な運用ルールについては `GEMINI.md` を参照してください。
