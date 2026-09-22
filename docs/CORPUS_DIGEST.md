# Corpus digest

szl-papers at `74ab598`, 66 documents.

## `thesis/arxiv/append-only-governance/ARXIV_METADATA.md`

- # arXiv submission metadata — Paper 1 (flagship)
- ## Title
- ## Authors
- ## arXiv categories
- ## ACM classification
- ## MSC 2020
- ## License
- ## Comments field (suggested)

```
>> ABSTRACT
   Agentic AI is post-deterministic: the same prompt and tools may yield different action sequences, so accountability cannot rest on re-deriving a deterministic trace. It must instea
   ## Honesty notes for the founder
   - F4/F7/F22 are kernel-checked at the named proof snapshot and registered in the locked-proven formula set; the canonical 749/14/163 baseline is a distinct earlier commit and the p
   - F4 and F7 were previously vacuous; the paper states this openly as the non-vacuity audit narrative — a strength, not a liability.
   - Paper-and-pencil consequences and pseudocode are labeled as such and are not added to the locked theorem count.
   - No fabricated benchmarks, citations, or arXiv IDs appear.
```

DOIs: `10.5281/zenodo.19944926.`

## `thesis/arxiv/append-only-governance/main.tex`

- \section{Introduction}\label{sec:intro}
- \section{The honesty doctrine and proof tiers}\label{sec:doctrine}
- \section{The receipt substrate}\label{sec:substrate}
- \section{System boundary, threat model, and proof obligations}
- \section{F4 --- Acyclicity of the receipt DAG, preserved under append}\label{sec:f4}
- \section{F7 --- FIFO reception ordering of the Chaski channel}\label{sec:f7}
- \section{F22 --- Append-only emit monotonicity}\label{sec:f22}
- \section{Derived consequences and an admission algorithm}

```
>> ABSTRACT
   Agentic AI is \emph{post-deterministic}: the same prompt and tools may yield
   different action sequences, so accountability cannot rest on re-deriving a
   deterministic trace. It must instead rest on a \emph{record} whose structural
   invariants are themselves verifiable. We give a machine-checked foundation for
   three such invariants over an AI decision-receipt substrate, with proof terms
   checked by Lean~4 at the named snapshot: (F4) the modeled receipt directed
   acyclic graph (DAG) is acyclic and remains acyclic under append; (F7) draining
   a modeled \emph{Chaski} batch preserves first-in-first-out (FIFO) order, with a
>> Conjecture~1 is disproved as originally stated, with a weaker-condition
   uniqueness question still open; Khipu safety is Conjecture~2.
   \end{itemize}
>> \begin{definition}[Receipt DAG]
   A \emph{receipt} is a node $0,1,\dots,n-1$ in emission order. A reference from a
   later receipt to an earlier one is a directed edge $(\mathrm{src},
   \mathrm{dst})$. The edge set is $\texttt{KhipuEdges} := \texttt{List}\,(\mathbb{N}
>> \begin{definition}[Chaski channel]
   Inter-organ messages flow over a FIFO queue $\texttt{ChaskiQueue} :=
   \texttt{List}\,\mathbb{N}$. \emph{Enqueue} appends a message to the back (send);
   \emph{dequeue}/\emph{drain} serves from the front (receive).
>> \begin{definition}[Emit log]
   The emit log after $n$ emissions is $\texttt{seqLog}\,n := \texttt{List.range}\,n
   = [0,1,\dots,n-1]$; emitting appends the next sequence number.
   \end{definition}
>> F4 & O1; O2 for append & No non-empty directed path returns to its source;
   append preserves that fact. \\
   F7 & O3 & Draining a batch sent to an empty channel returns the same ordered
   list, including option-valued positional equality. \\
>> F7 & O3 & Draining a batch sent to an empty channel returns the same ordered
   list, including option-valued positional equality. \\
   F22 & O4 & A new emission extends the prior log and values strictly increase
   with position. \\
```

DOIs: `10.1145/1629575.1629596`, `10.1145/357172.357176`, `10.5281/zenodo.19944926`

## `thesis/arxiv/append-only-governance/references.bib`


DOIs: `10.1145/1629575.1629596`, `10.1145/357172.357176`, `10.5281/zenodo.19944926`

## `thesis/arxiv/gpd-unified-v26/main.tex`

