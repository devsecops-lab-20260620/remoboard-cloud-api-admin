# テスト戦略

## ゴール

| イベント | 目的 |
|---|---|
| PR 作成 | 品質保証のための全テストを実行 |
| main マージ | Docker イメージをビルドして GHCR に push |

---

## テストレイヤー構造（4層）

```
┌─────────────────────────────────────────────────────────────────┐
│ ④ E2E / API Test   tests/e2e/        ← 完全なセッションフロー    │
│    DB あり・FastAPI TestClient・セキュリティシナリオ             │
├─────────────────────────────────────────────────────────────────┤
│ ③ Integration Test tests/integration/ ← FastAPI × PostgreSQL   │
│    DB あり・Alembic migration 実行済み・実 SQL 確認             │
├─────────────────────────────────────────────────────────────────┤
│ ② Unit Test        tests/unit/        ← ビジネスロジック単体     │
│    DB なし（in-memory）・AdminAuthService・Pydantic schemas      │
├─────────────────────────────────────────────────────────────────┤
│ ① Lint / 静的解析   ruff / mypy / bandit  ← コード品質・安全性  │
└─────────────────────────────────────────────────────────────────┘
```

---

## CI/CD フロー全体像

```
PR 作成
   │
   ├── ① Lint (ruff / mypy / bandit)
   │
   ├── ② Unit Test  ──────────────── DB なし / pytest
   │
   ├── ③ Integration Test ─────────── GitHub Actions services.postgres
   │        └── alembic upgrade head
   │
   └── ④ E2E Test ─────────────────── セキュリティ・セッション全フロー
            └── alembic upgrade head
                   ↓
          すべて成功 → PR マージ可能
                   ↓
          main にマージ
                   ↓
          Docker build → GHCR push (ghcr.io/<org>/<repo>:latest + :sha)
```

---

## ツール構成

| 種別 | ツール | 設定ファイル |
|---|---|---|
| Lint | ruff | `pyproject.toml [tool.ruff]` |
| 型チェック | mypy | `pyproject.toml [tool.mypy]` |
| セキュリティ | bandit | `pyproject.toml [tool.bandit]` |
| テスト実行 | pytest | `pyproject.toml [tool.pytest.ini_options]` |
| カバレッジ | pytest-cov | `--cov=app` |
| HTTP テスト | httpx / FastAPI TestClient | `tests/conftest.py` |

---

## ディレクトリ構成

```
tests/
  conftest.py              # 共有 fixtures（test_config, db_engine, client 等）
  unit/
    test_auth_service.py   # AdminAuthService の単体テスト（DB なし）
    test_schemas.py        # Pydantic schema バリデーションテスト
  integration/
    test_auth_api.py       # FastAPI エンドポイント × PostgreSQL
  e2e/
    test_auth_flow.py      # セッションライフサイクル全体 + セキュリティ

.github/workflows/
  ci.yml                   # PR 時: lint → unit → integration → e2e
  build-and-push.yml       # main マージ時: docker build → GHCR push

docker-compose.test.yml    # ローカルで全テストを実行する compose 定義
```

---

## テスト実行方法

### ① Unit Test のみ（DB 不要）

```bash
pytest tests/unit/ -v
```

### ② Integration + E2E（PostgreSQL が必要）

```bash
# ローカル: docker compose で Postgres を立ち上げて実行
docker compose -f docker-compose.test.yml up --build --exit-code-from api-test

# または手動で TEST_DATABASE_URL をセットして実行
export TEST_DATABASE_URL=postgresql://remoboard_admin:test-password@localhost:5432/remoboard_test
alembic upgrade head
pytest tests/integration/ tests/e2e/ -v
```

### ③ 全テスト一括

```bash
pytest -v
```

---

## セキュリティテスト項目（E2E 内で自動検証）

- JWT 期限切れトークンの拒否
- 署名改ざんトークンの拒否
- リフレッシュトークンをアクセストークンとして使用した場合の拒否
- ブルートフォース（5連続失敗でも 500 にならない）
- SQL Injection 試行の拒否
- Bearer プレフィックス欠如の拒否
- ログアウト後のセッション全失効（アクセス・リフレッシュ両方）

---

## DB 接続情報の扱い

- データベースの IP アドレス・ユーザー名・パスワードはすべて `.env` に記載
- `.env` は `.gitignore` に含まれており Git に含まれない
- CI 上では GitHub Actions の `env:` または `secrets` で設定
- テスト用 DB は `TEST_DATABASE_URL` 環境変数で指定

