# Analysis protocol v0 — before inspecting project outcomes

Date: 2026-09-29. This is an internal dated analysis plan, not a public preregistration. Feasibility-driven changes must be recorded, with exploratory changes separated from confirmatory comparisons.

## 1. Setting and decision

Patent-based technology intelligence for organizations active in battery thermal management and associated heat-transfer technologies. A decision at year end selects K newly visible external invention records for screening. K represents document-review capacity, not money or observed staff hours. Candidate availability, organization history, text vocabulary, learned features and citation networks must all respect the information cutoff.

Initial capacity grid: K in {10, 30, 50}; exploration-share grid {0, 0.1, 0.2, 0.3, 0.4}. Explore only candidates passing the same basic relevance screen. Organization familiarity is based on the previous five years of observable text and classification history. The specific distance definition and thresholds will be chosen on development years and frozen before held-out evaluation.

## 2. Units and sample

Primary decision unit: organization × decision year. No claim that repeated decisions or candidate documents are independent organizations. Report raw assignee versus resolved organization definitions. Eligibility uses only pre-cutoff activity, never subsequent survival. Merge application/grant duplicates; use verified priority/related-document data where available and separately disclose unresolved family duplication. The core corpus will be selected using period-appropriate classifications and technical terms, not later successes.

Target historic cutoffs: 2016–2021, with three years of subsequent observation through 2024. The dates remain feasibility assumptions until the acquired dataset is inspected. Do not expand a holdout after seeing the policy winners. Keep a final temporal holdout and, if enough organizations exist, a separately labelled organizational-transfer evaluation.

## 3. Outcomes and construct limits

Outcome A: distinct external citing organizations appearing within a fixed three-year post-decision window, or its prespecified high-attention indicator. Deduplicate citation records and exclude documented same-organization and same-family links where possible. The citing record's public visibility date, not the cited patent's citation_date field, establishes when a citation was observable. Grant-only data imply a conservative grant-visible scope and will be labelled as such.

Outcome B: how many technologically distant candidates with subsequent external attention are retained. Report this jointly with total high-attention candidates retained. Diversity alone is not a success criterion. Report full trade-off curves rather than an arbitrary weighted composite.

Secondary: ranking quality, calibration, redundancy, coverage of distinct technology clusters, and missed high-attention signals. These do not substitute for the primary decision trade-off. No unmeasured expert utility or actual business value will be inferred.

## 4. Models and policies

Start with text similarity/popularity, a regularized supervised baseline and gradient boosting; reproduce one relevant recent comparator if implementation and inputs allow a fair comparison. Statistical sophistication does not count as the contribution. All fitted text preprocessing uses only historical data. A forecast with a three-year label trains only on records whose labels were fully observable at that forecast origin.

Policy comparisons keep the candidate set, relevance floor, information cutoff and predictor fixed: score-only top K; standard maximal marginal relevance (MMR); random exploratory allocation; fixed-distance quota; a simple development-selected context rule. Apply any feasibility/relevance constraint equally across policies. Random allocation repeats use fixed seeds and remain separate from independent sampling uncertainty.

Use development outcomes to set hyperparameters and allocation rules. Evaluate the frozen rules on held-out years. Full exploration-share sweeps on the holdout are labelled response-curve evaluation, not used to claim a retrospectively optimal deployable rule.

## 5. Inference and sensitivity

Compare policies within the same organization-year. Show absolute paired differences and uncertainty; resample at organization level and assess temporal dependence. With few independent organizations, report wide uncertainty and descriptive results rather than treating candidate counts as the effective sample size. Knowledge concentration is the principal organization-level boundary; capacity is the decision constraint. Additional subgroups are exploratory and reported transparently.

Sensitivity directly targets validity: alternative relevance/distance cutoffs; exclusion of self/family citations; deduplication; citation concentration across assignees; earlier versus later cohorts; simple versus learned scores; grant-visible versus other demonstrably available records. Report costs as computational resources and screening slots unless real human time is measured.

## 6. Decisions and reporting

The data may show no useful quota advantage. That result will be evaluated for precision and management relevance, not suppressed. No model or outcome is silently replaced to obtain a positive result. A useful result must establish a meaningful trade-off, a transferable boundary, or evidence that a simpler policy suffices. Stop adding models when they do not address a specific unresolved claim.

Before manuscript readiness: verify current journal instructions; audit all numerical claims against saved outputs; preserve code/data manifests and a rerunnable analysis; distinguish partial previews from full-text evidence; disclose AI assistance as actually used.