- \section{Introduction}
- \section{Related Work}
- \section{The Lutar Invariant \texorpdfstring{$\Lam$}{Lambda}: Axiomatic
- #check Lutar.Round13.maxAgg_ne_Lambda
- #print axioms Lutar.Round13.lambda_unique_of_separable
- \section{The Eight Locked-Proven Formulas}
- \section{The Governed-Inference Pipeline}
- # Verify DSSE signature over the receipt

```
>> ABSTRACT
   Agentic and autonomous artificial intelligence is \emph{post-deterministic}:
   the same prompt, model, and tools may produce different action sequences, so
   accountability cannot rest on re-deriving a deterministic trace.  We present
   \textbf{Governed Post-Determinism (GPD)}, a machine-checked, cryptographically-receipted
   substrate that wraps a post-deterministic agent in checkable bounds, attested
   records, and replicated state, so that every governed inference carries a
   verifiable warrant.
   GPD is grounded in eight \emph{locked-proven} Lean~4 formulas---
>> \begin{definition}[Lutar Invariant $\Lam$~\cite{szl_v3,szl_concept}]
   \label{def:lambda}
   For trust-axis scores $x \in [0,1]^k$, the Lutar Invariant is
   \[
>> \begin{conjecture}[Conjecture 1 --- unconditional $\Lam$-uniqueness;
   machine-checked FALSE~\cite{szl_v14,szl_concept}]
   \label{conj:lambda}
   \emph{There is no proof that $\Lam$ is the unique A1--A5 aggregator.
>> \begin{theorem}[Theorem U; \experimental{};
   \lean{Lutar.\lb Round13.\lb lambda\_\lb unique\_\lb of\_\lb separable}~\cite{szl_v24,szl_concept}]
   \label{thm:U}
   Let $\Phi$ satisfy \{A1, A2, A3, A5\} and be \emph{slice-multiplicative}:
>> A3 (idempotence) forces $\sum_i \alpha_i = 1$.  A5 (permutation invariance)
   forces $\alpha_i = 1/k$ for all $i$.  Hence $\Phi(x) = \prod_i x_i^{1/k} =
   \Lam_k(x)$.  The full Lean derivation is in
   \texttt{Lutar/Round13/LambdaUniqueness.lean}.
>> Conjecture~1 requires the BKS $n$-adic construction~\cite{aczel1966}, which
   depends on functional analysis infrastructure not yet in Mathlib v4.18.0 (open
   as a roadmap item).
>> theorem locked_count_eight :
   Lutar.lockedDisclosed.length = 8 := by decide
   \end{lstlisting}
   The kernel baseline is \textbf{749 declarations / 14 unique axioms /
```

DOIs: `10.5281/zenodo.19867281`, `10.5281/zenodo.19944926`, `10.5281/zenodo.19983066`, `10.5281/zenodo.20119582`, `10.5281/zenodo.20174600`, `10.5281/zenodo.20434276`

## `thesis/arxiv/gpd-unified-v26/PAPER_NOTES.md`

- # PAPER_NOTES.md
- ## Governed Post-Determinism: A Machine-Checked, Cryptographically-Receipted
- ## Substrate for Verifiable AI Inference
- ## Page count and structure
- ## Claims vs. honest limitations
- ### What IS claimed (all honest, doctrine-compliant)
- ### What is HONESTLY labeled as NOT claimed
- ## arXiv submission metadata

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926.`

## `thesis/arxiv/gpd-unified-v26/references.bib`


DOIs: `10.1007/3-540-48184-2_32`, `10.1007/978-1-4757-6568-7`, `10.1007/978-3-030-79876-5_37`, `10.1007/BF01608499`, `10.1090/S0002-9904-1948-08994-7`, `10.1103/PhysRevLett.113.140401`, `10.1145/1629575.1629596`, `10.1145/3293611.3331591`

## `thesis/arxiv/gpd-v26/ARXIV_METADATA.md`

- # arXiv submission metadata — Paper 3 (GPD unification thesis, v26)
- ## Title
- ## Authors
- ## arXiv categories
- ## ACM classification
- ## MSC 2020
- ## License
- ## Comments field (suggested)

```
>> ABSTRACT
   Autonomous and agentic artificial intelligence is post-deterministic: the same prompt, model, and tools can produce different action sequences, and the controlling logic is statist
   ## Honesty notes for the founder
   - Single substantive change from v25: locked count five -> eight (genuine F4/F7/F22 proofs of 2026-06-10); kernel baseline unchanged.
   - GPD is grounded only in the SZL Zenodo DOI chain; no external "post-deterministic" framework is claimed as a source.
   - Lambda = Conjecture 1, Khipu = Conjecture 2, experimental tier labeled, trust never 100%. No fabricated results, citations, or arXiv IDs.
   - A Zenodo concept DOI (10.5281/zenodo.19944926) already exists for the program; this is the first arXiv submission of the thesis line. Cross-reference the DOI in the arXiv "Journa
```

DOIs: `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926.`

## `thesis/arxiv/gpd-v26/main.tex`

- \section*{Lineage and prior art (the SZL DOI chain)}
- \section{Introduction: the post-deterministic governance gap}
- \section{The honesty doctrine (load-bearing)}\label{sec:doctrine}
- \section{The unifying structure of GPD: the checkable-antecedent pattern}\label{sec:pattern}
- \section{Pillar P3 --- the Bounded-Recursion Control Plane: the Lutar invariant}\label{sec:p3}
- \section{Pillar P4 --- Semantic Quorum Assurance: Khipu BFT consensus}\label{sec:p4}
- \section{Pillar P2 --- Verifiable Intent-to-Execution: the receipt and provenance layer}\label{sec:p2}
- \section{Pillars P1 and P5 --- Protocol-Bounded Execution and Epistemic State Replication}\label{sec:p1p5}

```
>> ABSTRACT
   Autonomous and agentic artificial intelligence is \emph{post-deterministic}:
   the same prompt, model, and tools can produce different action sequences, and
   the controlling logic is statistical rather than fixed. Deployed into regulated
   and defense settings, such systems break the classical assumption that auditing
   means re-deriving a deterministic trace. The governance question is no longer
   ``what is the unique correct output?'' but ``under what authority did this
   system act, on what aggregated evidence of trust, and can the record be tampered
   with after the fact?'' This thesis unifies the SZL Holdings research program
>> F7 (the Chaski channel delivers FIFO, positionally), and F22 (the emit log is
   append-only and monotone)---plus F18 (Reed--Solomon coding) and attested
   supply-chain provenance (DSSE/cosign, Sigstore, SLSA Build L1+L2 where it runs).
   (P3)~Bounded-Recursion Control Plane: the Lutar invariant $\Lam$ (equal-weight
>> theorem, \texttt{locked\_count\_eight}, by \texttt{decide}); the locked-kernel
   baseline at \texttt{c7c0ba17} (749/14/163) is unchanged; the ${\sim}185$
   experimental CI-green theorems are a separate tier, never folded in.
   \end{abstract}
>> axiom-free); v25 ``GPD, Unification Edition'' (first statement of GPD; Wave-23
   incorporated; locked count was five).
   \paragraph{v26's place in the lineage.} v25 introduced the GPD unification. v26
>> F4/F7/F22 proofs. We make no claim that GPD ``solves'' AI governance, that $\Lam$
   is a theorem unconditionally, or that Khipu is unconditionally safe.
   %=================================================================
>> theorem with $\texttt{\#print axioms} \subseteq \Ucoreaxioms$ --- no project
   axiom.
   \subsection{Why this is the right theory of governance}
>> axiom.
   \subsection{Why this is the right theory of governance}
   Governing a post-deterministic system is \emph{not} proving it always behaves
```

DOIs: `10.1145/1629575.1629596.`, `10.1145/3372885.3373824.`, `10.5281/zenodo.19867281`, `10.5281/zenodo.19934129`, `10.5281/zenodo.19944926`, `10.5281/zenodo.20020841`, `10.5281/zenodo.20020845`, `10.5281/zenodo.20020846`

## `thesis/arxiv/gpd-v26/references.bib`


DOIs: `10.1145/1629575.1629596`, `10.1145/3372885.3373824`, `10.5281/zenodo.19944926`

## `thesis/arxiv/graph-substrate/ARXIV_METADATA.md`

- # arXiv submission metadata - Paper 2 (graph-substrate audit)
- ## Title
- ## Author
- ## arXiv categories
- ## ACM classification
- ## MSC 2020
- ## Suggested comments field
- ## Abstract (ready to paste)

```
>> ABSTRACT
   Formal verification proves that a conclusion follows from its premises, but it
   does not by itself show that a formal model captures the operational claim
   attached to it. We audit a Lean 4 graph-governance artifact merged as pull
   request #189 at commit
   `8de25baf1d5adcc11238d13e17a9a7eaaf05af6d`. A public CI run built the same Git
   tree and printed the axiom dependencies for 25 declarations: none depends on
   `sorryAx`; seven are axiom-free, four use only `propext`, one uses `propext` and
   `Quot.sound`, and thirteen use the standard Mathlib trio. The semantic findings
```

DOIs: `10.5281/zenodo.19944926.`

## `thesis/arxiv/graph-substrate/main.tex`

- \section{Introduction}\label{sec:intro}
- \section{Audit target and evidence method}\label{sec:method}
- \section{System and threat model}\label{sec:system}
- \section{Graph-shaped aggregation and topology blindness}\label{sec:lambda}
- \section{The \(1\)-WL factoring declaration}\label{sec:wl}
- \section{Finite-frontier and relabelling cores}\label{sec:frontier}
- \section{Metric coordinates and geometric iteration}\label{sec:metric}
- \section{Declaration inventory and axiom evidence}\label{sec:inventory}

```
>> ABSTRACT
   Formal verification can establish that a theorem follows from its premises
   without establishing that the formal model captures the operational claim
   attached to it. This distinction is acute for graph-shaped AI governance:
   putting a graph field in a record does not make an aggregate topology-sensitive,
   and naming a generic factoring lemma after Weisfeiler--Lehman (WL) refinement
   does not construct the required factorization. We conduct a source-level and
   kernel-evidence audit of a Lean~4 artifact merged as pull request \#189 at commit
   \commit. The focal artifact contains 17 printed declarations across
>> \begin{definition}[Kernel evidence]
   A declaration has kernel evidence when the pinned Lean toolchain elaborates and
   checks it, its \texttt{\#print axioms} output is captured, and the relevant
   source does not introduce \texttt{sorryAx} into that declaration.
>> \begin{definition}[Semantic evidence]
   A declaration has semantic evidence for a named system claim when its
   definitions mention the relevant system structure, its proof consumes premises
   that encode that structure, and countermodels excluded by the prose claim are
>> \begin{definition}[Refinement evidence]
   An abstract theorem has refinement evidence for an implementation when a
   checked or independently tested relation maps implementation states and steps
   to the abstract model and preserves the theorem's hypotheses.
>> Definition of WL, model class, and construction of the factorization \\
   T4 & An implementation can add work although the abstract measure only falls &
   Simulation/refinement proof for the real transition relation \\
   T5 & Convergence language hides an assumed one-step contraction &
>> \begin{proposition}[Topology blindness]\label{prop:blind}
   Fix a finite carrier \(V\) and score assignment \(s:V\to\texttt{Axes}\ 9\).
   Let \(e_1\) and \(e_2\) be \texttt{GraphExecution} values with that carrier and
   score assignment but arbitrary simple graphs \(G_1\) and \(G_2\). Then
>> Proposition~\ref{prop:blind} gives identical per-vertex and global
   \(\Lam\) values. Thus \(\Lgraph\) cannot detect a total loss of graph
   connectivity when scores remain fixed.
   \end{example}
```

DOIs: `10.1007/978-3-030-79876-5`, `10.1007/978-3-030-79876-5_37`, `10.1007/BF01200757`, `10.1007/BF02776078`, `10.1090/mbk/107`, `10.1145/1538788.1538814`, `10.1145/1629575.1629596`, `10.1145/3372885.3373824`

## `thesis/arxiv/graph-substrate/references.bib`


DOIs: `10.1007/BF01200757`, `10.1007/BF02776078`, `10.1090/mbk/107`, `10.1145/1629575.1629596`, `10.1145/357172.357176`, `10.1214/aoap/1177005980`, `10.5281/zenodo.19944926`

## `thesis/EXPERIMENTAL_LEAN_THEOREMS.md`

- # Experimental machine-checked Lean theorems (NOT locked-8)
- ## What "locked-8" means (unchanged)
- ## Experimental backbones merged to lutar-lean `main`
- ## Honesty boundary

## `thesis/ouroboros/corpus-v18/claims_v18_extracted.json`


## `thesis/ouroboros/corpus-v18/claims_v18_extracted.json.HARVEST_NOTE.txt`


## `thesis/ouroboros/corpus-v18/lean_per_version.json`


## `thesis/ouroboros/corpus-v18/main.tex`


DOIs: `10.5281/zenodo.19944926`

## `thesis/ouroboros/papers/v22/arxiv/00_README_ARXIV.md`

- # arXiv Submission Bundle — Ouroboros Thesis v22 (Convergence)
- ## Contents of `thesis_v22/arxiv/`
- ## How to compile (verify locally before upload)
- ## arXiv submission metadata (copy-paste)
- ## Founder-only actions (NOT done by the agent)
- ## Doctrine guardrails honored in this bundle

DOIs: `10.5281/zenodo.19944926`

## `thesis/ouroboros/papers/v22/arxiv/references.bib`


DOIs: `10.1007/3-540-45682-1_30`, `10.1007/s00199-007-0316-6`, `10.1023/A:1021840411064`, `10.1145/3149.214121`, `10.1214/074921707000000391`, `10.17487/RFC6962`, `10.4099/jjm1924.7.0_71`, `10.5281/zenodo.19944926`

## `thesis/ouroboros/papers/v22/arxiv/thesis_v22.tex`

- \section{Recent advances (the substance of v22)}
- \section{Doctrine attestation (verbatim)}
- \section{Honest posture}

```
>> ABSTRACT
   v22 (``Convergence'') consolidates the May--June 2026 formal-verification advances into the canonical
   thesis line. Its central correction: the claim that axioms A1--A4 force the weighted geometric mean is
   \emph{false}. The asymmetric mean $\Phi(x_1,x_2)=x_1^{2/3}\,x_2^{1/3}$ satisfies A1--A4 yet differs
   from \Lam{} and fails permutation invariance. We add A5 (permutation invariance) as a \emph{structure
   field} on \texttt{LutarAxioms} --- not a new axiom --- keeping the unique-axiom count at 14, and report
   the partial closure of the $n$-dimensional Cauchy functional-equation chain that, when complete, would
   discharge \Lam-uniqueness. It is \emph{not} complete on \texttt{main}; \Lam{} therefore remains
   \textbf{Conjecture 1}. We additionally report VCG mechanism truthfulness (proven on branch), the
```

DOIs: `10.5281/zenodo.19944926`

## `thesis/ouroboros/papers/v22/CITATION.cff`


DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926;`

## `thesis/ouroboros/papers/v22/ouroboros-thesis-v22.md`

- # The Ouroboros Thesis v22 — Convergence
- ## Abstract
- ## 1. Where v22 sits in the lineage
- ## 2. Recent advances (the substance of v22)
- ### 2.1 A5 axiom merge — the A1–A4 uniqueness gap, corrected (MERGED, PR #148)
- ### 2.2 The Cauchy_ND uniqueness chain — partial closure (IN REVIEW)
- ### 2.3 VCG mechanism truthfulness (IN REVIEW, PR #172)
- ### 2.4 SLSA L1 honest build provenance

```
>> ABSTRACT
   v22 ("Convergence") consolidates the formal-verification advances of the May–June 2026 innovation
   rounds into the canonical thesis line. Its central correction: the long-standing claim that axioms
   A1–A4 force the weighted geometric mean is **false**. The asymmetric mean
   Φ(x₁,x₂)=x₁^(2/3)·x₂^(1/3) satisfies A1–A4 yet differs from Λ, and fails permutation invariance.
   We add **A5 (permutation invariance)** as a *structure field* on `LutarAxioms` — not a new axiom —
   keeping the unique-axiom count at 14, and we report the *partial* closure of the n-dimensional
   Cauchy functional-equation chain (topology + functional-analysis + symmetric branches) that, when
   complete, would discharge Λ-uniqueness. **It is not complete on `main`; Λ therefore remains
>> Conjecture 1.** We additionally report: VCG mechanism truthfulness (dominant-strategy + individual
   rationality, proven on branch), **SLSA L1 honest** build provenance (5/5 GHCR images cosign-signed, verifiable via `cosign verify`; L2 roadmap, not yet claimed), the Round 10–11 fr
   crypto, distributed systems), and a **Sim-to-Real doctrine-transfer benchmark** modeled on the
   Walrus physical foundation model that measures a mean doctrine α-gap of **0.10** across five unseen
>> **A5 structure field** to `LutarAxioms`. `Lambda_A5_perm_invariant` is **sorry-free**
   (`Equiv.prod_comp` / `Fintype.prod_equiv`). Because A5 is a structure field, the **unique-axiom
   count stays 14**; the live corpus moves to 794 declarations / 14 unique axioms / 191 sorries
   (measured `974e5e0c`, 2026-06-03 17:32Z).
>> Conjecture 1.** We will elevate Λ to Theorem 1 *only* when every Cauchy_ND sorry closes on `main`
   and Lake CI is green.
   ### 2.3 VCG mechanism truthfulness (IN REVIEW, PR #172)
```

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926;`

## `thesis/ouroboros/papers/v22/README.md`

- # Paper v22 — Convergence
- ## What's new since v21
- ## Honest posture
- ## Doctrine v11 (LOCKED @ `c7c0ba17`)

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926.svg)`

## `thesis/ouroboros/papers/v23/0_README_v23.md`

- # The Ouroboros Thesis v23 — "Conditional Uniqueness" (preface)
- ## PUBLIC CLAIM (read this first)
- ## Doctrine invariants (verified unchanged by this paper)
- ## What this directory contains
- ## Lean source of record
- ## The result in one line

## `thesis/ouroboros/papers/v23/abstract.txt`


## `thesis/ouroboros/papers/v23/cauchy_nd_progress.md`

- # Ouroboros Thesis v23 (draft) — Cauchy_ND Closure Progress
- ## 1. State on `main` (Round 13, machine-checked)
- ## 2. The precise gap (algebraic, not topological)
- ## 3. v23 advance — Round 14 Strategy B (cancellative cone; 0 new axioms)
- ## 4. Why not introduce A6?
- ## 5. Honest status table
- ## References

```
>> A1–A5 aggregator equals the geometric mean `Λ_k(x) = (∏ xᵢ)^{1/k}`. Round 13 (PR #182) landed,
   sorry-free, the **terminal conditional theorem**
   ```
>> A1–A5 constrain Φ along three slices (monotone A1, homogeneous A2, diagonal A3, ≤-max A4, symmetric
   A5) but contain **no inter-axis exchange/bisymmetry law**. The single algebraic property that forces
   multiplicative separability is **bisymmetry / associativity** (Aczél; Kolmogorov–Nagumo):
   \[
>> A5) but contain **no inter-axis exchange/bisymmetry law**. The single algebraic property that forces
   multiplicative separability is **bisymmetry / associativity** (Aczél; Kolmogorov–Nagumo):
   \[
   \Phi(\Phi(x_{11},x_{12}),\Phi(x_{21},x_{22})) = \Phi(\Phi(x_{11},x_{21}),\Phi(x_{12},x_{22})).
>> A1–A5 lack it, and the maxAgg/min witnesses prove it is *independent* of A1–A5. Critically, A2 is
   **bare 1-homogeneity, not continuity** — so a "topological" closure that leans on A2-continuity is
   unavailable; and even full continuity does not help (max/min are continuous on the open orthant yet
   non-separable). **The missing content is algebraic.**
```

DOIs: `10.1007/s10474-021-01185-z`, `10.1007/s10474-021-01185-z).`, `10.14232/actasm-015-028-7`, `10.14232/actasm-015-028-7).`

## `thesis/ouroboros/papers/v23/cover_letter.txt`


DOIs: `10.5281/zenodo.19944926`

## `thesis/ouroboros/papers/v23/maxAgg_counterexample.md`

- # The maxAgg Counterexample — Narrative of the A1–A5 Insufficiency
- ## 1. The hope, and the obstacle
- ## 2. The witness: the maximum aggregator
- ## 3. Why max/min evade uniqueness — the structural reason
- ## 4. What the missing axiom would be (and why we do not add it)
- ## 5. Moral
- ## References

DOIs: `10.1007/s10474-021-01185-z`, `10.1007/s10474-021-01185-z).`

## `thesis/ouroboros/papers/v23/outline.md`

- # The Ouroboros Thesis v23 — "Conditional Uniqueness" — OUTLINE
- ## Section 1 — Abstract
- ## Section 2 — Introduction: what changed since v22
- ## Section 3 — Background
- ## Section 4 — Main result: the conditional uniqueness theorem
- ## Section 5 — Insufficiency theorem: A1–A5 do not determine Λ
- ## Section 6 — Path to the unconditional result
- ## Section 7 — Honest sorries: full table with dependency map

## `thesis/ouroboros/papers/v23/references.bib`


DOIs: `10.1002/j.1538-7305.1948.tb01338.x`, `10.1002/j.1538-7305.1950.tb00463.x`, `10.1007/3-540-45682-1_30`, `10.1007/978-0-387-68276-1`, `10.1007/978-3-030-79876-5_37`, `10.1007/978-3-642-38348-9_21`, `10.1007/BF01217730`, `10.1007/BF01726210`

## `thesis/ouroboros/papers/v23/v23_diff_from_v22.md`

- # v23 diff from v22 — what's new
- ## One-paragraph delta
- ## Itemized changes
- ## What did NOT change (carried verbatim from v22)
- ## Net scientific advance

## `thesis/ouroboros/papers/v24/.zenodo.json`


DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.20053148`

## `thesis/ouroboros/papers/v24/main.md`

- # The Ouroboros Thesis
- ### Axiom-Free Conditional Uniqueness of the Lutar Invariant: A Machine-Verified Trust Foundation for Governed Agentic AI
- ## Abstract
- ## 1. Introduction
- ## 2. The honesty doctrine
- ## 3. The Ouroboros loop: bounded self-governance
- ## 4. The Lutar invariant Λ and its uniqueness boundary
- ### 4.1 Definition and the aggregation axioms

```
>> ABSTRACT
   Governed deployment of agentic artificial intelligence in regulated and defense settings requires more than benchmark accuracy: it requires *checkable* guarantees about what a syst
   The headline advance of v24 is an **axiom-free conditional Λ-uniqueness theorem**. In v23 the conditional uniqueness of Λ was gated on a *declared* project axiom (A6′ block-consist
   The further advance reported in this revision (**v24.1**) is that **CUT-1 — the Aczél quasi-arithmetic *representation* theorem — is now fully closed on its stated, checkable hypot
   Crucially, the *unconditional* uniqueness of Λ under {A1–A5} remains machine-checked **false** (in-tree `maxAgg_ne_Lambda`; `maxAgg` and `min` are A1–A5 counterexamples), so Λ stay
   **Honesty note (verbatim).** The Lutar invariant Λ is **Conjecture 1** unconditionally and is *never* claimed proven unconditionally; unconditional uniqueness under A1–A5 is machin
   **Keywords:** governed agentic AI, trust aggregation, Lutar invariant, geometric mean, slice-multiplicativity, functional-equation uniqueness, Lean 4, Mathlib, axiom-free verificat
   ---
   ## 1. Introduction
>> **Definition (Λ).** For x ∈ [0,1]^k, the Lutar invariant is the equal-weight geometric mean Λ_k(x) = (∏_{i=1}^k x_i)^{1/k}.
   The candidate aggregators Φ : [0,1]^k → [0,1] are constrained by five axioms:
>> **Theorem 4.2 (Refutation of unconditional uniqueness). [machine-checked FALSE] [CI-green]** There exists Φ ≠ Λ_k satisfying A1–A5. In particular the max-aggregator maxAgg(x) = max
   *Lean reference.* The in-tree witness is `Round13.maxAgg_ne_Lambda`. The max function is monotone (A1), positively homogeneous (A2), idempotent (A3), bounded by itself hence ≤ max 
>> **Theorem 4.3 (Uniqueness given factorization). [experimental, axiom-free, CI-green]** Let Φ satisfy A1–A5 and suppose Φ *factors*: there exist exponents α_1, …, α_k ≥ 0 with Φ(x) 
   *Lean reference and sketch.* The Lean term is `lambda_unique_of_factors` (Round-13). Given factorization, idempotence (A3) forces ∑_i α_i = 1 and symmetry (A5) forces all α_i equal
>> **Axiom 6 (Block-consistency / aggregation-invariance, A6′).** Aggregating evidence within independent blocks and then across the block results equals aggregating the flattened col
   **Theorem 4.4 (v23 conditional uniqueness under declared A6′). [axiom-gated] [CI-green]** Under {A1–A5} together with the single declared axiom `A6'_block_consistent`, Λ_k is the u
>> **Theorem 4.4 (v23 conditional uniqueness under declared A6′). [axiom-gated] [CI-green]** Under {A1–A5} together with the single declared axiom `A6'_block_consistent`, Λ_k is the u
   Theorem 4.4 was honest but carried a cost: the trusted base included a *project axiom* that could not itself be discharged in-kernel. v24 removes that cost.
>> Theorem 4.4 was honest but carried a cost: the trusted base included a *project axiom* that could not itself be discharged in-kernel. v24 removes that cost.
   ### 4.4 The v24 advance: axiom-free conditional uniqueness (CUT-2)
```

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926);`

## `thesis/ouroboros/papers/v24/main.tex`

- \section{Introduction}
- \section{The honesty doctrine}
- \section{The Ouroboros loop: bounded self-governance}
- \section{The Lutar invariant $\La$ and its uniqueness boundary}
- \section{The proof-trail / receipt architecture}
- \section{The locked kernel and the frontier theorem families}
- \section{Verification status, in detail}
- \section{Why this is groundbreaking --- the honest case}

```
>> ABSTRACT
   \noindent
   Governed deployment of agentic artificial intelligence in regulated and
   defense settings requires more than benchmark accuracy: it requires
   \emph{checkable} guarantees about what a system did, why it was permitted to do
   it, and whether the record can be tampered with after the fact. This is
   \textbf{v24} of the Ouroboros thesis program of SZL Holdings, a DOI-pinned
   lineage (v1--v23) whose subject is a machine-verified trust substrate resting on
   three pillars: (i) the \emph{Ouroboros loop}, a bounded, well-founded
>> theorem, \lean{cut1\_sharp\_conditional\_lambda}, that drops two hypotheses
   (slice-bisymmetry and unit-normalization, both shown redundant). \textbf{This
   sharpens the conditional result; it does \emph{not} make $\La$ unconditional.}
   Crucially, the
>> theorem --- is now fully closed on its stated, checkable hypotheses}
   (\S\ref{sec:cut1}). Across Waves~18--22 every step of the BKS forward
   construction is discharged kernel-clean, ending with the Wave-22 derivation of
   the BKS Fourth-step ordering. The payoff is a \emph{sharpened} conditional
>> conjecture stays open --- and stays machine-checked false (next paragraph).
   \paragraph{What does \emph{not} change.}
   The single most important honest statement in this program is unchanged and we
>> axiom-free, CI-green} frontier theorems across Waves~11--22
   (\S\ref{sec:frontier}): CF-13 (a deep-equilibrium input-Lipschitz well-posedness
   margin \cite{baikolter2019}), CF-17 (a floating-point summation error bound
   \cite{higham2002}), the Wave-13 results (replay-root completeness, a
>> lemma, monotone-DEQ unique equilibrium, recurrent-depth Lipschitz contraction),
   culminating in the Wave-18--22 CUT-1 construction (\S\ref{sec:cut1}).
   Every one is \printax{}-clean. None is folded into the locked-five.
>> \begin{definition}[Bounded Ouroboros loop]
   A loop is \emph{bounded} if it admits a well-founded measure --- a ranking
   function into a well-ordered set that strictly decreases on each governed step,
   with no infinite descending chain.
```

DOIs: `10.5281/zenodo.19944926`

## `thesis/ouroboros/papers/v24/README.md`

- # Thesis v24.1 — Axiom-Free Conditional Uniqueness of the Lutar Invariant
- ## What this is
- ## The v24 advance (the headline)
- ## The v24.1 advance: CUT-1 closed on its stated hypotheses
- ## Files
- ## Verification status (honest tiers)
- ## Honesty doctrine (binding)
- ## Verify it yourself

```
>> theorem is complete and it **strengthens the conditional** Λ-uniqueness result. It does **not**
   make Λ unconditional; the unconditional conjecture stays open/false.
   - The experimental CI-green tier (~185 thms) is **separate** and is never folded into the locked-5.
   - Supply-chain posture: **SLSA L1 honest, L2 build-attestation present** — L2-verified, L3,
```

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926).`

## `thesis/ouroboros/papers/v24/refs.bib`


DOIs: `10.1002/047174882X`, `10.1002/j.1538-7305.1948.tb01338.x`, `10.1007/978-3-030-79876-5_37`, `10.1007/BF00417500`, `10.1007/BF01726210`, `10.1007/BF02418571`, `10.1007/s10726-018-9589-3`, `10.1016/0022-2496(83)90028-7`

## `thesis/ouroboros/papers/v25/README.md`

- # The Ouroboros Thesis v25 — "Governed Post-Determinism (GPD)"
- ## What this is
- ## The five GPD pillars (and their exact, honestly-tiered results)
- ## The unifying contribution
- ## Doctrine invariants (binding, unchanged)
- ## Files
- ## Lineage (unbroken DOI chain)

DOIs: `10.5281/zenodo.19867281)`, `10.5281/zenodo.19934129)`, `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926).`, `10.5281/zenodo.20020841)`, `10.5281/zenodo.20020845)`, `10.5281/zenodo.20020846)`

## `thesis/ouroboros/papers/v25/unified-gpd-thesis-v25.md`

- # Governed Post-Determinism
- ### A Unified Theory of Verifiable Autonomy: The Lutar Invariant, Khipu Consensus, and the Provenance Substrate
- ## Abstract
- ## Lineage and Prior Art (the SZL DOI chain)
- ### Zenodo deposits (verified resolving)
- ### Prior thesis versions (immutable; this v25 continues, never overwrites)
- ## 1. Introduction: the post-deterministic governance gap
- ### 1.1 The five pillars of GPD

```
>> ABSTRACT
   Autonomous and agentic artificial intelligence is **post-deterministic**: the same prompt, model, and tools can produce different action sequences, and the controlling logic is sta
   GPD rests on **five pillars**, each of which we map to an exact, honestly-tiered result from the SZL corpus. **(P1) Protocol-Bounded Execution** — agentic loops (the Ouroboros loop
   The unifying mathematical observation of GPD is a **single structural pattern**: in *each* pillar, the honest, reachable result is a **conditional theorem whose antecedent is the w
   We hold the SZL **honesty doctrine** binding throughout. Locked-proven = **exactly five** formulas {F1, F11, F12, F18, F19} at `c7c0ba17` (749 declarations / 14 axioms / 163 sorrie
   **Keywords:** governed post-determinism, agentic AI governance, trust aggregation, Lutar invariant, quasi-arithmetic means, slice-multiplicativity, Byzantine fault tolerance, condi
   ---
   ## Lineage and Prior Art (the SZL DOI chain)
   GPD is the *unification layer* over a DOI-pinned thesis lineage. It is grounded **exclusively** in the following SZL Holdings deposits and the prior thesis versions; it cites **no 
>> **Definition (Λ).** For `x ∈ [0,1]^k`, `Λ_k(x) = (∏_{i=1}^{k} x_i)^{1/k}` — the equal-weight geometric mean. Its defining governance behavior is **zero-absorption / weakest-link**:
   Candidate aggregators `Φ : [0,1]^k → [0,1]` are constrained by five axioms (Lean: `LutarAxioms`):
>> **Theorem 4.1 (Refutation of unconditional uniqueness). [machine-checked FALSE] [CI-green].** There exists `Φ ≠ Λ_k` satisfying A1–A5. The max-aggregator `maxAgg(x) = max_i x_i` sa
   *Lean reference.* `Lutar.Round13.maxAgg_ne_Lambda`, with companions `maxAgg_A5`, `maxAgg_A3`, `maxAgg_A2`; separation at `(4,1)` by `decide`. `#print axioms` reports Lean-core axio
>> **Definition 4.2 (Slice-multiplicativity / separability).** `Φ` is *slice-multiplicative* if there exist slice functions `f_i` with **(sep)** `Φ(x) = ∏_i f_i(x_i)`, **(mul)** `f_i(
   **Theorem U (Axiom-free conditional uniqueness of Λ). [experimental, axiom-free, CI-green].** Let `k > 0` and let `Φ` satisfy {A1, A2, A3, A5}. If `Φ` is slice-multiplicative, then
>> **Theorem U (Axiom-free conditional uniqueness of Λ). [experimental, axiom-free, CI-green].** Let `k > 0` and let `Φ` satisfy {A1, A2, A3, A5}. If `Φ` is slice-multiplicative, then
   ```
   #print axioms lambda_unique_of_separable = {propext, Classical.choice, Quot.sound}
>> theorem lambda_unique_of_separable {k : ℕ} (hk : 0 < k)
   (Φ : Aggregator k) (hL : LutarAxioms Φ)
   (f : Fin k → (NNReal → NNReal))
   (hsep  : ∀ x, Φ x = ∏ i, f i (x i))
>> **Conjecture 2 (Unconditional Khipu BFT safety). [Conjecture — NOT a theorem].** No two quorums certify conflicting verdicts, for arbitrary Byzantine behavior. This is **open**. It
   ### 5.3 The conditional theorem — agreement / no split-brain, axiom-clean (Wave 23)
```

DOIs: `10.1145/1629575.1629596`, `10.1145/1629575.1629596)`, `10.1145/357172.357176`, `10.1145/357172.357176);`, `10.5281/zenodo.19867281`, `10.5281/zenodo.19867281)`, `10.5281/zenodo.19867281);`, `10.5281/zenodo.19934129`

## `thesis/ouroboros/papers/v26/unified-gpd-thesis-v26.md`

- # Governed Post-Determinism
- ### A Unified Theory of Verifiable Autonomy: The Lutar Invariant, Khipu Consensus, and the Provenance Substrate
- ## Abstract
- ## Lineage and Prior Art (the SZL DOI chain)
- ### Zenodo deposits (verified resolving)
- ### Prior thesis versions (immutable; this v26 continues, never overwrites)
- ## 1. Introduction: the post-deterministic governance gap
- ### 1.1 The five pillars of GPD

```
>> ABSTRACT
   Autonomous and agentic artificial intelligence is **post-deterministic**: the same prompt, model, and tools can produce different action sequences, and the controlling logic is sta
   GPD rests on **five pillars**, each of which we map to an exact, honestly-tiered result from the SZL corpus. **(P1) Protocol-Bounded Execution** — agentic loops (the Ouroboros loop
   The unifying mathematical observation of GPD is a **single structural pattern**: in *each* pillar, the honest, reachable result is a **conditional theorem whose antecedent is the w
   We hold the SZL **honesty doctrine** binding throughout. Locked-proven = **exactly eight** formulas {F1, F4, F7, F11, F12, F18, F19, F22} (the locked count is itself a theorem, `lo
   **Keywords:** governed post-determinism, agentic AI governance, trust aggregation, Lutar invariant, quasi-arithmetic means, slice-multiplicativity, Byzantine fault tolerance, condi
   ---
   ## Lineage and Prior Art (the SZL DOI chain)
   GPD is the *unification layer* over a DOI-pinned thesis lineage. It is grounded **exclusively** in the following SZL Holdings deposits and the prior thesis versions; it cites **no 
>> **Definition (Λ).** For `x ∈ [0,1]^k`, `Λ_k(x) = (∏_{i=1}^{k} x_i)^{1/k}` — the equal-weight geometric mean. Its defining governance behavior is **zero-absorption / weakest-link**:
   Candidate aggregators `Φ : [0,1]^k → [0,1]` are constrained by five axioms (Lean: `LutarAxioms`):
>> **Theorem 4.1 (Refutation of unconditional uniqueness). [machine-checked FALSE] [CI-green].** There exists `Φ ≠ Λ_k` satisfying A1–A5. The max-aggregator `maxAgg(x) = max_i x_i` sa
   *Lean reference.* `Lutar.Round13.maxAgg_ne_Lambda`, with companions `maxAgg_A5`, `maxAgg_A3`, `maxAgg_A2`; separation at `(4,1)` by `decide`. `#print axioms` reports Lean-core axio
>> **Definition 4.2 (Slice-multiplicativity / separability).** `Φ` is *slice-multiplicative* if there exist slice functions `f_i` with **(sep)** `Φ(x) = ∏_i f_i(x_i)`, **(mul)** `f_i(
   **Theorem U (Axiom-free conditional uniqueness of Λ). [experimental, axiom-free, CI-green].** Let `k > 0` and let `Φ` satisfy {A1, A2, A3, A5}. If `Φ` is slice-multiplicative, then
>> **Theorem U (Axiom-free conditional uniqueness of Λ). [experimental, axiom-free, CI-green].** Let `k > 0` and let `Φ` satisfy {A1, A2, A3, A5}. If `Φ` is slice-multiplicative, then
   ```
   #print axioms lambda_unique_of_separable = {propext, Classical.choice, Quot.sound}
>> theorem lambda_unique_of_separable {k : ℕ} (hk : 0 < k)
   (Φ : Aggregator k) (hL : LutarAxioms Φ)
   (f : Fin k → (NNReal → NNReal))
   (hsep  : ∀ x, Φ x = ∏ i, f i (x i))
>> **Conjecture 2 (Unconditional Khipu BFT safety). [Conjecture — NOT a theorem].** No two quorums certify conflicting verdicts, for arbitrary Byzantine behavior. This is **open**. It
   ### 5.3 The conditional theorem — agreement / no split-brain, axiom-clean (Wave 23)
```

DOIs: `10.1145/1629575.1629596`, `10.1145/1629575.1629596)`, `10.1145/357172.357176`, `10.1145/357172.357176);`, `10.5281/zenodo.19867281`, `10.5281/zenodo.19867281)`, `10.5281/zenodo.19867281);`, `10.5281/zenodo.19934129`

## `thesis/ouroboros/README.md`

- # 📜 ouroboros-thesis
- # ouroboros-thesis — Ouroboros Thesis v18.0
- ## On Hugging Face
- ## Thesis statement
- ## Evidence table
- ## DOI chain
- ## Axiom Semantic Drift (v3 to v14)
- ### CAUCHY_ND sorry — symmetry gap (TH10 status) — A5 CORRECTION APPLIED 2026-06-02

```
>> A5 (permutation invariance) **fails**: `Φ(2,1) = 2^(2/3) ≠ 2^(1/3) = Φ(1,2)`.
   Source: PhD-Math functional analysis audit, `PHASE3_FINAL_SUMMARY.md` Gate 6 (2026-06-02).
   **Fix applied (MERGED 2026-06-03):** PR [szl-holdings/lutar-lean#148](https://github.com/szl-holdings/lutar-lean/pull/148)
```

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926).`, `10.5281/zenodo.19944926.svg)`, `10.5281/zenodo.19983066`, `10.5281/zenodo.19983066)`, `10.5281/zenodo.20434276`, `10.5281/zenodo.20434276)`

## `thesis/THESIS_LINEAGE.md`

- # THESIS_LINEAGE.md — The Ouroboros Thesis, v1 → v26
- ## Canonical timeline
- ## How innovation rounds (R1–R11) converge with thesis versions
- ## Recent advances landing in v22 (2026-06-03)

```
>> A5 --> v22
   subgraph KERNEL["Locked kernel"]
   K[lutar-lean @ c7c0ba17<br/>749 decl · 14 axioms · 163 sorries<br/>post-A5 live: 794 · 14 · 191]
>> A5 --> K
   LAMBDA{{"Λ Conjecture 1<br/>disproved as stated<br/>weaker-condition question open"}}
   K --> LAMBDA
```

DOIs: `10.5281/zenodo.19867281)`, `10.5281/zenodo.19934129)`, `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926.svg)`, `10.5281/zenodo.19983066)`, `10.5281/zenodo.20020841)`, `10.5281/zenodo.20020845)`

## `thesis/v19/main.md`

- # The Verification Bridge
- ### Consolidating the Multi-Track Substrate Expansion into a Per-Theorem Verified Index, on the Path from Expansion to Verified Anatomy
- ## Abstract
- ## 1. Why a bridge, and why it was almost skipped
- ## 2. The v18 baseline: what the expansion shipped
- ## 3. The per-theorem verified index (the bridge artifact)
- ## 4. The kernel-hardening invariant: locked vs. experimental scope
- ## 5. The honesty doctrine, carried across the bridge

```
>> ABSTRACT
   Between the multi-track *substrate expansion* (v18, 2026-05-30) and the formally-verified *anatomical substrate* (v20, 2026-06-01), the SZL Holdings Ouroboros line passed through a
   **Keywords:** formal verification, Lean 4, per-theorem index, governance substrate, honesty doctrine, sorry accounting, differential privacy, PAC-Bayes, mechanism design, certified
   *Honesty note (verbatim):* The Lutar invariant Λ is **Conjecture 1** unconditionally and is *never* claimed proven unconditionally. Exactly five formulas are locked/proven at `c7c0
   ---
   ## 1. Why a bridge, and why it was almost skipped
   The Ouroboros thesis line records the intellectual provenance of the SZL governance substrate as a sequence of versioned, DOI-pinned papers. For a period the lineage read "v18 → v2
   That work has a clear and defensible identity. v18 ("Multi-Track Substrate Expansion") was an *expansion* release: it grew the Lean corpus across many mathematical tracks at once. 
   **Thesis of v19.** A governance substrate earns trust not by the *number* of modules it ships but by the *legibility of their status*. v19's thesis is that the right unit of accoun
>> F12 and F19 prove only the *additive* fragments of, respectively, Kuramoto synchronization and the Bekenstein bound; they are honest scaffolding, never described as the full physic
   **The experimental scope and the drift gate.** Everything in the 2026-05-30 expansion track (Section 3) lives in an *experimental* scope that is counter-excluded from the locked co
>> **Proposition (scope-separation invariant, informal).** Adding an experimental module changes the *live* corpus counts but must leave the *locked* counts (749, 14, 163) at `c7c0ba1
   This invariant is not a theorem about mathematics; it is a theorem about *bookkeeping discipline*, and it is exactly the externalized meta-level (Lean kernel → CI → human sign-off)
>> **Conjecture 1 (The Lutar invariant; never a theorem).** The equal-weight geometric mean Λ_k is the correct unique trust aggregator for governed AI. This is an open claim about the
   ## 6. Position in the lineage
```

DOIs: `10.1002/j.1538-7305.1948.tb01338.x.`, `10.1007/11681878_14.`, `10.1007/978-3-030-79876-5_37.`, `10.1007/s10726-018-9589-3.`, `10.1109/CSF.2017.11.`, `10.1109/TIT.1964.1053661.`, `10.1111/j.1540-6261.1961.tb02789.x.`, `10.1137/0108018.`

## `thesis/v19/main.tex`

- \section{Why a bridge, and why it was almost skipped}
- \section{The v18 baseline: what the expansion shipped}
- \section{The per-theorem verified index (the bridge artifact)}
- \section{The kernel-hardening invariant: locked vs.\ experimental scope}
- \section{The honesty doctrine, carried across the bridge}
- \section{Position in the lineage}
- \section{Limitations}
- \section{Conclusion}

```
>> ABSTRACT
   \noindent
   Between the multi-track \emph{substrate expansion} (v18, 2026-05-30) and the
   formally-verified \emph{anatomical substrate} (v20, 2026-06-01), the SZL Holdings
   Ouroboros line passed through a short but pivotal phase whose product was not new
   breadth but new \emph{discipline}: the consolidation of a rapidly expanding Lean~4
   corpus into a per-theorem verified index with an honest, machine-checkable status for
   every claim. This paper, v19 ``The Verification Bridge,'' documents that phase. v18
   added roughly twenty-nine modules across coding theory, differential privacy,
>> theorem; the locked kernel proves exactly five formulas; SLSA is L1+L2, not L3; and
   every idealizing axiom is disclosed. v19's contribution is the \emph{bridge itself}:
   the move from ``we shipped many modules'' to ``here is exactly what each module
   proves, with a per-theorem status ledger,'' which is precisely the externalized
>> lemma-conditions.
   \end{remark}
   % =====================================================================
>> F12 and F19 prove only the \emph{additive} fragments of, respectively, Kuramoto
   synchronization and the Bekenstein bound; they are honest scaffolding, never described
   as the full physical theorems.
>> \begin{proposition}[Scope-separation invariant, informal]
   Adding an experimental module changes the \emph{live} corpus counts but must leave the
   \emph{locked} counts $(749,14,163)$ at \texttt{c7c0ba17} invariant. A change to the
   locked counts is a doctrine violation and fails CI.
>> \begin{conjecture}[The Lutar invariant; never a theorem]
   \label{conj:lambda}
   \statusConj\;
   The equal-weight geometric mean $\La_k$ is the correct unique trust aggregator for
```

DOIs: `10.5281/zenodo.19944926`

## `thesis/v19/README.md`

- # Thesis v19 — The Verification Bridge
- ## What this version is
- ## What this version is NOT
- ## Honest posture (load-bearing)
- ## Doctrine v11 (LOCKED @ `c7c0ba17`)
- ## Lineage

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926.svg)`

## `thesis/v19/refs.bib`


DOIs: `10.1002/j.1538-7305.1948.tb01338.x`, `10.1007/11681878_14`, `10.1007/978-3-030-79876-5_37`, `10.1007/s10726-018-9589-3`, `10.1109/CSF.2017.11`, `10.1109/TIT.1964.1053661`, `10.1111/j.1540-6261.1961.tb02789.x`, `10.1137/0108018`

## `thesis/v20/main.md`

- # The Culmination
- ### A Formally-Verified Anatomical Substrate: Presenting the Governance Corpus as a Twelve-Organ Cybernetic Body with a Per-Theorem Verified Index
- ## Abstract
- ## 1. What "culmination" means here
- ## 2. The anatomical substrate: twelve organs
- ## 3. The verified spine: the v18 thesis-theorem track
- ## 4. The five locked formulas, mapped onto the anatomy
- ## 5. Operational facts vs. proven theorems

```
>> ABSTRACT
   This paper, v20 "The Culmination," presents the SZL Holdings Ouroboros governance substrate as a single formally-verified *anatomical* object: a twelve-organ cybernetic body in whi
   **Keywords:** formal verification, Lean 4, cybernetic runtime, anatomical substrate, per-theorem index, honesty doctrine, governance algebra, event sourcing, Reed–Solomon, replay d
   *Honesty note (verbatim):* The Lutar invariant Λ is **Conjecture 1** unconditionally and is *never* claimed proven unconditionally. Exactly five formulas are locked/proven at `c7c0
   ---
   ## 1. What "culmination" means here
   The Ouroboros thesis line is a sequence of versioned, DOI-pinned papers that record the provenance of the SZL governance substrate. v18 ("Multi-Track Substrate Expansion") grew the
   We are precise about the word. "Culmination" here does **not** mean "everything is now proven." It means: the corpus has reached the point where it can be read as a single, legible
   **Thesis of v20.** A governance substrate is most trustworthy when it can be exhibited as an *anatomy*: a finite set of named organs, each with a typed interface, a deterministic s
>> F12 and F19 prove only *additive fragments* of, respectively, Kuramoto synchronization and the Bekenstein bound; they are honest scaffolding, never described as the full physical t
   ## 5. Operational facts vs. proven theorems
>> **Conjecture 1 (The Lutar invariant; never a theorem).** The equal-weight geometric mean Λ_k is the correct unique trust aggregator for governed AI. This is an open claim about the
   ## 8. Position in the lineage
```

