"""Scenario selection and lifecycle helpers."""

from __future__ import annotations

from typing import Dict, List

from scenarios import ScenarioDefinition, build_scenarios


class ScenarioManager:
    """Keeps track of the currently selected scenario."""

    def __init__(self) -> None:
        self._scenarios: Dict[str, ScenarioDefinition] = build_scenarios()
        self._names: List[str] = list(self._scenarios.keys())
        self._index = 0

    def names(self) -> List[str]:
        """Return the scenario names in UI order."""

        return list(self._names)

    def current(self) -> ScenarioDefinition:
        """Return the currently selected scenario."""

        return self._scenarios[self._names[self._index]]

    def set_current(self, name: str) -> ScenarioDefinition:
        """Select a scenario by name."""

        if name not in self._scenarios:
            raise KeyError(f"Unknown scenario '{name}'.")
        self._index = self._names.index(name)
        return self.current()

    def next(self) -> ScenarioDefinition:
        """Advance to the next scenario."""

        self._index = (self._index + 1) % len(self._names)
        return self.current()

    def previous(self) -> ScenarioDefinition:
        """Go back to the previous scenario."""

        self._index = (self._index - 1) % len(self._names)
        return self.current()
