# コードスタイルと規約

## コーディングスタイル
- **言語**: Python 3.x
- **インデント**: スペース4つ
- **文字エンコーディング**: UTF-8
- **コメント**: 日本語コメント使用

## 命名規約
- **関数名**: snake_case（例: `extract_stock_from_image`）
- **変数名**: snake_case（例: `image_data`, `stock_data`）
- **定数**: UPPER_CASE（例: `KEYWORDS`）
- **クラス名**: PascalCase（使用されている場合）

## ドキュメンテーション
- **Docstring**: Google形式のdocstringを使用
- **Args/Returns**: 型と説明を明記

## 設計パターン
- **Flask RESTful API**: シンプルなREST API設計
- **エラーハンドリング**: try-catch文でのエラー処理
- **初期化パターン**: アプリ起動時にOCRリーダーを一度だけ初期化