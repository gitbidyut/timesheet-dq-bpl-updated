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
        FullRepositoryId = "gitbidyut/timesheet-dq-bpl" # e.g., "myuser/my-repo"
        BranchName       = "main"

        # 🔑 IMPORTANT
        FilePaths = jsonencode([
           "data_quality.py",
            "Dockerfile"
         ])
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
