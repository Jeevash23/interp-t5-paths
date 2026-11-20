# Saved outputs

The studies' results, packed as deterministic tar archives compressed with xz. Member paths are relative to the release root, so `make unpack` (or `python tools/unpack.py`) puts every file where the study code reads it and checks each SHA-256 against `data/PACKED-FILES.json`. Text records inside the archives had personal strings replaced, as listed in `RELEASE-CHANGES.md`.

| Archive | Files | Packed (MB) | Unpacked (MB) | Contents |
|---|---|---|---|---|
| `reference-study-results.tar.xz` | 103 | 19.2 | 36.5 | the reference study's tables of exact silencing (development and confirmation models), which the replication checks read, its intact-network records of the 50 models at both stimuli, which P7's pooling and the simulator's identity check read, and P7's saved comparisons, which the re-scoring of P7's fly table reproduces |
| `study-results.tar.xz` | 11726 | 2.7 | 22.3 | the study's saved outputs: the confirmation run's record, each simulation record's metadata (with the SHA-256 of the record, whose time traces are not shipped), the wiring summaries, the scores, the per-subtype readouts from which the scores are replayed (added for the release), the independent recheck's output, and the development pilot's reports, tables, self-test scores and record metadata |

Total packed size: 21.9 MB. Rendered figures are not included; `make figures` draws them from these outputs.
