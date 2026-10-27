# REQUIEM — The Code We Buried

**An interactive graveyard for deleted Python functions, built on real Git history and local open-weight AI.**

> Every deleted function leaves a trace. But does the code actually die?

[**Explore the live cemetery**](https://requiem-code-we-buried.onrender.com/) · [**Inspect the source**](https://github.com/CricketGOAT22/requiem-code-we-buried) · [**Read the evidence review**](reports/gemma3-review.md)

Built for the 2026 Hacktoberfest **Ghost in the Machine** open-source AI challenge.

---

## The idea

Deleting a function does not necessarily erase what it did. Its implementation may be moved, renamed, absorbed elsewhere—or truly removed. Git retains earlier versions, but reconstructing their fate takes careful investigation.

**REQUIEM turns that investigation into an interactive cemetery.** Select a gravestone to inspect the function's last observed definition, the revision where that qualified name disappeared, possible structural descendants, source-code comparisons, and the evidence behind each observation. Gemma, running locally through Ollama, writes a short epitaph.

The twist: **a matching function is not proof of a resurrection.** Two functions can have identical normalized syntax trees and behave differently because surrounding constants or dependencies changed.

## Try the exhibit

### [Enter REQUIEM →](https://requiem-code-we-buried.onrender.com/)

The public exhibit is a **read-only, precomputed snapshot**. You can explore the cemetery, inspect source evidence and Git commit links, read locally generated Gemma epitaphs, and view the Evidence Lab without an account, a GPU, or a running model.

For new analysis and live local Gemma generation, follow the local setup below. **Render hosts the static exhibit; it does not run Ollama or connect to the author's Mac.**

## What the Git investigation found

Our published demonstration analyzes [Pallets Click](https://github.com/pallets/click), an established open-source Python project.

| Observation | Measured result |
| --- | ---: |
| First-parent commits visited | **120** |
| Consecutive commit pairs examined | **119** |
| Candidate function removals observed | **38** |
| Cases curated for the exhibit | **8** |
| Selected cases passing independent Git-object audit | **8 / 8** |

One case traces `Argument.human_readable_name` to a possible successor, `Argument.spec`, with **1.000 normalized structural similarity**. This is evidence of a strong *structural match*, not proof of intent, code ancestry, or equivalent runtime behavior.

Related methods from possible class transitions are grouped so one rename-like event does not become a row of misleading independent discoveries. The scan covers a bounded history window, not the project's entire history.

- [Source report](reports/click-history.json)
- [Independent audit](reports/click-audit.json)
- [Published static exhibition data](frontend/public/exhibit.json)

## The experiment: real citations, unsupported conclusions

We asked **Gemma 3 4B** to interpret evidence for three selected Click cases. Each case was presented twice: once with a baseline prompt and once with more evidence-cautious instructions.

All six responses followed the requested structured format and cited genuine evidence IDs. Under a strict, author-assisted human rubric, **all six explanations contained at least one assertion the supplied Git observations did not justify**—typically calling a possible successor a definite replacement or treating similar structure as proven equivalent behavior.

| Prompt condition | Fully supported explanations | Unsupported explanations |
| --- | ---: | ---: |
| Baseline | 0 / 3 | 3 / 3 |
| Evidence-cautious | 0 / 3 | 3 / 3 |

**What this does *not* mean:** Gemma has a general 100% hallucination rate. This was **one reviewer**, **three deliberately selected cases**, **one generation per condition**, and a strict evidence-only standard. Conditions were concealed during review, but this was not a double-blind study. The cautious prompt did not improve these three paired outcomes.

- [Raw model runs](reports/gemma3-lab.json)
- [Completed review workbook](reports/gemma3-review.json)
- [Review rubric, verdicts, and limitations](reports/gemma3-review.md)

### The Evidence Firewall

Instead of expecting a better prompt to guarantee truth, REQUIEM separates trust boundaries:

1. **Git scanner:** gathers source definitions, candidate disappearances, and potential structural matches.
2. **Independent auditor:** re-reads the referenced Git objects to verify the selected report observations.
3. **Deterministic factual view:** renders bounded statements from scan observations, not from the model's prose.
4. **Gemma interpretation:** produces a creative epitaph; its free-form explanation stays clearly marked **unverified**.

The firewall prevents a model-generated claim from *becoming the site's factual record*. It does **not** automatically verify AI prose, guarantee that an epitaph is accurate, or make the report's SHA-256 fingerprint an authenticity signature.

Run the synthetic adversarial demonstration to see an invented “security bug” assertion excluded from the factual panel:

~~~bash
python3 -m scripts.demo_claim_gate
~~~

## The false resurrection

A controlled two-commit fixture shows why structural identity is insufficient:

~~~python
# Before
MIN_AGE = 18
def can_enter(age):
    return age >= MIN_AGE

# After
MIN_AGE = 21
def can_enter_v2(age):
    return age >= MIN_AGE
~~~

For `age = 20`, the original function returns `True` and the later one `False`, despite identical normalized function structure. This is **a constructed counterexample**, not a claim about Click or a discovered real-world bug.

## Architecture

~~~text
Local Git repository
    └─ Python AST extraction + changed-file Git scanning
        └─ Candidate removals and structural matches
            ├─ Independent Git-object audit
            │   └─ Deterministic evidence panel (trusted *after* audit)
            └─ Gemma 3 via local Ollama
                └─ Creative epitaph + explicitly unverified prose

Local edition: Python API on 127.0.0.1:8765 + React/Vite
Public edition: audited snapshot + precomputed Gemma text → Render Static Site
~~~

Key paths: `backend/archaeology.py` (functions and Git evidence), `backend/afterlife.py` (structural similarity), `backend/history.py` (history scanning), `backend/audit.py` (auditing), `backend/claim_gate.py` (factual/model separation), `backend/narrator.py` (local AI), `frontend/` (the cemetery), and `scripts/` (repeatable experiments).

## Run it yourself

**Requirements:** Git, Python 3.11+ recommended, and Node.js 20+. **For live AI narration only:** [Ollama](https://ollama.com/download) and a locally downloaded `gemma3:4b` model. Python analysis and the public preview do not require an LLM.

~~~bash
git clone https://github.com/CricketGOAT22/requiem-code-we-buried.git
cd requiem-code-we-buried

# Test the Python engine (standard library only)
python3 -m unittest discover -s tests -v

# Audit the published real-history report
mkdir -p external
git clone --depth 200 https://github.com/pallets/click.git external/click
python3 -m scripts.audit_history \
  --repo external/click \
  --report reports/click-history.json \
  --output reports/click-audit.json
~~~

The Click history must contain the pinned commits referenced in the report. If a shallow clone doesn't contain them, fetch more history or use a full clone. Scanning from a moving `HEAD` can produce different cases as Click evolves.

**Run the interactive local edition** in separate terminals:

~~~bash
# Terminal A: Start Ollama (or launch the Ollama app), then:
ollama pull gemma3:4b
python3 -m scripts.serve --report reports/click-history.json

# Terminal B, from the project root:
cd frontend
npm install
npm run dev
~~~

Open the local URL printed by Vite. Click a grave and summon Gemma to generate a new epitaph.

**Preview the exact static edition used on Render:**

~~~bash
cd frontend
npm install
VITE_PUBLIC_EXHIBIT=true npm run build
npm run preview
~~~

The generated `frontend/public/exhibit.json` is committed for reproducibility. No Python API or Ollama process is required to preview it.

**Regenerate the public exhibit locally:**

~~~bash
python3 -m scripts.export_public \
  --repo external/click \
  --report reports/click-history.json \
  --review reports/gemma3-review.json \
  --model gemma3:4b \
  --confirm-public-source
~~~

Run this from the repository root, with Ollama running, after confirming the source excerpts are suitable to publish. The exporter re-audits the Git evidence and requires the matching completed human review. Generated epitaph wording can vary from the published snapshot.

## Why open-weight AI matters here

Repository histories can contain internal code, design decisions, and contributors' names. Running a compatible open-weight model **locally** lets developers interpret code without uploading each source excerpt to a third-party model API. We can also inspect and change our prompts, pin a model version, replace the model, and repeat comparisons without per-request hosted inference fees.

The public hosted exhibition has different privacy properties: it deliberately publishes excerpts from an already public project. **Private repositories should not be exported or deployed without permission and a careful disclosure review.** Local analysis also requires the usual caution when working with untrusted Git repositories and their configuration.

The Python Git scanner works without inference; Gemma powers the creative narration and experiments. This separation is intentional: Git supplies observations, the model supplies language, and neither alone proves historical causation.

## Limitations and reproducibility notes

- Analysis currently targets **Python** functions and selected Git revisions, not every language or entire project history.
- Normalized AST similarity is candidate discovery, **not semantic equivalence**.
- The independent audit verifies the recorded Git observations, not developers' intentions.
- AI epitaphs and interpretations can be inaccurate; only the bounded Git-derived panel is displayed as factual.
- Report fingerprints detect data changes but are **not cryptographic attestations** of Git authenticity.
- The public Render site is precomputed; it does **not** generate new AI text.
- The six-response human evaluation is descriptive, single-reviewer research, not a population estimate.

## Built with

Python · Git · Python AST · React · Vite · **Google Gemma 3** · **Ollama** · **Render**

---

*The repository may forget a name. The history keeps the trace.*
