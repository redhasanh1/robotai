// Static server for the robotai project site. No dependencies.
// Serves site/, data/*.json, research/*.md and the BOM spreadsheet straight from the repo,
// so a push to GitHub (which Railway redeploys) is all it takes to update the site.
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const PORT = process.env.PORT || 3000;
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
  ".urdf": "application/xml; charset=utf-8",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
};

// Only these paths are public; everything else in the repo stays private.
function resolve(urlPath) {
  const p = decodeURIComponent(urlPath.split("?")[0]);
  if (p === "/") return path.join(ROOT, "site", "index.html");
  if (p === "/robotai_BOM.xlsx") return path.join(ROOT, "robotai_BOM.xlsx");
  if (/^\/data\/[\w-]+\.json$/.test(p)) return path.join(ROOT, p);
  if (/^\/research\/[\w-]+\.md$/.test(p)) return path.join(ROOT, p);
  if (/^\/models\/[\w.-]+\.urdf$/.test(p)) return path.join(ROOT, "site", p);
  if (/^\/img\/[\w.-]+\.(png|jpe?g|webp|gif|svg)$/.test(p)) return path.join(ROOT, "site", p);
  if (/^\/[\w-]+\.(css|js|svg|png|jpg)$/.test(p)) return path.join(ROOT, "site", p);
  return null;
}

http
  .createServer((req, res) => {
    const file = resolve(req.url);
    if (!file) {
      res.writeHead(404).end("Not found");
      return;
    }
    fs.readFile(file, (err, body) => {
      if (err) {
        res.writeHead(404).end("Not found");
        return;
      }
      res.writeHead(200, {
        "Content-Type": TYPES[path.extname(file)] || "application/octet-stream",
        "Cache-Control": "no-cache",
      });
      res.end(body);
    });
  })
  .listen(PORT, () => console.log(`robotai site on :${PORT}`));
