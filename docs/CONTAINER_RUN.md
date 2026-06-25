# コンテナ実行方法

Docker を使って `remoboard-cloud-api-admin` を起動する手順です。

## 前提

- Docker がインストール済み
- データベースの IP アドレス、ログイン情報は `.env` に記載する想定

## 1. `.env` の用意

`.env.example` をコピーして `.env` を作成します。

```bash
cp .env.example .env
```

`.env` には少なくとも以下を設定します。

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

## 2. イメージのビルド

```bash
docker build -t remoboard-cloud-api-admin .
```

## 3. コンテナ起動

```bash
docker run --rm -p 8000:8000 --env-file .env remoboard-cloud-api-admin
```

## 4. 動作確認

```bash
curl http://127.0.0.1:8000/health
```

## 5. docker compose を使う場合

このリポジトリには `docker-compose.yml` も用意しています。

```bash
docker compose up --build
```

`env_file` で `.env` を読み込むため、DB の IP アドレスやログイン情報も `.env` にまとめて管理できます。

## 補足

- コンテナ内では `ADMIN_API_HOST=0.0.0.0` を推奨します。
- DB を使う構成に拡張する場合でも、接続先 IP や認証情報は `.env` へ集約してください。