DOIs: `10.1002/j.1538-7305.1948.tb01338.x.`, `10.1007/978-3-030-79876-5_37.`, `10.1007/BFb0013365.`, `10.1007/s10726-018-9589-3.`, `10.1103/PhysRevD.23.287.`, `10.1109/TIT.1964.1053661.`, `10.1137/0108018.`, `10.1145/1629575.1629596.`

## `thesis/v20/main.tex`

- \section{What ``culmination'' means here}
- \section{The anatomical substrate: twelve organs}
- \section{The verified spine: the v18 thesis-theorem track}
- \section{The five locked formulas, mapped onto the anatomy}
- \section{Operational facts vs.\ proven theorems}
- \section{Organ-to-obligation traceability map}
- \section{The honesty doctrine, carried into the anatomy}
- \section{Position in the lineage}

```
>> ABSTRACT
   \noindent
   This paper, v20 ``The Culmination,'' presents the SZL Holdings Ouroboros governance
   substrate as a single formally-verified \emph{anatomical} object: a twelve-organ
   cybernetic body in which each organ is a typed runtime component, the organs
   communicate through an append-only, content-addressed event log, and the whole is held
   to a per-theorem verified index inherited from the v19 Verification Bridge. The
   contribution of v20 is not a new mathematical theorem; it is a \emph{presentation} ---
   the consolidation of the multi-track corpus into an anatomy that can be read, audited,
>> F12 and F19 prove only \emph{additive fragments} of, respectively, Kuramoto
   synchronization and the Bekenstein bound; they are honest scaffolding, never described
   as the full physical theorems.
>> axiom~\cite{csato2018,aczel1948} are later v22/v23 results; v20 preserves the
   ``$\La =$ Conjecture~1'' label.)
   \item \textbf{Locked $=5$.} The locked kernel proves exactly $\{$F1, F11, F12, F18,
   F19$\}$. All other formal work is experimental until re-audited under the authoritative
>> F19$\}$. All other formal work is experimental until re-audited under the authoritative
   \texttt{lake build}.
   \item \textbf{Disclosed idealizations.} Where a proof needs cryptographic hardness it
   declares a named axiom (the SHA-256 axioms in \texttt{TH\_V18\_14}) and discloses it; it
>> \begin{conjecture}[The Lutar invariant; never a theorem]
   \statusConj\ The equal-weight geometric mean $\La_k$ is the correct unique trust
   aggregator for governed AI. This is an open claim about the \emph{right} axiomatization,
   not a mathematical theorem; the substrate carries the ``Conjecture~1'' label on $\La$ in
>> theorem; its contribution is the anatomical presentation and the claim-class tagging.
   \item \textbf{Open obligations remain.} Five thesis-spine modules carry open obligations
   (Section~\ref{sec:spine}); most of the runtime organ properties are open formulas
   (Section~\ref{sec:classes}).
>> Conjecture~1 unconditionally (never a theorem); locked/proven $=5$
   $\{$F1,F11,F12,F18,F19$\}$ @ \texttt{c7c0ba17} (749/14/163); declared axioms disclosed;
   SLSA L1+L2 (not L3). Quechua organ names are brand naming. No fabricated results, no
   fake citations.\normalsize
```

