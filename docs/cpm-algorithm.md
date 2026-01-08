# Critical Path Method (CPM) Algorithm

## Overview

The CPM engine calculates schedule dates for all activities based on their durations and dependencies.

## Key Concepts

### Schedule Dates
- **Early Start (ES)**: Earliest possible start date
- **Early Finish (EF)**: Earliest possible finish date (ES + Duration)
- **Late Start (LS)**: Latest possible start without delaying project
- **Late Finish (LF)**: Latest possible finish without delaying project

### Float
- **Total Float**: Time activity can be delayed without delaying project (LS - ES)
- **Free Float**: Time activity can be delayed without delaying successors

### Critical Path
Activities with zero total float form the critical path. Any delay on critical path activities delays the project.

## Dependency Types

| Type | Formula | Description |
|------|---------|-------------|
| FS | successor.ES = predecessor.EF + lag | Finish-to-Start (most common) |
| SS | successor.ES = predecessor.ES + lag | Start-to-Start |
| FF | successor.EF = predecessor.EF + lag | Finish-to-Finish |
| SF | successor.EF = predecessor.ES + lag | Start-to-Finish |

## Algorithm Steps

### 1. Forward Pass
Calculate ES and EF for all activities:

```python
for activity in topological_order:
    max_es = 0
    for predecessor in activity.predecessors:
        match dependency_type:
            case FS: es = predecessor.EF + lag
            case SS: es = predecessor.ES + lag
            case FF: es = predecessor.EF + lag - activity.duration
            case SF: es = predecessor.ES + lag - activity.duration
        max_es = max(max_es, es)

    activity.ES = max_es
    activity.EF = max_es + activity.duration
```

### 2. Backward Pass
Calculate LS and LF for all activities:

```python
project_end = max(activity.EF for all activities)

for activity in reverse_topological_order:
    min_lf = project_end
    for successor in activity.successors:
        match dependency_type:
            case FS: lf = successor.LS - lag
            case SS: lf = successor.LS - lag + activity.duration
            case FF: lf = successor.LF - lag
            case SF: lf = successor.LF - lag + activity.duration
        min_lf = min(min_lf, lf)

    activity.LF = min_lf
    activity.LS = min_lf - activity.duration
```

### 3. Float Calculation
```python
for activity in all_activities:
    activity.total_float = activity.LS - activity.ES
    activity.free_float = min(successor.ES) - activity.EF
```

## Performance

Target: < 500ms for 1000 activities

The implementation uses NetworkX for efficient graph operations and topological sorting.

## Example

```
A(5d) -> B(3d) -> C(2d)

Forward Pass:
A: ES=0, EF=5
B: ES=5, EF=8
C: ES=8, EF=10

Backward Pass (project end = 10):
C: LF=10, LS=8
B: LF=8, LS=5
A: LF=5, LS=0

Float:
A: TF=0, FF=0 (Critical)
B: TF=0, FF=0 (Critical)
C: TF=0, FF=0 (Critical)
```
