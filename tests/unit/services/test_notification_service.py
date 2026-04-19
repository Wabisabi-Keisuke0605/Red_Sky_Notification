"""
NotificationService のユニットテスト
"""

import pytest
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from services.notification_service import NotificationService, JST


class TestNotificationService:
    """NotificationServiceのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.service = NotificationService(location_name="テスト市")

    def test_initialization(self):
        """初期化のテスト"""
        assert self.service.location_name == "テスト市"

    def test_should_notify_within_window(self):
        """日の入り5分前の通知ウィンドウ内の場合"""
        # 現在時刻を日の入り3分前に設定
        now = datetime.now(JST)
        sunset_time = now + timedelta(minutes=3)
        sunset_unix = int(sunset_time.timestamp())

        weather_data = {
            "current": {
                "sunset": sunset_unix
            }
        }

        with patch('services.notification_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            
            should_notify, reason = self.service.should_notify(weather_data)
            
            assert should_notify is True
            assert "約5分前" in reason

    def test_should_notify_before_window(self):
        """日の入り5分前より前の場合"""
        now = datetime.now(JST)
        sunset_time = now + timedelta(minutes=10)
        sunset_unix = int(sunset_time.timestamp())

        weather_data = {
            "current": {
                "sunset": sunset_unix
            }
        }

        with patch('services.notification_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            
            should_notify, reason = self.service.should_notify(weather_data)
            
            assert should_notify is False
            assert "通知タイミング前" in reason

    def test_should_notify_after_sunset(self):
        """日の入り後の場合"""
        now = datetime.now(JST)
        sunset_time = now - timedelta(minutes=5)
        sunset_unix = int(sunset_time.timestamp())

        weather_data = {
            "current": {
                "sunset": sunset_unix
            }
        }

        with patch('services.notification_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            
            should_notify, reason = self.service.should_notify(weather_data)
            
            assert should_notify is False
            assert "過ぎています" in reason

    def test_should_notify_no_sunset_data(self):
        """日の入り時刻データがない場合"""
        weather_data = {
            "current": {}
        }

        should_notify, reason = self.service.should_notify(weather_data)
        
        assert should_notify is False
        assert "不明" in reason

    def test_create_notification_message(self):
        """通知メッセージの生成"""
        score = 85
        details = {
            "reasons": ["理由1", "理由2", "理由3"],
            "weather_desc": "晴れ",
            "clouds": 30,
            "visibility": 10000,
            "humidity": 50,
            "pop": 0.1,
        }
        sunset_time = "18:30"

        subject, message = self.service.create_notification_message(
            score, details, sunset_time
        )

        # 件名の確認
        assert "真っ赤な空アラート" in subject
        assert "テスト市" in subject

        # メッセージ本文の確認
        assert "テスト市" in message
        assert "18:30" in message
        assert "85/100" in message
        assert "理由1" in message
        assert "理由2" in message
        assert "理由3" in message
        assert "晴れ" in message
        assert "30%" in message
        assert "10,000m" in message
        assert "50%" in message
        assert "10%" in message

    def test_get_sunset_time_string(self):
        """日の入り時刻文字列の取得"""
        # 2024年1月1日 18:30 JSTを設定
        sunset_dt = datetime(2024, 1, 1, 18, 30, 0, tzinfo=JST)
        sunset_unix = int(sunset_dt.timestamp())

        weather_data = {
            "current": {
                "sunset": sunset_unix
            }
        }

        sunset_str = self.service.get_sunset_time_string(weather_data)
        
        assert sunset_str == "18:30"

    def test_get_sunset_time_string_no_data(self):
        """日の入り時刻データがない場合"""
        weather_data = {
            "current": {}
        }

        sunset_str = self.service.get_sunset_time_string(weather_data)
        
        assert sunset_str == "不明"

    def test_message_format_with_special_characters(self):
        """特殊文字を含むメッセージのフォーマット"""
        score = 90
        details = {
            "reasons": ["理由①", "理由②・詳細", "理由③（補足）"],
            "weather_desc": "快晴☀️",
            "clouds": 10,
            "visibility": 15000,
            "humidity": 40,
            "pop": 0,
        }
        sunset_time = "17:45"

        subject, message = self.service.create_notification_message(
            score, details, sunset_time
        )

        # 特殊文字が正しく含まれているか確認
        assert "理由①" in message
        assert "理由②・詳細" in message
        assert "理由③（補足）" in message
        assert "快晴☀️" in message

    def test_notification_service_with_different_location(self):
        """異なる地名でのサービス初期化"""
        service_tokyo = NotificationService(location_name="東京都")
        service_osaka = NotificationService(location_name="大阪市")

        assert service_tokyo.location_name == "東京都"
        assert service_osaka.location_name == "大阪市"

        # メッセージに地名が含まれることを確認
        score = 80
        details = {
            "reasons": ["テスト"],
            "weather_desc": "晴れ",
            "clouds": 20,
            "visibility": 10000,
            "humidity": 50,
            "pop": 0,
        }
        sunset_time = "18:00"

        _, message_tokyo = service_tokyo.create_notification_message(score, details, sunset_time)
        _, message_osaka = service_osaka.create_notification_message(score, details, sunset_time)

        assert "東京都" in message_tokyo
        assert "大阪市" in message_osaka

# Made with Bob
