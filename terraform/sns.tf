resource "aws_sns_topic" "dq_results" {
  name = "timesheet-dq-results"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.dq_results.arn
  protocol  = "email"
  endpoint  = "bidyut.pal@atos.net"
}
