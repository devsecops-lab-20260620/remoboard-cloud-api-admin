# テスト実行方法

## 前提

```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install ruff pytest pytest-cov pytest-asyncio httpx
```

---

## Unit Test（DB 不要）

```bash
pytest tests/unit/ -v
```

- PostgreSQL 不要。Mock とインメモリモードで動作
- 実行時間: 約 1 秒

### 検証内容

| ファイル | 内容 |
|---|---|
| `test_auth_service.py` | 認証・トークン発行・検証・失効（インメモリ） |
| `test_schemas.py` | Pydantic バリデーション |
| `test_health.py` | ヘルスチェックエンドポイント |
| `test_login_validation.py` | ログイン入力バリデーション (422) |
| `test_auth_db_paths.py` | DB あり/なし分岐、DB 例外時の振る舞い（Mock） |
| `test_db_unavailable.py` | DB 停止時に 503 が返ることの検証（Mock） |

---

## Integration Test（PostgreSQL 必要）

### 事前準備

テスト用データベースを作成済みであること（`docs/DATABASE_SETUP.md` 参照）。

`.env` に `TEST_DATABASE_URL` が設定されていること:

```dotenv
TEST_DATABASE_URL=postgresql://remoboard_test:<パスワード>@<DB_HOST>:5432/remoboard_test
```

### 実行

```bash
export TEST_DATABASE_URL=postgresql://remoboard_test:<パスワード>@<DB_HOST>:5432/remoboard_test
pytest tests/integration/ -v
```

- テスト開始時にテーブルを自動作成、終了時に自動削除
- 各テスト後にトランザクションを ROLLBACK（データが残らない）
- 実行時間: 約 1 秒

### 検証内容

| ファイル | 内容 |
|---|---|
| `test_auth_api.py` | ログイン・/me・リフレッシュ・ログアウトの全エンドポイント × 実 DB |

---

## 全テスト一括

```bash
export TEST_DATABASE_URL=postgresql://remoboard_test:<パスワード>@<DB_HOST>:5432/remoboard_test
pytest -v
```

---

## コンテナでテスト実行（DB 不要）

外部の PostgreSQL がなくても、Docker だけで全テストを実行できます。

```bash
docker compose -f docker-compose.test.yml up --build --exit-code-from api-test
```

内部で行われること:
1. PostgreSQL コンテナ起動（ヘルスチェック通過まで待機）
2. `alembic upgrade head`（テーブル自動作成）
3. `pytest tests/ -v`（Unit + Integration + E2E 全テスト実行）
4. 終了後にコンテナ自動停止

テスト後のクリーンアップ:

```bash
docker compose -f docker-compose.test.yml down -v
```

### 構成ファイル

| ファイル | 役割 |
|---|---|
| `Dockerfile.test` | テスト用イメージ（pytest 等を含む） |
| `docker-compose.test.yml` | PostgreSQL + テストランナーの定義 |

---

## カバレッジレポート

テスト実行時に自動生成されます（`pyproject.toml` で設定済み）。

- ターミナル: 実行後に表示
- XML: `coverage.xml`（CI 連携用）
