"""
WeatherRepository のユニットテスト
"""

import pytest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock
import urllib.error

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from repositories.weather_repository import WeatherRepository


class TestWeatherRepository:
    """WeatherRepositoryのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.repository = WeatherRepository()
        self.test_latitude = "33.5904"
        self.test_longitude = "130.4017"
        self.test_api_key = "test-api-key-123"

    def test_initialization_default_url(self):
        """デフォルトURLでの初期化"""
        repo = WeatherRepository()
        assert repo.base_url == "https://api.openweathermap.org/data/3.0"

    def test_initialization_custom_url(self):
        """カスタムURLでの初期化"""
        custom_url = "https://custom.api.com/v1"
        repo = WeatherRepository(base_url=custom_url)
        assert repo.base_url == custom_url

    @patch('urllib.request.urlopen')
    def test_fetch_weather_data_success(self, mock_urlopen):
        """天気データ取得成功のテスト"""
        # モックレスポンスの設定
        mock_response_data = {
            "current": {
                "temp": 20.5,
                "clouds": 30,
                "visibility": 10000,
                "humidity": 50,
                "sunset": 1234567890,
                "weather": [{"id": 801, "description": "few clouds"}]
            },
            "hourly": [
                {"pop": 0.1, "temp": 19.0}
            ]
        }
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # テスト実行
        result = self.repository.fetch_weather_data(
            self.test_latitude,
            self.test_longitude,
            self.test_api_key
        )

        # 検証
        assert result == mock_response_data
        assert result["current"]["temp"] == 20.5
        assert result["current"]["clouds"] == 30
        
        # URLが正しく構築されたことを確認
        call_args = mock_urlopen.call_args[0][0]
        assert self.test_latitude in call_args
        assert self.test_longitude in call_args
        assert self.test_api_key in call_args
        assert "exclude=minutely,daily,alerts" in call_args
        assert "units=metric" in call_args

    @patch('urllib.request.urlopen')
    def test_fetch_weather_data_timeout(self, mock_urlopen):
        """タイムアウトのテスト"""
        mock_response_data = {"current": {}, "hourly": []}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # カスタムタイムアウトで実行
        result = self.repository.fetch_weather_data(
            self.test_latitude,
            self.test_longitude,
            self.test_api_key,
            timeout=5
        )

        # タイムアウトパラメータが渡されたことを確認
        call_kwargs = mock_urlopen.call_args[1]
        assert call_kwargs.get('timeout') == 5

    @patch('urllib.request.urlopen')
    def test_fetch_weather_data_with_japanese_characters(self, mock_urlopen):
        """日本語を含むレスポンスの処理"""
        mock_response_data = {
            "current": {
                "weather": [{"description": "薄い雲"}]
            },
            "hourly": []
        }
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            mock_response_data,
            ensure_ascii=False
        ).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = self.repository.fetch_weather_data(
            self.test_latitude,
            self.test_longitude,
            self.test_api_key
        )

        assert result["current"]["weather"][0]["description"] == "薄い雲"

    @patch('urllib.request.urlopen')
    def test_fetch_weather_data_empty_response(self, mock_urlopen):
        """空のレスポンスの場合"""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = self.repository.fetch_weather_data(
            self.test_latitude,
            self.test_longitude,
            self.test_api_key
        )

        assert result == {}

    def test_url_construction(self):
        """URLが正しく構築されることを確認"""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"test": "data"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            self.repository.fetch_weather_data(
                "35.6762",
                "139.6503",
                "my-api-key"
            )

            # 呼び出されたURLを取得
            called_url = mock_urlopen.call_args[0][0]
            
            # URL構成要素の確認
            assert "lat=35.6762" in called_url
            assert "lon=139.6503" in called_url
            assert "appid=my-api-key" in called_url
            assert "exclude=minutely,daily,alerts" in called_url
            assert "units=metric" in called_url
            assert called_url.startswith("https://api.openweathermap.org/data/3.0/onecall")

    @patch('urllib.request.urlopen')
    def test_fetch_weather_data_with_all_fields(self, mock_urlopen):
        """すべてのフィールドを含む完全なレスポンス"""
        complete_response = {
            "lat": 33.5904,
            "lon": 130.4017,
            "timezone": "Asia/Tokyo",
            "current": {
                "dt": 1234567890,
                "sunrise": 1234560000,
                "sunset": 1234590000,
                "temp": 20.5,
                "feels_like": 19.0,
                "pressure": 1013,
                "humidity": 50,
                "clouds": 30,
                "visibility": 10000,
                "wind_speed": 3.5,
                "weather": [
                    {
                        "id": 801,
                        "main": "Clouds",
                        "description": "few clouds",
                        "icon": "02d"
                    }
                ]
            },
            "hourly": [
                {
                    "dt": 1234567890,
                    "temp": 19.0,
                    "pop": 0.1,
                    "weather": [{"id": 800, "description": "clear sky"}]
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(complete_response).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = self.repository.fetch_weather_data(
            self.test_latitude,
            self.test_longitude,
            self.test_api_key
        )

        # すべてのフィールドが正しく取得されることを確認
        assert result["lat"] == 33.5904
        assert result["current"]["temp"] == 20.5
        assert result["current"]["humidity"] == 50
        assert result["hourly"][0]["pop"] == 0.1

# Made with Bob
