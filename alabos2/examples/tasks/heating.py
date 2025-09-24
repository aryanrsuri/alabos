"""Example heating task implementation for alabos."""

import time
from typing import Any

from alabos_core.models.task import BaseTask


class HeatingTask(BaseTask):
    """Task for heating samples in a furnace."""

    def __init__(
        self,
        sample: str,
        target_temperature: float,
        duration: int,  # minutes
        atmosphere: str = "air",
        heating_rate: float = 10.0,  # °C/min
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.sample = sample
        self.target_temperature = target_temperature
        self.duration = duration
        self.atmosphere = atmosphere
        self.heating_rate = heating_rate

    @property
    def result_specification(self):
        """Define the expected result structure."""
        from pydantic import BaseModel

        class HeatingResult(BaseModel):
            sample_id: str
            target_temperature: float
            actual_temperature: float
            duration: int
            atmosphere: str
            final_temperature: float
            temperature_profile: list[dict[str, Any]]

        return HeatingResult

    def validate(self) -> bool:
        """Validate task parameters."""
        if self.target_temperature <= 0:
            self.set_message("Target temperature must be positive")
            return False

        if self.duration <= 0:
            self.set_message("Duration must be positive")
            return False

        if self.atmosphere not in ["air", "nitrogen", "argon", "vacuum"]:
            self.set_message("Invalid atmosphere specified")
            return False

        return True

    def run(self):
        """Execute the heating task."""
        # Get the sample
        sample = self.lab_view.get_sample(self.sample)
        sample_id = sample.sample_id

        # Request furnace resource
        with self.lab_view.request_resources({Furnace: ["$.inside", 1]}) as (
            devices,
            sample_positions,
        ):
            furnace = devices[Furnace]

            # Move sample to furnace if not already there
            if sample.position != f"{furnace.name}_inside":
                # This would trigger a movement task in a real implementation
                self.lab_view.move_sample(
                    sample=sample_id, position=f"{furnace.name}_inside"
                )

            # Close furnace door
            furnace.close_door()

            # Set up heating program
            program = {
                "steps": [
                    {
                        "temperature": self.target_temperature,
                        "duration": self.duration * 60,  # Convert to seconds
                        "atmosphere": self.atmosphere,
                        "ramp_rate": self.heating_rate,
                    }
                ]
            }

            # Run the heating program
            furnace.run_program(program)

            # Log temperature data during heating
            temperature_profile = []
            start_time = time.time()

            while furnace.is_running():
                current_temp = furnace.get_temperature()
                elapsed = time.time() - start_time

                temperature_profile.append(
                    {
                        "time": elapsed,
                        "temperature": current_temp,
                        "target": self.target_temperature,
                    }
                )

                # Log device signal
                self.logger.log_device_signal(
                    {
                        "device": furnace.name,
                        "temperature": current_temp,
                        "target_temperature": self.target_temperature,
                        "elapsed_time": elapsed,
                    }
                )

                time.sleep(10)  # Log every 10 seconds

            # Get final temperature
            final_temperature = furnace.get_temperature()

            # Create result
            result = {
                "sample_id": str(sample_id),
                "target_temperature": self.target_temperature,
                "actual_temperature": final_temperature,
                "duration": self.duration,
                "atmosphere": self.atmosphere,
                "final_temperature": final_temperature,
                "temperature_profile": temperature_profile,
            }

            return result


# Import required for the task to work
from alabos_core.models.device import Device


class Furnace(Device):
    """Mock furnace device for the heating task."""

    pass


def create_heating_task_template():
    """Create a heating task template."""
    from alabos_core.models.task import TaskTemplateCreate

    template = TaskTemplateCreate(
        name="heating_task",
        description="Heat a sample to a target temperature for a specified duration",
        category="thermal_processing",
        input_schema={
            "sample": {
                "type": "string",
                "required": True,
                "description": "Sample name",
            },
            "target_temperature": {
                "type": "number",
                "required": True,
                "description": "Target temperature in °C",
            },
            "duration": {
                "type": "integer",
                "required": True,
                "description": "Duration in minutes",
            },
            "atmosphere": {
                "type": "string",
                "required": False,
                "default": "air",
                "description": "Atmosphere (air, nitrogen, argon, vacuum)",
            },
            "heating_rate": {
                "type": "number",
                "required": False,
                "default": 10.0,
                "description": "Heating rate in °C/min",
            },
        },
        output_schema={
            "sample_id": {
                "type": "string",
                "required": True,
                "description": "Sample identifier",
            },
            "target_temperature": {
                "type": "number",
                "required": True,
                "description": "Target temperature in °C",
            },
            "actual_temperature": {
                "type": "number",
                "required": True,
                "description": "Actual final temperature in °C",
            },
            "duration": {
                "type": "integer",
                "required": True,
                "description": "Actual duration in minutes",
            },
            "atmosphere": {
                "type": "string",
                "required": True,
                "description": "Atmosphere used",
            },
            "final_temperature": {
                "type": "number",
                "required": True,
                "description": "Final temperature in °C",
            },
            "temperature_profile": {
                "type": "array",
                "required": True,
                "description": "Temperature profile during heating",
            },
        },
        required_device_types=[],  # Will be set when device types are created
        estimated_duration=30,  # 30 minutes estimated
        max_retries=2,
        retry_delay=300,  # 5 minutes between retries
        timeout=3600,  # 1 hour timeout
        requires_user_input=False,
        implementation_class="examples.alabos_example.tasks.heating.HeatingTask",
    )

    return template
