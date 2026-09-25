// Interactive SO-101 arm, loaded from the official open-source model (TheRobotStudio/SO-ARM100, Apache-2.0).
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import URDFLoader from "urdf-loader";

const URDF = "https://raw.githubusercontent.com/TheRobotStudio/SO-ARM100/main/Simulation/SO101/so101_new_calib.urdf";
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

let robot = null;
const manager = new THREE.LoadingManager();
const loader = new URDFLoader(manager);
loader.loadMeshCb = (path, manager, done) => {
  new STLLoader(manager).load(path, (geom) => {
    const m = new THREE.Mesh(geom);
    m.userData.servo = /sts3215/i.test(path);
    done(m);
  }, undefined, (e) => done(null, e));
};
loader.load(URDF, (r) => { robot = r; }, undefined, fail);

// Meshes stream in after the URDF itself, so paint and frame once everything has arrived.
manager.onLoad = () => {
  if (!robot) return;
  robot.rotation.x = -Math.PI / 2; // URDF is Z-up
  robot.traverse((o) => { if (o.isMesh) o.material = o.userData.servo ? servo : printed; }); // override URDF colours
  scene.add(robot);
  robot.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(robot);
  const c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
  controls.target.copy(c);
  camera.position.copy(c).add(new THREE.Vector3(0.25, 0.35, 1).normalize().multiplyScalar(size * 1.6));
  status.textContent = "SO-101 arm · drag to rotate";
};
manager.onError = fail;
function fail() { status.textContent = "3D model couldn't load. Check your connection."; }

// Gentle "reach and grab" motion across the six joints.
const pose = (t) => ({
  shoulder_pan: 0.6 * Math.sin(t * 0.5),
  shoulder_lift: -0.4 + 0.35 * Math.sin(t * 0.8),
  elbow_flex: 0.6 + 0.4 * Math.sin(t * 0.8 + 1),
  wrist_flex: 0.5 * Math.sin(t * 0.9 + 2),
  wrist_roll: 0.8 * Math.sin(t * 0.6),
  gripper: 0.7 + 0.7 * Math.sin(t * 1.6),
});

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
