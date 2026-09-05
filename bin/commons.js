#!/usr/bin/env node
// Private shim: forwards every argument to the installed aafp-commons
// Python package via `python -m aafp_commons`. Contains no ledger, signing,
// policy, constitution, packet, or world logic. Requires the aafp-commons
// wheel to be importable by the resolved interpreter.

const { spawn } = require("child_process");

const args = process.argv.slice(2);

function trySpawn(interpreter, cb) {
  const child = spawn(interpreter, ["-m", "aafp_commons", ...args], {
    stdio: "inherit",
  });
  child.on("error", (err) => {
    if (err.code === "ENOENT") {
      cb(err);
    } else {
      process.exitCode = 1;
      process.stderr.write(
        "commons: " + interpreter + " failed: " + err.message + "\n"
      );
    }
  });
  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
    } else {
      process.exitCode = code;
    }
  });
}

trySpawn("python3", (err) => {
  // python3 missing on PATH; fall back to python
  trySpawn("python", (err2) => {
    process.exitCode = 127;
    process.stderr.write(
      "commons: no python3 or python on PATH; install aafp-commons and retry.\n"
    );
    process.stderr.write(
      "  (" + err.message + " / " + err2.message + ")\n"
    );
  });
});
