    resource "aws_iam_role" "codebuild_role" {
  name = "codebuild-role-${var.env}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "codebuild.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "codebuild_policy" {
  role = aws_iam_role.codebuild_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
         "sagemaker:StartPipelineExecution",
          "logs:*",
          "s3:*",
          "ecr:GetAuthorizationToken",
				  "ecr:BatchCheckLayerAvailability",
				  "ecr:GetDownloadUrlForLayer",
				  "ecr:BatchGetImage",
				  "ecr:InitiateLayerUpload",
				  "ecr:UploadLayerPart",
				  "ecr:CompleteLayerUpload",
				  "ecr:PutImage",
          "iam:PassRole"         
          ]
      Resource = "*"
    }]
  })
}
