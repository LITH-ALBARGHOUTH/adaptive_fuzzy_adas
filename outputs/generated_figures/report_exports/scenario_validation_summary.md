# Scenario Validation Summary

This file compares expected scenario behavior against the measured simulation outputs.

| Scenario | Expected Behavior | Max Risk | Peak Brake | Peak Abs Steering | Min Distance | RMS Lane | Collision | Lane Departure | Overall |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| normal_driving | Low-risk, comfort-oriented cruising with only light braking. | 33.37 | 0.18 | 0.03 | 45.00 | 0.033 | False | False | True |
| high_speed_short_distance | Safety-dominant braking should emerge while avoiding collision. | 75.91 | 0.84 | 0.00 | 15.98 | 0.025 | False | False | True |
| large_lane_deviation | Strong lateral correction should dominate without leaving the lane. | 33.37 | 0.40 | 0.80 | 59.78 | 0.215 | False | False | True |
| poor_road_condition | Road degradation should raise risk and moderate throttle usage. | 59.19 | 0.20 | 0.32 | 37.03 | 0.018 | False | False | True |
| conflicting_tradeoff | Competing objectives should produce both notable braking and steering activity. | 74.46 | 0.75 | 0.53 | 20.17 | 0.182 | False | False | True |
| boundary_stop_and_go | The controller should remain stable at low speed and come close to a stop if needed. | 59.59 | 0.20 | 0.00 | 9.77 | 0.000 | False | False | True |
| boundary_open_road | Open-road comfort bias should keep throttle healthy and braking light. | 59.20 | 0.18 | 0.28 | 39.15 | 0.015 | False | False | True |

## normal_driving

| Check | Actual | Comparator | Target | Passed |
|---|---:|---|---:|---|
| max risk should stay below target | 33.372 | <= | 40.0 | True |
| peak brake should stay below target | 0.1821 | <= | 0.25 | True |
| peak throttle should reach target | 0.6655 | >= | 0.5 | True |
| RMS lane deviation should stay below target | 0.0331 | <= | 0.1 | True |
| minimum distance should stay above target | 45.0 | >= | 35.0 | True |
| collision expectation | False | == | False | True |
| lane departure expectation | False | == | False | True |

## high_speed_short_distance

| Check | Actual | Comparator | Target | Passed |
|---|---:|---|---:|---|
| max risk should be high enough | 75.9071 | >= | 65.0 | True |
| peak brake should reach target | 0.8372 | >= | 0.7 | True |
| peak throttle should stay below target | 0.25 | <= | 0.3 | True |
| minimum distance should stay above target | 15.9779 | >= | 10.0 | True |
| collision expectation | False | == | False | True |
| lane departure expectation | False | == | False | True |

## large_lane_deviation

| Check | Actual | Comparator | Target | Passed |
|---|---:|---|---:|---|
| peak steering magnitude should reach target | 0.7983 | >= | 0.7 | True |
| RMS lane deviation should stay below target | 0.2155 | <= | 0.3 | True |
| minimum distance should stay above target | 59.7764 | >= | 50.0 | True |
| collision expectation | False | == | False | True |
| lane departure expectation | False | == | False | True |

## poor_road_condition

| Check | Actual | Comparator | Target | Passed |
|---|---:|---|---:|---|
| max risk should be high enough | 59.1859 | >= | 50.0 | True |
| peak throttle should stay below target | 0.25 | <= | 0.3 | True |
| minimum distance should stay above target | 37.0333 | >= | 30.0 | True |
| collision expectation | False | == | False | True |
| lane departure expectation | False | == | False | True |

## conflicting_tradeoff

| Check | Actual | Comparator | Target | Passed |
|---|---:|---|---:|---|
| max risk should be high enough | 74.4602 | >= | 65.0 | True |
| peak brake should reach target | 0.7495 | >= | 0.6 | True |
| peak steering magnitude should reach target | 0.5301 | >= | 0.45 | True |
| minimum distance should stay above target | 20.1671 | >= | 15.0 | True |
| collision expectation | False | == | False | True |
| lane departure expectation | False | == | False | True |

## boundary_stop_and_go

| Check | Actual | Comparator | Target | Passed |
|---|---:|---|---:|---|
| max risk should be high enough | 59.5858 | >= | 50.0 | True |
| peak throttle should stay below target | 0.2115 | <= | 0.25 | True |
| peak steering magnitude should stay below target | 0.0 | <= | 0.1 | True |
| minimum distance should stay above target | 9.7724 | >= | 8.0 | True |
| collision expectation | False | == | False | True |
| lane departure expectation | False | == | False | True |

## boundary_open_road

| Check | Actual | Comparator | Target | Passed |
|---|---:|---|---:|---|
| peak brake should stay below target | 0.1811 | <= | 0.25 | True |
| peak throttle should reach target | 0.6183 | >= | 0.5 | True |
| minimum distance should stay above target | 39.1468 | >= | 30.0 | True |
| collision expectation | False | == | False | True |
| lane departure expectation | False | == | False | True |
