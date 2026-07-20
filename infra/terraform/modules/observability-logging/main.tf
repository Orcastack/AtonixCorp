resource "aws_cloudwatch_log_group" "application" {
  name              = "/atonixcorp/${var.name_prefix}/application"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "platform" {
  name              = "/atonixcorp/${var.name_prefix}/platform"
  retention_in_days = 90
  tags              = var.tags
}