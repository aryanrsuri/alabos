"""Initial migration for alabos database.

Revision ID: 001
Revises: None
Create Date: 2024-09-24 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# alembic revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")


    op.create_table(
        "task_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "version", sa.String(length=50), server_default="1.0.0", nullable=False
        ),
        sa.Column(
            "status", sa.String(length=20), server_default="active", nullable=False
        ),
        sa.Column(
            "input_schema",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "output_schema",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "parameter_schema",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "required_device_types",
            postgresql.JSON(asdict=True),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "preferred_device_types",
            postgresql.JSON(asdict=True),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("estimated_duration", sa.Integer(), nullable=True),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("retry_delay", sa.Integer(), server_default="60", nullable=False),
        sa.Column("timeout", sa.Integer(), nullable=True),
        sa.Column(
            "requires_user_input",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("implementation_class", sa.String(length=500), nullable=True),
        sa.Column("docker_image", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_task_templates_name"), "task_templates", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_task_templates_status"), "task_templates", ["status"], unique=False
    )


    op.create_table(
        "device_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("subcategory", sa.String(length=100), nullable=True),
        sa.Column("protocol", sa.String(length=50), nullable=False),
        sa.Column(
            "protocol_config_schema",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "capabilities",
            postgresql.JSON(asdict=True),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "specifications",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("max_sample_capacity", sa.Integer(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=True),
        sa.Column("avg_setup_time", sa.Integer(), nullable=True),
        sa.Column("avg_execution_time", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_device_types_category"), "device_types", ["category"], unique=False
    )
    op.create_index(
        op.f("ix_device_types_name"), "device_types", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_device_types_subcategory"),
        "device_types",
        ["subcategory"],
        unique=False,
    )


    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("location_type", sa.String(length=50), nullable=False),
        sa.Column("coordinates", postgresql.JSONB(asdict=True), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column(
            "environmental_conditions",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "safety_requirements",
            postgresql.JSON(asdict=True),
            server_default="[]",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["locations.id"],
        ),
    )
    op.create_index(
        op.f("ix_locations_location_type"), "locations", ["location_type"], unique=False
    )
    op.create_index(op.f("ix_locations_name"), "locations", ["name"], unique=False)


    op.create_table(
        "task_template_device_types",
        sa.Column("task_template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["device_type_id"],
            ["device_types.id"],
        ),
        sa.ForeignKeyConstraint(
            ["task_template_id"],
            ["task_templates.id"],
        ),
    )
    op.create_index(
        "ix_task_template_device_types_task_template_id",
        "task_template_device_types",
        ["task_template_id"],
        unique=False,
    )
    op.create_index(
        "ix_task_template_device_types_device_type_id",
        "task_template_device_types",
        ["device_type_id"],
        unique=False,
    )


    op.create_table(
        "workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "version", sa.String(length=50), server_default="1.0.0", nullable=False
        ),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="active", nullable=False
        ),
        sa.Column(
            "task_graph_template",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "default_sample_count", sa.Integer(), server_default="1", nullable=False
        ),
        sa.Column(
            "max_sample_count", sa.Integer(), server_default="100", nullable=False
        ),
        sa.Column(
            "variable_parameters",
            postgresql.JSON(asdict=True),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "default_max_concurrent_tasks",
            sa.Integer(),
            server_default="5",
            nullable=False,
        ),
        sa.Column(
            "optimization_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("optimization_targets", postgresql.JSONB(asdict=True), nullable=True),
        sa.Column("implementation_class", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_templates_category"),
        "workflow_templates",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_templates_name"), "workflow_templates", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_workflow_templates_status"),
        "workflow_templates",
        ["status"],
        unique=False,
    )


    op.create_table(
        "workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "version", sa.String(length=50), server_default="1.0.0", nullable=False
        ),
        sa.Column(
            "status", sa.String(length=20), server_default="draft", nullable=False
        ),
        sa.Column(
            "task_graph",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("sample_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "max_concurrent_tasks", sa.Integer(), server_default="5", nullable=False
        ),
        sa.Column(
            "start_conditions",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "stop_conditions",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("optimization_targets", postgresql.JSONB(asdict=True), nullable=True),
        sa.Column(
            "progress_percentage", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "current_task_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "completed_task_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "estimated_completion", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["workflow_templates.id"],
        ),
    )
    op.create_index(op.f("ix_workflows_name"), "workflows", ["name"], unique=False)
    op.create_index(op.f("ix_workflows_status"), "workflows", ["status"], unique=False)


    op.create_table(
        "samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", sa.String(length=100), nullable=True),
        sa.Column(
            "composition",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "properties",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("target_properties", postgresql.JSONB(asdict=True), nullable=True),
        sa.Column("current_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("position", sa.String(length=500), nullable=True),
        sa.Column(
            "status", sa.String(length=50), server_default="initialized", nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["current_task_id"],
            ["tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
        ),
    )
    op.create_index(op.f("ix_samples_batch_id"), "samples", ["batch_id"], unique=False)
    op.create_index(op.f("ix_samples_name"), "samples", ["name"], unique=False)
    op.create_index(op.f("ix_samples_status"), "samples", ["status"], unique=False)


    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_by", sa.String(length=255), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default="created", nullable=False
        ),
        sa.Column("priority", sa.Integer(), server_default="2", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "max_concurrent_tasks", sa.Integer(), server_default="5", nullable=False
        ),
        sa.Column(
            "resource_requirements",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("allocated_resources", postgresql.JSONB(asdict=True), nullable=True),
        sa.Column(
            "progress_percentage", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("total_tasks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_tasks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_tasks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cancelled_tasks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("queued_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "estimated_completion", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("actual_duration", sa.Integer(), nullable=True),
        sa.Column(
            "execution_mode",
            sa.String(length=50),
            server_default="normal",
            nullable=False,
        ),
        sa.Column(
            "execution_config",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("results", postgresql.JSONB(asdict=True), nullable=True),
        sa.Column(
            "artifacts",
            postgresql.JSON(asdict=True),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "logs", postgresql.JSON(asdict=True), server_default="[]", nullable=False
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_retry_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
        ),
    )
    op.create_index(op.f("ix_jobs_name"), "jobs", ["name"], unique=False)
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)


    op.create_table(
        "job_queues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "queue_name",
            sa.String(length=100),
            server_default="default",
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), server_default="2", nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "queued_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "estimated_start", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("actual_start", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resource_reservation", postgresql.JSONB(asdict=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
        ),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index(
        "ix_job_queues_queue_priority_time",
        "job_queues",
        ["queue_name", "priority", "queued_at"],
        unique=False,
    )

    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("device_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("serial_number", sa.String(length=100), nullable=True),
        sa.Column("model_number", sa.String(length=100), nullable=True),
        sa.Column("manufacturer", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("connection_string", sa.String(length=500), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default="offline", nullable=False
        ),
        sa.Column(
            "is_available", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("current_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_seen", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("uptime_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "total_runtime_seconds", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "config", postgresql.JSONB(asdict=True), server_default="{}", nullable=False
        ),
        sa.Column("calibration_data", postgresql.JSONB(asdict=True), nullable=True),
        sa.Column(
            "sample_positions",
            postgresql.JSON(asdict=True),
            server_default="[]",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["current_task_id"],
            ["tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["device_type_id"],
            ["device_types.id"],
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
        ),
        sa.UniqueConstraint("serial_number"),
    )
    op.create_index(op.f("ix_devices_name"), "devices", ["name"], unique=False)
    op.create_index(op.f("ix_devices_status"), "devices", ["status"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("task_template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="pending", nullable=False
        ),
        sa.Column("priority", sa.Integer(), server_default="2", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "inputs", postgresql.JSONB(asdict=True), server_default="{}", nullable=False
        ),
        sa.Column("outputs", postgresql.JSONB(asdict=True), nullable=True),
        sa.Column("result_data", postgresql.JSONB(asdict=True), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("execution_time", sa.Integer(), nullable=True),
        sa.Column("assigned_device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "prev_tasks",
            postgresql.JSON(asdict=True),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "next_tasks",
            postgresql.JSON(asdict=True),
            server_default="[]",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["assigned_device_id"],
            ["devices.id"],
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["task_template_id"],
            ["task_templates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
        ),
    )
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)




    op.create_table(
        "kafka_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(asdict=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(asdict=True), nullable=False),
        sa.Column(
            "processed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kafka_events_time_type",
        "kafka_events",
        ["created_at", "event_type"],
        unique=False,
    )
    op.create_index(
        "ix_kafka_events_entity",
        "kafka_events",
        ["entity_id", "entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_kafka_events_event_type"), "kafka_events", ["event_type"], unique=False
    )


    op.execute(
        "SELECT create_hypertable('kafka_events', 'created_at', if_not_exists => TRUE)"
    )


def downgrade() -> None:
    """Remove all created tables."""
    op.execute("DROP TABLE IF EXISTS kafka_events CASCADE")
    op.execute("DROP TABLE IF EXISTS devices CASCADE")
    op.execute("DROP TABLE IF EXISTS tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS job_queues CASCADE")
    op.execute("DROP TABLE IF EXISTS jobs CASCADE")
    op.execute("DROP TABLE IF EXISTS samples CASCADE")
    op.execute("DROP TABLE IF EXISTS workflows CASCADE")
    op.execute("DROP TABLE IF EXISTS workflow_templates CASCADE")
    op.execute("DROP TABLE IF EXISTS task_template_device_types CASCADE")
    op.execute("DROP TABLE IF EXISTS locations CASCADE")
    op.execute("DROP TABLE IF EXISTS device_types CASCADE")
    op.execute("DROP TABLE IF EXISTS task_templates CASCADE")
