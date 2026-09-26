// "How the hand fits together": the right InMoov forearm + wrist + hand, pulled apart on demand (exploded view).
// Built live from the same InMoov URDF as robot3d.js; only the forearm/hand meshes are fetched, and nothing
// InMoov-derived is stored in this repo (InMoov by Gael Langevin, CC BY-NC; URDF by Sentience Robotics, GPL-3.0).
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import URDFLoader from "urdf-loader";

const URDF = "/models/inmoov.urdf";
const KEEP = /^(right_elbow_x_link|right_wrist|i01\.rightHand)/;
const el = document.getElementById("hand3d");
const status = document.getElementById("hand3d-status");
const play = document.getElementById("hand-play");
const slider = document.getElementById("hand-slider");
const tip = document.getElementById("hand-tip");

const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
el.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.005, 20);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enableZoom = false; // keep page scrolling; the camera frames the exploded arm
scene.add(new THREE.HemisphereLight(0xffffff, 0x888899, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 2);
sun.position.set(1, 3, 2);
scene.add(sun);

const mats = {
  finger: new THREE.MeshStandardMaterial({ color: "#f3d6c2", roughness: 0.55 }),
  palm: new THREE.MeshStandardMaterial({ color: "#bccfe2", roughness: 0.5 }),
  forearm: new THREE.MeshStandardMaterial({ color: "#e9ecf0", roughness: 0.5 }),
  hot: new THREE.MeshStandardMaterial({ color: css("--hw") || "#e07a2f", roughness: 0.45 }),
};

// Friendly names for the URDF links.
function label(link) {
  if (link === "right_elbow_x_link") return "Forearm shell";
  if (link.startsWith("right_wrist")) return "Wrist rotation";
  if (/wrist/.test(link)) return "Palm";
  const f = { thumb: "Thumb", index: "Index finger", majeure: "Middle finger", ring: "Ring finger", pinky: "Pinky" };
  const key = Object.keys(f).find((k) => link.toLowerCase().includes(k));
  if (!key) return link;
  const n = (link.split(".").pop().match(/\d+/) || ["1"])[0];
  return n === "0" ? `${f[key]}, base` : `${f[key]}, segment ${n}`;
}

const parts = [];
let t = 0, target = 0;
const group = new THREE.Group();
scene.add(group);

(async () => {
  // Only fetch meshes that belong to the forearm/hand links.
  const xml = new DOMParser().parseFromString(await (await fetch(URDF)).text(), "text/xml");
  const wanted = new Set();
  for (const l of xml.querySelectorAll("robot > link")) {
    if (!KEEP.test(l.getAttribute("name"))) continue;
    for (const m of l.querySelectorAll("visual mesh")) wanted.add(m.getAttribute("filename").split("/").pop());
  }
  const manager = new THREE.LoadingManager();
  let done = 0;
  const loader = new URDFLoader(manager);
  loader.loadMeshCb = (path, mgr, cb) => {
    const url = path.slice(path.indexOf("https://"));
    if (!wanted.has(url.split("/").pop())) return cb(new THREE.Object3D());
    loader.defaultMeshLoader(url, mgr, (m, e) => { status.textContent = `Loading the hand… ${++done}/${wanted.size} parts`; cb(m, e); });
  };
  // onLoad can fire before or after the URDF callback, and more than once; build when both are ready.
  let robot = null, loaded = false;
  manager.onLoad = () => { loaded = true; if (robot) build(robot); };
  loader.load(URDF, (r) => { robot = r; if (loaded) build(robot); },
    undefined, () => { status.textContent = "3D model couldn't load. Check your connection."; });
})();

function build(robot) {
  if (parts.length) return;
  robot.rotation.x = -Math.PI / 2;
  scene.add(robot);
  scene.updateMatrixWorld(true);
  const meshes = [];
  robot.traverse((o) => {
    if (!o.isMesh) return;
    let p = o;
    while (p && !p.isURDFLink) p = p.parent;
    if (p && KEEP.test(p.name)) meshes.push([o, p.name]);
  });
  for (const [m, link] of meshes) {
    group.attach(m); // keep the assembled world position
    m.name = label(link);
    m.userData.base = /Forearm/.test(m.name) ? mats.forearm : /Palm|Wrist/.test(m.name) ? mats.palm : mats.finger;
    m.material = m.userData.base;
  }
  scene.remove(robot);

  // Explode: push each part along the arm axis and out sideways from it.
  const box = new THREE.Box3().setFromObject(group), C = box.getCenter(new THREE.Vector3());
  const centre = (o) => new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3());
  const avg = (list) => list.reduce((a, o) => a.add(centre(o)), new THREE.Vector3()).divideScalar(Math.max(list.length, 1));
  const kids = [...group.children];
  const axis = avg(kids.filter((o) => !/Forearm|Wrist/.test(o.name))).sub(avg(kids.filter((o) => /Forearm/.test(o.name)))).normalize();
  for (const o of kids) {
    const d = centre(o).sub(C), along = axis.clone().multiplyScalar(d.dot(axis)), side = d.clone().sub(along);
    if (side.length() < 0.005) side.set(Math.random() - 0.5, 0, Math.random() - 0.5).setLength(0.005);
    o.userData.home = o.position.clone();
    o.userData.off = along.multiplyScalar(1.1).add(side.multiplyScalar(/Forearm/.test(o.name) ? 5 : 2.2));
    parts.push(o);
  }
  // Frame so both the assembled and the fully exploded arm fit.
  explode(1);
  const wide = new THREE.Box3().setFromObject(group);
  explode(0);
  fit = { box: wide };
  fitCamera();
  status.textContent = `${parts.length} parts · hover one to see its name`;
  play.disabled = false;
  slider.disabled = false;
}

