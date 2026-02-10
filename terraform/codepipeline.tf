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


resource "aws_cloudwatch_event_target" "trigger_pipeline" {
  rule      = aws_cloudwatch_event_rule.result.name
  target_id = "CodePipelineTarget"
  arn       = aws_codepipeline.pipeline.arn
  role_arn = aws_iam_role.eventbridge_role.arn
}

resource "aws_iam_role" "eventbridge_role" {
  name = "eventbridge-start-codepipeline-role"

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
      Action = "codepipeline:StartPipelineExecution"
      Resource = aws_codepipeline.pipeline.arn
    }]
  })
}


