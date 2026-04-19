"""
SnsClient のユニットテスト
"""

import pytest
import sys
import os
from unittest.mock import Mock

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from resources.sns_client import SnsClient


class TestSnsClient:
    """SnsClientのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.mock_sns_client = Mock()
        self.sns_client = SnsClient(client=self.mock_sns_client)

    def test_initialization_with_client(self):
        """クライアントを指定して初期化"""
        mock_client = Mock()
        client = SnsClient(client=mock_client)
        assert client.client == mock_client

    def test_initialization_without_client(self):
        """クライアントを指定せずに初期化"""
        client = SnsClient()
        assert client.client is not None

    def test_publish_success(self):
        """SNS通知送信成功のテスト"""
        # モックの設定
        self.mock_sns_client.publish.return_value = {
            "MessageId": "test-message-id-123",
            "ResponseMetadata": {
                "HTTPStatusCode": 200
            }
        }

        # テスト実行
        result = self.sns_client.publish(
            topic_arn="arn:aws:sns:ap-northeast-1:123456789012:test-topic",
            subject="テスト件名",
            message="テストメッセージ本文"
        )

        # 検証
        assert result["MessageId"] == "test-message-id-123"
        assert result["ResponseMetadata"]["HTTPStatusCode"] == 200
        
        # publishが正しいパラメータで呼ばれたことを確認
        self.mock_sns_client.publish.assert_called_once_with(
            TopicArn="arn:aws:sns:ap-northeast-1:123456789012:test-topic",
            Subject="テスト件名",
            Message="テストメッセージ本文"
        )

    def test_publish_with_japanese_content(self):
        """日本語を含む通知の送信"""
        self.mock_sns_client.publish.return_value = {
            "MessageId": "msg-456"
        }

        result = self.sns_client.publish(
            topic_arn="arn:aws:sns:ap-northeast-1:123456789012:topic",
            subject="🌅 真っ赤な空アラート【福岡市】",
            message="真っ赤な空が見れるぞ！\n場所: 福岡市\n日の入り時刻: 18:30"
        )

        assert result["MessageId"] == "msg-456"
        
        # 日本語が正しく渡されたことを確認
        call_args = self.mock_sns_client.publish.call_args[1]
        assert "真っ赤な空" in call_args["Subject"]
        assert "福岡市" in call_args["Message"]

    def test_publish_with_long_message(self):
        """長いメッセージの送信"""
        long_message = "テスト" * 1000  # 長いメッセージ
        
        self.mock_sns_client.publish.return_value = {
            "MessageId": "msg-long"
        }

        result = self.sns_client.publish(
            topic_arn="arn:aws:sns:ap-northeast-1:123456789012:topic",
            subject="長いメッセージ",
            message=long_message
        )

        assert result["MessageId"] == "msg-long"
        
        # 長いメッセージが渡されたことを確認
        call_args = self.mock_sns_client.publish.call_args[1]
        assert len(call_args["Message"]) == len(long_message)

    def test_publish_failure(self):
        """SNS通知送信失敗のテスト"""
        # publishが例外を発生させるように設定
        self.mock_sns_client.publish.side_effect = Exception("SNS publish failed")

        # 例外が発生することを確認
        with pytest.raises(Exception) as exc_info:
            self.sns_client.publish(
                topic_arn="arn:aws:sns:ap-northeast-1:123456789012:topic",
                subject="テスト",
                message="テスト"
            )

        assert "Failed to publish SNS message" in str(exc_info.value)
        assert "SNS publish failed" in str(exc_info.value)

    def test_publish_with_invalid_topic_arn(self):
        """無効なトピックARNでの送信"""
        self.mock_sns_client.publish.side_effect = Exception("Invalid topic ARN")

        with pytest.raises(Exception) as exc_info:
            self.sns_client.publish(
                topic_arn="invalid-arn",
                subject="テスト",
                message="テスト"
            )

        assert "Failed to publish SNS message" in str(exc_info.value)

    def test_publish_with_empty_subject(self):
        """空の件名での送信"""
        self.mock_sns_client.publish.return_value = {
            "MessageId": "msg-empty-subject"
        }

        result = self.sns_client.publish(
            topic_arn="arn:aws:sns:ap-northeast-1:123456789012:topic",
            subject="",
            message="メッセージ本文"
        )

        assert result["MessageId"] == "msg-empty-subject"
        
        # 空の件名が渡されたことを確認
        call_args = self.mock_sns_client.publish.call_args[1]
        assert call_args["Subject"] == ""

    def test_publish_with_special_characters(self):
        """特殊文字を含む通知の送信"""
        self.mock_sns_client.publish.return_value = {
            "MessageId": "msg-special"
        }

        result = self.sns_client.publish(
            topic_arn="arn:aws:sns:ap-northeast-1:123456789012:topic",
            subject="テスト: 特殊文字 & < > \" '",
            message="改行\nタブ\t記号!@#$%^&*()"
        )

        assert result["MessageId"] == "msg-special"

    def test_publish_multiple_times(self):
        """複数回の通知送信"""
        self.mock_sns_client.publish.side_effect = [
            {"MessageId": "msg-1"},
            {"MessageId": "msg-2"},
            {"MessageId": "msg-3"},
        ]

        result1 = self.sns_client.publish("arn:1", "件名1", "本文1")
        result2 = self.sns_client.publish("arn:2", "件名2", "本文2")
        result3 = self.sns_client.publish("arn:3", "件名3", "本文3")

        assert result1["MessageId"] == "msg-1"
        assert result2["MessageId"] == "msg-2"
        assert result3["MessageId"] == "msg-3"
        assert self.mock_sns_client.publish.call_count == 3

    def test_publish_returns_full_response(self):
        """完全なレスポンスが返されることを確認"""
        full_response = {
            "MessageId": "test-id",
            "ResponseMetadata": {
                "RequestId": "request-123",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "content-type": "text/xml"
                },
                "RetryAttempts": 0
            }
        }
        
        self.mock_sns_client.publish.return_value = full_response

        result = self.sns_client.publish(
            topic_arn="arn:aws:sns:ap-northeast-1:123456789012:topic",
            subject="テスト",
            message="テスト"
        )

        # 完全なレスポンスが返されることを確認
        assert result == full_response
        assert "ResponseMetadata" in result
        assert result["ResponseMetadata"]["HTTPStatusCode"] == 200

# Made with Bob
