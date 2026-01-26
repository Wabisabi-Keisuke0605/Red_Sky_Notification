"""
真っ赤な空アラート - Lambda関数
福岡市版

判定条件:
- 時間帯：日の入り付近
- 太陽光を反射させるための雲が多少存在すること
- 降水確率が低いこと
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
import boto3

# 環境変数
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")
LATITUDE = os.environ.get("LATITUDE", "33.5904")
LONGITUDE = os.environ.get("LONGITUDE", "130.4017")
LOCATION_NAME = os.environ.get("LOCATION_NAME", "福岡市")
SCORE_THRESHOLD = int(os.environ.get("SCORE_THRESHOLD", "80"))
API_KEY_PARAM = os.environ.get(
    "OPENWEATHERMAP_API_KEY_PARAM", "/red-sky-alert/openweathermap-api-key"
)

# 日本標準時
JST = timezone(timedelta(hours=9))

# AWSクライアント
ssm_client = boto3.client("ssm")
sns_client = boto3.client("sns")


def get_api_key() -> str:
    """SSMパラメータストアからAPIキーを取得"""
    response = ssm_client.get_parameter(Name=API_KEY_PARAM, WithDecryption=True)
    return response["Parameter"]["Value"]


def fetch_weather_data(api_key: str) -> dict:
    """OpenWeatherMap One Call API 3.0 から天気データを取得"""
    url = (
        f"https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={LATITUDE}&lon={LONGITUDE}"
        f"&exclude=minutely,daily,alerts"
        f"&units=metric"
        f"&appid={api_key}"
    )

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        raise
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        raise


def calculate_red_sky_score(weather_data: dict) -> tuple[int, dict]:
    
    #真っ赤な空の出現可能性をスコアリング（0-100）

    # OpenWeatherMapでは高度別雲量が取得できないため、
    # 全体の雲量と天気コードから推測
    
    current = weather_data.get("current", {})
    hourly = weather_data.get("hourly", [{}])[0]  # 直近1時間の予報

    details = {
        "clouds": current.get("clouds", 0),
        "visibility": current.get("visibility", 0),
        "humidity": current.get("humidity", 0),
        "weather_id": current.get("weather", [{}])[0].get("id", 0),
        "weather_desc": current.get("weather", [{}])[0].get("description", ""),
        "pop": hourly.get("pop", 0),
    }

    score = 0
    reasons = []

    # ========================================
    # 1. 雲量チェック（最大40点）
    # ========================================
    clouds = details["clouds"]
    weather_id = details["weather_id"]

    # 天気コードから雲の種類を推測
    # 800: 快晴, 801: 薄雲, 802: 散在雲, 803: 千切れ雲, 804: 曇天
    if weather_id == 800:  # 快晴
        if clouds <= 10:
            score += 30
            reasons.append(f"快晴（雲量{clouds}%）- 良好")
        else:
            score += 35
            reasons.append(f"ほぼ快晴（雲量{clouds}%）- 良好")
    elif weather_id == 801:  # few clouds (11-25%)
        score += 40  # 最高点 - 薄い雲が理想的
        reasons.append(f"薄雲あり（雲量{clouds}%）- 最適")
    elif weather_id == 802:  # scattered clouds (25-50%)
        score += 35
        reasons.append(f"散在雲（雲量{clouds}%）- 良好")
    elif weather_id == 803:  # broken clouds (51-84%)
        if clouds <= 70:
            score += 20
            reasons.append(f"千切れ雲（雲量{clouds}%）- やや多い")
        else:
            score += 10
            reasons.append(f"雲多め（雲量{clouds}%）- 厳しい")
    elif weather_id == 804:  # overcast (85-100%)
        score += 0
        reasons.append(f"曇天（雲量{clouds}%）- 不適")
    elif 700 <= weather_id < 800:  # 霧・靄など
        score += 5
        reasons.append("霧・靄あり - 不適")
    elif weather_id < 700:  # 雨・雪など
        score += 0
        reasons.append("降水あり - 不適")
    else:
        # その他の場合は雲量で判定
        if 20 <= clouds <= 60:
            score += 35
            reasons.append(f"雲量{clouds}% - 良好")
        elif clouds < 20:
            score += 30
            reasons.append(f"雲量{clouds}% - 快晴寄り")
        elif 60 < clouds <= 80:
            score += 15
            reasons.append(f"雲量{clouds}% - やや多い")
        else:
            score += 0
            reasons.append(f"雲量{clouds}% - 曇天")

    # ========================================
    # 2. 視程チェック（最大30点）
    # ========================================
    visibility = details["visibility"]
    if visibility >= 10000:
        score += 30
        reasons.append(f"視程{visibility}m - 最良")
    elif visibility >= 8000:
        score += 25
        reasons.append(f"視程{visibility}m - 良好")
    elif visibility >= 5000:
        score += 15
        reasons.append(f"視程{visibility}m - 普通")
    elif visibility >= 3000:
        score += 5
        reasons.append(f"視程{visibility}m - やや悪い")
    else:
        score += 0
        reasons.append(f"視程{visibility}m - 不良")

    # ========================================
    # 3. 降水確率チェック（最大20点）
    # ========================================
    pop = details["pop"]
    if pop == 0:
        score += 20
        reasons.append("降水確率0% - 最良")
    elif pop <= 0.1:
        score += 15
        reasons.append(f"降水確率{int(pop*100)}% - 良好")
    elif pop <= 0.2:
        score += 10
        reasons.append(f"降水確率{int(pop*100)}% - 普通")
    elif pop <= 0.3:
        score += 5
        reasons.append(f"降水確率{int(pop*100)}% - やや高い")
    else:
        score += 0
        reasons.append(f"降水確率{int(pop*100)}% - 高い")

    # ========================================
    # 4. 湿度チェック（最大10点）
    # ========================================
    humidity = details["humidity"]
    if humidity < 50:
        score += 10
        reasons.append(f"湿度{humidity}% - 乾燥で最良")
    elif humidity < 65:
        score += 8
        reasons.append(f"湿度{humidity}% - 良好")
    elif humidity < 80:
        score += 5
        reasons.append(f"湿度{humidity}% - 普通")
    else:
        score += 0
        reasons.append(f"湿度{humidity}% - 高い")

    details["score"] = score
    details["reasons"] = reasons

    return score, details


def get_sunset_time(weather_data: dict) -> tuple[datetime, str]:
    """日の入り時刻を取得"""
    current = weather_data.get("current", {})
    sunset_unix = current.get("sunset", 0)

    if sunset_unix == 0:
        return None, "不明"

    sunset_dt = datetime.fromtimestamp(sunset_unix, tz=JST)
    sunset_str = sunset_dt.strftime("%H:%M")

    return sunset_dt, sunset_str


def should_notify(weather_data: dict) -> tuple[bool, str]:
    """
    日の入り5分前〜日の入りの間かどうかを判定
    """
    sunset_dt, sunset_str = get_sunset_time(weather_data)

    if sunset_dt is None:
        return False, "日の入り時刻不明"

    now = datetime.now(JST)

    # 日の入り5分前〜日の入りの間のみ通知
    notify_start = sunset_dt - timedelta(minutes=5)
    notify_end = sunset_dt

    if now < notify_start:
        minutes_until = int((notify_start - now).total_seconds() / 60)
        return False, f"日の入り{sunset_str}の{minutes_until}分前（通知タイミング前）"
    elif now > notify_end:
        return False, f"日の入り{sunset_str}を過ぎています"
    else:
        return True, f"日の入り{sunset_str}の約5分前"


def send_notification(score: int, details: dict, sunset_time: str) -> dict:
    """SNSで通知を送信"""

    subject = f"🌅 真っ赤な空アラート【{LOCATION_NAME}】"

    now = datetime.now(JST)

    reasons_text = "\n".join("・" + r for r in details.get("reasons", []))

    message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌅 真っ赤な空アラート
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 場所: {LOCATION_NAME}
🕐 日の入り時刻: {sunset_time}
📊 出現可能性スコア: {score}/100

【判定詳細】
{reasons_text}

【現在の気象条件】
・天気: {details.get('weather_desc', '不明')}
・雲量: {details.get('clouds', 0)}%
・視程: {details.get('visibility', 0):,}m
・湿度: {details.get('humidity', 0)}%
・降水確率: {int(details.get('pop', 0) * 100)}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
※ 日の入り前後の西の空をご覧ください
※ Honda Kids「魔法のような色の空はなぜ見えるか」参照
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

通知時刻: {now.strftime('%Y-%m-%d %H:%M:%S')} JST
"""

    response = sns_client.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject,
        Message=message,
    )

    return response


