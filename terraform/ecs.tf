# -----------------------------------------------------------------------------
# ECS Cluster & Task Definitions (Fargate)
# -----------------------------------------------------------------------------

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = { Name = "${var.project_name}-ecs-cluster" }
}

# ECS Security Group (Allows traffic from ALB, and allows outbound anywhere)
resource "aws_security_group" "ecs_tasks_sg" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Allow inbound access from the ALB only"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol        = "tcp"
    from_port       = 8080
    to_port         = 8080
    security_groups = [aws_security_group.alb_sg.id]
  }

  ingress {
    protocol        = "tcp"
    from_port       = 8501
    to_port         = 8501
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-ecs-tasks-sg" }
}

# CloudWatch Log Group for ECS
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7
}

# -----------------------------------------------------------------------------
# FARGATE SERVICES
# -----------------------------------------------------------------------------

# 1. Main Dashboard (Streamlit)
resource "aws_ecs_task_definition" "dashboard" {
  family                   = "${var.project_name}-dashboard"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  # Using the same role for task and exec for simplicity in this architecture
  task_role_arn            = aws_iam_role.ecs_execution_role.arn 

  container_definitions = jsonencode([{
    name      = "dashboard"
    image     = "${aws_ecr_repository.flight_pipeline.repository_url}:latest"
    essential = true
    command   = ["python", "-m", "streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
    portMappings = [{
      containerPort = 8501
      hostPort      = 8501
    }]
    environment = [
      { name = "KAFKA_BOOTSTRAP_SERVERS", value = "${aws_instance.pipeline_server.private_ip}:9092" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "dashboard"
      }
    }
  }])
}

resource "aws_ecs_service" "dashboard" {
  name            = "${var.project_name}-dashboard-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.dashboard.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks_sg.id]
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.dashboard.arn
    container_name   = "dashboard"
    container_port   = 8501
  }
}

# 2. Live Map Dashboard (FastAPI)
resource "aws_ecs_task_definition" "live_map" {
  family                   = "${var.project_name}-live-map"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([{
    name      = "live-map"
    image     = "${aws_ecr_repository.flight_pipeline.repository_url}:live-map-latest"
    essential = true
    portMappings = [{
      containerPort = 8080
      hostPort      = 8080
    }]
    environment = [
      { name = "KAFKA_BOOTSTRAP_SERVERS", value = "${aws_instance.pipeline_server.private_ip}:9092" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "live-map"
      }
    }
  }])
}

resource "aws_ecs_service" "live_map" {
  name            = "${var.project_name}-live-map-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.live_map.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks_sg.id]
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.live_map.arn
    container_name   = "live-map"
    container_port   = 8080
  }
}

# 3. Streaming Worker (Faust) - No Load Balancer needed
resource "aws_ecs_task_definition" "streaming" {
  family                   = "${var.project_name}-streaming"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([{
    name      = "streaming"
    image     = "${aws_ecr_repository.flight_pipeline.repository_url}:latest"
    essential = true
    command   = ["python", "-u", "-m", "streaming.worker", "worker", "-l", "warn"]
    environment = [
      { name = "KAFKA_BOOTSTRAP_SERVERS", value = "${aws_instance.pipeline_server.private_ip}:9092" },
      { name = "S3_BUCKET_NAME", value = var.s3_bucket_name }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "streaming"
      }
    }
  }])
}

resource "aws_ecs_service" "streaming" {
  name            = "${var.project_name}-streaming-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.streaming.arn
  desired_count   = 1 # Can autoscale to X depending on Kafka Partitions
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks_sg.id]
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    assign_public_ip = true
  }
}

# 4. Ingestion Service (OpenSky API Poller) - No Load Balancer needed
resource "aws_ecs_task_definition" "ingestion" {
  family                   = "${var.project_name}-ingestion"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([{
    name      = "ingestion"
    image     = "${aws_ecr_repository.flight_pipeline.repository_url}:latest"
    essential = true
    command   = ["python", "-u", "ingestion/producer.py"]
    environment = [
      { name = "KAFKA_BOOTSTRAP_SERVERS", value = "${aws_instance.pipeline_server.private_ip}:9092" },
      { name = "OPENSKY_API_URL", value = "https://opensky-network.org/api/states/all" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ingestion"
      }
    }
  }])
}

resource "aws_ecs_service" "ingestion" {
  name            = "${var.project_name}-ingestion-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ingestion.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks_sg.id]
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    assign_public_ip = true
  }
}
