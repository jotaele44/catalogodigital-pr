# catalogodigital-pr — Catálogo Digital de Puerto Rico (PRDC)

Directorio independiente de datos de Puerto Rico. Cataloga fuentes, instituciones, documentos y conjuntos de datos mediante estándares de procedencia, trazabilidad, interoperabilidad, calidad y reproducibilidad científica.

Independent, Spanish-primary/bilingual-target, data-first catalog. Metadata and direct links first; selective preservation only. No official endorsement implied.

**Pre-implementation candidate.** The recovered local foundation is extended with typed SQLite contracts, institutional universe scaffolding, format/protocol vocabularies and fail-closed access. No live source verification, bulk acquisition, public release or AFK certification.

## Replay

```sh
sha256sum -c checksums.sha256
python -m unittest discover -s tests -v
python -m prdc
```

Original APF candidate: `specifications/APF-v1.0.md`; revision 2: `specifications/APF-v1.0-candidate-r2.md`. Gate inventory: `reports/gates.json`. The overlay manifest excludes existing remote `.gitignore` and `LICENSE`, which are preserved on GitHub. The local test receipt is not hosted CI evidence.
