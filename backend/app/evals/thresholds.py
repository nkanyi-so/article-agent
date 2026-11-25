"""Every number that decides whether an eval passes. One file, so a change is one diff.

A threshold is changed only by a decision record with the run that justifies it
(docs/decisions/0010), never to make a failing run pass.
"""

# How many times every case is run. One run of a case moves by up to 0.2 with no cause
# (docs/decisions/0014), so the scores below are applied to each case's mean over its runs.
REPEATS = 3

# E1 to E7 are exact: one failure in any run fails the check.

# E8: mean share of each case's hand-listed key facts that some kept sentence cites.
COVERAGE_MEAN_MIN = 0.70

# E9: share of drafted sentences the ground check removed, over all valid cases. Set from
# the first judged live run, which removed 9 of 174 (docs/decisions/0014).
REMOVAL_RATE_MAX: float | None = 0.10

# J1: judged groundedness, each cited answer read with its question: the mean over cases
# of each case's mean, and the lowest case's mean.
GROUNDEDNESS_MEAN_MIN = 0.90
GROUNDEDNESS_CASE_MIN = 0.80

# J2: the judge against hand-labelled pairs. Every known negative must also be failed.
CALIBRATION_AGREEMENT_MIN = 0.90
