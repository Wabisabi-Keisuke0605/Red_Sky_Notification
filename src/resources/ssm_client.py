"""
SSM Parameter Store クライアントのラッパー
"""

import boto3


class SsmClient:
    """SSM Parameter Store へのアクセスを提供するクライアント"""

    def __init__(self, client=None):
        """
        Args:
            client: boto3 SSMクライアント（テスト時にモック注入可能）
        """
        self.client = client or boto3.client("ssm")

    def get_parameter(
        self, name: str, with_decryption: bool = True
    ) -> str:
        """
        パラメータを取得

        Args:
            name: パラメータ名
            with_decryption: 復号化するか

        Returns:
            パラメータ値

        Raises:
            Exception: 取得に失敗した場合
        """
        try:
            response = self.client.get_parameter(
                Name=name, WithDecryption=with_decryption
            )
            return response["Parameter"]["Value"]
        except Exception as e:
            raise Exception(f"Failed to get SSM parameter {name}: {str(e)}")