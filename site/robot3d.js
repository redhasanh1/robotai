// Interactive full robot: XLeRobot (2x SO-101 arms, IKEA cart base, pan-tilt camera head), loaded from the
// open-source model in Vector-Wangel/XLeRobot (Apache-2.0).
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import URDFLoader from "urdf-loader";

const URDF = "https://raw.githubusercontent.com/Vector-Wangel/XLeRobot/main/simulation/Maniskill/assets/xlerobot/xlerobot.urdf";
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

const printed = new THREE.MeshStandardMaterial({ color: css("--accent") || "#2f5bea", roughness: 0.55 });
const servo = new THREE.MeshStandardMaterial({ color: "#23262d", roughness: 0.4, metalness: 0.2 });
const cart = new THREE.MeshStandardMaterial({ color: "#c9ccd2", roughness: 0.7, metalness: 0.1 });
const kind = (path) => (/motor|camera/i.test(path) ? servo : /raskog/i.test(path) ? cart : printed);

let robot = null;
const manager = new THREE.LoadingManager();
const loader = new URDFLoader(manager);
loader.loadMeshCb = (path, manager, done) => {
  if (!/\.stl$/i.test(path)) return done(new THREE.Group()); // tiny .ply jaw-tip colliders: skip
  new STLLoader(manager).load(path, (geom) => {
    const m = new THREE.Mesh(geom);
    m.userData.mat = kind(path);
    done(m);
  }, undefined, (e) => done(null, e));
};
loader.load(URDF, (r) => { robot = r; }, undefined, fail);

// Meshes stream in after the URDF itself, so paint and frame once everything has arrived.
manager.onLoad = () => {
  if (!robot) return;
  robot.rotation.x = -Math.PI / 2; // URDF is Z-up
  robot.traverse((o) => { if (o.isMesh && o.userData.mat) o.material = o.userData.mat; }); // override URDF colours
  scene.add(robot);
  robot.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(robot);
  const c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
  controls.target.copy(c);
  camera.position.copy(c).add(new THREE.Vector3(0.8, 0.25, 1).normalize().multiplyScalar(size * 1.7));
  status.textContent = "The robot · two arms, camera head, mobile base · drag to rotate";
};
manager.onError = fail;
function fail() { status.textContent = "3D model couldn't load. Check your connection."; }

// Idle "working" motion: both arms reach and grab out of phase, the head looks around, the base turns slowly.
const arm = (t, k) => ({ Rotation: 0.35 * Math.sin(t * 0.5 + k), Pitch: -0.3 + 0.3 * Math.sin(t * 0.8 + k), Elbow: 0.4 + 0.35 * Math.sin(t * 0.8 + k + 1),
  Wrist_Pitch: 0.4 * Math.sin(t * 0.9 + k + 2), Wrist_Roll: 0.6 * Math.sin(t * 0.6 + k), Jaw: 0.5 + 0.5 * Math.sin(t * 1.6 + k) });
const pose = (t) => {
  const out = { head_pan_joint: 0.5 * Math.sin(t * 0.35), head_tilt_joint: 0.2 * Math.sin(t * 0.5), root_z_rotation_joint: 0.25 * Math.sin(t * 0.15) };
  for (const [j, v] of Object.entries(arm(t, 0))) out[j] = v;
  for (const [j, v] of Object.entries(arm(t, Math.PI))) out[j + "_2"] = v;
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
  if (robot && !still) for (const [j, v] of Object.entries(pose(ms / 1000))) robot.joints[j]?.setJointValue(v);
  controls.update();
  renderer.render(scene, camera);
});
