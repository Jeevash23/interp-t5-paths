# Changes from the original project

This release was exported from the project folder in which the study ran. Files are copied byte for byte except
those listed below. There are four kinds of change:

- **adapted:** the code named the companion studies' folders beside the project; it now names their copies under
  `reference/flyvis-first-order` and `reference/model-vs-fly`, and P7's `config.json` names the reference study's copy.
  The study's freeze check (`code/freeze.py check`) accepts the changes listed here, through `tools/release_paths.py`.
  The run scripts take the Python from `PYTHON` and the GPU lock helper from `code/gpu_lock.py`, leave the FlyVis model
  folder out of their write audit, and no longer ask systemd to keep the machine awake.
- **redacted:** records in which personal or machine-specific strings were replaced:
  - paths: the companion studies' folders by their copies under `reference/` (so the keys of the freeze records name
    files in this release), another study's folder by `<companion-project>`, and the operating system's name by
    `[distro]`;
  - clock times: the records gave a few local clock times; this copy gives the same instants in UTC. The reference
    study's simulator sets flyvis's `TIMEZONE` (used only for the time stamps of its log messages) to UTC;
  - the work was done in sessions of a language-model assistant, as the manuscript states; the coordinating session's
    name and the assistant's working terms are replaced by neutral words ("the coordinating session", "session"), and
    the approval records name the author in the same neutral way ("approval wording");
  - the record of the search for prior work quoted a service's message about the author's account; the sentence now
    says only which search was used;
  - machine details: the GPU's model name is replaced by its memory size.
- **added:** `results/confirmation/derived/PER-SUBTYPE.csv`, the frozen readout function's output for every
  confirmation record, written for this release from the original records (see the README). It is a derived output,
  not one the study wrote.
- **not shipped:** the raw simulation records (time traces) of the confirmation run and the pilot, the run logs and
  the study's working status notes. No file named in a freeze record is left out.

`AMENDMENTS-1-2.sha256` gives the digest of `AMENDMENTS.md`, which is unchanged.

