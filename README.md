#  【BUMP】【真っ赤な空駆動】真っ赤な空をサーバーレスで見逃さないようにしたい(in福岡市)

福岡市で真っ赤な夕焼け空が出現しそうな時に、メールで通知するサービスです。

## 概要
BUMP OF CHICKENの「真っ赤な空を見ただろうか」には、真っ赤な空を見つけた時に、思い人もこの空を見ているだろうかと気にしている描写が歌詞に含まれています。
最悪の場合、思い人が真っ赤な空を見ることができていない可能性があるので、AWSのサーバーレスサービスを用いて、少しでも「思い人」が真っ赤な空を見られる可能性が上がるようなソリューションを作りたいと思いました。

Honda Kids「[魔法のような色の空はなぜ見えるか](https://www.honda.co.jp/kids/explore/twilight/)」の記事に基づき、気象条件から「真っ赤な空」の出現可能性をスコアリングし、高確率の場合に日の入り5分前にメール通知を送信します。

### 主な機能

- OpenWeatherMap APIから福岡市の気象データを取得
- 雲量・視程・湿度・降水確率からスコアを算出（0〜100点）
- スコア80点以上かつ日の入り5分前の場合のみ通知
- 季節に応じた自動スケジューリング（日の入り時刻の変動に対応）

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                    EventBridge                          │
│      (季節ごとに日の入り前後の時間帯で15分間隔起動)         　  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      Lambda                             │
│  1. SSM Parameter Store からAPIキー取得                   │
│  2. OpenWeatherMap API から気象データ取得                  │
│  3. 日の入り5分前かどうか判定                               │
│  4. 真っ赤な空スコア計算（0-100点）                         │
│  5. スコア80点以上ならSNS通知                              │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    SNS Topic                            │
│                  購読者へメール配信                        │
└─────────────────────────────────────────────────────────┘
```

## 判定ロジック

### スコアリング（0-100点）

| 項目 | 最大点数 | 最適条件 |
|------|---------|----------|
| 雲量・雲の種類 | 40点 | 薄雲（20-40%）が最適 |
| 視程 | 30点 | 10km以上 |
| 降水確率 | 20点 | 0% |
| 湿度 | 10点 | 50%未満 |

### 通知条件

- **スコア80点以上** かつ **日の入り5分前** の場合のみ通知

## 前提条件

- Python 3.9以上
- Node.js 20以上
- AWS CLI
- AWS CDK CLI
- OpenWeatherMap アカウント

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/Wabisabi-Keisuke0605/Red_Sky_Notification
cd Red_Sky_Notification
```

### 2. OpenWeatherMap APIキーの取得

1. [OpenWeatherMap](https://openweathermap.org/) でアカウント作成
2. [API Keys](https://home.openweathermap.org/api_keys) からAPIキーを取得
3. [One Call API 3.0](https://openweathermap.org/api/one-call-3) のサブスクリプションを有効化（無料枠: 1,000 calls/日）

### 3. APIキーをSSM Parameter Storeに保存

セキュリティ上の注意: APIキーは絶対にコードにハードコードしないでください。必ずSSM Parameter Storeに保存してください。
以下のコマンドを実行して、SSMにキーを保管してください。

```bash
aws ssm put-parameter \
  --name "/red-sky-alert/openweathermap-api-key" \
  --value "YOUR_API_KEY_HERE" \
  --type SecureString \
  --region ap-northeast-1
```

成功すると以下のようなレスポンスが返ります：

```json
{
    "Version": 1,
    "Tier": "Standard"
}
```

### 4. 仮想環境のセットアップ

```bash
# 仮想環境作成
python3 -m venv .venv

# 仮想環境有効化（Mac/Linux）
source .venv/bin/activate

# 仮想環境有効化（Windows）
.venv\Scripts\activate

# 依存パッケージインストール
pip install -r requirements.txt
```

### 5. テスト（任意）

```bash
# テスト用パッケージインストール
pip install -r requirements-dev.txt

# ユニットテスト実行
pytest

# CloudFormationテンプレート生成確認
cdk synth
```

### 6. CDKデプロイ

```bash
# CDK Bootstrap（初回のみ）
cdk bootstrap

# デプロイ
cdk deploy
```

途中で「Do you wish to deploy these changes (y/n)?」と表示されたら `y` を入力してください。

### 7. メール購読の登録

デプロイ完了後に表示される `SubscribeCommand` を実行します：

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-northeast-1:YOUR_ACCOUNT_ID:red-sky-alert-fukuoka \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region ap-northeast-1
```

登録後、確認メールが届くので承認してください。

## 通知サンプル

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 真っ赤な空が見られるぞ！(多分)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

場所: {LOCATION_NAME}
日の入り時刻: {sunset_time}
出現可能性スコア: {score}/100

【判定詳細】
{reasons_text}

【現在の気象条件】
・天気: {details.get('weather_desc', '不明')}
・雲量: {details.get('clouds', 0)}%
・視程: {details.get('visibility', 0):,}m
・湿度: {details.get('humidity', 0)}%
・降水確率: {int(details.get('pop', 0) * 100)}%
"""
```

## プロジェクト構造

```
RedSkyAlert/
├── red_sky_alert/
│   ├── __init__.py
│   └── red_sky_alert_stack.py    # CDKスタック定義
├── lambda/
│   └── index.py                   # Lambda関数（判定ロジック）
├── tests/
│   └── unit/
│       └── test_red_sky_alert_stack.py
├── .gitignor
├── app.py                         # CDKエントリーポイント
├── cdk.json                       # CDK設定
├── requirements.txt               # 本番用依存パッケージ
└── README.md
```

## カスタマイズ

### 対象地域の変更

`red_sky_alert/red_sky_alert_stack.py` の環境変数を変更：

```python
environment={
    "LATITUDE": "35.6762",    # 緯度
    "LONGITUDE": "139.6503",  # 経度
    "LOCATION_NAME": "東京",
    # ...
}
```

### 通知閾値の変更

```python
environment={
    "SCORE_THRESHOLD": "70",  # 70点以上で通知（デフォルト: 80）
    # ...
}
```

## 料金

すべてAWS無料枠内で運用可能です：

| サービス | 無料枠 |
|----------|--------|
| Lambda | 100万リクエスト/月 |
| EventBridge | 無料 |
| SNS（メール） | 1,000通/月 |
| SSM Parameter Store | 標準パラメータは無料 |
| OpenWeatherMap | 1,000 calls/日 |

## トラブルシューティング

### Lambda関数のテスト実行

```bash
aws lambda invoke \
  --function-name red-sky-checker-fukuoka \
  --region ap-northeast-1 \
  --log-type Tail \
  output.json

cat output.json
```

### CloudWatchログの確認

```bash
aws logs tail /aws/lambda/red-sky-checker-fukuoka --follow
```

### スタックの削除

```bash
cdk destroy
```

## 参考資料

- [Honda Kids「魔法のような色の空はなぜ見えるか」](https://www.honda.co.jp/kids/explore/twilight/)
- [OpenWeatherMap One Call API 3.0](https://openweathermap.org/api/one-call-3)
- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)

## ライセンス

MIT