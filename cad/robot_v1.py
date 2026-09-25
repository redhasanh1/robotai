"""robotai v1: the full original humanoid (upper body + dynamic legs) as one jointed model.

Run headless:  blender -b -P cad/robot_v1.py -- site/models/robot_v1.glb
The root Empty sits at the hip centre; the soles end LEG_LENGTH below it (~0.98 m); the head tops out ~0.82 m above.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import legs  # noqa: E402
import parts as P  # noqa: E402
import upper  # noqa: E402

P.init_scene()
root = P.joint("robot_root", None, (0, 0, 0))
legs.build(root)
upper.build(root)
P.export(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "robot_v1.glb")
