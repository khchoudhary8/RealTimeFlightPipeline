# -----------------------------------------------------------------------------
# IAM Policies for Flight Pipeline
# -----------------------------------------------------------------------------

# 1. ECR Push/Pull Policy (Used by GitHub Actions or CI/CD user)
resource "aws_iam_policy" "ecr_push_policy" {
  name        = "${var.project_name}-ecr-push-policy"
  description = "Allows pushing docker images to the flight pipeline ECR repository"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GetAuthorizationToken"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Sid    = "PushToFlightPipelineRepo"
        Effect = "Allow"
        Action = [
          "ecr:CompleteLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:InitiateLayerUpload",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = aws_ecr_repository.flight_pipeline.arn
      }
    ]
  })
}

# 2. S3 Full Access Policy (Used by Local Streaming Worker & Future ECS Tasks)
# In an enterprise environment, we restrict this to ONLY the specific bucket!
resource "aws_iam_policy" "s3_pipeline_policy" {
  name        = "${var.project_name}-s3-pipeline-policy"
  description = "Allows full read/write/delete access to the flight pipeline S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3BucketAccess"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket_name}"
      },
      {
        Sid    = "S3ObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket_name}/*"
      }
    ]
  })
}

# Reference the existing IAM User
data "aws_iam_user" "existing_user" {
  user_name = "flightstreaming"
}

# Attach both policies to the existing user
resource "aws_iam_user_policy_attachment" "ecr_attach" {
  user       = data.aws_iam_user.existing_user.user_name
  policy_arn = aws_iam_policy.ecr_push_policy.arn
}

resource "aws_iam_user_policy_attachment" "s3_attach" {
  user       = data.aws_iam_user.existing_user.user_name
  policy_arn = aws_iam_policy.s3_pipeline_policy.arn
}

# 3. ECS Task Execution Role (Required for Fargate to pull ECR images & log to CloudWatch)
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.project_name}-ecs-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
