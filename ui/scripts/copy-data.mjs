// Copies the aggregate export (python -m screening export-ui) into public/ for the app.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../reports/ui/data.json");
const dst = resolve(here, "../public/data.json");

if (!existsSync(src) && !existsSync(dst)) {
  console.error(`Missing ${src} and ${dst}\nProvide the approved aggregate export at public/data.json or regenerate it using the Python pipeline.`);
  process.exit(1);
}

if (existsSync(src)) {
  mkdirSync(dirname(dst), { recursive: true });
  copyFileSync(src, dst);
  console.log(`data.json -> ${dst}`);
} else {
  console.log(`Using existing public data: ${dst}`);
}
