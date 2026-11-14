/**
 * Typed access to src/data/routes.json (written by tools/generate_routes.py).
 *
 * Everything the site shows about package behaviour is read from here.
 * Helpers below only *reshape* recorded values (group, filter, format);
 * they never invent behaviour.
 */
import raw from "../data/generated/routes.json";

export interface RegistryRow {
  index: number;
  route: string;
  postfix: string;
  name: string | null;
  route_version: number | null;
  source_version: number | null;
  callback: string;
  view_class: string | null;
  actions: Record<string, string> | null;
}
export interface RequestRecord {
  method: string;
  path: string;
  status: number;
  headers: Record<string, string>;
  body: unknown;
  package_calls: Record<string, number>;
  resolve: {
    error?: string;
    route?: string;
    url_name?: string | null;
    callback?: string;
    view_class?: string | null;
    registry_index?: number | null;
    patterns_tried: number;
    kwargs?: Record<string, unknown>;
  };
}
export interface CheckVersionsRun {
  command: string;
  env: Record<string, string>;
  exit_code: number;
  stdout: string;
  stderr: string | null;
  stderr_last_line: string;
  stderr_line_count: number;
}
export interface MatrixCell {
  callback: string;
  source_version: number | null;
  route: string;
}
export interface Scenario {
  scenario: string;
  title: string;
  question: string;
  views_module: string | null;
  views_source: { file: string; code: string } | null;
  settings_overrides: Record<string, unknown>;
  effective_settings: {
    "django.conf.settings": {
      API_BASE_PATH: string;
      API_MIN_VERSION: number;
      API_MAX_VERSION: number;
      MIDDLEWARE: string[];
      REST_FRAMEWORK: Record<string, unknown>;
      API_VERSION_LIFECYCLE: Record<string, unknown> | null;
      LAB_VIEWS_MODULE: string | null;
    };
    "django_api_versioning.settings.api_settings": {
      API_BASE_PATH: string;
      API_MIN_VERSION: number;
      API_MAX_VERSION: number;
    };
  };
  registry: RegistryRow[];
  matrix: Record<string, Record<string, MatrixCell>>;
  build_version_matrix: Record<string, Record<string, string>>;
  check_versions: CheckVersionsRun[];
  requests: RequestRecord[];
  reverse: { call: string; result: string | null; error: { type: string; message: string } | null }[];
  logs: { phase: string; level: string; logger: string; message: string }[];
  recorded_errors?: { case: string; error: string | null; message: string | null }[];
  registry_size_after_setup: number;
  setup_package_calls: Record<string, number>;
  urlconf_import: {
    ok: boolean;
    error: { type: string; message: string; frames: { file: string; line: number; function: string; code: string }[] } | null;
    package_calls: Record<string, number>;
    registry_size_after: number;
  };
  matrix_equal_to?: { scenario: string; equal: boolean };
}
export interface RoutesData {
  schema_version: number;
  generated_at: string;
  generator: string;
  source: {
    repository: string;
    package: string;
    version: string;
    commit: string;
    install_url: string;
    install_method: string;
    archive_sha256: string | null;
    files: { file: string; sha256: string }[];
  };
  environment: { python: string; implementation: string; django: string; djangorestframework: string };
  source_refs: {
    symbols: Record<string, { file: string; start: number; end: number }>;
    lines: Record<string, { file: string; line: number; code: string }>;
    non_routing_settings_usage: Record<string, { file: string; line: number }[]>;
  };
  lab_settings_file: { file: string; code: string };
  lab_urls_file: { file: string; code: string };
  scenarios: Record<string, Scenario>;
}

export const data = raw as unknown as RoutesData;
export const source = data.source;
export const shortCommit = source.commit.slice(0, 7);
export const env = data.environment;

export function scenario(name: string): Scenario {
  const s = data.scenarios[name];
  if (!s) throw new Error(`Scenario ${name} is not in routes.json`);
  return s;
}

export const scenarioNames = Object.keys(data.scenarios);

