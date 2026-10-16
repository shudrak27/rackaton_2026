// Copies the aggregate export (python -m screening export-ui) into public/ for the app.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../reports/ui/data.json");
const dst = resolve(here, "../public/data.json");

if (!existsSync(src)) {
  console.error(`Missing ${src}\nRun: python -m screening train && python -m screening export-ui`);
  process.exit(1);
}
mkdirSync(dirname(dst), { recursive: true });
copyFileSync(src, dst);
console.log(`data.json -> ${dst}`);
