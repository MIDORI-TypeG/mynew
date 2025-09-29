# 推奨コマンド

## 開発コマンド

### ローカル実行
```bash
# 開発モードで実行
python main.py

# または
flask run
```

### 依存関係の管理
```bash
# 依存関係のインストール
pip install -r requirements.txt

# 新しい依存関係を追加した場合
pip freeze > requirements.txt
```

### デプロイ関連
```bash
# Gunicornでの実行（本番環境想定）
gunicorn main:app

# ポート指定
gunicorn main:app --bind 0.0.0.0:5000
```

## Windows固有コマンド
```cmd
# ディレクトリ一覧
dir

# ファイル検索
findstr "text" *.py

# 環境変数の設定
set FLASK_ENV=development
```

## Git操作
```bash
git add .
git commit -m "commit message"
git push origin main
```