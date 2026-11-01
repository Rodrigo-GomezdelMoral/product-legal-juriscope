# Responsible AI impact assessment

Juriscope's impact assessment follows the sections of the
[Microsoft Responsible AI Impact Assessment Template](https://msblogs.thesourcemediaassets.com/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Template.pdf)
(June 2022) and the responsible AI guidance of the
[Well-Architected AI workload guide](https://learn.microsoft.com/azure/well-architected/ai/responsible-ai). Measured figures carry
their date and come from [evaluation.md](evaluation.md). **Status, 2026-10-31:** the question-to-answer flow and the evaluation gate
are implemented and tested locally against the shared models, and so are the API's sign-in boundary, feedback events and
deletion (phase 4, with the Cosmos DB emulator). Easy Auth and the deployment come in phase 7, so nothing here has run in staging
or production yet.

## 1. System information

- **What it is:** a research tool for the lawyers and paralegals of one criminal-law firm. It answers questions on the Spanish
  Criminal Code (Ley Orgánica 10/1995, `BOE-A-1995-25444`) with numbered citations. Each cited article is shown in full, in the
  version that applies to the date of the facts, from the official consolidated text of the BOE.
- **How it works:** *Analyst*, a language model, reads the question and decides whether the Code can answer it. Code searches the
  Code and picks each article's version. *Counsel*, a language model, drafts claims that may cite only the retrieved articles. Code
  then drops every claim whose citations were not retrieved. The model never writes the article text: it always comes from the
  version store ([ADR-001](adr/001-graph-workflow.md), [ADR-005](adr/005-structured-output-and-verification.md)).
- **Deployment:** one firm, one Entra ID tenant, a web client behind Entra sign-in, hosted in Sweden Central. Released through
  staging and an approved production release.
- **Languages:** the answer follows the language of the question; article text stays verbatim in Spanish.
- **Intended use:** support for the firm's lawyers in steps 2 to 6 of their research (identification, search, reading, version check
  and contrast). The lawyer reads the cited articles, drafts the note and decides.

## 2. Intended uses

- **Fitness for purpose:** the expensive error in this practice is citing a wording that was not in force on the date of the facts.
  Juriscope selects the version by code from the BOE's version history and shows the current version beside it when it differs. It
  refuses when the Code does not support an answer. The evaluation gate measures retrieval, citation precision, version accuracy,
  refusals and groundedness on every change to prompts, agents, retrieval or the corpus (REQ-05).
- **Stakeholders:**

  | Stakeholder | Benefit | Potential harm |
  |---|---|---|
  | Lawyers and paralegals | 30 to 75 minutes saved per question on steps 2 to 6 (K1) | overreliance on an answer that misses a relevant provision |
  | The firm's clients and defendants | faster, better-sourced defence work | a wrong or outdated rule carried into their defence |
  | The knowledge lead | KPI workbook and feedback to steer quality (phase 4 onward) | none specific |
  | Victims and third parties named in a question | none directly | special-category data (GDPR art. 10) in a question |

- **Goals of the Responsible AI Standard that apply:**
  - *Human oversight (A5):* every answer is reviewed by a lawyer, who drafts and signs the work product. No action with side effects
    exists, so there is no approval step inside the product.
  - *Intelligibility (T1):* every claim names its articles, and every article opens the official BOE text.
  - *Communication to stakeholders (T2) and disclosure of AI interaction (T3):* the interface says the answers are generated and are
    not legal advice, and shows the BOE reuse notice (phase 5).
  - *Quality of service (F1):* the product answers in Spanish and English and is measured in both. Co-official languages are out of
    scope.
- **Readiness and role of humans:** proven technology (retrieval plus a pinned model) on a narrow, well-structured corpus. The task is
  of moderate complexity. A professional reviews every output, in a controlled environment of 18 named users.

## 3. Adverse impact

- **Restricted uses:** none by law. Juriscope is an internal tool of a law firm and is not offered to the public.
- **Unsupported uses:** legal advice to the public; decisions without a lawyer; case law, doctrine or laws other than the Criminal
  Code; drafting or exporting documents; uploading documents.
- **Known limitations:**
  - **Only the Criminal Code**, and only its consolidated text, which the BOE publishes as informative and not official.
  - **Repealed provisions cannot be retrieved:** the index holds today's text. Facts dated before a repeal find nothing for the
    repealed provision, so the answer refuses or omits it (ADR-003 records it in phase 6).
  - **Questions on sexual offences against minors are refused.** The shared content filter (`guardrail-chat`, Sexual at medium)
    blocked both such questions on every attempt in phase 2, and Juriscope returns a typed `content_filter` refusal. A lawyer
    researching those offences must read the articles in the BOE directly. Lowering the threshold would change a guardrail
    shared by four products, so it stays as it is.
  - **The same filter refuses a question on sharing intimate images without consent** (article 197.7), in every phase 3 run. It
    is the one false refusal of the golden set.
  - **Model retirement:** `gpt-5-mini` 2025-08-07 retires on 2027-02-09 ([ADR-010](adr/010-model-lifecycle.md)); the replacement
    must pass the full suite.
- **Predictable failures:**
  - *False negative:* a relevant article is not retrieved, so the answer is incomplete. Measured by Recall@5.
  - *False positive:* an article that does not support the claim is cited. Measured by citation precision and groundedness.
  - *Wrong version:* measured by version accuracy.
  - *Wrong refusal:* an answerable question is refused, or an unanswerable one answered. Measured by false and correct refusal.
- **Misuse:**
  - Prompt injection asking the system to ignore its rules. Mitigated by Prompt Shields in the shared guardrail, retrieval decided by
    code, verification by code, and the adversarial set with a canary (`ZEBRA-7731`). **Residual, measured on 2026-10-31:**
    with prompt v2 the canary appeared in about 1 of 15 adversarial cases, once in a claim and once in a refusal reason. Prompt v3
    (phase 4) removed both paths: *Counsel* reads only *Analyst*'s restatement, and a refusal carries a value from a fixed list. It
    then appeared in 0 of 15 cases in each of two runs ([evaluation.md](evaluation.md)), but in CI on 2026-10-31 it appeared
    once (1 of 15): *Analyst* copied the whole question, instruction included, into its restatement, and *Counsel* wrote the
    instruction's phrase into a claim. Since `analyst_v4.md` and `analyst_v5.md`, *Analyst* lists in `left_out` the passages of
    the lawyer's message that are not the legal question; code removes them from the restatement and drops any claim that
    repeats one (a run of eight letters or digits touching a word foreign to the Criminal Code). The canary then appeared in 0
    of 15 cases in nine pull-request runs and two full runs. Residual: an encoded or spelled-out canary, or a code shorter
    than eight characters, is stopped only if the restatement leaves the instruction out; and an English instruction that
    literally contains a claim's wording can drop that true claim.
  - A user pasting a client's identity into a question. The interface asks users not to (phase 5); questions are stored only in the
    firm's own Cosmos DB account for at most 90 days.
- **Sensitive uses:** the output can affect a person's legal position, because a defence may rely on it. This is why every claim is
  cited and verified, the article text is official, the version is chosen by code, and a lawyer reviews every answer.

## 4. Data requirements

- **No training or fine-tuning.** The models are used as deployed. The only domain data is the public text of the Criminal Code,
  reused under Ley 37/2007 with its source, update date and modifications stated ([data/README.md](../data/README.md)).
- **Questions** may hold special-category data (criminal matters) and are covered by professional secrecy:
  - at rest in Sweden Central (Cosmos DB, Application Insights), deleted by a 90-day TTL or on request;
  - telemetry never carries question or answer text;
  - the search service in Spain Central holds only the Code and processes the query text;
  - inference runs on Global Standard deployments, which may process outside the EU ([ADR-009](adr/009-inference-and-data-residency.md));
    Data Zone EU is the documented alternative.
- **Evaluation data** is generated from the version store, and the author verified every golden item on 2026-10-31.

## 5. Summary of impact

| Harm | Mitigation | Evidence |
|---|---|---|
| A wrong rule | citations to retrieved articles only; verification by code; groundedness judge | `test_claims_cite_retrieved_articles`, `test_unverified_claim_is_dropped`; citation precision and groundedness in the gate |
| An outdated rule | version chosen by code from the BOE history; current version shown beside it | `test_version_at`, `test_facts_date_selects_version`; version accuracy in the gate |
| An answer from model knowledge | out-of-scope and no-evidence refusals | `test_out_of_scope_refused_without_retrieval`, `test_no_evidence_refusal`; correct refusal in the gate |
| Overreliance | full articles beside every answer; "not legal advice"; lawyer review; feedback (REQ-09) | phase 5 interface; phase 4 feedback events |
| Injection | Prompt Shields; code decides retrieval and citations; code keeps *Analyst*'s `left_out` passages out of the restatement and the answer; canary | `test_injected_instructions_never_reach_the_answer`, `test_claims_drop_only_text_foreign_to_the_code`; adversarial set, canary appearances 0 |
| Disclosure of client data | user partition, no text in telemetry, `store: False`, 90-day TTL, deletion | phase 4 tests; phase 7 live checks |

The author holds the review and sign-off roles and signs off at release 1.0.0.
