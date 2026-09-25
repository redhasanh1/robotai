// Interactive robot: the life-size InMoov humanoid (Gael Langevin's design) that robotai v1 is built on.
// URDF from Sentience-Robotics/inmoov_urdf (GPL-3.0), xacro pre-expanded into /models/inmoov.urdf;
// its ~290 Collada meshes stream from that repo.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import URDFLoader from "urdf-loader";

const URDF = "/models/inmoov.urdf";
const el = document.getElementById("arm3d");
const status = document.getElementById("arm3d-status");

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
// Keep the model's own light/dark split, re-shaded to the site palette; hands pick up the accent.
const repaint = (o, inHand) => {
  const c = o.material?.color;
  const isDark = c && c.r + c.g + c.b < 0.9;
  o.material = isDark ? dark : inHand ? accent : shell;
};

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
  const box = new THREE.Box3().setFromObject(robot);
  const c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
  // Frame the upper body (head to hips); the pedestal below stands in for the hoverboard base.
  const upper = new THREE.Vector3(c.x, box.max.y - 0.5, c.z);
  controls.target.copy(upper);
  camera.position.copy(upper).add(new THREE.Vector3(0.35, 0.1, 1).normalize().multiplyScalar(2.3));
  status.textContent = "robotai v1 · life-size InMoov humanoid · drag to rotate";
};
manager.onError = fail;
function fail() { status.textContent = "3D model couldn't load. Check your connection."; }

// Idle motion: arms reach and return out of phase, fingers curl, head looks around, torso twists slightly.
const FINGERS = ["index", "index2", "index3", "majeure", "majeure2", "majeure3", "ringFinger", "ringfinger2", "ringfinger3", "pinky", "pinky2", "pinky3", "thumb", "thumb3"];
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

const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
renderer.setAnimationLoop((ms) => {
  if (robot && !still) {
    for (const [j, v] of Object.entries(pose(ms / 1000))) {
      const joint = robot.joints[j];
      if (joint) joint.setJointValue(THREE.MathUtils.clamp(v, joint.limit.lower, joint.limit.upper));
    }
  }
  controls.update();
  renderer.render(scene, camera);
});