DOIs: `10.1002/j.1538-7305.1948.tb01338.x.`, `10.1007/978-3-030-79876-5`, `10.1007/BFb0013365.`, `10.1007/s10726-018-9589-3.`, `10.1103/PhysRevD.23.287.`, `10.1109/TIT.1964.1053661.`, `10.1137/0108018.`, `10.1145/1629575.1629596.`

## `thesis/v20/README.md`

- # Thesis v20 — The Culmination
- ## What this version is
- ## What this version is NOT
- ## Honest posture (load-bearing)
- ## Doctrine v11 (LOCKED @ `c7c0ba17`)
- ## Lineage

```
>> theorem, the machine-checked refutation of unconditional uniqueness, and the VCG proof
   are all later (v22/v23) results and are **not** claimed here.
   ## Honest posture (load-bearing)
```

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926.svg)`

## `thesis/v20/refs.bib`


DOIs: `10.1002/j.1538-7305.1948.tb01338.x`, `10.1007/978-3-030-79876-5_37`, `10.1007/BFb0013365`, `10.1007/s10726-018-9589-3`, `10.1103/PhysRevD.23.287`, `10.1109/TIT.1964.1053661`, `10.1137/0108018`, `10.1145/1629575.1629596`

## `thesis/v21/main.md`

- # The PURIQ-OS Substrate
- ### An Honest, Audit-Ready Cybernetic Runtime for Verifiable Agentic AI
- ## Abstract
- ## 1. Introduction — What Changed Since v20
- ### 1.1 Claim discipline
- ### 1.2 Doctrine v11 (verbatim, LOCKED @ `c7c0ba17`)
- ### 1.3 Honesty contract
- ### 1.4 Roadmap of this paper

```
>> ABSTRACT
   This paper records every new finding shipped in the v20→v21 working session for the SZL Holdings Ouroboros substrate. We describe **PURIQ-OS**, a 12-organ cybernetic runtime with a
   ---
   ## 1. Introduction — What Changed Since v20
   Version 20 of the Ouroboros thesis ("The Culmination") presented the substrate as a formally-verified anatomical body under Doctrine v11 [8]. This v21 records what was built *after
   ### 1.1 Claim discipline
   The posture of this document is deliberately conservative. We separate three claim classes and never blur them:
   1. **Proved.** Results mechanised in Lean 4 with no `sorry` and no external axioms beyond Lean's standard logical core. Five of the twenty-three formulas are in this class.
   2. **Operational fact.** Engineering claims established by running, signing, and verifying real artifacts: DSSE envelopes, a Rekor transparency-log entry, an LMDB write/kill/restar
