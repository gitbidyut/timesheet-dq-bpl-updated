resource "aws_iam_role" "codepipeline_role" {
  name = "codepipeline-role-${var.env}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "codepipeline.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "codepipeline_policy" {
  role = aws_iam_role.codepipeline_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:*"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = ["codebuild:StartBuild", "codebuild:BatchGetBuilds"]
        Resource = aws_codebuild_project.start_pipeline.arn
      },
      {
        Effect = "Allow"
        Action = "codestar-connections:UseConnection"
        Resource = "arn:aws:codeconnections:eu-west-1:361509912577:connection/9c948075-73f7-4c60-8d1a-2539faa9ba9f"
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = aws_iam_role.codebuild_role.arn
      }
    ]
  })
}
