"""Shared Mamdani fuzzy-inference infrastructure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import skfuzzy as fuzz

from config import MembershipSpec, VariableConfig


@dataclass
class BuiltVariable:
    """Built variable with universe and discrete membership arrays."""

    name: str
    universe: np.ndarray
    terms: Dict[str, np.ndarray]
    specs: Dict[str, MembershipSpec]


@dataclass
class FuzzyRule:
    """Simple AND-based Mamdani rule."""

    name: str
    antecedents: Tuple[Tuple[str, str], ...]
    consequent: Tuple[str, str]
    description: str
    weight: float = 1.0


@dataclass
class RuleActivation:
    """Rule activation detail for explainability and plotting."""

    rule_name: str
    description: str
    output_name: str
    consequent_label: str
    antecedent_memberships: Dict[str, float]
    firing_strength: float
    clipped_membership: np.ndarray


@dataclass
class OutputExplanation:
    """Explainable result for a single output variable."""

    output_name: str
    crisp_value: float
    dominant_label: str
    label_memberships: Dict[str, float]
    aggregated_membership: np.ndarray
    activations: List[RuleActivation]
    universe: np.ndarray
    terms: Dict[str, np.ndarray]
    used_default_output: bool

    @property
    def max_firing_strength(self) -> float:
        """Return the strongest rule activation for this output."""

        if not self.activations:
            return 0.0
        return max(activation.firing_strength for activation in self.activations)


@dataclass
class EngineResult:
    """Full explainable output for one fuzzy engine."""

    engine_name: str
    input_values: Dict[str, float]
    clipped_inputs: Dict[str, float]
    input_memberships: Dict[str, Dict[str, float]]
    outputs: Dict[str, OutputExplanation]

    @property
    def crisp_outputs(self) -> Dict[str, float]:
        return {name: explanation.crisp_value for name, explanation in self.outputs.items()}

    @property
    def used_default_output(self) -> bool:
        """Return True if any output fell back to a default value."""

        return any(explanation.used_default_output for explanation in self.outputs.values())

    def output(self, output_name: str) -> OutputExplanation:
        return self.outputs[output_name]


def build_membership_array(universe: np.ndarray, spec: MembershipSpec) -> np.ndarray:
    """Create a discrete membership array from a spec."""

    if spec.shape == "tri":
        return fuzz.trimf(universe, spec.params)
    if spec.shape == "trap":
        return fuzz.trapmf(universe, spec.params)
    raise ValueError(f"Unsupported membership shape: {spec.shape}")


class MamdaniEngine:
    """Reusable Mamdani inference engine with centroid defuzzification."""

    def __init__(
        self,
        name: str,
        input_configs: Dict[str, VariableConfig],
        output_configs: Dict[str, VariableConfig],
        rules: Dict[str, List[FuzzyRule]],
        default_outputs: Dict[str, float],
    ) -> None:
        self.name = name
        self.input_variables = self._build_variables(input_configs)
        self.output_variables = self._build_variables(output_configs)
        self.rules = rules
        self.default_outputs = default_outputs
        self._validate_rules()

    @staticmethod
    def _build_variables(configs: Dict[str, VariableConfig]) -> Dict[str, BuiltVariable]:
        built: Dict[str, BuiltVariable] = {}
        for name, config in configs.items():
            built[name] = BuiltVariable(
                name=name,
                universe=config.universe,
                terms={
                    label: build_membership_array(config.universe, spec)
                    for label, spec in config.labels.items()
                },
                specs=config.labels,
            )
        return built

    def _validate_rules(self) -> None:
        """Validate rule references eagerly so broken configurations fail fast."""

        for output_name, output_variable in self.output_variables.items():
            if output_name not in self.rules:
                raise ValueError(
                    f"Engine '{self.name}' is missing a rule list for output '{output_name}'."
                )
            if output_name not in self.default_outputs:
                raise ValueError(
                    f"Engine '{self.name}' is missing a default value for output '{output_name}'."
                )

            for rule in self.rules[output_name]:
                if not 0.0 <= rule.weight <= 1.0:
                    raise ValueError(
                        f"Rule '{rule.name}' in engine '{self.name}' has invalid weight {rule.weight}."
                    )

                consequent_output_name, consequent_label = rule.consequent
                if consequent_output_name != output_name:
                    raise ValueError(
                        f"Rule '{rule.name}' targets '{consequent_output_name}' but is registered "
                        f"under output '{output_name}'."
                    )
                if consequent_label not in output_variable.terms:
                    raise ValueError(
                        f"Rule '{rule.name}' in engine '{self.name}' references unknown consequent "
                        f"label '{consequent_label}' for output '{output_name}'."
                    )

                for variable_name, label_name in rule.antecedents:
                    if variable_name not in self.input_variables:
                        raise ValueError(
                            f"Rule '{rule.name}' in engine '{self.name}' references unknown input "
                            f"variable '{variable_name}'."
                        )
                    if label_name not in self.input_variables[variable_name].terms:
                        raise ValueError(
                            f"Rule '{rule.name}' in engine '{self.name}' references unknown label "
                            f"'{label_name}' for input '{variable_name}'."
                        )

    def fuzzify_inputs(
        self,
        inputs: Dict[str, float],
    ) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
        """Clip and fuzzify all input values."""

        clipped_inputs: Dict[str, float] = {}
        memberships: Dict[str, Dict[str, float]] = {}

        for name, variable in self.input_variables.items():
            if name not in inputs:
                raise KeyError(f"Missing required input '{name}' for engine '{self.name}'.")

            value = float(inputs[name])
            lower = float(variable.universe[0])
            upper = float(variable.universe[-1])
            clipped = float(np.clip(value, lower, upper))
            clipped_inputs[name] = clipped
            memberships[name] = {
                label: float(fuzz.interp_membership(variable.universe, term, clipped))
                for label, term in variable.terms.items()
            }

        return clipped_inputs, memberships

    def compute(self, inputs: Dict[str, float]) -> EngineResult:
        """Run Mamdani inference and return explainable results."""

        clipped_inputs, input_memberships = self.fuzzify_inputs(inputs)
        outputs: Dict[str, OutputExplanation] = {}

        for output_name, output_variable in self.output_variables.items():
            aggregated = np.zeros_like(output_variable.universe, dtype=float)
            activations: List[RuleActivation] = []

            for rule in self.rules[output_name]:
                antecedent_memberships = {
                    f"{var_name}.{label}": input_memberships[var_name][label]
                    for var_name, label in rule.antecedents
                }
                firing_strength = (
                    min(antecedent_memberships.values()) * rule.weight
                    if antecedent_memberships
                    else 0.0
                )
                consequent_label = rule.consequent[1]
                clipped_membership = np.fmin(
                    firing_strength,
                    output_variable.terms[consequent_label],
                )
                aggregated = np.fmax(aggregated, clipped_membership)
                activations.append(
                    RuleActivation(
                        rule_name=rule.name,
                        description=rule.description,
                        output_name=output_name,
                        consequent_label=consequent_label,
                        antecedent_memberships=antecedent_memberships,
                        firing_strength=float(firing_strength),
                        clipped_membership=clipped_membership,
                    )
                )

            used_default_output = float(np.max(aggregated)) <= 1e-9
            if used_default_output:
                crisp_value = self.default_outputs[output_name]
            else:
                crisp_value = float(fuzz.defuzz(output_variable.universe, aggregated, "centroid"))

            label_memberships = {
                label: float(fuzz.interp_membership(output_variable.universe, term, crisp_value))
                for label, term in output_variable.terms.items()
            }
            dominant_label = max(label_memberships, key=label_memberships.get)

            outputs[output_name] = OutputExplanation(
                output_name=output_name,
                crisp_value=crisp_value,
                dominant_label=dominant_label,
                label_memberships=label_memberships,
                aggregated_membership=aggregated,
                activations=activations,
                universe=output_variable.universe,
                terms=output_variable.terms,
                used_default_output=used_default_output,
            )

        return EngineResult(
            engine_name=self.name,
            input_values={name: float(value) for name, value in inputs.items()},
            clipped_inputs=clipped_inputs,
            input_memberships=input_memberships,
            outputs=outputs,
        )
