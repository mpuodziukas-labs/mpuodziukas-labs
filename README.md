# mpuodziukas-labs

Applied AI for the load-bearing layer: evaluation gates, AI security, agent tracing,
and COBOL fixed-point correctness.

Every repo is clone-and-run. Claims are reproducible or unmade.

## Selected work

| Repo | What | Run |
|------|------|-----|
| [rag-groundedness-gate](https://github.com/mpuodziukas-labs/rag-groundedness-gate) | Blocks a RAG answer whose numbers or claims are not in the source, on a CPU with no API key | `python -m pytest tests/ -q` |
| [agent-trace-receipts](https://github.com/mpuodziukas-labs/agent-trace-receipts) | Tamper-evident trace of every agent step: what it read, called, got back, and how long it took | `python3 -m pytest -v` |
| [llm-adversarial-gate](https://github.com/mpuodziukas-labs/llm-adversarial-gate) | LLM adversarial-validation gate over OWASP LLM Top 10 classes, with an eval corpus | `python3 -m pytest -q` |
| [cobol-pic-probe](https://github.com/mpuodziukas-labs/cobol-pic-probe) | COBOL PIC fixed-point truncation failure class, with a deterministic replay harness | `python3 -m pytest -q` |

## Public surface check

`.github/workflows/public-surface.yml` runs daily against the public GitHub API. It fails when a
public repo is not on `.github/public-surface.tsv`, when a listed repo's history carries an identity
other than the owner's, or when a listed repo's latest CI run on its default branch did not succeed.
`python3 .github/public-surface.py --selftest` plants each failure and shows it caught.

## Honesty Statement

The repos above use synthetic data. None of them carries client, employer, or production data, and
no number in them comes from a paid engagement.

## Limitations

The surface check reads only what the public API returns: it cannot see private repos, deleted
history held in forks, or CI runs older than the latest 20 on a branch.

Operated by Michael Puodziukas - https://puodziukas.dev
