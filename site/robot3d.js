// Interactive robot viewer: the life-size InMoov humanoid standing on walking legs.
//   Upper body: InMoov (Gael Langevin's design). URDF from Sentience-Robotics/inmoov_urdf (GPL-3.0), xacro
//     pre-expanded into /models/inmoov.urdf; its ~290 Collada meshes stream from that repo. Its pole stand is hidden.
//   Legs: Berkeley Humanoid Lite biped (HybridRobotics, CC-BY-SA-4.0), scaled to adult proportions and bolted
//     under the InMoov pelvis. This is the leg concept, not a final leg design.
// data-focus picks the framing: (none) whole robot, "arm" right-arm close-up, "legs" hips-to-feet close-up.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import URDFLoader from "urdf-loader";

const INMOOV = "/models/inmoov.urdf";
const LEGS_BASE = "https://raw.githubusercontent.com/HybridRobotics/Berkeley-Humanoid-Lite-Assets/main/data/robots/berkeley_humanoid/berkeley_humanoid_lite";
const LEGS_URDF = `${LEGS_BASE}/urdf/berkeley_humanoid_lite_biped.urdf`;
const LEG_LENGTH = 0.9; // metres, hip to sole, for a 1.8 m humanoid

const el = document.getElementById("arm3d");
const status = document.getElementById("arm3d-status");
const FOCUS = el.dataset.focus || "home";

const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
el.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 20);
camera.position.set(0, 1.2, 4);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enableZoom = false;

scene.add(new THREE.HemisphereLight(0xffffff, 0x888899, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(1, 2, 1.5);
scene.add(sun);

const shell = new THREE.MeshStandardMaterial({ color: "#eef0f3", roughness: 0.5 });
const dark = new THREE.MeshStandardMaterial({ color: "#2a2d34", roughness: 0.45 });
const accent = new THREE.MeshStandardMaterial({ color: css("--accent") || "#2f5bea", roughness: 0.5 });
const glow = new THREE.MeshStandardMaterial({ color: css("--hw") || "#e07a2f", roughness: 0.4, emissive: css("--hw") || "#e07a2f", emissiveIntensity: 0.25 });
// Keep each model's light/dark split, re-shaded to the site palette. On the home page the hands pick up
// the accent; on close-up pages everything stays neutral so a highlighted part stands out.
function repaint(root) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const c = o.userData.srcColor || o.material?.color;
    o.userData.srcColor = c;
    const isDark = c && c.r + c.g + c.b < 0.9;
    let p = o, inHand = false;
    while (p && !inHand) { inHand = /Hand/.test(p.name || ""); p = p.parent; }
    o.userData.base = isDark ? dark : inHand && FOCUS === "home" ? accent : shell;
    o.material = o.userData.base;
  });
}
const linkOf = (o) => { while (o && !o.isURDFLink) o = o.parent; return o?.name || ""; };

let body = null, legs = null;
const legRig = new THREE.Group(); // positions and scales the legs under the InMoov pelvis
const manager = new THREE.LoadingManager();
manager.onProgress = (_, n, total) => { status.textContent = `Loading the robot… ${n}/${total} parts`; };
manager.onError = fail;
function fail() { status.textContent = "3D model couldn't load. Check your connection."; }

const bodyLoader = new URDFLoader(manager);
// Mesh URLs in the InMoov URDF are absolute, but urdf-loader prefixes its working path; undo that.
bodyLoader.loadMeshCb = (path, mgr, done) => bodyLoader.defaultMeshLoader(path.slice(path.indexOf("https://")), mgr, done);
bodyLoader.load(INMOOV, (r) => { body = r; }, undefined, fail);

const legLoader = new URDFLoader(manager);
// The biped URDF points at ./assets/merged/, but the published meshes live in meshes/.
legLoader.loadMeshCb = (path, mgr, done) => legLoader.defaultMeshLoader(`${LEGS_BASE}/meshes/${path.split("/").pop()}`, mgr, done);
legLoader.load(LEGS_URDF, (r) => { legs = r; }, undefined, fail);

// onLoad fires whenever the loading queue drains, not once; everything here is safe to repeat.
manager.onLoad = () => {
  if (!body || !legs) return;
  body.rotation.x = -Math.PI / 2; // URDFs are Z-up
  legs.rotation.x = -Math.PI / 2;
  if (!body.parent) scene.add(body);
  if (!legs.parent) { legRig.add(legs); scene.add(legRig); }
  // Hide only the pole-stand mesh; base_node is the InMoov root link, so hiding the link hides everything.
  for (const v of body.links.base_node.children) if (v.isURDFVisual) v.visible = false;
  repaint(body);
  repaint(legs);
  applyPose(0);
  mountLegs();
  frame();
  window.dispatchEvent(new Event("robot3d:ready"));
};

