# Galactus - Semi-Autonomous Lab Management System

Galactus is a modern, semi-autonomous laboratory management system designed to bridge the gap between human-designed experiments and fully autonomous laboratory operations. It provides a flexible framework for defining task templates, workflow orchestration, and resource management with comprehensive event tracking and analytics.

## Key Features

- **Task Templates**: Reusable task definitions with input/output schemas linked to device types
- **Workflow Management**: DAG-based workflows with samples and task dependencies
- **Device Integration**: Physical devices with location tracking and communication protocols
- **Event-Driven Architecture**: Kafka-based event system for all lab operations
- **Time-Series Analytics**: TimescaleDB integration for comprehensive data analysis
- **RESTful API**: FastAPI-based API for UI and LLM integration
- **Resource Scheduling**: Intelligent scheduling based on task requirements and device availability
- **Job Queue Management**: Celery-based task execution with priority queuing

## Architecture

Galactus is built on a modern tech stack:

- **Backend**: Python with FastAPI, SQLAlchemy, and Pydantic
- **Database**: PostgreSQL with TimescaleDB extension for time-series data
- **Message Queue**: Kafka for event-driven communication
- **Task Queue**: Celery with Redis for task execution
- **Frontend**: React-based web interface (planned)

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL with TimescaleDB extension
- Kafka
- Redis (for Celery)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/galactus.git
   cd galactus
   ```

2. **Install dependencies**
   ```bash
   pip install -e .
   ```

3. **Set up environment variables**
   Create a `.env` file with your configuration:
   ```env
   GALACTUS_POSTGRES_HOST=localhost
   GALACTUS_POSTGRES_DATABASE=galactus
   GALACTUS_POSTGRES_USER=galactus
   GALACTUS_POSTGRES_PASSWORD=password
   GALACTUS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   GALACTUS_REDIS_HOST=localhost
   ```

4. **Initialize the database**
   ```bash
   galactus init-db
   ```

5. **Start the services**
   ```bash
   # Start Kafka consumer
   galactus consume-events

   # Start API server
   galactus api

   # Start task worker (in another terminal)
   galactus launch-worker

   # Start scheduler (in another terminal)
   galactus launch-scheduler
   ```

## Quick Start

### 1. Define Device Types

```python
from galactus_core.models.device import DeviceTypeCreate

# Create a furnace device type
furnace_type = DeviceTypeCreate(
    name="tube_furnace",
    category="furnace",
    subcategory="tube_furnace",
    protocol="modbus",
    capabilities=["temperature_control", "atmosphere_control"],
    specifications={
        "max_temperature": 1200.0,
        "heating_rate": 10.0,
        "cooling_rate": 5.0,
        "atmosphere_options": ["air", "nitrogen", "argon"]
    }
)
```

### 2. Create Task Templates

```python
from galactus_core.models.task import TaskTemplateCreate

# Create a heating task template
heating_template = TaskTemplateCreate(
    name="heating_task",
    description="Heat a sample to target temperature",
    category="thermal_processing",
    input_schema={
        "sample": {"type": "string", "required": True, "description": "Sample name"},
        "target_temperature": {"type": "number", "required": True, "description": "Target temperature in °C"},
        "duration": {"type": "integer", "required": True, "description": "Duration in minutes"}
    },
    output_schema={
        "final_temperature": {"type": "number", "required": True, "description": "Final temperature"},
        "temperature_profile": {"type": "array", "required": True, "description": "Temperature over time"}
    },
    required_device_types=[furnace_type_id],
    estimated_duration=30,  # 30 minutes
    implementation_class="examples.galactus_example.tasks.heating.HeatingTask"
)
```

### 3. Define Workflows

```python
from galactus_core.models.workflow import WorkflowCreate, SampleCreate

# Create samples
samples = [
    SampleCreate(
        name="sample_1",
        composition={"Si": 0.5, "Ge": 0.5},
        properties={"target_density": 3.2}
    ),
    SampleCreate(
        name="sample_2",
        composition={"Si": 0.7, "Ge": 0.3},
        properties={"target_density": 2.8}
    )
]

# Create workflow
workflow = WorkflowCreate(
    name="thermal_annealing_study",
    description="Study the effect of annealing temperature on sample properties",
    task_graph={
        "tasks": {
            "heat_sample_1": {
                "type": "heating_task",
                "parameters": {
                    "target_temperature": 800,
                    "duration": 60
                },
                "samples": ["sample_1"]
            },
            "heat_sample_2": {
                "type": "heating_task",
                "parameters": {
                    "target_temperature": 900,
                    "duration": 60
                },
                "samples": ["sample_2"]
            }
        },
        "dependencies": {
            "heat_sample_1": [],
            "heat_sample_2": []
        }
    },
    sample_count=2,
    samples=samples
)
```

### 4. Submit and Execute

```python
from galactus_core.api.workflow import submit_workflow
from galactus_core.api.job import create_job

# Submit workflow
workflow_response = submit_workflow(workflow)

# Create and queue job
job = create_job(
    workflow_id=workflow_response.id,
    priority=2,
    max_concurrent_tasks=2
)

print(f"Job {job.id} created and queued for execution")
```

## Event System

Galactus uses Kafka to emit events for all major operations:

### Event Types

- `task.created` - New task created
- `task.started` - Task execution started
- `task.completed` - Task completed successfully
- `task.failed` - Task failed
- `workflow.created` - New workflow created
- `workflow.started` - Workflow execution started
- `device.status_changed` - Device status changed
- `job.queued` - Job queued for execution
- `sample.position_changed` - Sample moved to new position

### Consuming Events

```python
from galactus_core.events.consumer import EventConsumer

consumer = EventConsumer()

def handle_task_completion(event):
    print(f"Task {event.entity_id} completed: {event.data}")

consumer.register_handler("task.completed", handle_task_completion)
consumer.subscribe_to_entity_events("task", ["completed", "failed"])
consumer.start()
```

## API Reference

Galactus provides a RESTful API for all operations:

### Task Templates
- `GET /api/task-templates` - List all task templates
- `POST /api/task-templates` - Create new task template
- `GET /api/task-templates/{id}` - Get specific template
- `PUT /api/task-templates/{id}` - Update template
- `DELETE /api/task-templates/{id}` - Delete template

### Workflows
- `GET /api/workflows` - List workflows
- `POST /api/workflows` - Create workflow
- `GET /api/workflows/{id}` - Get workflow details
- `PUT /api/workflows/{id}/status` - Update workflow status

### Jobs
- `GET /api/jobs` - List jobs
- `POST /api/jobs` - Create and queue job
- `GET /api/jobs/{id}` - Get job status
- `PUT /api/jobs/{id}/cancel` - Cancel job

### Devices
- `GET /api/devices` - List devices
- `POST /api/devices` - Register device
- `GET /api/devices/{id}/status` - Get device status
- `PUT /api/devices/{id}/status` - Update device status

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black galactus_core/

# Lint code
ruff galactus_core/

# Type checking
mypy galactus_core/
```

### Database Migrations

```bash
# Create new migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Configuration

Galactus is configured through environment variables and a configuration file. See `galactus_core/database/config.py` for available options.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Galactus draws inspiration from the ALabOS project while incorporating modern architectural patterns and technologies for improved scalability and flexibility in semi-autonomous laboratory environments.
