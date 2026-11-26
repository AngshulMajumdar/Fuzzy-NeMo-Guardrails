# Implemented mathematical contract

The controller implements a stochastic extended finite-state machine with
configuration `(s, b, v)`: observed protocol state `s`, posterior row vector `b`
over a finite latent alphabet, and bounded extended variables `v` containing
counters, grants and execution identifiers. The finite control graph remains
finite; real-valued probabilities and extended variables are not a finite
enumeration of all runtime configurations.

## Bayesian filtering

For previous action `a` and new observation `o`, the factorized update is

\[
\tilde b = bT_a\operatorname{diag}(B_{:,o}),\qquad
b^+ = \tilde b/(\tilde b\mathbf1).
\]

Every transition matrix and every emission row is nonnegative and normalized.
`forward` rescales likelihoods before multiplication to reduce underflow.
Zero evidence mass stops the session; no arbitrary posterior is substituted.
The default transition is used if an action-specific transition is omitted.
In this factorization, trusted events change protocol state and carry no
additional latent-state likelihood beyond the supplied observation.

General joint event/observation kernels are also supported:

\[
b^+=\frac{bM^{s,a}_{e,o}}{bM^{s,a}_{e,o}\mathbf1},\qquad
\sum_{e,o}M^{s,a}_{e,o}\mathbf1=\mathbf1.
\]

Every `(s,a)` group must be supplied and normalized. An absent `(e,o)` pair has
zero probability. The trusted protocol update is `s^+=delta(s,a,e)`. A trusted
event API call uses the `neutral` observation, so joint models must explicitly
provide probability for the event/neutral pairs they intend to accept.

## Admissibility and robust risk

For action `a`, the nominal risk score is `r_a=b R[:,a]`. With a total-variation
uncertainty radius `eta`, the implemented conservative upper bound is

\[
\bar r_a=\min\{\max_i R_{ia},\;bR_{:,a}
+\eta(\max_iR_{ia}-\min_iR_{ia})\}.
\]

Here total variation is half the L1 distance. This is an upper bound; it is not
claimed to be the exact robust optimum for every multi-state distribution.
The admissible set includes actions of the current stage whose protocol
successors are safe for every declared trusted event, whose hard validators
permit the candidate, and whose risk bound is at most the configured allowance.
Tool permission checks are hard constraints on `execute_tool`. `stop` has zero
declared risk, is always available, closes the protocol and clears grants.

## Probability projection and action selection

Utilities are the posterior expected per-state utilities, with explicit routing
bonuses for requesting required verification or refusing hard-blocked content.
For reference probabilities `q_a proportional to exp(u_a/tau)`, the implemented
distribution is

\[
p_a^*=\frac{q_a\mathbf1[a\in A]}{\sum_{j\in A}q_j}.
\]

It minimizes `D_KL(p || q)` over distributions supported on `A`. A masked stable
softmax implements the same solution without assigning forbidden actions a
small positive floor. All forbidden probabilities are exactly zero. By default
the runtime selects the maximum-probability action for reproducibility; a policy
can choose `selection: sample` for stochastic action selection. The belief
transition remains stochastic in either mode.

## Conditional probability budget

The default `risk_semantics: model_score` makes no calibrated probability claim.
If the host supplies valid conditional bounds on actual violations at every
decision, choose `conditional_bound`, state the envelope assumption and optionally
set `session_alpha`. For at most `H=max_decisions` decisions, each allowance is
`min(risk_threshold, session_alpha/H)`. Consequently the sum of allocated
allowances does not exceed `session_alpha`, and the probability of any violation
is bounded by that sum **under the stated conditional-envelope assumptions**.
Independence between turns is unnecessary. The software checks accounting and
numeric structure; it cannot establish that an asserted semantic envelope is true.
The guarantee does not cover bypasses, custom tools outside the wrapper, arbitrary
session resets or a detector whose stated bounds are invalid.

## Output and cost

The exact proposed response is passed to validators and the RiskProvider before
release. Rechecking it does not duplicate the evidence from its input. Tool
results pass the same output gate. Default finite-state filtering costs O(n^2)
and action risk/utility evaluation O(nk); text encoding, validators, extensions,
serialization, policy validation and storage have their own costs. The bundled
model uses four latent modes, seven actions and six observations. It is a
hand-configured stochastic model, not fitted experimental evidence.
