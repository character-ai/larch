# PLAN: Agentic Skill Engineering article series

## Purpose

A plan for a series of short articles on **agentic skill engineering**: the discipline of building reliable, low-cost, high-quality software workflows that are executed by AI agents rather than written by hand.

The series teaches transferable principles. Larch, an MIT-licensed public Claude Code plugin, is the running worked example throughout, so articles can link directly to real source, issues, and run logs.

Target audience: the full spectrum from beginners to advanced.

## How this document is organized

- **Five parts**, each grouping related themes. A short **series spine** of two opener posts sits before Part I.
- Each **theme** holds several **article proposals**: a title and a one or two sentence content summary. Bodies come later; this stage fixes the titles and content ideas only.
- **Design rationale worth noting:**
  - Cost is separated from determinism because they are different stories for different readers, even though cost reduction also reduces non-determinism.
  - Observability is a top-level theme because the self-tuning analytics layer is the most distinctive part of the system.
  - CI and "prompts as a software artifact" are split because one is the verification gate and the other is the source hygiene behind it.

## Series spine

The two opener posts. Publish these first; everything else hangs off them.

- **"Agentic skill engineering: notes from operating a large prompt codebase."** The thesis post. Why this is a distinct discipline, neither prompt engineering nor conventional software engineering, and the throughline for the series. Pull the real line and run-log size figures from the size-reporting skill before publishing.
- **"Larch in one diagram: design, implement, review, and why it is a loop."** The system overview as a teaching artifact. Establishes shared vocabulary used by every later post.

## Part I: Foundations

### Theme 1: The agentic skills programming model

- **"Your compiler is a coin flip."** Programming against a stochastic interpreter: what carries over from software engineering and what inverts.
- **"Your prompt has a memory hierarchy."** Progressive disclosure across metadata, body, and on-demand resources. Why loading too much is as costly as loading too little.
- **"Every token competes: the knowledge-delta principle."** Write only what the model does not already know. The short-skill-beats-long example, where a tiny skill outperforms a much longer one.
- **"Freedom calibration: scripts versus principles."** Match specificity to fragility. Exact steps for migrations, loose principles for creative work. Getting it backwards either breaks files or suppresses quality.
- **"The description is the API."** Activation gates: a perfect skill with a vague description never triggers. WHAT, WHEN, and the keywords a user would actually type.

## Part II: Engineering against the machine

### Theme 2: Determinism engineering

- **"Non-determinism is the enemy: a field guide to where randomness leaks in."** A taxonomy of the entry points and what each one costs.
- **"The prompt decides, the script executes."** Push every non-trivial action into deterministic code behind a single CLI. Why "no inline pipelines in the prompt" is a correctness rule, not a style preference.
- **"Design for interruption."** Sentinels, idempotency ledgers, and state adoption. Assume every run gets killed halfway and has to resume cleanly.
- **"The phantom completion signal."** A postmortem on spurious completion notifications, the polling loops they tempt, and the guard that banned the loop. Real incident, real fix, general principle.
- **"Let the agent improvise, but only here."** Where the main agent may fix a merge conflict or a CI failure on its own, and where it must stay on the rails. How to draw that boundary deliberately.

### Theme 3: Cost engineering

- **"Tokens are the new cloud bill."** Treat cost as a first-class design constraint, with the same rigor as latency or memory.
- **"Right model, right job."** Model routing. Why a strong specialist, for example a dedicated reviewer model, can be cheaper per unit of value than a cheap generalist.
- **"The cheapest token is the one you never send."** Deterministic offload as cost control, not only as a correctness control.
- **"Context is a budget, not a buffer."** Minimize what each agent has to read. Keep durable bulk in committed logs and keep the tracking issue slim.
- **"Measure before you cut."** Per-step, per-model cost attribution to find the one expensive step instead of guessing. Grounded in the token-report tooling.

## Part III: Quality at scale

### Theme 4: Multi-agent orchestration and quality

- **"Panels beat soloists."** Why several independent reviewers find more than one careful pass does, and when the overhead pays for itself.
- **"Voting as adjudication."** YES/NO thresholds, neutralized ballots, and reading votes as untrusted data. Resolving disagreement without a human in the loop.
- **"Vendor diversity is a feature."** Multiple model vendors as complementary lenses. Cite the measured cost of dropping a vendor from the panel.
- **"Make your reviewers compete."** Point competition and scoreboards: incentive design for agents, and its effect on finding quality.
- **"Spawn skeptics: adversarial verification."** Asking independent agents to refute a finding before trusting it, to kill plausible-but-wrong output.

### Theme 5: Continuous integration as the load-bearing gate

- **"CI matters more when a machine writes the code."** The thesis. In human-driven development, CI is a safety net under a careful author. In agentic development, the author cannot be trusted to self-verify, so CI becomes the primary correctness authority. The gate is load-bearing, and that reframing changes how much you invest in it.
- **"Make the gate ungameable."** No-bypass merge rules: not even an admin or an over-eager agent can merge red CI. Why neither the system nor the operator should be able to route around the gate, and what changes when the gate is truly mandatory.
- **"Fast CI is a correctness feature."** Slow CI stalls the agentic loop, inflates token cost, and tempts shortcuts. Tricks: parallel jobs, test sharding, repacking shards from real timing data, and profiling the slowest step. Speed as the enabler of autonomy.
- **"Tests and linters as the agent's seatbelt."** The deterministic verification layer: colocated unit tests, contract tests, and parity harnesses during migrations. Dense, fast, deterministic checks matter more when the contributor is stochastic.
- **"Roll your own linters."** The highest-leverage CI habit: when a single recurring bug class earns a small bespoke linter. The wrapped-grep trap as the canonical war story, a stray probe in a prompt that silently aborts a whole step, plus portability and substitution-safety checks. Encode each hard-won lesson as an executable assertion so the same mistake cannot ship twice.

