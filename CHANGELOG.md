# Changelog

## 0.6.0 (unreleased)

### Added

- Integrate the native TypeSafe frontend into the local console and source-export
  public lab, with byte-bound art and token constants in the Python package (#78).

### Fixed

- Clear stale report decisions when the submitted evidence changes (#78).
- Fail closed on mismatched twelfth-gate source and raw study evidence.
- Wrap long identity text on narrow screens.
- Check installed distributions with isolated Python and verify dependency
  consistency in the canonical release gate.

Distribution metadata reads its version from `szl_triage.__version__`.
The bundled `szl_decide` component retains its own version.

### Runtime scope

The wheel supports `szl-triage decide` and the loopback `szl-triage serve` command.
The separately deployed public lab requires its source export and
`SOURCE_BINDING.json`, as described in the README; it is not a wheel-only entry
point.

Earlier releases are documented in GitHub Releases.
