# Linux 直実行方法

`remoboard-cloud-api-admin` を Linux 上で直接起動する手順です。

## 前提

- Python 3.11 以上
- Git が利用可能
- pip が利用可能

## 1. ソース取得

```bash
git clone <repository-url>
cd remoboard-cloud-api-admin
```

## 2. 仮想環境作成・依存インストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. 環境変数ファイルの準備

```bash
cp .env.example .env
```

`.env` を編集し、本番環境に合わせた値を設定してください。

```dotenv
# サーバー
ADMIN_API_HOST=0.0.0.0
ADMIN_API_PORT=8000

# 管理者アカウント
ADMIN_AUTH_USERNAME=admin
ADMIN_AUTH_PASSWORD=<強力なパスワードに変更>
ADMIN_AUTH_DISPLAY_NAME=Remoboard Administrator

# トークン設定
ADMIN_AUTH_JWT_SECRET=<ランダムな文字列に変更>
ADMIN_AUTH_ACCESS_TOKEN_TTL_SECONDS=3600
ADMIN_AUTH_REFRESH_TOKEN_TTL_SECONDS=604800
ADMIN_AUTH_ISSUER=remoboard-cloud-api-admin

# データベース接続
DB_HOST=192.168.1.10
DB_PORT=5432
DB_NAME=remoboard
DB_USER=remoboard_admin
DB_PASSWORD=<強力なパスワードに変更>
```

> **重要**: `ADMIN_AUTH_JWT_SECRET` と `ADMIN_AUTH_PASSWORD` は必ずデフォルト値から変更してください。

## 4. 起動

```bash
python main.py
```

ヘルスチェック:

```bash
curl http://127.0.0.1:8000/health
```

## 5. 動作確認

```bash
curl -X POST http://127.0.0.1:8000/api/admin/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<設定したパスワード>"}'
```

## 6. systemd でサービス化（任意）

`/etc/systemd/system/remoboard-admin-api.service` を作成:

```ini
[Unit]
Description=remoboard-cloud-api-admin
After=network.target

[Service]
Type=simple
User=remoboard
WorkingDirectory=/opt/remoboard-cloud-api-admin
EnvironmentFile=/opt/remoboard-cloud-api-admin/.env
ExecStart=/opt/remoboard-cloud-api-admin/.venv/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now remoboard-admin-api
sudo systemctl status remoboard-admin-api
```

## 注意事項

- `ADMIN_API_HOST=0.0.0.0` は外部からアクセス可能になります。ファイアウォールで接続元を制限してください。
- 本番運用では TLS 終端（nginx / ALB 等）を前段に配置してください。
- `.env` は `.gitignore` に含め、Git にコミットしないでください。
