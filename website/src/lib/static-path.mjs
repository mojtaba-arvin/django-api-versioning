import { realpath, stat } from "node:fs/promises";
import path from "node:path";

export function normalizeBasePath(value = "/") {
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
