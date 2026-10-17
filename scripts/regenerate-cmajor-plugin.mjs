#!/usr/bin/env node
/**
 * Regenerate the embedded JUCE C++ source from the current Cmajor patch.
 *
 * Usage:
 *   CMAJOR_INCLUDE_PATH=/path/to/cmajor/include node scripts/regenerate-cmajor-plugin.mjs
 *   node scripts/regenerate-cmajor-plugin.mjs /path/to/cmajor/include
 *
 * This copies only cmajor_plugin.cpp back to the repository, preserving the
 * Njohrr-specific helper headers under include/.
 */
import { spawnSync } from "node:child_process";
import { copyFile, mkdtemp, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const includePath = process.env.CMAJOR_INCLUDE_PATH || process.argv[2];

if (!includePath) {
  console.error("Set CMAJOR_INCLUDE_PATH or pass the path to the Cmajor include directory.");
  process.exit(2);
}

const cmajCommand = process.env.CMAJ_EXECUTABLE || "cmaj";
const outputDir = await mkdtemp(path.join(tmpdir(), "njohrr-cmajor-"));

async function findGeneratedFile(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isFile() && entry.name === "cmajor_plugin.cpp") return fullPath;
    if (entry.isDirectory()) {
      const found = await findGeneratedFile(fullPath);
      if (found) return found;
    }
  }
  return null;
}

try {
  const args = [
    "generate",
    "--target=juce",
    "--output=" + outputDir,
    "--cmajorIncludePath=" + path.resolve(includePath),
    path.join(root, "patch", "Eisenpuls_Synth.cmajorpatch"),
  ];
  const result = spawnSync(cmajCommand, args, { cwd: root, stdio: "inherit" });

  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error("cmaj generate failed with exit code " + result.status);
  }

  const generatedCpp = await findGeneratedFile(outputDir);
  if (!generatedCpp) {
    throw new Error("Generation completed but no cmajor_plugin.cpp was found in " + outputDir);
  }

  await copyFile(generatedCpp, path.join(root, "cmajor_plugin.cpp"));
  console.log("Updated cmajor_plugin.cpp from patch/Eisenpuls_Synth.cmajorpatch.");
  console.log("Now rebuild the VST3 so the embedded UI includes the FX tab.");
} catch (error) {
  console.error(error.message || error);
  process.exitCode = 1;
} finally {
  await rm(outputDir, { recursive: true, force: true });
}
