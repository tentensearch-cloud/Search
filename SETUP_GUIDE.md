# 🤖 ニュース監視ボット (LINE通知版) セットアップガイド

このシステムは、GitHub Actionsを使用して、PCがオフの状態でも24時間自動でニュースを監視し、LINEに通知を送るものです。

## 1. LINEの準備

1.  [LINE Developers](https://developers.line.biz/) にログインします。
2.  **Messaging API** のチャネルを作成します。
3.  以下の2つの情報を取得してください：
    -   **Messaging API設定** タブの「チャネルアクセストークン（長期）」
    -   **チャネル基本設定** タブのあなたの「ユーザーID」

## 2. GitHubリポジトリの作成とアップロード

1.  GitHubで新しいリポジトリ（Private推奨）を作成します。
2.  このフォルダのファイルをすべてアップロード（push）します。

```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/あなたのユーザー名/リポジトリ名.git
git push -u origin main
```

## 3. GitHub Secrets (環境変数) の設定

GitHubのリポジトリ設定（Settings）から、以下の **Secrets** を追加してください。

| 名前 | 値の例 |
| :--- | :--- |
| `GOOGLE_API_KEY` | あなたのGemini APIキー |
| `LINE_CHANNEL_ACCESS_TOKEN` | 先ほど取得したチャネルアクセストークン |
| `LINE_USER_ID` | 先ほど取得したユーザーID |
| `RSS_FEEDS` | GoogleアラートのRSS URL (複数ある場合はカンマ `,` 区切り) |

## 4. 実行の確認

1.  GitHubの **Actions** タブをクリックします。
2.  **"News Monitor LINE Bot"** を選択します。
3.  **Run workflow** ボタンをクリックして手動でテスト実行します。
4.  成功すれば、LINEにニュース通知が届きます。
5.  以降は1時間ごとに自動実行されます。

## 💡 特徴

-   **緊急ニュース**: キーワードに基づき、通知の先頭に `🚨【緊急】` が付きます。
-   **重複除外**: 以前送信した内容と酷似している記事（類似度80%以上）は自動的にスキップされます。
-   **Gemini制限回避**: エラー発生時に自動で利用可能な別のGeminiモデルに切り替えます。
