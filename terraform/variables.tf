variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name to be used for tagging and resource naming"
  type        = string
  default     = "flight-pipeline"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for the flight pipeline"
  type        = string
  default     = "realtimeflightstreamingbuckett"
}
