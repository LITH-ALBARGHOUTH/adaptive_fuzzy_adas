"""Manual player input sampling for the 3D demo."""

from __future__ import annotations

from ursina import held_keys

from vehicle import ControlCommand


def _move_towards(current: float, target: float, rate: float) -> float:
    if current < target:
        return min(current + rate, target)
    return max(current - rate, target)


class InputController:
    """Samples smooth arcade-style manual commands from the keyboard."""

    def __init__(self) -> None:
        self._throttle = 0.0
        self._brake = 0.0
        self._steering = 0.0

    def reset(self) -> None:
        """Reset the smoothed control state."""

        self._throttle = 0.0
        self._brake = 0.0
        self._steering = 0.0

    def sample(self, dt: float) -> ControlCommand:
        """Return a smoothed control command based on WASD input."""

        throttle_target = 1.0 if held_keys["w"] or held_keys["up arrow"] else 0.0
        brake_target = 1.0 if held_keys["s"] or held_keys["down arrow"] else 0.0
        steering_target = 0.0
        if held_keys["a"] or held_keys["left arrow"]:
            steering_target -= 1.0
        if held_keys["d"] or held_keys["right arrow"]:
            steering_target += 1.0

        self._throttle = _move_towards(self._throttle, throttle_target, 3.6 * dt)
        self._brake = _move_towards(self._brake, brake_target, 4.5 * dt)
        self._steering = _move_towards(self._steering, steering_target, 5.5 * dt)

        if brake_target > 0.0:
            self._throttle = min(self._throttle, 0.2)

        return ControlCommand(
            throttle=max(0.0, min(1.0, self._throttle)),
            brake=max(0.0, min(1.0, self._brake)),
            steering=max(-1.0, min(1.0, self._steering)),
        )
