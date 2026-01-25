from aws_cdk import (
    Duration,
    Stack,
    CfnOutput,
    aws_lambda as lambda_,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_events as events,
    aws_events_targets as targets,
    aws_ssm as ssm,
    aws_iam as iam,
)
from constructs import Construct
import os

class RedSkyAlertStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "RedSkyAlertQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )

        ####################################
        # SNS Topic - 真っ赤な空のアラート通知 #
        ####################################

        alert_topic = sns.Topic(
            self,
            "RedSkyAlertTopic",
            topic_name="red-sky-alert-fukuoka",
            display_name="福岡県での真っ赤な空アラート"
        )

        ##########################################
        # SSM Parameter - OpenWeatherMap API Key #
        ##########################################

        api_key_param = ssm.StringParameter.from_secure_string_parameter_attributes(
            self,
            "OpenWeatherMapApiKey",
            parameter_name="/red-sky-alert/openweathermap-api-key",
        )

        #################################
        # Lambda Function - 天気判定&通知 #
        #################################

        red_sky_checker = lambda_.Function(
            self,
            "RedSkyCheckerFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), "..", "lambda")),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "SNS_TOPIC_ARN": alert_topic.topic_arn,
                # 福岡市の緯度経度
                "LATITUDE": "33.5904",
                "LONGITUDE": "130.4017",
                "LOCATION_NAME": "福岡市",

                # 通知閾値（80以上で通知）
                "SCORE_THRESHOLD": "80",

                # SSM パラメータ名
                "OPENWEATHERMAP_API_KEY_PARAM": "/red-sky-alert/openweathermap-api-key",
            },
            description="福岡市で真っ赤な空の発生可能性を判定し、SNS通知を送信する"
        )

        # LambdaにSSMパラメータの読み取り権限を付与
        api_key_param.grant_read(red_sky_checker)

        # LambdaにSNS発行権限を付与
        alert_topic.grant_publish(red_sky_checker)


        ##################################
        #EventBridge -定期的に判定を実行する #
        ##################################

        # 春と秋用の時間設定
        spring_autumn_rule = events.Rule(
            self,
            "SpringAutumnCheckRule",
            rule_name="red-sky-check-spring-autumn",
            description="春秋季の真っ赤な空チェック（3月〜4月、9月〜10月）",
            schedule=events.Schedule.cron(
                minute="0,15,30,45",
                hour="8,9",  # UTC 08:00-09:45 = JST 17:00-18:45
                month="3,4,9,10",
            ),
            enabled=True,
        )

        # 夏用の時間設定
        summer_rule = events.Rule(
            self,
            "SummerCheckRule",
            rule_name="red-sky-check-summer",
            description="夏季の真っ赤な空チェック（5月〜8月）",
            schedule=events.Schedule.cron(
                minute="0,15,30,45",
                hour="9,10",  # UTC 09:00-10:45 = JST 18:00-19:45
                month="5,6,7,8",
            ),
            enabled=True,
        )
        summer_rule.add_target(targets.LambdaFunction(red_sky_checker))

        # 冬用の時間設定
        winter_rule = events.Rule(
            self,
            "WinterCheckRule",
            rule_name="red-sky-check-winter",
            description="冬季の真っ赤な空チェック（11月〜2月）",
            schedule=events.Schedule.cron(
                minute="0,15,30,45",
                hour="7,8",  # UTC 07:00-08:45 = JST 16:00-17:45
                month="1,2,11,12",
            ),
            enabled=True,
        )
        winter_rule.add_target(targets.LambdaFunction(red_sky_checker))


        ###########
        # Outputs #
        ###########

        CfnOutput(
            self,
            "SnsTopicArn",
            value=alert_topic.topic_arn,
            description="SNS Topic ARN - メール購読登録用",
        )

        CfnOutput(
            self,
            "LambdaFunctionName",
            value=red_sky_checker.function_name,
            description="Lambda関数名",
        )

        CfnOutput(
            self,
            "SubscribeCommand",
            value=f"aws sns subscribe --topic-arn {alert_topic.topic_arn} "
                  f"--protocol email --notification-endpoint YOUR_EMAIL@example.com",
            description="メール購読登録コマンド",
        )