>> **Theorem 3.1 (F1 — Replay-hash determinism).** For any pure deterministic step `f : α → β` and input `x`, replay reproduces the original: `f(x) = f(x)`; and over a recorded trace,
   ```lean
   theorem f1_replay_hash_determinism {a b : Type}
>> theorem f1_replay_hash_determinism {a b : Type}
   (f : a -> b) (x : a) : f x = f x := rfl
   theorem f1_replay_trace_stable {a b : Type}
   (f : a -> b) (xs : List a) : xs.map f = xs.map f := rfl
>> theorem f1_replay_trace_stable {a b : Type}
   (f : a -> b) (xs : List a) : xs.map f = xs.map f := rfl
   ```
>> **Theorem 3.2 (F11 — Ayni reciprocity conservation).** Event-sourced reciprocity conserves balance: folding a credit `c` then an equal debit `c` onto balance `b` returns `b`, i.e. 
   ```lean
   theorem f11_ayni_reciprocity_conservation (b c : Int) :
>> theorem f11_ayni_reciprocity_conservation (b c : Int) :
   (b + c) - c = b := by simp [Int.add_sub_cancel]
   theorem f11_tit_for_tat_parity (g d : Int) :
   (g + d) - (0 + d) = g := by simp
>> theorem f11_tit_for_tat_parity (g d : Int) :
   (g + d) - (0 + d) = g := by simp
   ```
