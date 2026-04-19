import json
import urllib.request
import urllib.error
from typing import Dict

class WeatherRepository:
    def __init__(self, base_url:str ="https://api.openweathermap.org/data/3.0") ->None:
        self.base_url = base_url

    def fetch_weather_data(self, latitude: str, longitude: str, api_key: str, timeout: int=10) -> Dict:
        url = (
            f"{self.base_url}/onecall"
            f"?lat={latitude}&lon={longitude}"
            f"&exclude=minutely,daily,alerts"
            f"&units=metric"
            f"&appid={api_key}"
        )

        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP error occurred: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"URL error occurred: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"An error occurred: {str(e)}")