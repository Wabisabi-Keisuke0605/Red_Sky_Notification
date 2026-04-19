"""
SSM Parameter Store からパラメータを取得するリポジトリ
"""

import boto3
from typing import Optional


class ParameterRepository:
    """SSM Parameter Store へのアクセスを管理するリポジトリ"""

    def __init__(self, ssm_client=None):
        self.ssm_client = ssm_client or boto3.client("ssm")

    def get_parameter(
        self, parameter_name: str, with_decryption: bool = True
    ) -> str:
        """
        SSM Parameter Store からパラメータ値を取得

        Args:
            parameter_name: パラメータ名
            with_decryption: 復号化するかどうか（SecureString用）

        Returns:
            パラメータ値（文字列）

        Raises:
            ValueError: パラメータが見つからない場合
            Exception: その他のエラーが発生した場合
        """
        try:
            response = self.ssm_client.get_parameter(
                Name=parameter_name, WithDecryption=with_decryption
            )
            return response["Parameter"]["Value"]
        except self.ssm_client.exceptions.ParameterNotFound:
            raise ValueError(f"Parameter not found: {parameter_name}")
        except Exception as e:
            raise Exception(f"Failed to get parameter {parameter_name}: {str(e)}")

    def get_api_key(self, parameter_name: str) -> str:
        """APIキーを取得"""
        return self.get_parameter(parameter_name, with_decryption=True)
