resource "aws_ecr_repository" "dq_repo" {
  name                 = "timesheet-dq-processing"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}