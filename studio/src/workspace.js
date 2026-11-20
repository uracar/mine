// A project folder that the AIs can read and write, and nothing outside it.
import fs from "node:fs";
import path from "node:path";
import { LIMITS } from "./config.js";

export class Workspace {
  constructor(root) {
    this.root = path.resolve(root);
    fs.mkdirSync(this.root, { recursive: true });
  }

  // Turn a model-supplied relative path into a real path, refusing anything
  // that escapes the project folder ("..", absolute paths, symlinks out).
  resolve(relPath) {
    if (typeof relPath !== "string" || relPath.trim() === "") {
      throw new Error("path must be a non-empty string");
    }
    const target = path.resolve(this.root, relPath);
    const rel = path.relative(this.root, target);
    if (rel === "" || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) {
      throw new Error(`path "${relPath}" is outside the project folder`);
    }
    // Check the deepest existing ancestor with realpath so a symlink can't lead out.
    let probe = target;
    while (!fs.existsSync(probe)) probe = path.dirname(probe);
    const real = fs.realpathSync(probe);
    const realRoot = fs.realpathSync(this.root);
    if (real !== realRoot && !real.startsWith(realRoot + path.sep)) {
      throw new Error(`path "${relPath}" resolves outside the project folder`);
    }
    return target;
  }

  relative(absPath) {
    return path.relative(this.root, absPath).split(path.sep).join("/");
  }

  read(relPath) {
    const p = this.resolve(relPath);
    if (!fs.existsSync(p)) throw new Error(`no such file: ${relPath}`);
    return fs.readFileSync(p, "utf8");
  }

  write(relPath, contents) {
    if (Buffer.byteLength(contents, "utf8") > LIMITS.maxFileBytes) {
      throw new Error(`file too large (limit ${LIMITS.maxFileBytes} bytes); split it into modules`);
    }
    const p = this.resolve(relPath);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, contents, "utf8");
    return contents.split("\n").length;
  }

  // Replace one exact snippet. Fails unless it appears exactly once.
  edit(relPath, oldStr, newStr) {
    const text = this.read(relPath);
    const count = text.split(oldStr).length - 1;
    if (count === 0) throw new Error(`old_str not found in ${relPath}; read the file and copy the text exactly`);
    if (count > 1) throw new Error(`old_str appears ${count} times in ${relPath}; include more surrounding text`);
    this.write(relPath, text.replace(oldStr, () => newStr));
  }

  list(dir = ".") {
    const start = dir === "." ? this.root : this.resolve(dir);
    if (!fs.existsSync(start)) return [];
    const out = [];
    const walk = (d) => {
      for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
        const full = path.join(d, entry.name);
        if (entry.isDirectory()) walk(full);
        else out.push(`${this.relative(full)} (${fs.statSync(full).size} bytes)`);
      }
    };
    walk(start);
    return out.sort();
  }
}