```

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926.`

## `thesis/v21/main.tex`

- \section{Introduction --- What Changed Since v20}
- \section{PURIQ-OS Runtime}
- \section{Agentic Formulas (Lean-proved + sorry-tagged)}
- \section{KIPU+QILLQAQ Substrate and the 16-Organ Genome}
- \section{AYNI-OS Reciprocity}
- \section{Wire D + DSSE}
- \section{Khipu DAG + Reed--Solomon}
- \section{Unay + LMDB Persistence}

```
>> ABSTRACT
   \noindent
   This paper records every new finding shipped in the v20$\to$v21 working session for the
   SZL Holdings Ouroboros substrate. We describe \textbf{PURIQ-OS}, a 12-organ cybernetic
   runtime with an explicit scheduler, Khipu event emission, a daemon loop, and a
   replay-hash gate, framed honestly in the cybernetic tradition of Wiener~\cite{wiener1948}
   and the information theory of Shannon~\cite{shannon1948}. We present \textbf{23 agentic
   formulas}, of which \textbf{five are mechanised in Lean~4 with no \texttt{sorry} and no
   external axioms} (F1, F11, F12, F18, F19); the remaining eighteen are stated honestly and
>> theorem. Doctrine v11 numbers are reproduced verbatim: \textbf{749 declarations, 14
   unique axioms, 163 sorries} at lutar-lean \texttt{c7c0ba17}. No mystical claims are made;
   Quechua organ names are brand naming.
   \end{abstract}
>> F1 (\S\ref{sec:formulas}), proved in Lean. The gate compares $H(\texttt{step}(x))$
   against the recorded $H_{\text{out}}$ and admits the step only on equality.
   % =====================================================================
>> \begin{theorem}[F1 --- Replay-hash determinism]\statusLocked\ For any pure deterministic
   step $f:\alpha\to\beta$ and input $x$, replay reproduces the original: $f(x)=f(x)$; and
   over a recorded trace, $\texttt{map}\,f\,\texttt{xs}=\texttt{map}\,f\,\texttt{xs}$.
   \end{theorem}
>> theorem f1_replay_hash_determinism {a b : Type}
   (f : a -> b) (x : a) : f x = f x := rfl
   theorem f1_replay_trace_stable {a b : Type}
   (f : a -> b) (xs : List a) : xs.map f = xs.map f := rfl
>> theorem f1_replay_trace_stable {a b : Type}
   (f : a -> b) (xs : List a) : xs.map f = xs.map f := rfl
   \end{lstlisting}
>> \begin{theorem}[F11 --- Ayni reciprocity conservation]\statusLocked\ Event-sourced
   reciprocity conserves balance: $(b+c)-c=b$ over $\mathbb{Z}$. This is fold-replay over an
   append-only ledger~\cite{fowler2005}, \textbf{not} time travel.
   \end{theorem}
```

DOIs: `10.1002/j.1538-7305.1948.tb01338.x.`, `10.1007/978-3-030-79876-5`, `10.1007/BFb0013365.`, `10.1103/PhysRevD.23.287.`, `10.1126/science.7466396.`, `10.1137/0108018.`, `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926.`

## `thesis/v21/README.md`

- # Thesis v21 — The PURIQ-OS Substrate
- ## What this version is
- ## Honest posture (load-bearing)
- ## Doctrine v11 (LOCKED @ `c7c0ba17`)
- ## Lineage

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926.svg)`

## `thesis/v21/refs.bib`


DOIs: `10.1002/j.1538-7305.1948.tb01338.x`, `10.1007/978-3-030-79876-5_37`, `10.1007/BFb0013365`, `10.1103/PhysRevD.23.287`, `10.1126/science.7466396`, `10.1137/0108018`, `10.5281/zenodo.19944926`

## `thesis/v22/main.md`

- # Convergence
- ### An Honest, Audit-Ready Convergence of the Λ-Aggregator Uniqueness Chain, Mechanism Truthfulness, and Sim-to-Real Doctrine Transfer
- ## Abstract
- ## 1. Where v22 Sits in the Lineage
- ### 1.1 Claim discipline (carried verbatim from v21)
- ### 1.2 The central correction stated plainly
- ### 1.3 Doctrine v11 (verbatim, LOCKED @ `c7c0ba17`)
- ## 2. Related Work: Means Characterizations, Mechanism Design, and Provenance

```
>> ABSTRACT
   v22 ("Convergence") consolidates the formal-verification advances of the May–June 2026 innovation rounds into the canonical thesis line. Its central correction is stated up front: 
   ---
   ## 1. Where v22 Sits in the Lineage
   Version 22 follows v21 ("The PURIQ-OS Substrate", 2026-06-01). It is **not** a new architecture; it is the **convergence** of the mathematical-rigor work that v14–v21 deferred. Whe
   ### 1.1 Claim discipline (carried verbatim from v21)
   v22 preserves the three-class claim discipline of its predecessors and never blurs the classes:
   1. **Proved (on main, locked).** Mechanised in Lean 4 with no `sorry` and a disclosed axiom footprint, included in the locked kernel @ `c7c0ba17`.
   2. **Proved (on branch, in review).** Mechanised and sorry-free on a feature branch but *not yet merged to main* — e.g. the VCG truthfulness lemmas and the A5 structure-field merge