let fit = null;
// Place the camera so the whole exploded arm fits the stage at its current aspect ratio.
function fitCamera() {
  if (!fit) return;
  const size = fit.box.getSize(new THREE.Vector3()), c = fit.box.getCenter(new THREE.Vector3());
  const tan = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  const radius = size.length() / 2;
  const dist = Math.max(radius / tan, radius / (tan * camera.aspect)) * 0.92;
  const dir = new THREE.Vector3(0.55, 0.3, 0.9).normalize();
  controls.target.copy(c);
  camera.position.copy(c).addScaledVector(dir, dist);
  controls.update();
}
function explode(v) { for (const o of parts) o.position.copy(o.userData.home).addScaledVector(o.userData.off, v); }
const ease = (x) => x * x * (3 - 2 * x);
function setLabel() { play.textContent = target > 0.5 ? "Put together" : "Take apart"; }
play.addEventListener("click", () => { target = t > 0.5 ? 0 : 1; setLabel(); });
slider.addEventListener("input", () => { t = target = +slider.value; explode(ease(t)); setLabel(); });

const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
let hot = null;
renderer.domElement.addEventListener("pointermove", (e) => {
  const r = renderer.domElement.getBoundingClientRect();
  mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const h = ray.intersectObjects(parts, false)[0];
  if (hot && (!h || h.object !== hot)) { hot.material = hot.userData.base; hot = null; }
  if (h) {
    hot = h.object;
    hot.material = mats.hot;
    tip.textContent = hot.name;
    tip.style.left = `${e.clientX - r.left + 14}px`;
    tip.style.top = `${e.clientY - r.top + 10}px`;
    tip.hidden = false;
  } else tip.hidden = true;
});
renderer.domElement.addEventListener("pointerleave", () => { tip.hidden = true; });

function resize() {
  const w = el.clientWidth, h = el.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  fitCamera();
}
new ResizeObserver(resize).observe(el);
resize();
(function loop() {
  requestAnimationFrame(loop);
  if (Math.abs(target - t) > 1e-3) {
    t = Math.min(1, Math.max(0, t + Math.sign(target - t) * 0.004));
    slider.value = t;
    explode(ease(t));
  }
  controls.update();
  renderer.render(scene, camera);
})();