/** GitHub permalink pinned to the recorded commit. */
export function gh(file: string, start?: number, end?: number): string {
  const anchor = start ? `#L${start}${end && end !== start ? `-L${end}` : ""}` : "";
  return `${source.repository}/blob/${source.commit}/${file}${anchor}`;
}
export function symbolRef(key: string) {
  const s = data.source_refs.symbols[key];
  if (!s) throw new Error(`Unknown symbol ref ${key}`);
  return { ...s, url: gh(s.file, s.start, s.end), label: `${s.file.replace("django_api_versioning/", "")}:${s.start}` };
}
export function lineRef(key: string) {
  const s = data.source_refs.lines[key];
  if (!s) throw new Error(`Unknown line ref ${key}`);
  return { ...s, url: gh(s.file, s.line), label: `${s.file.replace("django_api_versioning/", "")}:${s.line}` };
}

export const pypiUrl = `https://pypi.org/project/${source.package}/${source.version}/`;
export const repoUrl = source.repository;
export const commitUrl = `${source.repository}/commit/${source.commit}`;
export const docsUrl = `${source.repository}/blob/${source.commit}/README.md`;
export const contractUrl = `${source.repository}/blob/${source.commit}/docs/reference/versioning-contract.md`;

/** Versions API_MIN_VERSION..API_MAX_VERSION as seen by the package. */
export function versionsOf(s: Scenario): number[] {
  const { API_MIN_VERSION: min, API_MAX_VERSION: max } = s.effective_settings["django_api_versioning.settings.api_settings"];
  return Array.from({ length: max - min + 1 }, (_, i) => min + i);
}

export interface Segment {
  postfix: string;
  callback: string;
  source_version: number | null;
  from: number;
  to: number;
  /** true when the run starts at its own declared version (a declaration point). */
  startsAtDeclaration: boolean;
}

/**
 * Group registry rows of one postfix into runs of consecutive versions that
 * share callback + source_version. Pure reshaping of recorded rows.
 */
export function segmentsOf(s: Scenario, postfix: string): Segment[] {
  const rows = s.registry
    .filter((r) => r.postfix === postfix && r.route_version !== null)
    .sort((a, b) => (a.route_version! - b.route_version!));
  const out: Segment[] = [];
  for (const r of rows) {
    const label = r.view_class ?? r.callback;
    const last = out.at(-1);
    if (last && last.callback === label && last.source_version === r.source_version && last.to === r.route_version! - 1) {
      last.to = r.route_version!;
    } else {
      out.push({
        postfix,
        callback: label,
        source_version: r.source_version,
        from: r.route_version!,
        to: r.route_version!,
        startsAtDeclaration: r.source_version === r.route_version,
      });
    }
  }
  return out;
}

export function postfixesOf(s: Scenario): { versioned: string[]; unversioned: RegistryRow[] } {
  const versioned = [...new Set(s.registry.filter((r) => r.route_version !== null).map((r) => r.postfix))];
  const unversioned = s.registry.filter((r) => r.route_version === null);
  return { versioned, unversioned };
}

/** Stable colour slot per callback inside one scenario (presentation only). */
export function colourSlots(s: Scenario): Map<string, number> {
  const map = new Map<string, number>();
  for (const r of s.registry) {
    const label = r.view_class ?? r.callback;
    if (!map.has(label)) map.set(label, map.size % 4);
  }
  return map;
}

export function request(s: Scenario, path: string): RequestRecord {
  const r = s.requests.find((q) => q.path === path);
  if (!r) throw new Error(`Request ${path} not recorded in ${s.scenario}`);
  return r;
}

export function totalCalls(calls: Record<string, number>, match?: string): number {
  return Object.entries(calls)
    .filter(([k]) => !match || k.endsWith(match))
    .reduce((n, [, v]) => n + v, 0);
}

/** 1-based line numbers in a recorded source file that contain `needle`. */
export function linesContaining(code: string, needle: string): number[] {
  return code
    .split("\n")
    .map((l, i) => (l.includes(needle) ? i + 1 : 0))
    .filter(Boolean);
}

export function labCommand(name: string, cmd = "check_versions"): string {
  return name === "main" ? `python manage.py ${cmd}` : `LAB_SCENARIO=${name} python manage.py ${cmd}`;
}

export const generatedDate = data.generated_at.slice(0, 10);