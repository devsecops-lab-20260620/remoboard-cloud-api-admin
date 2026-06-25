# データベースセットアップ

`remoboard-cloud-api-admin` が使用する PostgreSQL データベースの初期構築手順です。

## 前提

- PostgreSQL 15 以上がインストール済み
- 管理者権限（`CREATE ROLE` / `CREATE DATABASE` が可能なユーザー）でログインできること
- `psql` クライアントが利用可能

## 1. ユーザーとデータベースの作成

PostgreSQL の管理者ユーザーで接続し、以下を実行します。

```bash
psql -h <DB_HOST> -U <管理者ユーザー> -d postgres
```

```sql
-- アプリ用ユーザー作成
CREATE USER remoboard_admin WITH PASSWORD '<強力なパスワード>';

-- データベース作成
CREATE DATABASE remoboard OWNER remoboard_admin;

-- 権限付与
GRANT ALL PRIVILEGES ON DATABASE remoboard TO remoboard_admin;
```

接続確認:

```bash
psql -h <DB_HOST> -U remoboard_admin -d remoboard -c "SELECT 1;"
```

## 2. .env の設定

`.env` に作成した接続情報を記載します。

```dotenv
DB_HOST=<DB_HOST>
DB_PORT=5432
DB_NAME=remoboard
DB_USER=remoboard_admin
DB_PASSWORD=<設定したパスワード>
```

または `DATABASE_URL` で一括指定も可能です。

```dotenv
DATABASE_URL=postgresql://remoboard_admin:<パスワード>@<DB_HOST>:5432/remoboard
```

## 3. マイグレーション実行

仮想環境を有効化した状態で Alembic を実行し、テーブルを作成します。

```bash
source .venv/bin/activate
alembic upgrade head
```

成功すると以下のテーブルが作成されます。

| テーブル名 | 用途 |
|---|---|
| `admin_revoked_tokens` | JWT 個別失効（jti ブラックリスト） |
| `admin_revoked_sessions` | セッション単位失効（sid ブラックリスト） |
| `alembic_version` | マイグレーション管理 |

確認:

```bash
psql -h <DB_HOST> -U remoboard_admin -d remoboard -c "\dt"
```

## 4. 接続テスト

API を起動し、ヘルスチェックとログイン→ログアウトのフローが正常に動作することを確認してください。

```bash
python main.py
```

```bash
# ログイン
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/admin/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<ADMIN_AUTH_PASSWORD>"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# /me（トークン検証 + DB revocation チェック）
curl http://127.0.0.1:8000/api/admin/auth/me \
  -H "Authorization: Bearer $TOKEN"

# ログアウト（DB に失効レコードが書き込まれる）
curl -X POST http://127.0.0.1:8000/api/admin/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

## トラブルシューティング

| 症状 | 原因と対処 |
|---|---|
| `connection refused` | DB ホストの `pg_hba.conf` でアプリサーバーの IP を許可してください |
| `FATAL: password authentication failed` | ユーザー名・パスワードを確認 |
| `FATAL: database "remoboard" does not exist` | 手順 1 の `CREATE DATABASE` を実行 |
| `alembic upgrade` でタイムアウト | `.env` の `DB_HOST` が正しいか確認 |
