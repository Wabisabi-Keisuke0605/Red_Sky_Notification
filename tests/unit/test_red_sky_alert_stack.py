import aws_cdk as core
import aws_cdk.assertions as assertions

from red_sky_alert.red_sky_alert_stack import RedSkyAlertStack

# example tests. To run these tests, uncomment this file along with the example
# resource in red_sky_alert/red_sky_alert_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = RedSkyAlertStack(app, "red-sky-alert")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
