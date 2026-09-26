# Tendon-level finger model (hand/tendon_sim.py)

One InMoov finger (45/28/22 mm phalanges), flexor on the palm side and extensor on the back, both on a 12 mm horn; each line is a MuJoCo spatial tendon used as a string (pulls only, 1 mm slack, PTFE drag as tendon friction). Horn swept 0 -> 2.6 rad -> 0. Torque is the net line pull x horn radius as % of MG996R stall (1.08 N*m at 6 V).

| variant | closes to | horn for 90% | torque at 90% | servo stalls at horn (flexion) | hysteresis |
|---|---|---|---|---|---|
| nominal | 0.936 | 2.3 rad | 73.3% | 2.52 rad (0.92) | 0.026 |
| PTFE drag x4 | 0.936 | 2.3 rad | 73.3% | 2.52 rad (0.92) | 0.026 |
| tight middle hinge | 0.936 | 2.3 rad | 73.3% | 2.52 rad (0.92) | 0.026 |
| 5 mm slack | 0.839 | 2.36 rad | 46.2% | never | 0.025 |
| stretchy line (mono, not braid) | 0.593 | 2.26 rad | 7.7% | never | 0.027 |
| closing on an object | 0.89 | 2.02 rad | 103.2% | 2.02 rad (0.72) | 0.099 |

What it means for the build:

1. Calibrate the closed end at about 2.3 rad of horn (~132 deg) per finger. 0.2 rad further, the line fights the joint stops and the servo stalls (131% of stall demanded at 2.6 rad).
2. Closing on an object reaches stall at 72% flexion: the squeeze guard (hand/guard.py) is necessary, not optional.
3. Slack costs closure (5 mm: 94% -> 84%) but halves the load - a little slack is a safety margin.
4. Line choice matters: a stretchy monofilament only reaches 59%. The 200 lb PE braid is right.
5. The fingertip curls first; the base joint lags (0.15 rad at full pull in the trace) - expect grasps to look hooked.

Limit: extra PTFE drag and a tight hinge change nothing here - with two taut, stiff lines the pose is set by the strings, and friction would only show once there is slack. Validate against the real finger in week 2.

# Grey-box plant on the tendon finger (tools/tendon_to_greybox.py)

The tendon-level finger (hand/tendon_sim.py) driven through the servo model stands in for the real finger; 20 s excitation to fit, 15 s of new commands to test.

| model | error on new commands |
|---|---|
| datasheet plant | 6.4 deg |
| sysid-fitted plant (v_max 3.47, tau 0.074, backlash 0.035) | 6.6 deg |
| fitted plant + learned residual | **1.4 deg** |

Fitting the speed/lag/slack parameters does not help: that structure cannot express how a tendon finger curls (tip first, non-linear flexion vs horn, stops at 94%). The learned residual is what covers it - the tendon model is the argument for keeping it.
