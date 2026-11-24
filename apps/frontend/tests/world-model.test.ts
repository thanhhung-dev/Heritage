import assert from "node:assert/strict";
import test from "node:test";
import { resolveWorldFiles, resolveWorldUrl } from "../features/tour/three/world-model";
import type { HeritageModelAsset } from "../types/heritage";

function model(partial: Partial<HeritageModelAsset> & Pick<HeritageModelAsset, "file_url">): HeritageModelAsset {
  return {
    id: 1,
    format: "glb",
    lod_level: 0,
    compression: null,
    file_size_bytes: null,
    ...partial,
  };
}

test("scene without its own GLB stays on the tour default world", () => {
  assert.equal(resolveWorldUrl(null, "/ext.glb"), "/ext.glb");
  assert.equal(resolveWorldUrl({ models: [] }, "/ext.glb"), "/ext.glb");
});

test("interior scene picks its own GLB and ignores splat plus higher LOD", () => {
  const url = resolveWorldUrl({
    models: [
      model({ id: 1, file_url: "/int-lod1.glb", lod_level: 1 }),
      model({ id: 2, file_url: "/int.splat", format: "splat", lod_level: 0 }),
      model({ id: 3, file_url: "/int.glb", lod_level: 0 }),
    ],
  }, "/ext.glb");
  assert.equal(url, "/int.glb");
});

test("missing format still accepts a glTF url and skips a blank url", () => {
  const url = resolveWorldUrl({
    models: [
      model({ file_url: "  ", format: "glb" }),
      model({ file_url: "/room.gltf", format: "" }),
    ],
  }, "/ext.glb");
  assert.equal(url, "/room.gltf");
});

test("use_interior_model selects the heritage interior GLB unless the scene has its own", () => {
  assert.equal(
    resolveWorldUrl({ models: [], use_interior_model: true }, "/ext.glb", "/int.glb"),
    "/int.glb",
  );
  assert.equal(
    resolveWorldUrl({ models: [], use_interior_model: false }, "/ext.glb", "/int.glb"),
    "/ext.glb",
  );
  assert.equal(
    resolveWorldUrl(
      { models: [model({ file_url: "/own.glb" })], use_interior_model: true },
      "/ext.glb",
      "/int.glb",
    ),
    "/own.glb",
  );
});

test("multiple GLBs show the coarsest LOD first and keep the lowest as the full file", () => {
  const files = resolveWorldFiles({
    models: [
      model({ id: 1, file_url: "/int-lod1.glb", lod_level: 1 }),
      model({ id: 3, file_url: "/int.glb", lod_level: 0 }),
      model({ id: 4, file_url: "/int-lod2.glb", lod_level: 2 }),
    ],
  }, "/ext.glb");
  assert.deepEqual(files, { preview: "/int-lod2.glb", full: "/int.glb" });
});

test("a single interior URL has no separate preview", () => {
  assert.deepEqual(
    resolveWorldFiles({ models: [], use_interior_model: true }, "/ext.glb", "/int.glb"),
    { preview: "/int.glb", full: "/int.glb" },
  );
});

