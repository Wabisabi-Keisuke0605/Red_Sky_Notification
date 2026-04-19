"""
SNS 通知クライアント
"""

import boto3
from typing import Dict


class SnsClient:
    """SNS通知を送信するクライアント"""

    def __init__(self, client=None):
        """
        Args:
            client: boto3 SNSクライアント（テスト時にモック注入可能）
        """
        self.client = client or boto3.client("sns")

    def publish(self, topic_arn: str, subject: str, message: str) -> Dict:
        """
        SNS通知を送信

        Args:
            topic_arn: SNSトピックARN
            subject: 件名
            message: メッセージ本文

        Returns:
            SNS publish レスポンス

        Raises:
            Exception: 送信に失敗した場合
        """
        try:
            response = self.client.publish(
                TopicArn=topic_arn,
                Subject=subject,
                Message=message,
            )
            return response
        except Exception as e:
            raise Exception(f"Failed to publish SNS message: {str(e)}")