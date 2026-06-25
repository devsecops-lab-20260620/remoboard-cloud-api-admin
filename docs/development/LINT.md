# Lint 実行方法

`remoboard-cloud-api-admin` では [Ruff](https://docs.astral.sh/ruff/) を使用してコード品質を管理しています。

## 前提

```bash
source .venv/bin/activate
pip install ruff
```

## チェック実行

```bash
ruff check .
```

## 自動修正

```bash
ruff check --fix .
```

## フォーマット

```bash
ruff format .
```

フォーマット差分の確認のみ（変更しない）:

```bash
ruff format --check .
```

## 設定

`pyproject.toml` の `[tool.ruff]` セクションで管理しています。

| 項目 | 値 |
|---|---|
| 行長上限 | 120 |
| ターゲット | Python 3.11 |
| 有効ルール | E, W, F, I, B, S, UP |
| ignore | S101, S105, S106, B008 |

- `S101`/`S105`/`S106` — テストでの assert やテスト用パスワードを許可
- `B008` — FastAPI の `Depends()` パターンを許可
- `tests/**` では `S`（security）・`B`（bugbear）ルールを緩和

## CI での利用例

```bash
ruff check . --output-format=github
ruff format --check .
```
