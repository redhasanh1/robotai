"""Export just robotai's detailed legs (cad/legs.py) to bolt under the InMoov upper body on the site.
blender -b -P cad/legs_only.py -- site/models/legs_v2.glb"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import legs  # noqa: E402
import parts as P  # noqa: E402

P.init_scene()
root = P.joint("legs_root", None, (0, 0, 0))
legs.build(root)
P.export(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "legs_v2.glb")
