"""
真っ赤な空の出現可能性をスコアリングするサービス
"""

from typing import Tuple, Dict, List


class RedSkyScorerService:
    """真っ赤な空のスコア計算ロジックを提供するサービス"""

    def calculate_score(self, weather_data: Dict) -> Tuple[int, Dict]:
        """
        真っ赤な空の出現可能性をスコアリング（0-100）

        OpenWeatherMapでは高度別雲量が取得できないため、
        全体の雲量と天気コードから推測

        Args:
            weather_data: OpenWeatherMap APIから取得した天気データ

        Returns:
            (スコア, 詳細情報の辞書)
        """
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
        reasons: List[str] = []

        # 1. 雲量チェック（最大40点）
        score_clouds, reason_clouds = self._score_clouds(
            details["clouds"], details["weather_id"]
        )
        score += score_clouds
        reasons.append(reason_clouds)

        # 2. 視程チェック（最大30点）
        score_visibility, reason_visibility = self._score_visibility(
            details["visibility"]
        )
        score += score_visibility
        reasons.append(reason_visibility)

        # 3. 降水確率チェック（最大20点）
        score_pop, reason_pop = self._score_precipitation(details["pop"])
        score += score_pop
        reasons.append(reason_pop)

        # 4. 湿度チェック（最大10点）
        score_humidity, reason_humidity = self._score_humidity(details["humidity"])
        score += score_humidity
        reasons.append(reason_humidity)

        details["score"] = score
        details["reasons"] = reasons

        return score, details

    def _score_clouds(self, clouds: int, weather_id: int) -> Tuple[int, str]:
        """
        雲量と天気コードからスコアを計算

        Args:
            clouds: 雲量（%）
            weather_id: OpenWeatherMap天気コード

        Returns:
            (スコア, 理由)
        """
        # 天気コードから雲の種類を推測
        # 800: 快晴, 801: 薄雲, 802: 散在雲, 803: 千切れ雲, 804: 曇天
        if weather_id == 800:  # 快晴
            if clouds <= 10:
                return 30, f"快晴（雲量{clouds}%）- 良好"
            else:
                return 35, f"ほぼ快晴（雲量{clouds}%）- 良好"
        elif weather_id == 801:  # few clouds (11-25%)
            return 40, f"薄雲あり（雲量{clouds}%）- 最適"
        elif weather_id == 802:  # scattered clouds (25-50%)
            return 35, f"散在雲（雲量{clouds}%）- 良好"
        elif weather_id == 803:  # broken clouds (51-84%)
            if clouds <= 70:
                return 20, f"千切れ雲（雲量{clouds}%）- やや多い"
            else:
                return 10, f"雲多め（雲量{clouds}%）- 厳しい"
        elif weather_id == 804:  # overcast (85-100%)
            return 0, f"曇天（雲量{clouds}%）- 不適"
        elif 700 <= weather_id < 800:  # 霧・靄など
            return 5, "霧・靄あり - 不適"
        elif weather_id < 700:  # 雨・雪など
            return 0, "降水あり - 不適"
        else:
            # その他の場合は雲量で判定
            if 20 <= clouds <= 60:
                return 35, f"雲量{clouds}% - 良好"
            elif clouds < 20:
                return 30, f"雲量{clouds}% - 快晴寄り"
            elif 60 < clouds <= 80:
                return 15, f"雲量{clouds}% - やや多い"
            else:
                return 0, f"雲量{clouds}% - 曇天"

    def _score_visibility(self, visibility: int) -> Tuple[int, str]:
        """
        視程からスコアを計算

        Args:
            visibility: 視程（メートル）

        Returns:
            (スコア, 理由)
        """
        if visibility >= 10000:
            return 30, f"視程{visibility}m - 最良"
        elif visibility >= 8000:
            return 25, f"視程{visibility}m - 良好"
        elif visibility >= 5000:
            return 15, f"視程{visibility}m - 普通"
        elif visibility >= 3000:
            return 5, f"視程{visibility}m - やや悪い"
        else:
            return 0, f"視程{visibility}m - 不良"

    def _score_precipitation(self, pop: float) -> Tuple[int, str]:
        """
        降水確率からスコアを計算

        Args:
            pop: 降水確率（0.0-1.0）

        Returns:
            (スコア, 理由)
        """
        if pop == 0:
            return 20, "降水確率0% - 最良"
        elif pop <= 0.1:
            return 15, f"降水確率{int(pop*100)}% - 良好"
        elif pop <= 0.2:
            return 10, f"降水確率{int(pop*100)}% - 普通"
        elif pop <= 0.3:
            return 5, f"降水確率{int(pop*100)}% - やや高い"
        else:
            return 0, f"降水確率{int(pop*100)}% - 高い"

    def _score_humidity(self, humidity: int) -> Tuple[int, str]:
        """
        湿度からスコアを計算

        Args:
            humidity: 湿度（%）

        Returns:
            (スコア, 理由)
        """
        if humidity < 50:
            return 10, f"湿度{humidity}% - 乾燥で最良"
        elif humidity < 65:
            return 8, f"湿度{humidity}% - 良好"
        elif humidity < 80:
            return 5, f"湿度{humidity}% - 普通"
        else:
            return 0, f"湿度{humidity}% - 高い"