#!/usr/bin/env node
/** Validate and copy the committed source evidence into Astro's public directory. */
import { copyFile, mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const websiteRoot = path.resolve(scriptDirectory, "..");
const generatedDirectory = path.join(websiteRoot, "src", "data", "generated");
const publicDirectory = path.join(websiteRoot, "public", "data");
const routesPath = path.join(generatedDirectory, "routes.json");
const outputPath = path.join(generatedDirectory, "check_versions_output.txt");
const routes = JSON.parse(await readFile(routesPath, "utf8"));
const checkOutput = await readFile(outputPath, "utf8");

if (routes.schema_version !== 1) throw new Error("Unsupported routes.json schema version.");
if (!/^[a-f0-9]{40}$/.test(routes.source?.commit ?? "")) throw new Error("Evidence has no full source commit SHA.");
if (!routes.source?.files?.length || !routes.source?.evidence_files?.length) {
  throw new Error("Evidence must include package and lab input hashes.");
}
if (!routes.scenarios?.main || Object.keys(routes.scenarios).length !== 18) {
  throw new Error("Expected the 18 recorded Segment Lab scenarios.");
}
const recordedRun = routes.scenarios.main.check_versions?.find(
  (run) => run.command === "python manage.py check_versions" && run.exit_code === 0,
);
if (!recordedRun || recordedRun.stdout !== checkOutput) {
  throw new Error("check_versions_output.txt does not match the recorded successful command output.");
}

await mkdir(publicDirectory, { recursive: true });
await copyFile(routesPath, path.join(publicDirectory, "routes.json"));
await copyFile(outputPath, path.join(publicDirectory, "check_versions_output.txt"));
console.log("[evidence] copied " + Object.keys(routes.scenarios).length + " scenarios from source commit " + routes.source.commit.slice(0, 7) + ".");