def handler(event, context):
    """Lambda ハンドラー"""

    print(f"Event: {json.dumps(event)}")
    print(f"Location: {LOCATION_NAME} ({LATITUDE}, {LONGITUDE})")
    print(f"Score Threshold: {SCORE_THRESHOLD}")

    try:
        # 1. APIキー取得
        api_key = get_api_key()
        print("API key retrieved successfully")

        # 2. 天気データ取得
        weather_data = fetch_weather_data(api_key)
        print(
            f"Weather data retrieved: "
            f"{json.dumps(weather_data.get('current', {}), indent=2)}"
        )

        # 3. 通知タイミングチェック
        should_send, timing_info = should_notify(weather_data)
        print(f"Notification timing check: {should_send} - {timing_info}")

        if not should_send:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Not notification time",
                        "timing": timing_info,
                        "location": LOCATION_NAME,
                    }
                ),
            }

        # 4. スコア計算
        score, details = calculate_red_sky_score(weather_data)
        print(f"Score: {score}/100")
        print(f"Details: {json.dumps(details, indent=2, ensure_ascii=False)}")

        # 5. 閾値判定
        if score < SCORE_THRESHOLD:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Score below threshold",
                        "score": score,
                        "threshold": SCORE_THRESHOLD,
                        "details": details,
                        "location": LOCATION_NAME,
                    }
                ),
            }

        # 6. 通知送信
        _, sunset_time = get_sunset_time(weather_data)
        notification_response = send_notification(score, details, sunset_time)
        print(f"Notification sent: {notification_response.get('MessageId')}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Notification sent successfully",
                    "score": score,
                    "details": details,
                    "location": LOCATION_NAME,
                    "sunset_time": sunset_time,
                    "message_id": notification_response.get("MessageId"),
                }
            ),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()

        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": str(e),
                    "location": LOCATION_NAME,
                }
            ),
        }