# lifelog

Windows PC のアクティビティを自動記録し、ブラウザで可視化するセルフトラッキングツールです。

## 概要

- アクティブウィンドウを1秒ごとにポーリングして SQLite に記録
- Chrome / Edge の DevTools Protocol 経由でブラウザの URL も取得
- FastAPI + Chart.js 製の Web ダッシュボードで閲覧・分析
- システムトレイアプリとして常駐し、ダブルクリック1発で起動

## 機能

### トラッキング
- フォアグラウンドウィンドウのアプリ名・タイトル・URL を記録
- アイドル検出（5分間入力なし → idle フラグ）
- シングルインスタンスロック（多重起動防止）

### ダッシュボード
| タブ | 内容 |
|------|------|
| 日次 | カテゴリ別ドーナツグラフ・フォーカススコア・アプリランキング・セッション一覧 |
| 週次 | 曜日ごとのカテゴリ積み上げ棒グラフ |
| ヒートマップ | GitHub 風の年間活動ヒートマップ |

- ダーク / ライトテーマ切り替え
- CSV・JSON エクスポート
- キーボードナビゲーション（`←` / `→` で日付移動）

### カテゴリ分類
アプリ名と URL のパターンマッチングで自動分類：

| カテゴリ | 例 |
|----------|----|
| 作業 | VS Code、PyCharm、Excel、GitHub、Jira など |
| 娯楽 | YouTube、Netflix、Steam、Spotify など |
| SNS/通信 | Twitter/X、Instagram、Reddit など |
| ブラウザ | Chrome、Edge、Firefox（URL 未分類時） |
| システム | エクスプローラ、タスクマネージャ など |
| その他 | 上記以外 |

### 通知
- 設定した時間制限を超えると Windows 通知で警告
- 毎日 21:00 に当日のサマリー通知

### バックアップ
- 毎週日曜 03:00 に `data/backups/` へ DB をコピー
- 最新 7 世代を保持

## ディレクトリ構成

```
lifelog/
├── launcher.py        # システムトレイアプリ（起動エントリポイント）
├── tracker.py         # ウィンドウポーリング・DB 書き込み
├── api.py             # FastAPI サーバー
├── db.py              # SQLite 操作
├── categories.py      # カテゴリ分類ロジック
├── notifier.py        # Windows 通知
├── backup.py          # 自動バックアップ
├── categories.json    # カテゴリ・制限ルール設定（編集可）
├── launch.vbs         # コンソールなしで launcher.py を起動
├── setup.ps1          # デスクトップ・スタートアップへのショートカット登録
├── Pipfile            # 依存パッケージ
├── frontend/
│   └── index.html     # ダッシュボード UI（バニラ JS + Chart.js）
└── data/
    ├── lifelog.db     # SQLite データベース
    ├── tracker.log    # トラッカーログ
    └── backups/       # 自動バックアップ
```

## セットアップ

### 必要環境
- Windows 10 / 11
- Python 3.12
- pipenv

### インストール

```powershell
# リポジトリをクローン
git clone https://github.com/<your-name>/lifelog.git
cd lifelog

# 依存パッケージをインストール
pipenv install
```

### ショートカット登録（初回のみ）

PowerShell を**管理者として実行**し：

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser  # 初回のみ
.\setup.ps1
```

デスクトップとスタートアップフォルダに `lifelog` のショートカットが作成されます。

## 起動方法

### デスクトップアイコンから（通常）

デスクトップの `lifelog` をダブルクリック → システムトレイに緑アイコンが表示され、ブラウザが自動で開きます。

### コマンドラインから

```powershell
pipenv run python launcher.py
```

### 手動で各サービスを起動する場合

```powershell
# トラッカー
pipenv run python tracker.py

# API サーバー（別ターミナル）
pipenv run uvicorn api:app --port 8000
```

ブラウザで `http://localhost:8000` を開く。

## ブラウザ URL トラッキングの有効化

Chrome / Edge で URL を記録するにはリモートデバッグポートが必要です。

**Chrome の場合：**
ショートカットのリンク先に `--remote-debugging-port=9222` を追記：
```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**Edge の場合：**
```
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9223
```

## カテゴリ・制限のカスタマイズ

`categories.json` を直接編集します（再起動不要、ホットリロード対応）。

### カテゴリルールの追加例

```json
{
  "category": "work",
  "url_patterns": ["mycompany.atlassian.net"],
  "app_patterns": ["myapp.exe"]
}
```

### 時間制限の設定

```json
"limits": {
  "youtube.com": 3600,
  "twitter.com": 1800
}
```

単位は秒。制限を超えると Windows 通知が届きます。

## API エンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/days` | 記録がある日付一覧 |
| GET | `/api/sessions?date=YYYY-MM-DD` | 指定日のセッション一覧（カテゴリ付き） |
| GET | `/api/summary?date=YYYY-MM-DD` | アプリ別集計 |
| GET | `/api/category_summary?date=YYYY-MM-DD` | カテゴリ別集計・フォーカススコア |
| GET | `/api/weekly?date=YYYY-MM-DD` | 週次集計（月〜日） |
| GET | `/api/heatmap?start=YYYY-MM-DD&end=YYYY-MM-DD` | 期間別日次アクティブ時間 |
| GET | `/api/ranking?date=YYYY-MM-DD&limit=10` | アプリ・URL 別使用時間ランキング |
| GET | `/api/export/csv?date=YYYY-MM-DD` | CSV ダウンロード |
| GET | `/api/export/json?date=YYYY-MM-DD` | JSON ダウンロード |

## データベーススキーマ

```sql
CREATE TABLE sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,   -- ISO 8601 (YYYY-MM-DDTHH:MM:SS)
    ended_at    TEXT NOT NULL,
    app_name    TEXT NOT NULL,   -- プロセス名 (例: code.exe)
    win_title   TEXT NOT NULL,   -- ウィンドウタイトル
    url         TEXT,            -- ブラウザ URL (nullable)
    idle        INTEGER NOT NULL DEFAULT 0  -- 1 = アイドル中
);
```

## 依存パッケージ

| パッケージ | 用途 |
|------------|------|
| fastapi / uvicorn | Web API サーバー |
| pywin32 | Windows API（フォアグラウンドウィンドウ取得） |
| psutil | プロセス名取得 |
| plyer | Windows 通知 |
| pystray | システムトレイアイコン |
| pillow | トレイアイコン描画 |

## トラブルシューティング

**トレイアイコンが表示されない**
- `pipenv install` が完了しているか確認
- `pipenv run python launcher.py` をコマンドラインから実行してエラーを確認

**URL が記録されない**
- Chrome / Edge がデバッグポート付きで起動しているか確認
- ファイアウォールで `localhost:9222` / `localhost:9223` がブロックされていないか確認

**多重起動エラー**
- `data/tracker.lock` を削除してから再起動

**ログ確認**
```
data/tracker.log
```