Files added for the release: `code/gpu_lock.py` (a copy of the GPU lock helper, which `code/run.sh` ran from another
study's folder), `tools/`, the READMEs, `requirements.txt`, `ENVIRONMENT.md`, `Makefile`, `LICENSE` and this file. The
files under `reference/` are copies of the companion studies' files (also part of their own releases). Saved outputs
are archives under `data/saved-outputs/`; `tools/unpack.py` restores them byte for byte and checks each SHA-256 against
`data/PACKED-FILES.json`. Compression is not a change and is not listed below.

To check both freeze records against this release: `make check-freezes`.

## Files that differ from the project originals

| File | Change | Original SHA-256 | Release SHA-256 | Frozen in |
|---|---|---|---|---|
| `AUTHOR-APPROVAL.txt` | redacted (approval wording x1, local clock time x2) | `50c587cd69935cb9b76c08e0bf1220f0c41d912f8c43c6736dadb09e4c771b0c` | `c184fed21e9042d4c1b59442db07d7d0f571f896a59493aa50f506b2bcb8e279` | `FREEZE-1.json` |
| `FREEZE-1.json` | redacted (companion study folder x6) | `fa6f732584d573340dbbc91d753f77a85e2b201cff1ba2ea21921bc69a81952a` | `f56b1346c864025b3d9166a80225fe0b68a2924e94014ce7aca805eac7485afb` | - |
| `FREEZE-2.json` | redacted (companion study folder x4) | `b740e1b8b5eb69105955f3f5ff2d9c742d79d750c2c4ac2644230afb99e8bf1f` | `a400a5c0be0574201a38503e3a72479b711f67af4217146561fc375df5e58e2c` | - |
| `PILOT-NOTES.md` | redacted (approval wording x1, machine details x1) | `7463196e4d987f1a30ab40a8d9b4743f93d21a8962aeab1a76c302dca1f2a351` | `8ee667dd495161beaf2722d58d4c3acea8746a4e1ffd0021b6e878018dca6ead` | `FREEZE-1.json` |
| `PROTOCOL-DRAFT.md` | redacted (approval wording x5, assistant wording x6, machine details x1) | `2972e26eec56d6d6cad2ba5d083299ad25e8bf6b28c691dd9d24dca3f384f5d1` | `d5de6024c08b0b47b10964b78b9933af3627c48aaa87eff9471be864ed48a4c6` | - |
| `PROTOCOL.md` | redacted (approval wording x2, assistant wording x2, companion study folder x1, machine details x3) | `217c47a52e3f014800a29a9dcf0c6838e65202cd99039e0d25aa62e27d34dff5` | `449884ff4e80d136d590f38310a4777ab0186e264d6d07a6532ec36562812e29` | `FREEZE-1.json` |
| `REPORT.md` | redacted (approval wording x1, local clock time x1, machine details x2) | `4499035e28a3b840ba8e3814fe0a914dd79d6777d84d551e29d5342ad06d9bdd` | `841ae7f000df0363d38a1d6b966bbafaba2896a36eaf2b239d08bf337103144a` | - |
| `SCOOP-CHECK.md` | redacted (account detail x1, approval wording x7, local clock time x1) | `b8a215eb9c77e48530fc8cc650722b980f977f6067d32b12cb263fe03900f3de` | `b2d6341e5e82856ff1a9232f605b39ade4723263a090452439c0122b6058d2ec` | `FREEZE-1.json` |
| `code/freeze.py` | adapted: the companion studies' files that the code reads or imports are shipped in reference/flyvis-first-order and reference/model-vs-fly; the freeze check accepts the changes this release documents (tools/release_paths.py) | `dd4cd83b65c42600f78d23172d4b363eed17b239772da91ab98ad7f3d7c742cc` | `c1ee1839059274819a2c4135a3221e903dbe3f2b42dbe28a9341f8c73efe4820` | `FREEZE-1.json` |
| `code/inspect_wiring.py` | adapted: the companion studies' files that the code reads or imports are shipped in reference/flyvis-first-order and reference/model-vs-fly | `22e275579accdd1aa22a3d1af1956791a75bc75f8f7c804110eaaa822effcf40` | `be4f4bf529c4ebb0b5db41e59f4fd2f952cc7c84a3900f8ca7a84b8980ccb7bd` | `FREEZE-1.json` |
| `code/pilot_analyse.py` | adapted: the companion studies' files that the code reads or imports are shipped in reference/flyvis-first-order and reference/model-vs-fly | `39ce2a17c7d0ae0b99ac57a3b4e4fa31be05239383bdff9a6c86ff9d15d3ac3e` | `7b37faeca008b334db4ebda7843750f5d35858459cc81648b8365247986024cd` | `FREEZE-1.json` |
| `code/pilot_run.sh` | adapted and redacted: the companion studies' files that the code reads or imports are shipped in reference/flyvis-first-order and reference/model-vs-fly; the write audit skips the FlyVis model folder, where flyvis builds its tables on first use (machine details x1) | `0244692d4dc81ad8e7996b568c580ceeb8a9f4cf86ca10fd34fd19793480dbf5` | `befa5f5965ed6068e4108b90fb651fa3adc76dc07fe46cac7165c34de377d333` | `FREEZE-1.json` |
| `code/pilot_simulate.py` | adapted: the companion studies' files that the code reads or imports are shipped in reference/flyvis-first-order and reference/model-vs-fly | `1de81fdf8ad31ad06f4ff419cb4501d0143c876e0390ca80063b5069dd38a0fb` | `305a5860f9cb9cf9ac6e7e130b88797373fddbebb4f17b320b24d97d04d63575` | `FREEZE-1.json` |
| `code/run.sh` | adapted and redacted: the companion studies' files that the code reads or imports are shipped in reference/flyvis-first-order and reference/model-vs-fly; the run no longer asks systemd to keep the machine awake (systemd-inhibit), which not every system has; the write audit skips the FlyVis model folder, where flyvis builds its tables on first use (machine details x1) | `026f82642b4923335eb83a361dab97851705b9d111beb68a9219a913c07b7f0e` | `e562ff44ec9453753e8883c732a5a0bdc8af8e7cbc3dc0adeefd6c84e1d08a36` | `FREEZE-1.json` |
| `code/score.py` | adapted: the companion studies' files that the code reads or imports are shipped in reference/flyvis-first-order and reference/model-vs-fly | `7b26ad6fdee8c3869d86f5b526a9ba710e532c014ab261fce6987e6720e967ba` | `7316b1315c8a404d46614cfe00646966fa8f5ff51c3e96eec68f8ac27410c0d1` | `FREEZE-2.json` |
| `code/score_p7_table.py` | adapted: the companion studies' files that the code reads or imports are shipped in reference/flyvis-first-order and reference/model-vs-fly | `5fee39b70a5d123d396eb96a4fc412c67fc5ea899100cc3144b5083a9465c72e` | `d02e6d8d5cd4cf345f487316a8bc7011610340a3ee889300b411141b6905ef79` | `FREEZE-2.json` |
| `code/simulate.py` | adapted: the companion studies' files that the code reads or imports are shipped in reference/flyvis-first-order and reference/model-vs-fly | `eae43970de4fe43d26bf05b2a90a9fffc48474747218f8952de4c104be995e2c` | `39b7093757199d0f1aeba33d040b4dc01ffb5e19c36b1660174109f689f9de0d` | `FREEZE-1.json` |
| `recheck/RECHECK.md` | redacted (assistant wording x1, machine details x1) | `cafc2b13e932310bfd3667e3f5f86a6ecf765e6ea1cc4dce2b455b02117c5755` | `d5e177757d1d9da70fe125a9d971bd58f27b718d2a8ed28479c46f0a87f0b6eb` | - |
| `recheck/recheck.py` | adapted: the companion studies' files that the code reads or imports are shipped in reference/flyvis-first-order and reference/model-vs-fly | `d03200b2ee7d951137a5bb7b092cc9665332bbf592f6aaad29f0b272e42ecab2` | `8a6bd62f9de8f063b156125665dbe346ee0a4056e0a7cd31ce52e359f77c8ee8` | - |
| `reference/flyvis-first-order/02-Code/stage1/common.py` | redacted (time zone x1) | `e465cb2e1e16b52433e9a642365f2ca6c910ef8d60dbe1bbe91146de648fff50` | `9834aeb2355a31a04faf0cc7611047f02983b6f0b72e118196f94f4884980f41` | `FREEZE-1.json` |
| `reference/model-vs-fly/config.json` | adapted: P7's configuration names the reference study's copy in this release | `fbfd5c991f4fa08433ecfffb0e65ca40ea2135334eb957a7698a74bd1c6e33ea` | `2824f035ee2fb3e43af393be952e06d6a4df9f913803f387613dd6b112bd2142` | `FREEZE-2.json` |
| `results/confirmation/confirmation-run.json` | redacted (machine details x1, platform string x1); shipped inside `data/saved-outputs/study-results.tar.xz` | `1b446114208f3123b660d2ca5eec43db50035a093daed614b89269657be1d222` | `aeaa01602814f4e7d91468504ddaea5cd96e3465b31e5623ae82a0541bc40e2a` | - |
| `results/confirmation/scores/P7-TABLE-RESCORE.json` | redacted (companion study folder x1); shipped inside `data/saved-outputs/study-results.tar.xz` | `bf0a27dd055d582c6bf22b4380c7e6626128b737a7fa286d03281cb0e79ffe8c` | `6a21d29e780462d0c6a4e447dc2a7fb46a9f68d197a7af793d776740e20b06f8` | - |
| `results/pilot-v1/pilot-run-000-only.json` | redacted (machine details x1, platform string x1); shipped inside `data/saved-outputs/study-results.tar.xz` | `f9787d6bc82da034bd32884845eb1de1cfe5a9fd3d546b7a5522e93c1cad6d8e` | `9c2da8906b65c235d569c9c77cd5078197bf4a05b242cf013cb61053c09bf14b` | - |
| `results/pilot-v1/pilot-run.json` | redacted (machine details x1, platform string x1); shipped inside `data/saved-outputs/study-results.tar.xz` | `1d7b5e92a4b565fd176f1f0bf6bdb6361ed0d494d673ce933ecb6ee49386c103` | `1d12e552cbd8f9bda1cb67cfe30e02b24e4d96019afbce717a22262193260d44` | - |
| `results/pilot/pilot-run.json` | redacted (machine details x1, platform string x1); shipped inside `data/saved-outputs/study-results.tar.xz` | `5b28c527cb2d3aa3566e0453b62b52791105254c85d7ee1ec9ca93e5e4695a4f` | `0f4a27ec5efa961d03b2b56b10a2a7bb5b0f9e854b9691208740c5b662600e6e` | `FREEZE-1.json` |
| `results/pilot/scores-selftest/P7-TABLE-RESCORE.json` | redacted (companion study folder x1); shipped inside `data/saved-outputs/study-results.tar.xz` | `b374b5309a42a85e6e6247da8e7d34c439e8baa6251d8d3a9e38c134b6a2543e` | `ab6217f25a87102c69c94e27b3305f828399c9714145624c0b15a90d400518cc` | - |
