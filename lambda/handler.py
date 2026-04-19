"""
真っ赤な空アラート - Lambda関数ハンドラー
"""

import json
import os
import sys

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from repositories.parameter_repository import ParameterRepository
from repositories.weather_repository import WeatherRepository
from services.red_sky_scorer import RedSkyScorerService
from services.notification_service import NotificationService
from resources.sns_client import SnsClient

# 環境変数
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")
LATITUDE = os.environ.get("LATITUDE", "33.5904")
LONGITUDE = os.environ.get("LONGITUDE", "130.4017")
LOCATION_NAME = os.environ.get("LOCATION_NAME", "福岡市")
SCORE_THRESHOLD = int(os.environ.get("SCORE_THRESHOLD", "80"))
API_KEY_PARAM = os.environ.get(
    "OPENWEATHERMAP_API_KEY_PARAM", "/red-sky-alert/openweathermap-api-key"
)


def handler(event, context):
    """Lambda ハンドラー"""

    print(f"Event: {json.dumps(event)}")
    print(f"Location: {LOCATION_NAME} ({LATITUDE}, {LONGITUDE})")
    print(f"Score Threshold: {SCORE_THRESHOLD}")

    try:
        # 依存性の初期化
        parameter_repo = ParameterRepository()
        weather_repo = WeatherRepository()
        scorer_service = RedSkyScorerService()
        notification_service = NotificationService(location_name=LOCATION_NAME)
        sns_client = SnsClient()

        # 1. APIキー取得
        api_key = parameter_repo.get_api_key(API_KEY_PARAM)
        print("API key retrieved successfully")

        # 2. 天気データ取得
        weather_data = weather_repo.fetch_weather_data(LATITUDE, LONGITUDE, api_key)
        print(
            f"Weather data retrieved: "
            f"{json.dumps(weather_data.get('current', {}), indent=2)}"
        )

        # 3. 通知タイミングチェック
        should_send, timing_info = notification_service.should_notify(weather_data)
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
        score, details = scorer_service.calculate_score(weather_data)
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
        sunset_time = notification_service.get_sunset_time_string(weather_data)
        subject, message = notification_service.create_notification_message(
            score, details, sunset_time
        )
        notification_response = sns_client.publish(SNS_TOPIC_ARN, subject, message)
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
