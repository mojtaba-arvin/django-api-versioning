#!/usr/bin/env node
/** Serve the generated static artifact, including clean URLs and project-site bases. */
import { createReadStream } from "node:fs";
import { realpath, stat } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const websiteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const root = path.resolve(process.env.DIST_DIR ?? path.join(websiteRoot, "dist"));
const host = process.env.HOST ?? "127.0.0.1";
const port = Number(process.env.PORT ?? 4173);
const basePath = process.env.PUBLIC_BASE_PATH ?? "/";
const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".xml": "application/xml; charset=utf-8",
};

function normalizeBasePath(value = "/") {
  const parts = value.split("/").filter(Boolean);
  return parts.length ? `/${parts.join("/")}` : "";
}

/** Resolve a request path to a regular file contained by the static output root. */
export async function resolveStaticFile(rootDirectory, pathname, configuredBasePath = "/") {
  let decoded;
  try { decoded = decodeURIComponent(pathname); } catch { return null; }
  if (decoded.includes("\\") || decoded.includes("\0")) return null;

  const rootDirectoryPath = path.resolve(rootDirectory);
  const basePrefix = normalizeBasePath(configuredBasePath);
  if (basePrefix) {
    if (decoded === basePrefix) decoded = "/";
    else if (decoded.startsWith(basePrefix + "/")) decoded = decoded.slice(basePrefix.length);
    else return null;
  }

  const relative = decoded.replace(/^\/+/, "");
  const candidate = path.resolve(rootDirectoryPath, relative);
  if (candidate !== rootDirectoryPath && !candidate.startsWith(rootDirectoryPath + path.sep)) return null;

  let file = candidate;
  try {
    const candidateInfo = await stat(file);
    if (candidateInfo.isDirectory()) file = path.join(file, "index.html");
  } catch {
    if (!path.extname(file)) file = path.join(file, "index.html");
  }

  try {
    const [fileInfo, realRoot, realFile] = await Promise.all([
      stat(file),
      realpath(rootDirectoryPath),
      realpath(file),
    ]);
    if (!fileInfo.isFile()) return null;
    if (realFile !== realRoot && !realFile.startsWith(realRoot + path.sep)) return null;
    return realFile;
  } catch {
    return null;
  }
}

const server = createServer(async (request, response) => {
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405, { Allow: "GET, HEAD" }).end();
    return;
  }
  const pathname = new URL(request.url ?? "/", "http://localhost").pathname;
  const file = await resolveStaticFile(root, pathname, basePath);
  if (!file) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" }).end("Not found\n");
    return;
  }
  const info = await stat(file);
  response.writeHead(200, {
    "Content-Type": types[path.extname(file)] ?? "application/octet-stream",
    "Content-Length": info.size,
    "X-Content-Type-Options": "nosniff",
  });
  if (request.method === "HEAD") response.end();
  else createReadStream(file).pipe(response);
});

server.listen(port, host, () => {
  const mount = normalizeBasePath(basePath);
  console.log(`Serving ${root} at http://${host}:${port}${mount}/`);
});
