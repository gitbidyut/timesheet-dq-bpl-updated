resource "aws_codepipeline" "pipeline" {
  name     = "bpl-timesheet-${var.env}"
  role_arn = aws_iam_role.codepipeline_role.arn

  artifact_store {
    type     = "S3"
    location = aws_s3_bucket.artifacts.bucket
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source"]

      configuration = {
        ConnectionArn    = "arn:aws:codeconnections:eu-west-1:361509912577:connection/9c948075-73f7-4c60-8d1a-2539faa9ba9f"
        FullRepositoryId = "gitbidyut/timesheet-dq-bpl-updated" # e.g., "myuser/my-repo"
        BranchName       = "main"

      }
    }
  }

  stage {
    name = "RunDQ"

    action {
      name            = "StartSageMakerPipeline"
      category        = "Build"
      owner           = "AWS"
      version          = "1"
      provider        = "CodeBuild"
      input_artifacts = ["source"]

      configuration = {
        ProjectName = aws_codebuild_project.start_pipeline.name
      }
    }
  }
}

resource "aws_cloudwatch_event_rule" "timesheet_result" {
  name        = "trigger-sns-on-timesheet-result"
  description = "Trigger SNS when DQ result is uploaded to S3"

  event_pattern = jsonencode({
    source = ["aws.s3"],
    detail-type = ["Object Created"],
    detail = {
      bucket = {
        name = ["bpl-timesheet-results-dev"]
      },
      object = {
        key = [{
          prefix = "ouput/"
        }]
      }
    }
  })
}



resource "aws_cloudwatch_event_target" "trigger_pipeline" {
  rule      = aws_cloudwatch_event_rule.timesheet_result.name
  target_id = "SendDQResultSNS"
  arn       = aws_sns_topic.dq_results.id
  role_arn = aws_iam_role.eventbridge_role.arn
}

resource "aws_iam_role" "eventbridge_role" {
  name = "eventbridge-sns-publish-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_policy" {
  role = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sns:Publish"
      Resource =aws_sns_topic.dq_results.arn
    }]
  })
}