>> A5 permutation-invariance, merged via PR #148 as a *structure field*, leaves the **unique-axiom count at 14**; the post-A5 live corpus measures 794 declarations / 14 unique axioms 
   ---
>> theorem Lambda_A5_perm_invariant : IsPermutationInvariant Lambda := by
   intro sigma; simpa using Fintype.prod_equiv sigma _ _ (by simp)
   -- #print axioms Lambda_A5_perm_invariant  => [propext, Quot.sound]
   ```
>> **Theorem 7.1 (vcgDominantStrategyTruth — in review).** In the trust-weighted VCG mechanism, truthful reporting of an agent's private valuation is a **dominant strategy**: for ever
   **Theorem 7.2 (vcgIndividualRationality — in review).** Participation in the mechanism never yields negative utility: each agent's equilibrium utility is non-negative, so a rationa
>> **Theorem 7.2 (vcgIndividualRationality — in review).** Participation in the mechanism never yields negative utility: each agent's equilibrium utility is non-negative, so a rationa
   ### 7.1 The trust-weighted allocation setting
```

DOIs: `10.1007/3-540-48184-2_32`, `10.1007/978-3-030-79876-5_37`, `10.1007/s10726-018-9589-3`, `10.1109/SP.1982.10014`, `10.1111/j.1540-6261.1961.tb02789.x`, `10.1126/science.7466396`, `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`

## `thesis/v22/main.tex`

