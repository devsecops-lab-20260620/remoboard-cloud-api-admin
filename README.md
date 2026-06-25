# remoboard-cloud-api-admin

`remoboard-cloud-api-admin` は、管理者向け認証 API を提供する軽量な Python サービスです。標準ライブラリのみで動作するため、追加のランタイム依存はありません。

## 機能

- 管理者ログイン
- アクセストークン / リフレッシュトークン発行
- 現在の管理者情報取得
- ログアウト（トークン失効）
- ヘルスチェック

## ドキュメント

- `docs/API.md`
- `docs/LINUX_RUN.md`
- `docs/CONTAINER_RUN.md`
- `docs/INDEX.md`

## エンドポイント

### `GET /health`
稼働状態を返します。

### `POST /api/admin/auth/login`
管理者認証を行い、トークンを発行します。

リクエスト例:

```json
{
  "username": "admin",
  "password": "change-me-now"
}
```

### `GET /api/admin/auth/me`
Bearer アクセストークンを用いて現在の管理者情報を返します。

### `POST /api/admin/auth/refresh`
リフレッシュトークンを使って新しいトークンを発行します。

```json
{
  "refresh_token": "..."
}
```

### `POST /api/admin/auth/logout`
Bearer アクセストークンを使ってセッション全体を失効します。

## 環境変数

`.env.example` を参照してください。

## 起動方法

```bash
python main.py
```

デフォルトでは `127.0.0.1:8000` で起動します。

## テスト

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## 実装メモ

- JWT は HMAC-SHA256 で署名しています。
- トークン失効はメモリ内のブラックリストで管理します。
- 管理者アカウントは環境変数で設定します。