## Part IV: Operating and evolving the system

### Theme 6: Observability and self-improvement

- **"Log everything. Commit the logs."** Run logs as the durable substrate that lets a system study itself, and why they belong in version control rather than a transient dashboard.
- **"Closing the loop: how the review system tunes itself."** Fluff analysis feeding back into tighter reviewer and judge instructions. The system measures its own waste and corrects it.
- **"Calibrating the judges."** Voter agreement, chronic outliers, and detecting a reviewer that has quietly drifted out of calibration.
- **"Mining your own rejects."** Recovering real bugs from findings the panel voted down. Turning false negatives into filed work.
- **"The analytics flywheel."** How measurement, not intuition, drives the roadmap. The capstone for this theme.

### Theme 7: Process and workflow architecture

- **"The tracking issue is your database."** Durable state in the issue tracker, not in the context window. Externalized state as the backbone of long-running agentic work.
- **"The handoff contract: issue-anchored plans."** How a design phase hands a vetted plan to a build phase through an explicit wire format, and why the contract must be machine-readable.
- **"Throughput versus quality is a false binary."** Heavy parallelism plus hard gates. You can have both when the gates are deterministic.
- **"Where to put the human."** Approval gates, override patterns, and respecting the operator's time. When to ask, when to proceed, when to let the operator override.

## Part V: Treating the system as software

### Theme 8: Prompts as a software artifact

- **"Your prompt is a codebase now."** Versioning, reviewing, and migrating natural-language instructions like real source.
- **"Portability for prompts."** Why runtime portability, for example targeting the oldest shell you will actually hit, is a prompt problem, enforced by a linter rather than left to discipline.
- **"Regression-testing a stochastic system."** The halt-rate harness: how to test something that will not give the same answer twice.
- **"No shims."** Hard-cutover migration discipline: retire the old surface in the same change, then lint that it is gone.

### Theme 9: Trust and security boundaries

- **"LLM output is untrusted input."** Reading ballots, plans, and reviews as data to validate, never as instructions to obey.
- **"Prompt injection from your own config."** Treating even your own guidance files as untrusted context, and why.
- **"Redaction by default."** Keeping secrets and local paths out of logs you commit to a public repository.

## Writing guidelines

Each article is a concise educational tool. These are craft DOs.

- **One hard-won lesson per post.** If you cannot name the lesson in a single sentence, the post is not ready.
- **Apply knowledge-delta to the reader.** Skip what they already know. Spend the words on the part that took a year to learn.
- **Show the scar.** Naive approach, then why it broke (a real incident where possible), then the principle, then how Larch embodies it, then the takeaway.
- **Ladder the spectrum.** The first third is followable by a beginner. The last third carries the nuance an advanced reader came for.
- **Evidence over adjectives.** Prefer a measured figure to a claim. Verify every figure against current data before publishing.
- **Name the principle.** Give each lesson a memorable handle so it is easy to recall and reuse across posts.
- **Ground every claim in real artifacts.** Link to issues, PRs, run logs, and source so readers can verify and dig deeper. Larch is MIT-licensed and public, so link freely.
- **Write in a clear, direct voice.** First person is fine. Lead with the answer, keep sentences short, and bold the key terms so the text scans.
- **Stop early.** Aim for 800 to 1500 words. When unsure how short to go, go shorter.

## Suggested sequencing

- **Do not publish strictly in theme order.** Start with the spine plus one flagship article per theme to establish breadth, then go deep where readers engage.
- **Lead with the postmortems** (the phantom completion signal, the wrapped-grep trap). Concrete failure stories are the most engaging entry points and pull readers into the rest of the series.
- **Cross-link aggressively.** The series is a graph, not a line. Each post should point to the two or three posts that deepen it.
- **Keep a running glossary** of coined terms (below) so the vocabulary stays consistent across posts.
- **Expand the themes that generate the most reader questions.** Let genuine reader interest, not the outline, decide depth.
- **Do not over-plan before shipping.** Publish the opener and two posts, then adjust the rest of the plan from what you learn.

## Glossary of coinages

A consistency aid. Use these handles the same way across every article.

- **Knowledge delta.** The gap between what a skill teaches and what the model already knows. The only thing worth spending tokens on.
- **Freedom calibration.** Matching instruction specificity to task fragility: tight scripts for fragile work, loose principles for creative work.
- **Determinism offload.** Moving logic out of the model and into deterministic scripts to remove a source of randomness.
- **Deterministic spine, stochastic edge.** The architecture pattern: deterministic scripts carry the load, the model makes only the judgment calls.
- **The context budget.** Treating each agent's input window as a scarce budget to spend deliberately.
- **Vendor diversity.** Using multiple model vendors as complementary review lenses rather than as interchangeable substitutes.
- **The tracking issue is the database.** Externalizing durable state to the issue tracker instead of holding it in the context window.
- **The analytics flywheel.** Measurement skills feeding insights back into the system that produced the data, so it improves itself.
- **The load-bearing gate.** CI as the primary correctness authority in agentic development, not a secondary safety net.
- **Prompt as codebase.** Treating natural-language instructions as source: versioned, reviewed, linted, tested, and migrated.
