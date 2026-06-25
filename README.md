# remoboard-cloud-api-admin

管理者向け認証 API を提供する Python サービスです。FastAPI + SQLAlchemy + PostgreSQL で構成されています。

## 機能

- 管理者ログイン（JWT 発行）
- アクセストークン / リフレッシュトークン発行
- 現在の管理者情報取得
- ログアウト（セッション全失効）
- ヘルスチェック

## エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/health` | 稼働状態 |
| POST | `/api/admin/auth/login` | ログイン・トークン発行 |
| GET | `/api/admin/auth/me` | 現在の管理者情報 |
| POST | `/api/admin/auth/refresh` | トークンローテーション |
| POST | `/api/admin/auth/logout` | セッション失効 |

## クイックスタート

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 編集して接続情報を設定
python main.py
```

## テスト

```bash
# Unit Test（DB 不要）
pytest tests/unit/ -v

# Integration + E2E（PostgreSQL 必要）
export TEST_DATABASE_URL=postgresql://remoboard_test:password@localhost:5432/remoboard_test
pytest tests/integration/ tests/e2e/ -v

# コンテナで全テスト一括（DB 不要）
docker compose -f docker-compose.test.yml up --build --exit-code-from api-test
```

## ドキュメント

[docs/INDEX.md](docs/INDEX.md) を参照してください。

## 技術スタック

- Python 3.12
- FastAPI / Uvicorn
- SQLAlchemy / Alembic
- PostgreSQL
- JWT (HMAC-SHA256)