// Scale the legs to adult proportions and hang them from the InMoov hip.
function mountLegs() {
  legRig.scale.setScalar(1);
  legRig.position.set(0, 0, 0);
  legRig.rotation.set(0, -Math.PI / 2, 0); // Berkeley legs face +x; InMoov faces the camera (+z)
  scene.updateMatrixWorld(true);
  const lb = new THREE.Box3().setFromObject(legs);
  legRig.scale.setScalar(LEG_LENGTH / (lb.max.y - lb.min.y));
  scene.updateMatrixWorld(true);
  const hip = body.links.torso_bottom_link.getWorldPosition(new THREE.Vector3());
  const lb2 = new THREE.Box3().setFromObject(legs);
  const top = lb2.getCenter(new THREE.Vector3()).setY(lb2.max.y);
  legRig.position.add(hip.sub(top));
  scene.updateMatrixWorld(true);
}

function frame() {
  const box = new THREE.Box3();
  if (FOCUS === "arm") {
    box.setFromObject(body.links.right_shoulder_y_link);
    aim(box, new THREE.Vector3(-0.9, 0.2, 1), 0.95);
    status.textContent = "One arm, shoulder to fingertips · drag to rotate";
  } else if (FOCUS === "legs") {
    box.setFromObject(legs);
    aim(box, new THREE.Vector3(0.9, 0.25, 1), 2.1);
    status.textContent = "The legs · 12 joints, hips to feet · drag to rotate";
  } else {
    box.setFromObject(body).union(new THREE.Box3().setFromObject(legs));
    aim(box, new THREE.Vector3(0.35, 0.12, 1), 1.45);
    status.textContent = "robotai · life-size InMoov humanoid on walking legs · drag to rotate";
  }
}
function aim(box, dir, dist) {
  const c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
  controls.target.copy(c);
  camera.position.copy(c).add(dir.normalize().multiplyScalar(size * dist));
}

// ---- motion ----
const FINGERS = ["index", "index2", "index3", "majeure", "majeure2", "majeure3", "ringFinger", "ringfinger2", "ringfinger3", "pinky", "pinky2", "pinky3", "thumb", "thumb3"];
function bodyPose(t) {
  if (FOCUS === "arm") {
    // Arm held out in front, forearm raised, wrist turning and fingers curling, so every part stays in view.
    const out = {
      right_shoulder_x_link_joint: 0.55, right_shoulder_y_link_joint: 0.1,
      right_elbow_x_link_joint: 0.9 + 0.08 * Math.sin(t * 0.6),
      right_wrist_z_link_joint: 0.6 * Math.sin(t * 0.5),
    };
    const curl = 0.5 + 0.5 * Math.sin(t * 1.1);
    for (const f of FINGERS) out[`i01.rightHand.${f}_link_joint`] = curl;
    return out;
  }
  // Arms swing opposite the legs, fingers curl, head looks around.
  const out = {
    "i01.head.rothead_link_joint": 0.4 * Math.sin(t * 0.4),
    "i01.head.neck.001_link_joint": 0.1 * Math.sin(t * 0.55),
  };
  for (const [side, k] of [["left", 0], ["right", Math.PI]]) {
    out[`${side}_shoulder_x_link_joint`] = 0.25 + 0.25 * Math.sin(t * 1.6 + k);
    out[`${side}_elbow_x_link_joint`] = 0.5 + 0.2 * Math.sin(t * 1.6 + k + 0.6);
    const curl = 0.5 + 0.5 * Math.sin(t * 1.2 + k);
    for (const f of FINGERS) out[`i01.${side === "left" ? "leftHand" : "rightHand"}.${f}_link_joint`] = curl;
  }
  return out;
}
// Stepping in place: each leg lifts in turn, with the ankle keeping the foot flat.
function legPose(t) {
  const out = {};
  for (const [side, k] of [["left", 0], ["right", Math.PI]]) {
    const lift = Math.max(0, Math.sin(t * 1.6 + k));
    out[`leg_${side}_hip_pitch_joint`] = -0.5 * lift;
    out[`leg_${side}_knee_pitch_joint`] = 1.0 * lift;
    out[`leg_${side}_ankle_pitch_joint`] = -0.5 * lift;
  }
  return out;
}
function set(robot, values) {
  for (const [j, v] of Object.entries(values)) {
    const joint = robot.joints[j];
    if (joint) joint.setJointValue(THREE.MathUtils.clamp(v, joint.limit.lower, joint.limit.upper));
  }
}
function applyPose(t) {
  set(body, bodyPose(t));
  set(legs, FOCUS === "arm" ? {} : legPose(t));
}

// Highlight API for the part lists: match URDF link names by list, prefix or regex; null clears.
window.robot3d = {
  highlight(part) {
    for (const robot of [body, legs]) {
      robot?.traverse((o) => {
        if (!o.isMesh || !o.userData.base) return;
        const name = linkOf(o);
        const hit = part && !(part.exclude || []).includes(name) && ((part.links || []).includes(name)
          || (part.prefix && name.startsWith(part.prefix)) || (part.match && new RegExp(part.match).test(name)));
        o.material = hit ? glow : o.userData.base;
      });
    }
  },
};

function resize() {
  const w = el.clientWidth, h = el.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(el);

const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
renderer.setAnimationLoop((ms) => {
  if (body && legs && body.parent && !still) applyPose(ms / 1000);
  controls.update();
  renderer.render(scene, camera);
});
