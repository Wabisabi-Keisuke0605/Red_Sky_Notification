"""
通知判定とメッセージ生成を行うサービス
"""

from datetime import datetime, timezone, timedelta
from typing import Tuple, Dict, Optional

# 日本標準時
JST = timezone(timedelta(hours=9))


class NotificationService:
    """通知タイミングの判定とメッセージ生成を提供するサービス"""

    def __init__(self, location_name: str = "福岡市"):
        """
        Args:
            location_name: 地名
        """
        self.location_name = location_name

    def should_notify(self, weather_data: Dict) -> Tuple[bool, str]:
        """
        日の入り5分前〜日の入りの間かどうかを判定

        Args:
            weather_data: 天気データ

        Returns:
            (通知すべきか, 判定理由)
        """
        sunset_dt, sunset_str = self._get_sunset_time(weather_data)

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

    def create_notification_message(
        self, score: int, details: Dict, sunset_time: str
    ) -> Tuple[str, str]:
        """
        通知メッセージを生成

        Args:
            score: スコア
            details: 詳細情報
            sunset_time: 日の入り時刻

        Returns:
            (件名, 本文)
        """
        subject = f"🌅 真っ赤な空アラート【{self.location_name}】"

        now = datetime.now(JST)
        reasons_text = "\n".join("・" + r for r in details.get("reasons", []))

        message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 真っ赤な空が見れるぞ！(多分)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

場所: {self.location_name}
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

通知時刻: {now.strftime('%Y-%m-%d %H:%M:%S')} JST
"""

        return subject, message

    def _get_sunset_time(self, weather_data: Dict) -> Tuple[Optional[datetime], str]:
        """
        日の入り時刻を取得

        Args:
            weather_data: 天気データ

        Returns:
            (日の入り時刻のdatetime, 時刻文字列)
        """
        current = weather_data.get("current", {})
        sunset_unix = current.get("sunset", 0)

        if sunset_unix == 0:
            return None, "不明"

        sunset_dt = datetime.fromtimestamp(sunset_unix, tz=JST)
        sunset_str = sunset_dt.strftime("%H:%M")

        return sunset_dt, sunset_str

    def get_sunset_time_string(self, weather_data: Dict) -> str:
        """
        日の入り時刻の文字列を取得

        Args:
            weather_data: 天気データ

        Returns:
            日の入り時刻文字列
        """
        _, sunset_str = self._get_sunset_time(weather_data)
        return sunset_str
