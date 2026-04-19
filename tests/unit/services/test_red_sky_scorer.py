"""
RedSkyScorerService のユニットテスト
"""

import pytest
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from services.red_sky_scorer import RedSkyScorerService


class TestRedSkyScorerService:
    """RedSkyScorerServiceのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.scorer = RedSkyScorerService()

    def test_calculate_score_with_ideal_conditions(self):
        """理想的な気象条件でのスコア計算"""
        weather_data = {
            "current": {
                "clouds": 30,  # 薄雲
                "visibility": 10000,  # 視程最良
                "humidity": 45,  # 低湿度
                "weather": [{"id": 801, "description": "few clouds"}],
            },
            "hourly": [{"pop": 0}],  # 降水確率0%
        }

        score, details = self.scorer.calculate_score(weather_data)

        # 理想的な条件なので高スコアを期待
        assert score >= 80, f"Expected score >= 80, got {score}"
        assert details["clouds"] == 30
        assert details["visibility"] == 10000
        assert details["humidity"] == 45
        assert details["pop"] == 0
        assert len(details["reasons"]) == 4

    def test_calculate_score_with_poor_conditions(self):
        """悪い気象条件でのスコア計算"""
        weather_data = {
            "current": {
                "clouds": 95,  # 曇天
                "visibility": 2000,  # 視程不良
                "humidity": 85,  # 高湿度
                "weather": [{"id": 804, "description": "overcast clouds"}],
            },
            "hourly": [{"pop": 0.5}],  # 降水確率50%
        }

        score, details = self.scorer.calculate_score(weather_data)

        # 悪い条件なので低スコアを期待
        assert score < 30, f"Expected score < 30, got {score}"
        assert details["clouds"] == 95
        assert details["visibility"] == 2000

    def test_score_clouds_clear_sky(self):
        """快晴時の雲量スコア"""
        score, reason = self.scorer._score_clouds(5, 800)
        assert score == 30
        assert "快晴" in reason

    def test_score_clouds_few_clouds(self):
        """薄雲時の雲量スコア（最適条件）"""
        score, reason = self.scorer._score_clouds(20, 801)
        assert score == 40  # 最高点
        assert "薄雲" in reason
        assert "最適" in reason

    def test_score_clouds_overcast(self):
        """曇天時の雲量スコア"""
        score, reason = self.scorer._score_clouds(90, 804)
        assert score == 0
        assert "曇天" in reason

    def test_score_visibility_excellent(self):
        """視程が最良の場合"""
        score, reason = self.scorer._score_visibility(10000)
        assert score == 30
        assert "最良" in reason

    def test_score_visibility_poor(self):
        """視程が不良の場合"""
        score, reason = self.scorer._score_visibility(2000)
        assert score == 0
        assert "不良" in reason

    def test_score_precipitation_zero(self):
        """降水確率0%の場合"""
        score, reason = self.scorer._score_precipitation(0)
        assert score == 20
        assert "0%" in reason

    def test_score_precipitation_high(self):
        """降水確率が高い場合"""
        score, reason = self.scorer._score_precipitation(0.6)
        assert score == 0
        assert "60%" in reason

    def test_score_humidity_low(self):
        """湿度が低い場合"""
        score, reason = self.scorer._score_humidity(40)
        assert score == 10
        assert "乾燥" in reason

    def test_score_humidity_high(self):
        """湿度が高い場合"""
        score, reason = self.scorer._score_humidity(85)
        assert score == 0

    def test_calculate_score_with_missing_data(self):
        """データが不足している場合のデフォルト値処理"""
        weather_data = {
            "current": {},
            "hourly": [{}],
        }

        score, details = self.scorer.calculate_score(weather_data)

        # デフォルト値で計算される
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert details["clouds"] == 0
        assert details["visibility"] == 0
        assert details["humidity"] == 0
        assert details["weather_id"] == 0
        assert details["pop"] == 0

    def test_score_range(self):
        """スコアが0-100の範囲内であることを確認"""
        test_cases = [
            {"clouds": 0, "visibility": 10000, "humidity": 30, "weather_id": 800, "pop": 0},
            {"clouds": 50, "visibility": 5000, "humidity": 60, "weather_id": 802, "pop": 0.2},
            {"clouds": 100, "visibility": 1000, "humidity": 90, "weather_id": 804, "pop": 0.8},
        ]

        for test_data in test_cases:
            weather_data = {
                "current": {
                    "clouds": test_data["clouds"],
                    "visibility": test_data["visibility"],
                    "humidity": test_data["humidity"],
                    "weather": [{"id": test_data["weather_id"], "description": "test"}],
                },
                "hourly": [{"pop": test_data["pop"]}],
            }

            score, _ = self.scorer.calculate_score(weather_data)
            assert 0 <= score <= 100, f"Score {score} is out of range [0, 100]"

# Made with Bob
