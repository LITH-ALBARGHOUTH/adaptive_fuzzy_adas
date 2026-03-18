# Conflict-Oriented Rule Notes

These examples highlight how the rule base handles interacting and competing conditions.

## Collision risk depends on interacting inputs, not a single monotonic trend.

- `r6_close_highspeed`: `IF front_distance IS close AND speed IS high THEN risk_level IS critical`
  Description: Close spacing at high speed is immediately critical. (weight=1.00)
- `r8_close_lowspeed`: `IF front_distance IS close AND speed IS low THEN risk_level IS medium`
  Description: Short spacing at low speed is still non-negligible. (weight=0.85)
- `r12_medium_medspeed_goodroad`: `IF front_distance IS medium AND speed IS medium AND road_condition IS good THEN risk_level IS low`
  Description: A healthy road surface makes medium spacing at cruise speed relatively safe. (weight=1.00)
- `r13_medium_medspeed_poorroad`: `IF front_distance IS medium AND speed IS medium AND road_condition IS poor THEN risk_level IS high`
  Description: Moderate speed with degraded grip elevates a medium gap to high risk. (weight=1.00)

## Lane correction strength changes with speed and steering stability even for similar offsets.

- `r6_left_highspeed`: `IF lane_deviation IS left AND speed IS high THEN lane_stability IS strong_right`
  Description: At high speed, moderate left drift requires stronger correction. (weight=1.00)
- `r15_left_lowspeed_stable`: `IF lane_deviation IS left AND speed IS low AND steering_stability IS stable THEN lane_stability IS right`
  Description: At low speed a moderate right correction is enough for left drift. (weight=1.00)
- `r8_left_unstable`: `IF lane_deviation IS left AND steering_stability IS unstable THEN lane_stability IS strong_right`
  Description: Unstable steering amplifies left-drift urgency. (weight=1.00)

## Meta decisions explicitly balance comfort against safety and lateral urgency.

- `t9_lowrisk_centered_highcomfort`: `IF risk_level IS low AND lane_stability IS centered AND comfort_efficiency IS high THEN throttle_command IS strong`
  Description: Low risk, centered lane, and high comfort preference invite stronger throttle. (weight=1.00)
- `t11_lowrisk_centered_lowcomfort`: `IF risk_level IS low AND lane_stability IS centered AND comfort_efficiency IS low THEN throttle_command IS light`
  Description: Low comfort preference restrains throttle even when risk is low. (weight=1.00)
- `b14_mediumrisk_centered_highcomfort`: `IF risk_level IS medium AND comfort_efficiency IS high AND lane_stability IS centered THEN brake_command IS none`
  Description: Comfort introduces a competing no-brake tendency in medium risk. (weight=0.45)
- `b11_highrisk_strongleft`: `IF risk_level IS high AND lane_stability IS strong_left THEN brake_command IS hard`
  Description: High risk and severe left lateral demand justify hard braking. (weight=1.00)
