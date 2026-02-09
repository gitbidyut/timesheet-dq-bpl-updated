resource "aws_s3_bucket" "raw" {
  bucket = "bpl-timesheet-raw-${var.env}"
}

resource "aws_s3_bucket" "results" {
  bucket = "bpl-timesheet-results-${var.env}"
}

resource "aws_s3_bucket" "artifacts" {
  bucket        = "bpl-timesheet-artifacts-${var.env}"
  force_destroy = true
}