- \section{Where v22 Sits in the Lineage}
- \section{Related Work: Means Characterizations, Mechanism Design, and Provenance}
- \section{Formal Preliminaries: the Axioms and the Invariant}
- \section{A5 Axiom Merge --- the A1--A4 Uniqueness Gap, Corrected (MERGED, PR \#148)}
- \section{The Cauchy\_ND Uniqueness Chain --- Partial Closure (IN REVIEW)}
- \section{The Axiom-Count Invariant Under the A5 Merge}
- \section{VCG Mechanism Truthfulness (Proven on Branch, PR \#172)}
- \section{SLSA L1+L2 Build Provenance (Achieved)}

```
>> ABSTRACT
   \noindent
   v22 (``Convergence'') consolidates the formal-verification advances of the
   May--June 2026 innovation rounds into the canonical thesis line. Its central
   correction is stated up front: the long-standing claim that axioms A1--A4 force
   the weighted geometric mean is \textbf{false}. The asymmetric mean
   $\Phi(x_1,x_2)=x_1^{2/3}\,x_2^{1/3}$ satisfies A1--A4 yet differs from $\La$ and
   fails permutation invariance. We add \textbf{A5 (permutation invariance)} as a
   \emph{structure field} on the axiom record --- \textbf{not} a new axiom --- keeping
>> Conjecture~1.} We additionally report: VCG mechanism truthfulness (dominant-strategy
   incentive compatibility plus individual rationality, proven on branch); \textbf{SLSA
   L1+L2} build provenance (5/5 GHCR images verified via \texttt{slsa-verifier}); the
   Round~10--11 frontier formalizations (physics, quantum, CS, crypto, distributed
>> A1--A4'' was \textbf{incorrect}. v22 names the guilty lemma, exhibits the
   counterexample, adds the missing structure (A5), and reports honestly that the
   resulting uniqueness chain is \emph{still open}. This is the Lakatosian discipline
   of the whole thesis line made concrete: a refuted conjecture is corrected in the
>> A1--A4 are \emph{insufficient} to force the geometric mean. Kolmogorov (1930) and
   Nagumo (1930) gave the quasi-arithmetic-mean characterizations; Acz\'el (1948) gave
   the functional-equation route to means; Hardy, Littlewood \& P\'olya (1934)
   developed the power-mean family; and Voorneveld (2008) characterized aggregators
>> A1 Continuity & $\Phi$ is continuous on the unit cube. \\
   A2 Homogeneity & $\Phi(t\cdot x)=t\cdot\Phi(x)$ (positive homogeneity of degree 1). \\
   A3 Idempotence & $\Phi(c,\dots,c)=c$ on the diagonal. \\
   A4 Boundedness & $\min x_i \le \Phi(x) \le \max x_i$ (fixes endpoints). \\
>> A2 Homogeneity & $\Phi(t\cdot x)=t\cdot\Phi(x)$ (positive homogeneity of degree 1). \\
   A3 Idempotence & $\Phi(c,\dots,c)=c$ on the diagonal. \\
   A4 Boundedness & $\min x_i \le \Phi(x) \le \max x_i$ (fixes endpoints). \\
   A5 Permutation invariance & $\Phi(x)$ invariant under any reordering (the NEW structure field). \\
>> A3 Idempotence & $\Phi(c,\dots,c)=c$ on the diagonal. \\
   A4 Boundedness & $\min x_i \le \Phi(x) \le \max x_i$ (fixes endpoints). \\
   A5 Permutation invariance & $\Phi(x)$ invariant under any reordering (the NEW structure field). \\
   \bottomrule
```

DOIs: `10.1007/3-540-48184-2`, `10.1007/978-3-030-79876-5`, `10.1007/s10726-018-9589-3`, `10.1109/SP.1982.10014`, `10.1111/j.1540-6261.1961.tb02789.x`, `10.1126/science.7466396`, `10.5281/zenodo.19944926`, `10.5281/zenodo.20119582`

## `thesis/v22/README.md`

- # Thesis v22 — Convergence
- ## What this is
- ## The one-line thesis
- ## Files
- ## The central correction (§4)
- ## What v22 reports (honest tiers)
- ## How to reproduce
- # 1. Verify the A5 lemma is sorry-free and Lean-core only

```
>> axiom A6′ (the v23 route). **Λ therefore remains Conjecture 1.**
   ## What v22 reports (honest tiers)
```

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.20119582`, `10.5281/zenodo.20119582)`

## `thesis/v22/refs.bib`


DOIs: `10.1007/3-540-48184-2_32`, `10.1007/978-3-030-79876-5_37`, `10.1007/s10726-018-9589-3`, `10.1109/SP.1982.10014`, `10.1111/j.1540-6261.1961.tb02789.x`, `10.1126/science.7466396`

## `thesis/v23/main.md`

- # The Unified Substrate
- ### A Machine-Verified Trust Foundation for Governed Agentic AI: Unifying the Ouroboros Loop, the Lutar Invariant, and a Disclosed-Axiom Proof Trail
- ## Abstract
- ## 1. Introduction
- ## 2. The honesty doctrine
- ## 3. The Ouroboros loop: bounded self-governance
- ## 4. The Lutar invariant Λ and its uniqueness boundary
- ### 4.1 Definition and axioms

```
>> ABSTRACT
   Governed deployment of agentic artificial intelligence in regulated and defense settings requires more than benchmark accuracy: it requires *checkable* guarantees about what a syst
   Our central methodological commitment is an **honesty doctrine**: we distinguish, at every point of assertion, among *proven* (kernel-verified, Lean-core axioms only), *proven unde
   Crucially, the *unconditional* uniqueness of Λ under {A1–A5} is provably **false**: we exhibit a machine-checked counterexample. We therefore label Λ as **Conjecture 1** unconditio
   ---
   ## 1. Introduction
   The deployment of agentic AI into regulated industries (finance, healthcare) and defense settings has exposed a gap that benchmark performance cannot close: a *trust* gap. A regula
   This paper is the twenty-third and unifying version of a thesis program that SZL Holdings has developed since April 2026. The prior twenty-two versions each advanced a piece of the
   The single most important honest statement in this paper is this: the central trust aggregator's unconditional uniqueness is **false**, and we prove it false by machine. The aggreg
>> **Definition (Λ).** For x ∈ [0,1]^k, the Lutar invariant is the equal-weight geometric mean Λ_k(x) = (∏_{i=1}^k x_i)^{1/k}.
   The governance axioms a trust aggregator Φ : [0,1]^k → [0,1] should satisfy:
>> **Theorem 4.2 (`maxAgg_ne_Lambda`, `unconditional_lambda_is_false`).** The max aggregator `maxAgg(x) = max_i x_i` satisfies A1–A5 but is **not** equal to Λ. At x = (4,1) (rescaled 
   This is the epistemic heart of the paper: we did not merely fail to prove unconditional uniqueness, we *proved its negation*.
>> **Theorem 4.3 (`lambda_unique_of_factors`, Round-13).** Λ is the unique A1–A5 aggregator that additionally factors multiplicatively over its arguments. **[sorry-free]**.
   ### 4.4 The conditional uniqueness theorem — Theorem 4.4 *(CI-green under declared A6′)*
>> **Theorem 4.4 (`lambda_unique_under_block`).** Under {A1–A5} together with the declared axiom **A6′ (block-consistency)**, Λ is the *unique* aggregator. **[CI-green]** (Lutar/Wave4
   `#print axioms lambda_unique_under_block` ⇒ `[A6'_block_consistent, propext, Quot.sound, Classical.choice]`.
```

DOIs: `10.1002/j.1538-7305.1948.tb01338.x`, `10.1002/j.1538-7305.1948.tb01338.x)`, `10.1007/BF00417500`, `10.1007/BF00417500)`, `10.1007/BF02418571`, `10.1007/BF02418571)`, `10.1007/s10726-018-9589-3`, `10.1007/s10726-018-9589-3);`

## `thesis/v23/main.tex`

- \section{Introduction: the problem of governed AI}
- \section{The lineage: from loop to invariant to verified substrate}
- \section{The Ouroboros loop thesis}
- \section{The Lutar invariant $\La$}
- \section{The proof-trail / receipt architecture}
- \section{The locked kernel and the honest counts}
- \section{The mathematics: stated theorems with status}
- \section{Why this is groundbreaking --- the honest case}

```
>> ABSTRACT
   \noindent
   Governed deployment of agentic artificial intelligence in regulated and defense
   settings requires more than benchmark accuracy: it requires \emph{checkable}
   guarantees about what a system did, why it was permitted to do it, and whether the
   record can be tampered with after the fact. We present the \textbf{Unified
   Substrate} (v23), the consolidation of twenty-two prior thesis versions (v1--v22)
   of SZL Holdings into a single coherent account of a machine-verified trust
   substrate for governed AI. The substrate rests on three pillars: (i) the
>> axiom \texttt{A6'\_block\_consistent} and is never conflated with the unconditional
   claim. Exactly five formulas are locked/proven. Declared idealizations
   (\texttt{hash\_collision\_resistant}, \texttt{ecdsa\_unforgeable}, the Merkle
   collision-resistance axioms, and \texttt{A6'\_block\_consistent}) are disclosed in
>> \begin{definition}[Bounded Ouroboros loop]
   A loop is \emph{bounded} if it admits a well-founded measure: a ranking function
   into a well-ordered set that strictly decreases on each governed step, with no
   infinite descending chain.
>> \begin{definition}[Lutar invariant]
   For $x = (x_1,\dots,x_k) \in [0,1]^k$, the \emph{Lutar invariant} is the equal-weight
   geometric mean
   \[
>> \begin{axiom}[Monotonicity, A1]
   $\Phi$ is non-decreasing in each argument.
   \end{axiom}
   \begin{axiom}[Positive homogeneity, A2]
>> \begin{axiom}[Positive homogeneity, A2]
   $\Phi(c\cdot x) = c\,\Phi(x)$ for $c>0$.
   \end{axiom}
   \begin{axiom}[Idempotence / normalization, A3]
>> \begin{axiom}[Idempotence / normalization, A3]
   $\Phi(c,\dots,c) = c$.
   \end{axiom}
   \begin{axiom}[Boundedness, A4]
```

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.20119582`

## `thesis/v23/README.md`

- # Thesis v23 — The Unified Substrate
- ## What this is
- ## The one-line thesis
- ## Files
- ## Verification status (honest tiers)
- ## How to reproduce the verification
- # 1. Kernel-check the locked core + Wave-3/4 modules
- # 2. Disclose the trusted axiom base

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.20119582`, `10.5281/zenodo.20119582)`

## `thesis/v23/refs.bib`


DOIs: `10.1002/j.1538-7305.1948.tb01338.x`, `10.1007/BF00417500`, `10.1007/BF02418571`, `10.1007/s10726-018-9589-3`, `10.1016/0022-2496(83)90028-7`, `10.1093/analys/23.6.121`, `10.1103/PhysRevLett.23.880`, `10.1109/PROC.1975.9939`

## `thesis/v24/main.md`

- # The Ouroboros Thesis
- ### Axiom-Free Conditional Uniqueness of the Lutar Invariant: A Machine-Verified Trust Foundation for Governed Agentic AI
- ## Abstract
- ## 1. Introduction
- ## 2. The honesty doctrine
- ## 3. The Ouroboros loop: bounded self-governance
- ## 4. The Lutar invariant Λ and its uniqueness boundary
- ### 4.1 Definition and the aggregation axioms

```
>> ABSTRACT
   Governed deployment of agentic artificial intelligence in regulated and defense settings requires more than benchmark accuracy: it requires *checkable* guarantees about what a syst
   The headline advance of v24 is an **axiom-free conditional Λ-uniqueness theorem**. In v23 the conditional uniqueness of Λ was gated on a *declared* project axiom (A6′ block-consist
   Crucially, the *unconditional* uniqueness of Λ under {A1–A5} remains machine-checked **false** (in-tree `maxAgg_ne_Lambda`; `maxAgg` and `min` are A1–A5 counterexamples), so Λ stay
   **Honesty note (verbatim).** The Lutar invariant Λ is **Conjecture 1** unconditionally and is *never* claimed proven unconditionally; unconditional uniqueness under A1–A5 is machin
   **Keywords:** governed agentic AI, trust aggregation, Lutar invariant, geometric mean, slice-multiplicativity, functional-equation uniqueness, Lean 4, Mathlib, axiom-free verificat
   ---
   ## 1. Introduction
   The deployment of agentic AI into regulated industries (finance, healthcare) and defense settings has exposed a gap that benchmark performance cannot close: a *trust* gap. A regula
>> **Definition (Λ).** For x ∈ [0,1]^k, the Lutar invariant is the equal-weight geometric mean Λ_k(x) = (∏_{i=1}^k x_i)^{1/k}.
   The candidate aggregators Φ : [0,1]^k → [0,1] are constrained by five axioms:
>> **Theorem 4.2 (Refutation of unconditional uniqueness). [machine-checked FALSE] [CI-green]** There exists Φ ≠ Λ_k satisfying A1–A5. In particular the max-aggregator maxAgg(x) = max
   *Lean reference.* The in-tree witness is `Round13.maxAgg_ne_Lambda`. The max function is monotone (A1), positively homogeneous (A2), idempotent (A3), bounded by itself hence ≤ max 
>> **Theorem 4.3 (Uniqueness given factorization). [experimental, axiom-free, CI-green]** Let Φ satisfy A1–A5 and suppose Φ *factors*: there exist exponents α_1, …, α_k ≥ 0 with Φ(x) 
   *Lean reference and sketch.* The Lean term is `lambda_unique_of_factors` (Round-13). Given factorization, idempotence (A3) forces ∑_i α_i = 1 and symmetry (A5) forces all α_i equal
>> **Axiom 6 (Block-consistency / aggregation-invariance, A6′).** Aggregating evidence within independent blocks and then across the block results equals aggregating the flattened col
   **Theorem 4.4 (v23 conditional uniqueness under declared A6′). [axiom-gated] [CI-green]** Under {A1–A5} together with the single declared axiom `A6'_block_consistent`, Λ_k is the u
>> **Theorem 4.4 (v23 conditional uniqueness under declared A6′). [axiom-gated] [CI-green]** Under {A1–A5} together with the single declared axiom `A6'_block_consistent`, Λ_k is the u
   Theorem 4.4 was honest but carried a cost: the trusted base included a *project axiom* that could not itself be discharged in-kernel. v24 removes that cost.
>> Theorem 4.4 was honest but carried a cost: the trusted base included a *project axiom* that could not itself be discharged in-kernel. v24 removes that cost.
   ### 4.4 The v24 advance: axiom-free conditional uniqueness (CUT-2)
```

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926);`

## `thesis/v24/main.tex`

- \section{Introduction}
- \section{The honesty doctrine}
- \section{The Ouroboros loop: bounded self-governance}
- \section{The Lutar invariant $\La$ and its uniqueness boundary}
- \section{The proof-trail / receipt architecture}
- \section{The locked kernel and the frontier theorem families}
- \section{Verification status, in detail}
- \section{Why this is groundbreaking --- the honest case}

```
>> ABSTRACT
   \noindent
   Governed deployment of agentic artificial intelligence in regulated and
   defense settings requires more than benchmark accuracy: it requires
   \emph{checkable} guarantees about what a system did, why it was permitted to do
   it, and whether the record can be tampered with after the fact. This is
   \textbf{v24} of the Ouroboros thesis program of SZL Holdings, a DOI-pinned
   lineage (v1--v23) whose subject is a machine-verified trust substrate resting on
   three pillars: (i) the \emph{Ouroboros loop}, a bounded, well-founded
>> \begin{definition}[Bounded Ouroboros loop]
   A loop is \emph{bounded} if it admits a well-founded measure --- a ranking
   function into a well-ordered set that strictly decreases on each governed step,
   with no infinite descending chain.
>> \begin{definition}[Lutar invariant]
   For $x = (x_1,\dots,x_k)\in[0,1]^k$, the \emph{Lutar invariant} is the
   equal-weight geometric mean
   \[
>> \begin{axiom}[Monotonicity, A1]\label{ax:a1}
   $\Phi$ is non-decreasing in each argument.
   \end{axiom}
   \begin{axiom}[Positive homogeneity, A2]\label{ax:a2}
>> \begin{axiom}[Positive homogeneity, A2]\label{ax:a2}
   $\Phi(c\cdot x) = c\,\Phi(x)$ for $c>0$ (scale-covariance).
   \end{axiom}
   \begin{axiom}[Idempotence / normalization, A3]\label{ax:a3}
>> \begin{axiom}[Idempotence / normalization, A3]\label{ax:a3}
   $\Phi(c,\dots,c) = c$.
   \end{axiom}
   \begin{axiom}[Boundedness, A4]\label{ax:a4}
>> \begin{axiom}[Boundedness, A4]\label{ax:a4}
   $\Phi(x)\le \max_i x_i$.
   \end{axiom}
   \begin{axiom}[Permutation invariance, A5]\label{ax:a5}
```

DOIs: `10.5281/zenodo.19944926`

## `thesis/v24/README.md`

- # Thesis v24 — Axiom-Free Conditional Uniqueness of the Lutar Invariant
- ## What this is
- ## The v24 advance (the headline)
- ## Files
- ## Verification status (honest tiers)
- ## Honesty doctrine (binding)
- ## Verify it yourself
- # => {propext, Classical.choice, Quot.sound}  (no project axiom)

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.19944926)`, `10.5281/zenodo.19944926).`

## `thesis/v24/refs.bib`


DOIs: `10.1002/047174882X`, `10.1002/j.1538-7305.1948.tb01338.x`, `10.1007/978-3-030-79876-5_37`, `10.1007/BF00417500`, `10.1007/BF01726210`, `10.1007/BF02418571`, `10.1007/s10726-018-9589-3`, `10.1016/0022-2496(83)90028-7`

## `preprints/ouroboros-arxiv/main.tex`

- \section{Introduction}
- \section{The A1--A15 Axiom System}
- \section{The \texorpdfstring{\(\Lambda\)}{Lambda}-Axis Calculus}
- \section{The Dual-Witness Receipt Protocol}
- \section{PAC-Bayesian Convergence Bounds}
- \section{Quantum Substrate and DPI Bound}
- \section{Evaluation}
- \section{Limitations and Open Problems}

```
>> ABSTRACT
   Autonomous AI agents now perform consequential actions across
   critical infrastructure, financial settlement, and national-security
   workloads, yet no deployed framework simultaneously provides
   (i)~a machine-checked formal proof of every governance invariant,
   (ii)~a running agentic substrate whose every output emits a
   cryptographically-ordered dual-witness receipt,
   (iii)~a unified observability and security layer that ingests
   industry-standard telemetry into the same governance-score pipeline,
>> axiom.
   No axiom is silent: each carries a primary-source citation and a
   discharge target.
>> \begin{axiom}[A1 -- Monotonicity]
   For all governance vectors \(x, y\) with \(x_i \le y_i\) componentwise,
   \(\Phi(x) \le \Phi(y)\).
   \textup{Lean:} \texttt{LutarAxioms.mono}
>> \begin{axiom}[A2 -- Homogeneity]
   For all \(c \ge 0\) and \(x\), \(\Phi(c \cdot x) = c\,\Phi(x)\).
   \textup{Lean:} \texttt{LutarAxioms.homog}
   (\texttt{Lutar/Axioms.lean}, line~81).
>> \begin{axiom}[A3 -- Diagonal Normalisation]
   For all \(c \ge 0\), \(\Phi(c,\ldots,c) = c\).
   \textup{Lean:} \texttt{LutarAxioms.diag}
   (\texttt{Lutar/Axioms.lean}, line~82).
>> \begin{axiom}[A4 -- Upper Bound]
   For all \(x\), \(\Phi(x) \le \max_i x_i\).
   \textup{Lean:} \texttt{LutarAxioms.upper}
   (\texttt{Lutar/Axioms.lean}, line~83).
>> \begin{axiom}[A5--A10 -- Infrastructure Axioms (v14--v17)]
   Pinsker inequality (\texttt{pinsker}),
   KL non-negativity (\texttt{klDivergence\_nonneg}),
   sub-Gaussian moments (\texttt{MomentSubGaussian}),
```

DOIs: `10.5281/zenodo.19944926`, `10.5281/zenodo.20434276`
