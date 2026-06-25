# API 仕様

`remoboard-cloud-api-admin` は、管理者向けの認証 API を提供します。

## 共通仕様

- ベース URL: `http://<host>:<port>`
- 文字コード: UTF-8
- リクエストボディ: JSON
- レスポンスボディ: JSON
- 認証方式: `Authorization: Bearer <access_token>`

## ステータスコード

- `200 OK`: 正常
- `204 No Content`: OPTIONS 応答
- `400 Bad Request`: リクエスト不正
- `401 Unauthorized`: 認証失敗またはトークン無効
- `404 Not Found`: 未定義パス
- `500 Internal Server Error`: サーバー内部エラー

## エンドポイント

### `GET /health`
稼働確認用エンドポイントです。

#### 応答例
```json
{
  "status": "ok"
}
```

---

### `POST /api/admin/auth/login`
管理者認証を行い、アクセストークンとリフレッシュトークンを発行します。

#### リクエスト例
```json
{
  "username": "admin",
  "password": "change-me-now"
}
```

#### curl 例
```bash
curl -X POST http://127.0.0.1:8000/api/admin/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<password>"}'
```

#### 成功レスポンス例
```json
{
  "token_type": "bearer",
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "expires_in": 3600,
  "refresh_expires_in": 604800,
  "admin": {
    "username": "admin",
    "display_name": "Remoboard Administrator",
    "roles": [
      "admin"
    ]
  }
}
```

#### エラー例
- `400 Bad Request`: `username` または `password` が不足
- `401 Unauthorized`: 認証情報が不正

---

### `GET /api/admin/auth/me`
アクセストークンに紐づく管理者情報を返します。

#### ヘッダー例
```http
Authorization: Bearer <access_token>
```

#### curl例
```bash
curl -X GET http://127.0.0.1:8000/api/admin/auth/me \
  -H 'Authorization: Bearer <access_token>'
```

#### 成功レスポンス例
```json
{
  "admin": {
    "username": "admin",
    "display_name": "Remoboard Administrator",
    "roles": [
      "admin"
    ]
  }
}
```

#### エラー例
- `401 Unauthorized`: Bearer トークンがない、または無効

---

### `POST /api/admin/auth/refresh`
リフレッシュトークンを使って、新しいトークンペアを発行します。

#### リクエスト例
```json
{
  "refresh_token": "<jwt>"
}
```

#### 成功レスポンス例
```json
{
  "token_type": "bearer",
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "expires_in": 3600,
  "refresh_expires_in": 604800
}
```

#### エラー例
- `400 Bad Request`: `refresh_token` が不足
- `401 Unauthorized`: リフレッシュトークンが無効、失効済み、または期限切れ

---

### `POST /api/admin/auth/logout`
Bearer アクセストークンを使って、セッション全体を失効します。

#### ヘッダー例
```http
Authorization: Bearer <access_token>
```

#### 成功レスポンス例
```json
{
  "status": "logged_out"
}
```

#### 補足
- ログアウト後は、同一セッションのアクセストークンとリフレッシュトークンが無効になります。

---

## CORS / OPTIONS

ブラウザ経由の利用を想定し、`OPTIONS` に対して `204 No Content` を返します。

---

## トークン仕様

- 署名アルゴリズム: `HS256`
- トークン種別: `access` / `refresh`
- 失効管理: メモリ内ブラックリスト
- セッション失効: ログアウト時にセッション単位で無効化

