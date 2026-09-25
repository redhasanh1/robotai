// Interactive robot viewer. data-focus picks the model and framing:
//   (none) home: the life-size InMoov humanoid (Gael Langevin's design) that robotai v1 is built on.
//          URDF from Sentience-Robotics/inmoov_urdf (GPL-3.0), xacro pre-expanded into /models/inmoov.urdf;
//          its ~290 Collada meshes stream from that repo.
//   arm    the same model, close-up on the right arm, with part highlighting.
//   legs   Stanford's ToddlerBot (MIT), the closest open design to our servo walker, stepping in place.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import URDFLoader from "urdf-loader";

const el = document.getElementById("arm3d");
const status = document.getElementById("arm3d-status");
const FOCUS = el.dataset.focus || "home";
const ARM = FOCUS === "arm";
const LEGS = FOCUS === "legs";
const URDF = LEGS
  ? "https://raw.githubusercontent.com/hshi74/toddlerbot/main/toddlerbot/descriptions/toddlerbot_2xc_gripper/toddlerbot_2xc_gripper.urdf"
  : "/models/inmoov.urdf";

const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
el.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 10);
camera.position.set(0.45, 0.35, 0.45);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.15, 0);
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
// Keep the model's own light/dark split, re-shaded to the site palette. On the home page the hands
// pick up the accent; on /arm everything stays neutral so a highlighted part stands out.
const repaint = (o, inHand) => {
  const c = o.userData.srcColor || o.material?.color;
  o.userData.srcColor = c;
  const isDark = c && c.r + c.g + c.b < 0.9;
  o.userData.base = isDark ? dark : inHand && FOCUS === "home" ? accent : shell;
  o.material = o.userData.base;
};
const linkOf = (o) => { while (o && !o.isURDFLink) o = o.parent; return o?.name || ""; };

let robot = null;
const manager = new THREE.LoadingManager();
const loader = new URDFLoader(manager);
// Mesh URLs in the URDF are absolute, but urdf-loader prefixes its working path; undo that.
loader.loadMeshCb = (path, mgr, done) => loader.defaultMeshLoader(path.slice(path.indexOf("https://")), mgr, done);
manager.onProgress = (_, n, total) => { status.textContent = `Loading the robot… ${n}/${total} parts`; };
loader.load(URDF, (r) => { robot = r; }, undefined, fail);

// Meshes stream in after the URDF itself, so paint and frame once everything has arrived.
manager.onLoad = () => {
  if (!robot) return;
  // onLoad fires whenever the queue drains, not once; everything below is safe to repeat.
  robot.rotation.x = -Math.PI / 2; // URDF is Z-up
  robot.traverse((o) => {
    if (!o.isMesh) return;
    let p = o, inHand = false;
    while (p && !inHand) { inHand = /Hand/.test(p.name || ""); p = p.parent; }
    repaint(o, inHand);
  });
  if (!robot.parent) scene.add(robot);
  robot.updateMatrixWorld(true);
  if (LEGS) {
    applyPose(0);
    robot.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(robot);
    const c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
    controls.target.copy(c);
    camera.position.copy(c).add(new THREE.Vector3(0.9, 0.3, 1).normalize().multiplyScalar(size * 1.5));
    status.textContent = "The walker · 12 leg joints · drag to rotate";
  } else if (ARM) {
    applyPose(0);
    robot.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(robot.links.right_shoulder_y_link);
    const c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
    controls.target.copy(c);
    camera.position.copy(c).add(new THREE.Vector3(-0.9, 0.2, 1).normalize().multiplyScalar(size * 0.95));
    status.textContent = "One arm, shoulder to fingertips · drag to rotate";
  } else {
    const box = new THREE.Box3().setFromObject(robot);
    const c = box.getCenter(new THREE.Vector3());
    // Frame the upper body (head to hips); the pedestal below stands in for the hoverboard base.
    const upper = new THREE.Vector3(c.x, box.max.y - 0.5, c.z);
    controls.target.copy(upper);
    camera.position.copy(upper).add(new THREE.Vector3(0.35, 0.1, 1).normalize().multiplyScalar(2.3));
    status.textContent = "robotai v1 · life-size InMoov humanoid · drag to rotate";
  }
  window.dispatchEvent(new Event("robot3d:ready"));
};
manager.onError = fail;
function fail() { status.textContent = "3D model couldn't load. Check your connection."; }

