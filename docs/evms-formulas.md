# Earned Value Management System (EVMS) Formulas

## Core Values

| Acronym | Name | Description |
|---------|------|-------------|
| **BCWS** | Budgeted Cost of Work Scheduled | Planned Value (PV) - What we planned to spend |
| **BCWP** | Budgeted Cost of Work Performed | Earned Value (EV) - Value of work completed |
| **ACWP** | Actual Cost of Work Performed | Actual Cost (AC) - What we actually spent |
| **BAC** | Budget at Completion | Total authorized budget |

## Earned Value Methods

| Method | When Applied | Description |
|--------|--------------|-------------|
| **0/100** | At completion | 0% until done, 100% when complete |
| **50/50** | At start/completion | 50% at start, 50% at completion |
| **% Complete** | Continuously | Based on measured % complete |
| **Milestone** | At milestones | Based on milestone achievement |

## Variances

### Cost Variance (CV)
```
CV = BCWP - ACWP
```
- **CV > 0**: Under budget
- **CV < 0**: Over budget

### Schedule Variance (SV)
```
SV = BCWP - BCWS
```
- **SV > 0**: Ahead of schedule
- **SV < 0**: Behind schedule

## Performance Indices

### Cost Performance Index (CPI)
```
CPI = BCWP / ACWP
```
- **CPI > 1.0**: Under budget (getting more value per dollar)
- **CPI < 1.0**: Over budget (getting less value per dollar)

### Schedule Performance Index (SPI)
```
SPI = BCWP / BCWS
```
- **SPI > 1.0**: Ahead of schedule
- **SPI < 1.0**: Behind schedule

## Estimates

### Estimate at Completion (EAC)

**CPI Method** (current cost performance continues):
```
EAC = BAC / CPI
```

**Typical Method** (original estimates for remaining work):
```
EAC = ACWP + (BAC - BCWP)
```

### Estimate to Complete (ETC)
```
ETC = EAC - ACWP
```

### Variance at Completion (VAC)
```
VAC = BAC - EAC
```
- **VAC > 0**: Expected under budget
- **VAC < 0**: Expected over budget

## To-Complete Performance Index (TCPI)

Performance required to meet target:

**To meet BAC:**
```
TCPI = (BAC - BCWP) / (BAC - ACWP)
```

**To meet EAC:**
```
TCPI = (BAC - BCWP) / (EAC - ACWP)
```

- **TCPI > 1.0**: Harder performance required
- **TCPI < 1.0**: Easier performance acceptable

## Example Calculation

Given:
- BAC = $100,000
- BCWS = $50,000 (50% planned complete)
- BCWP = $45,000 (45% earned)
- ACWP = $40,000 (spent)

Results:
- CV = $45,000 - $40,000 = **$5,000** (under budget)
- SV = $45,000 - $50,000 = **-$5,000** (behind schedule)
- CPI = $45,000 / $40,000 = **1.125** (efficient)
- SPI = $45,000 / $50,000 = **0.90** (behind)
- EAC = $100,000 / 1.125 = **$88,889**
- VAC = $100,000 - $88,889 = **$11,111** (expected savings)
