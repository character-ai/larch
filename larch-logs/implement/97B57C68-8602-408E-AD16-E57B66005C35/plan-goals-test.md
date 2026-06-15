## Goal
Implement issue #4407: [IMPLEMENTING] Python unit tests CI matrix job should be split into 4 matrix sub-jobs, each running about 1/4 of the unit tests.

## Implementation Plan
AThis is in order to speed up CI.  Also add timing output to individual Python unit tests, if not already present in log, in order to be able to repartition.

## Test plan
(no test plan section in plan-file)