// Idle motion: arms reach and return out of phase, fingers curl, head looks around, torso twists slightly.
const FINGERS = ["index", "index2", "index3", "majeure", "majeure2", "majeure3", "ringFinger", "ringfinger2", "ringfinger3", "pinky", "pinky2", "pinky3", "thumb", "thumb3"];
const armPose = (t) => {
  // Arm held out in front, forearm raised, wrist turning and fingers curling, so every part stays in view.
  const out = {
    right_shoulder_x_link_joint: 0.55, right_shoulder_y_link_joint: 0.1,
    right_elbow_x_link_joint: 0.9 + 0.08 * Math.sin(t * 0.6),
    right_wrist_z_link_joint: 0.6 * Math.sin(t * 0.5),
  };
  const curl = 0.5 + 0.5 * Math.sin(t * 1.1);
  for (const f of FINGERS) out[`i01.rightHand.${f}_link_joint`] = curl;
  return out;
};
// Stepping in place: legs alternate lifting, with the ankle keeping the foot flat.
const walkPose = (t) => {
  const out = {};
  for (const [side, k] of [["left", 0], ["right", Math.PI]]) {
    const lift = Math.max(0, Math.sin(t * 2.4 + k));
    out[`${side}_hip_pitch`] = -0.45 * lift;
    out[`${side}_knee`] = 0.9 * lift;
    out[`${side}_ankle_pitch`] = -0.45 * lift;
    out[`${side}_shoulder_pitch`] = 0.3 * Math.sin(t * 2.4 + k + Math.PI);
  }
  out.waist_yaw = 0.08 * Math.sin(t * 2.4);
  return out;
};
const pose = (t) => {
  const out = {
    "i01.head.rothead_link_joint": 0.45 * Math.sin(t * 0.4),
    "i01.head.neck.001_link_joint": 0.12 * Math.sin(t * 0.55),
    "i01.torso.midStom_link_joint": 0.12 * Math.sin(t * 0.3),
  };
  for (const [side, k] of [["left", 0], ["right", Math.PI]]) {
    out[`${side}_shoulder_x_link_joint`] = 0.35 + 0.35 * Math.sin(t * 0.7 + k);
    out[`${side}_shoulder_y_link_joint`] = 0.15 * Math.sin(t * 0.5 + k);
    out[`${side}_elbow_x_link_joint`] = 0.6 + 0.4 * Math.sin(t * 0.7 + k + 0.8);
    out[`${side}_wrist_z_link_joint`] = 0.5 * Math.sin(t * 0.6 + k);
    const hand = side === "left" ? "leftHand" : "rightHand";
    const curl = 0.5 + 0.5 * Math.sin(t * 1.2 + k);
    for (const f of FINGERS) out[`i01.${hand}.${f}_link_joint`] = curl;
  }
  return out;
};

function resize() {
  const w = el.clientWidth, h = el.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(el);

function applyPose(t) {
  for (const [j, v] of Object.entries((LEGS ? walkPose : ARM ? armPose : pose)(t))) {
    const joint = robot.joints[j];
    if (joint) joint.setJointValue(THREE.MathUtils.clamp(v, joint.limit.lower, joint.limit.upper));
  }
}

// Highlight API for /arm: pass link names (or a prefix) to light them up; null clears.
window.robot3d = {
  highlight(part) {
    if (!robot) return;
    robot.traverse((o) => {
      if (!o.isMesh || !o.userData.base) return;
      const name = linkOf(o);
      const hit = part && !(part.exclude || []).includes(name) && ((part.links || []).includes(name)
        || (part.prefix && name.startsWith(part.prefix)) || (part.match && new RegExp(part.match).test(name)));
      o.material = hit ? glow : o.userData.base;
    });
  },
};

const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
renderer.setAnimationLoop((ms) => {
  if (robot && !still) applyPose(ms / 1000);
  controls.update();
  renderer.render(scene, camera);
});
