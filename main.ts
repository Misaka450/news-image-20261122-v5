import { mkdirSync, copyFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const currentDir = dirname(fileURLToPath(import.meta.url));
const sourceImagePath = join(currentDir, 'entry.png');
const targetOutputDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const targetImagePath = join(targetOutputDir, 'entry.png');

mkdirSync(targetOutputDir, { recursive: true });
copyFileSync(sourceImagePath, targetImagePath);
process.exitCode = 0;
