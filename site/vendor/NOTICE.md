# Viewer dependency

`model-viewer.min.js` is the bundled distribution of `@google/model-viewer` 4.3.1 by Google and contributors, with the compatibility patch described below, licensed under Apache-2.0 (see LICENSE-model-viewer). Bundled third-party notices are retained in the distribution.

Source: https://github.com/google/model-viewer

Package: https://registry.npmjs.org/@google/model-viewer/-/model-viewer-4.3.1.tgz

The collection's CC BY-NC-ND license does not replace this software license.

## Pivot metadata compatibility patch

The bundled GLTFLoader interprets any node `extras.pivot` value as a numeric
three-component pivot. This collection's existing GLBs use that optional metadata
field for a human-readable description. Treating the description as a vector
produces `NaN` node transforms and a blank viewer.

The loader condition now requires an array of exactly three finite numbers before
performing its pivot conversion. Other metadata values, including descriptions,
remain unchanged. Numeric pivots retain the upstream behavior. Released GLBs,
geometry, artwork, and animation data are unchanged.

The only distribution edit is this condition:

```diff
-if(void 0!==e.userData.pivot&&i.length>0)
+if(Array.isArray(e.userData.pivot)&&e.userData.pivot.length===3&&e.userData.pivot.every(Number.isFinite)&&i.length>0)
```

- Upstream SHA-256: `283b0672384614b4847636c306fc93fe4b1fcadc76d668b4e47f0ca76bcf033b`
- Patched SHA-256: `22bd28e639df581c1cf59ccebd51cee7b437ddf095eac1d8392d24baec2f38b8`
- Regression check: `node --test tools/test_model_viewer_compat.mjs`

The regression executes the actual patched branch from the bundled loader. It
checks descriptive metadata, numeric pivots, malformed values, and nodes without
children; it also verifies that reversing this one condition reproduces the
upstream distribution hash.
