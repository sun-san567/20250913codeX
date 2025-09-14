# 改善ロードマップ（課題対応）

本ドキュメントは現状評価の課題に対する、具体的な解決策と段階的導入手順をまとめたものです。

## 1. アーキテクチャ（複雑性/同期/環境）
- 方針統一（段階的移行）
  - Phase A: Streamlitをソース・オブ・トゥルース（CSV）として維持、Webフロントは閲覧専用
  - Phase B: Laravel API + DB へ完全移行（Streamlitは閲覧停止 or API参照に切替）
- データ同期の一元化
  - Phase B 以降は「DBのみ」正とし、CSVは「エクスポートのみ」。同時書込は禁止
  - Laravelにマイグレーション/インポートAPIを用意（CSV→DB）
- 開発環境の簡略化
  - docker-compose で Laravel(PHP-FPM)+DB+Nginx を起動
  - フロントはVite単体（APIは `.env` でURL切替）

## 2. フロントエンド（状態/エラー/型）
- 状態管理の明確化
  - 取得系: React Query（キャッシュ/ローディング/エラー）
  - 局所UI: useState のみ
- エラーハンドリング
  - axiosインターセプタで共通処理（メッセージ化/リトライ方針）
  - useQueryの error をUI表示（トースト）
- 型安全性
  - any 禁止（lint/tsconfig/CIで担保）

## 3. バックエンド（実装/認証/性能）
- 実装着手：weights/exercises/settings のCRUD + share-links のReadOnly閲覧
- 認証（Sanctum）
  - メール/パスワード or OAuth（後日）
  - 共有リンクはトークン+オプションのパスコード
- 性能
  - インデックス: weights(date), exercises(date), exercises(activity), exercises(unique tracker_id,date,activity)
  - 集計は日付範囲指定 + ページング

## 4. データ管理（移行/バックアップ/バージョニング）
- CSV→DB 移行手順を文書化（本Repoに追加）
- バックアップ
  - dev: SQLite ファイルの定期コピー
  - prod: DBスナップショット + mysqldump 定期実行
- バージョニング
  - Laravel Migrations を唯一のスキーマ変更手段に統一

## 5. UI/UX（一貫性/レスポンシブ/ローディング）
- 一貫性
  - コンポーネント指針（ボタン/フォーム/カード）とトークン（余白/角丸/影）を定義
- レスポンシブ
  - 2カラム→1カラムへの自然なブレークポイント
- ローディング
  - スケルトン/スピナー/aria-busy の付与

## 6. セキュリティ（認証/暗号化/ヘッダ）
- 認証・認可
  - Sanctum + ポリシー（owner/editor/viewer/trainer）
- 暗号化
  - HTTPS前提、.env 秘匿、共有リンクの passcode はハッシュ
- セキュリティヘッダ
  - Nginx/Laravelで CSP,HSTS,X-Frame-Options を設定

## 7. パフォーマンス（DB/フロント/リアルタイム）
- DB: 適切なIndex、期間絞込、必要に応じて集計テーブル
- フロント: Vite code splitting、Chartのlazyロード
- リアルタイム: 将来、SSE/WSでコメント/タスク更新

## 8. テスト（戦略/実装/CI）
- 戦略
  - 単体: TSコンポーネント、ユーティリティ
  - API契約: OpenAPIでモック検証
  - E2E（後日）: Playwright
- 実装
  - frontend: Vitest + React Testing Library
  - backend: Pest/PhpUnit
- CI
  - GitHub Actions: lint/test/build をプルリクで必須化

## 9. ドキュメント（API/運用）
- OpenAPI 仕様追加（本Repo api/openapi.yaml）
- 運用ドキュメント（デプロイ/監視/バックアップ）

---
優先順: 1) API実装着手 + OpenAPI, 2) Frontの取得系React Query化, 3) CIでテスト必須化
