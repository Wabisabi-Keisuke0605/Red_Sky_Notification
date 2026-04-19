"""
ParameterRepository のユニットテスト
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from repositories.parameter_repository import ParameterRepository


class TestParameterRepository:
    """ParameterRepositoryのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.mock_ssm_client = Mock()
        self.repository = ParameterRepository(ssm_client=self.mock_ssm_client)

    def test_get_parameter_success(self):
        """パラメータ取得成功のテスト"""
        # モックの設定
        self.mock_ssm_client.get_parameter.return_value = {
            "Parameter": {
                "Value": "test-value-123"
            }
        }

        # テスト実行
        result = self.repository.get_parameter("/test/parameter")

        # 検証
        assert result == "test-value-123"
        self.mock_ssm_client.get_parameter.assert_called_once_with(
            Name="/test/parameter",
            WithDecryption=True
        )

    def test_get_parameter_with_decryption_false(self):
        """復号化なしでのパラメータ取得"""
        self.mock_ssm_client.get_parameter.return_value = {
            "Parameter": {
                "Value": "plain-value"
            }
        }

        result = self.repository.get_parameter("/test/parameter", with_decryption=False)

        assert result == "plain-value"
        self.mock_ssm_client.get_parameter.assert_called_once_with(
            Name="/test/parameter",
            WithDecryption=False
        )

    def test_get_parameter_not_found(self):
        """パラメータが見つからない場合"""
        # ParameterNotFound例外をモック
        self.mock_ssm_client.exceptions = MagicMock()
        self.mock_ssm_client.exceptions.ParameterNotFound = Exception
        self.mock_ssm_client.get_parameter.side_effect = Exception("Parameter not found")

        # ValueErrorが発生することを確認
        with pytest.raises(ValueError) as exc_info:
            self.repository.get_parameter("/nonexistent/parameter")

        assert "Parameter not found" in str(exc_info.value)

    def test_get_api_key_success(self):
        """APIキー取得成功のテスト"""
        self.mock_ssm_client.get_parameter.return_value = {
            "Parameter": {
                "Value": "api-key-xyz789"
            }
        }

        result = self.repository.get_api_key("/api/key")

        assert result == "api-key-xyz789"
        # with_decryption=Trueで呼ばれることを確認
        self.mock_ssm_client.get_parameter.assert_called_once_with(
            Name="/api/key",
            WithDecryption=True
        )

    def test_get_api_key_calls_get_parameter(self):
        """get_api_keyがget_parameterを正しく呼び出すことを確認"""
        self.mock_ssm_client.get_parameter.return_value = {
            "Parameter": {
                "Value": "secret-key"
            }
        }

        result = self.repository.get_api_key("/secret/api-key")

        # get_parameterが正しいパラメータで呼ばれたことを確認
        assert result == "secret-key"
        call_args = self.mock_ssm_client.get_parameter.call_args
        assert call_args[1]["Name"] == "/secret/api-key"
        assert call_args[1]["WithDecryption"] is True

    def test_initialization_without_client(self):
        """クライアントを指定せずに初期化"""
        # boto3.client()が呼ばれることを確認するため、
        # 実際のboto3をモックする必要があるが、
        # ここでは初期化が成功することだけを確認
        repo = ParameterRepository()
        assert repo.ssm_client is not None

    def test_get_parameter_with_special_characters(self):
        """特殊文字を含むパラメータ名"""
        self.mock_ssm_client.get_parameter.return_value = {
            "Parameter": {
                "Value": "value-with-special-chars"
            }
        }

        result = self.repository.get_parameter("/path/to/param-with_special.chars")

        assert result == "value-with-special-chars"
        self.mock_ssm_client.get_parameter.assert_called_once()

    def test_get_parameter_empty_value(self):
        """空の値を持つパラメータ"""
        self.mock_ssm_client.get_parameter.return_value = {
            "Parameter": {
                "Value": ""
            }
        }

        result = self.repository.get_parameter("/empty/parameter")

        assert result == ""

    def test_multiple_get_parameter_calls(self):
        """複数回のパラメータ取得"""
        self.mock_ssm_client.get_parameter.side_effect = [
            {"Parameter": {"Value": "value1"}},
            {"Parameter": {"Value": "value2"}},
            {"Parameter": {"Value": "value3"}},
        ]

        result1 = self.repository.get_parameter("/param1")
        result2 = self.repository.get_parameter("/param2")
        result3 = self.repository.get_parameter("/param3")

        assert result1 == "value1"
        assert result2 == "value2"
        assert result3 == "value3"
        assert self.mock_ssm_client.get_parameter.call_count == 3

# Made with Bob
