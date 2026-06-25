# Linux 直実行方法

`remoboard-cloud-api-admin` を Linux 上で直接起動する手順です。

## 前提

- Python 3.11 以上を推奨
- Git が利用可能
- データベースの IP アドレス、ログイン情報は `.env` に記載する想定

## 1. ソース取得

```bash
git clone <repository-url>
cd remoboard-cloud-api-admin
```

## 2. 仮想環境作成

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. 環境変数ファイルの準備

`.env.example` をコピーして `.env` を作成します。

```bash
cp .env.example .env
```

`.env` には以下を設定します。

```dotenv
ADMIN_API_HOST=0.0.0.0
ADMIN_API_PORT=8000
ADMIN_AUTH_USERNAME=admin
ADMIN_AUTH_PASSWORD=change-me-now
ADMIN_AUTH_DISPLAY_NAME=Remoboard Administrator
ADMIN_AUTH_JWT_SECRET=change-this-secret-in-production
ADMIN_AUTH_ACCESS_TOKEN_TTL_SECONDS=3600
ADMIN_AUTH_REFRESH_TOKEN_TTL_SECONDS=604800

# データベース接続情報は .env に記載する前提
DB_HOST=192.168.1.10
DB_PORT=5432
DB_NAME=remoboard
DB_USER=remoboard_admin
DB_PASSWORD=please-change-me
```

> 現時点の API 実装は DB を利用しませんが、将来的な連携や周辺サービス用の接続情報は `.env` に集約してください。

## 4. 起動

```bash
python main.py
```

起動後、以下で確認できます。

```bash
curl http://127.0.0.1:8000/health
```

## 5. 動作確認

```bash
curl -X POST http://127.0.0.1:8000/api/admin/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"change-me-now"}'
```

## 補足

- `ADMIN_API_HOST=0.0.0.0` にすると外部から到達可能になります。
- 本番運用では TLS 終端を別途用意してください。

