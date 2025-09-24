"""
Example furnace device implementation for alabos.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from alabos_core.models.device import Device, DeviceStatus, DeviceCapability
from alabos_core.models.base import BaseDBModel


class Furnace(Device):
    """Example furnace device implementation."""

    def __init__(
        self,
        name: str,
        max_temperature: float = 1200.0,
        heating_rate: float = 10.0,  # °C/min
        cooling_rate: float = 5.0,   # °C/min
        *args,
        **kwargs
    ):
        super().__init__(name, *args, **kwargs)
        self.max_temperature = max_temperature
        self.heating_rate = heating_rate
        self.cooling_rate = cooling_rate
        self.current_temperature = 25.0  # Room temperature
        self.target_temperature = 25.0
        self.is_heating = False
        self.is_door_open = False

    @property
    def description(self) -> str:
        return f"Furnace (max: {self.max_temperature}°C, heating: {self.heating_rate}°C/min)"

    @property
    def sample_positions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": f"{self.name}_inside",
                "description": "Inside the furnace chamber",
                "number": 8,
                "max_temperature": self.max_temperature,
            }
        ]

    @property
    def capabilities(self) -> List[str]:
        return [
            DeviceCapability.TEMPERATURE_CONTROL,
            DeviceCapability.ATMOSPHERE_CONTROL,
        ]

    def is_running(self) -> bool:
        return self.is_heating or abs(self.current_temperature - self.target_temperature) > 1.0

    def connect(self):
        """Connect to the furnace hardware."""
        print(f"Connecting to furnace {self.name}...")
        # Implementation would connect to actual hardware
        time.sleep(1)
        print(f"Furnace {self.name} connected")

    def disconnect(self):
        """Disconnect from the furnace hardware."""
        print(f"Disconnecting from furnace {self.name}...")
        # Implementation would disconnect from hardware
        print(f"Furnace {self.name} disconnected")

    def set_temperature(self, temperature: float, rate: Optional[float] = None):
        """Set target temperature."""
        if temperature > self.max_temperature:
            raise ValueError(f"Temperature {temperature}°C exceeds maximum {self.max_temperature}°C")

        self.target_temperature = temperature
        self.heating_rate = rate or self.heating_rate

        # Emit event
        from alabos_core.events.producer import event_producer
        event_producer.send_device_event(
            device_id=self.id,
            event_type="status_changed",
            data={
                "target_temperature": temperature,
                "heating_rate": self.heating_rate,
                "status": "heating" if temperature > self.current_temperature else "cooling"
            }
        )

    def get_temperature(self) -> float:
        """Get current temperature."""
        return self.current_temperature

    def open_door(self):
        """Open the furnace door."""
        self.is_door_open = True
        print(f"Furnace {self.name} door opened")

    def close_door(self):
        """Close the furnace door."""
        self.is_door_open = False
        print(f"Furnace {self.name} door closed")

    def run_program(self, program: Dict[str, Any]):
        """Run a temperature program."""
        print(f"Running program on furnace {self.name}: {program}")

        for step in program.get("steps", []):
            target_temp = step.get("temperature")
            duration = step.get("duration", 0)
            atmosphere = step.get("atmosphere", "air")

            self.set_temperature(target_temp)

            # Simulate heating/cooling
            temp_diff = target_temp - self.current_temperature
            rate = self.heating_rate if temp_diff > 0 else self.cooling_rate
            estimated_time = abs(temp_diff) / rate

            print(f"Heating to {target_temp}°C (estimated: {estimated_time".1f"} min)")

            # Simulate the process
            time.sleep(min(duration, 2))  # Simulate with max 2 seconds

            self.current_temperature = target_temp
            print(f"Reached {target_temp}°C")


def create_furnace(
    name: str,
    location: str = "Lab 1",
    max_temperature: float = 1200.0,
    **kwargs
) -> Furnace:
    """Factory function to create a furnace device."""
    furnace = Furnace(
        name=name,
        max_temperature=max_temperature,
        **kwargs
    )

    # Set device properties
    furnace.ip_address = kwargs.get("ip_address", "192.168.1.100")
    furnace.port = kwargs.get("port", 502)
    furnace.status = DeviceStatus.ONLINE

    return furnace
