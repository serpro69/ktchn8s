# NFS workflow cleanup — local verification and review

The checkout matched the handoff: clean `feat/nas_layout` at
`b3e25da50ce81db785c655cf2593f0278bf7f376`. This record covers the subsequent
uncommitted workflow cleanup, not a deployed revision or a new live acceptance.

## Scope and preserved contracts

The [public guide](../../../../guides/how_to_use_nfs_for_persistent_storage.md)
now separates provisioning, optional post-install probes, disruptive two-client
acceptance and migration-tool verification. NFS checks moved to the
`nfs_validation` role; targeted existing-client preparation moved to focused
prerequisites task entry points. Public acceptance play names and the legacy
`validate_nfs` route remain available. New Make targets do not invoke storage
convergence or controller dependency installation.

Twelve relocated files are byte-identical to the baseline. The lifecycle entry
changes its helper include and completion wording. Shared controller preflight
now runs before scratch writes in both validation paths, requires an absolute
kubeconfig path and avoids checksumming that file.
Basic validation adds admission and mounted-storage guards. The audit play,
confined harness, core migration helper, task completion record and user settings
restriction are unchanged. Existing provisioning/export/maintenance follow-ups
remain in [implementation.md](../implementation.md#deferred-follow-ups-explicit).

## Local verification

All checks below used existing tools, synthetic data and temporary workspaces.
No development-shell startup or dependency installation was needed.

| Check | Result and limit |
| --- | --- |
| `test_nfs_workflow.py` | Seven tests passed: sixteen recorded Make cases and 17 real Ansible assertion-only admission cases. Python 3.10.12 and Ansible Core 2.19.4. No operational task execution. |
| `test_nfs_readiness.py` | Six tests passed without skips on existing venv Python 3.12.10; shared payload and VM-controller teardown regressions. No VMs launched. |
| `test_nfs_readiness_backing.sh` | Seven local synthetic backing-link cases passed. No mounts. |
| Offline Ansible syntax | Four public check/repair plays, the Molecule verifier and all twelve initial role task entry points parsed using installed collections. Dynamic entries were also imported explicitly; the later preflight extraction and its callers were rechecked. |
| Offline Pod rendering | Unpinned writer, pinned writer and pinned reader rendered; shared payload, UID1000, scoped NFS path and placement checked. No Kubernetes command executed. |
| Documentation | 39 final local links, including this review record, and exact installed-Markdown heading anchors passed; one new migration-task anchor corrected. MkDocs/environment repair deliberately not reopened. |
| Source reconciliation | No former explicit task/asset paths remain in the bounded source/documentation reference search; expected `tasks_from` callers resolve to their new roles. `git diff --check` passed. |

The first workflow-test run failed because its result matcher expected Ansible's
default assertion message even when a task supplies `fail_msg`. The matcher was
corrected to require `evaluated_to: false`; all five initial tests then passed. The final suite adds default-config and tag-filter
regressions for seven passing tests. The operational assertions were not weakened.

## Independent code review

The isolated `code-reviewer` (GPT-6.1 Sol) approved the repository code with no
P0–P3 findings. It inspected 43 original paths: 31 changed files and twelve
unchanged contracts/callers, using sanitized candidate and historical source.
Its role-metadata and stale-reference evidence requests were resolved. It also
reviewed the final guide-anchor correction and bounded TODO update. A focused
continuation approved the final Make/preflight/test fixes with no findings after
inspecting fifteen additional or updated files; no evidence requests remain.

Supported in source against the review base: default provisioning order, the
legacy/basic validation paths, fixture ownership and teardown gates, full
independent-client lifecycle, role-variable/asset resolution, Make routing and
migration-tool separation. The reviewer performed no tests or host operations.
Live behavior after relocation remains unverified by this review.

The external reviewer (observed Claude Opus 5.5) initially returned COMMENT
with one P2 and five P3 findings: expanded environment-based kubeconfig selection,
a bad/newly fixed anchor, a feature-branch link, tag filtering, late controller
preflight and incomplete recorder coverage. The fixes restore the baseline
config-selection behavior, reject `ANSIBLE_TAGS`, move preflight before fixtures,
correct links and cover defaults/filtering with unconditional prerequisite
recording. Its final continuation returned APPROVE, code only: all prior findings were
fixed or acceptably mitigated, with no new P0–P2 issues and no outstanding
source requests. Optional wording and out-of-scope historical-doc nits do not
change that verdict. Backend discovery
selected PAL clink because no API reviewer was configured. Claude was the only
eligible installed client (Anthropic assumed from the shipped mapping; an
operator declaration overrides that assumption). Agy and Codex executables were
absent; Gemini is retired and was also absent. Configured external model was
unknown; the returned model identifies Anthropic. Initial external receipt
metadata shows all eight criteria reads and 45 source/instruction reads, with no
permission denials; the follow-up records fourteen additional reads and no
denials. Only generic source snapshots and
synthetic evidence were supplied; inventory, credentials and private operator
records were excluded.

Both reviewers approve the repository cleanup within their stated source
coverage. Neither independently executed the tests or established live behavior.
There are no outstanding material review findings and no systemic P0/P1 findings
to index. The external P2 was its own finding; no cross-reviewer corroboration is
claimed for it.

## Remaining operational scope

The recorded Task 1, 11 and 13 live guarantees remain completed; this cleanup
neither repeats nor supersedes that evidence. No homelab command, Kubernetes
command, live mount, migration, parity job or application rollout ran here.

Tasks 5–8 and 10 remain pending. Owner: operator for any future live check after
relevant configuration changes; choose its documented public entry point and
require complete execution and cleanup. Migration additionally requires explicit
owner authorization and source/recovery-copy reconciliation. Code approval does
not authorize that work or resolve the existing media PV/PVC release mismatch.
