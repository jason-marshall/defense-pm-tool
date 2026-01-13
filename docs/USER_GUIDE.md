# Defense PM Tool - User Guide

A comprehensive guide to using the Defense Program Management Tool for schedule management and EVMS compliance.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Programs](#programs)
3. [Work Breakdown Structure (WBS)](#work-breakdown-structure-wbs)
4. [Activities & Dependencies](#activities--dependencies)
5. [Schedule Analysis (CPM)](#schedule-analysis-cpm)
6. [EVMS Management](#evms-management)
7. [Import & Export](#import--export)
8. [Reports](#reports)
9. [Best Practices](#best-practices)

---

## Getting Started

### Creating an Account

1. Navigate to the application URL
2. Click "Register" to create a new account
3. Enter your email, password, and full name
4. Verify your email (if required)
5. Log in with your credentials

### Dashboard Overview

After logging in, you'll see:
- **My Programs**: List of programs you have access to
- **Recent Activity**: Recent changes across your programs
- **Quick Actions**: Create new program, import schedule

---

## Programs

### Creating a Program

1. Click "New Program" from the dashboard
2. Fill in required fields:
   - **Name**: Descriptive program name (e.g., "F-35 Block 4 Upgrade")
   - **Code**: Unique identifier (e.g., "F35-BLK4-001")
   - **Planned Start Date**: Program start date
   - **Planned End Date**: Program end date
   - **Budget at Completion (BAC)**: Total program budget
3. Optional fields:
   - Contract Number
   - Contract Type (FFP, CPFF, CPIF, etc.)
   - Description
4. Click "Create Program"

### Program Settings

Access program settings to:
- Update program details
- Manage team access
- Configure EVMS periods
- Set program defaults

---

## Work Breakdown Structure (WBS)

The WBS provides a hierarchical decomposition of work.

### Creating WBS Elements

1. Navigate to your program
2. Click "WBS" tab
3. Click "Add Root Element" for top-level items
4. Fill in:
   - **Name**: Element name (e.g., "Systems Engineering")
   - **WBS Code**: Hierarchical code (e.g., "1.1")
   - **Description**: Optional description
5. To add child elements, click the "+" icon on a parent element

### WBS Hierarchy Example

```
1.0 Program Management
    1.1 Systems Engineering
        1.1.1 Requirements Analysis
        1.1.2 System Design
    1.2 Software Development
        1.2.1 Frontend Development
        1.2.2 Backend Development
    1.3 Test & Evaluation
2.0 Hardware
    2.1 Design
    2.2 Fabrication
```

### Best Practices for WBS

- Use consistent numbering (1.0, 1.1, 1.1.1)
- Keep depth manageable (3-5 levels)
- Align with contract CWBS requirements
- Ensure complete coverage (no work gaps)

---

## Activities & Dependencies

### Creating Activities

1. Navigate to "Activities" tab
2. Click "Add Activity"
3. Fill in:
   - **Name**: Activity description
   - **Code**: Unique activity code
   - **Duration**: Duration in days
   - **WBS Element**: Assign to WBS (optional)
   - **Budgeted Cost**: Planned cost for this activity
4. Advanced options:
   - **Milestone**: Check for zero-duration milestones
   - **Constraint Type**: ASAP, SNET, SNLT, etc.
   - **Constraint Date**: Required for certain constraints

### Creating Dependencies

Dependencies define the logical sequence of activities.

1. Navigate to "Dependencies" tab or use the Gantt view
2. Click "Add Dependency"
3. Select:
   - **Predecessor**: Activity that must happen first
   - **Successor**: Activity that follows
   - **Type**: Relationship type
   - **Lag**: Days of delay (positive) or overlap (negative)

### Dependency Types

| Type | Name | Description | Example |
|------|------|-------------|---------|
| **FS** | Finish-to-Start | B starts when A finishes | Design → Build |
| **SS** | Start-to-Start | B starts when A starts | Training starts with Implementation |
| **FF** | Finish-to-Finish | B finishes when A finishes | Testing finishes with Development |
| **SF** | Start-to-Finish | B finishes when A starts | Rare, used for just-in-time |

### Using Lag and Lead

- **Lag (+)**: Delay between activities
  - FS+5: Successor starts 5 days after predecessor finishes
  - Example: "Concrete pour" → [5-day cure time] → "Form removal"

- **Lead (-)**: Overlap between activities
  - FS-3: Successor starts 3 days before predecessor finishes
  - Example: "Design" → [start coding 80% through design] → "Development"

---

## Schedule Analysis (CPM)

The Critical Path Method (CPM) calculates your schedule.

### Running CPM Analysis

1. Navigate to "Schedule" tab
2. Click "Calculate Schedule"
3. Review results:
   - **Early Start/Finish**: Earliest possible dates
   - **Late Start/Finish**: Latest dates without delay
   - **Total Float**: Schedule flexibility
   - **Critical Path**: Activities with zero float

### Understanding Results

| Metric | Description |
|--------|-------------|
| **Early Start (ES)** | Earliest day activity can begin |
| **Early Finish (EF)** | Earliest day activity can complete |
| **Late Start (LS)** | Latest day activity can begin without delay |
| **Late Finish (LF)** | Latest day activity can complete without delay |
| **Total Float** | Days of flexibility (LS - ES or LF - EF) |
| **Free Float** | Days before affecting successor |
| **Critical** | True if Total Float = 0 |

### Critical Path

The critical path is the longest path through the network:
- Activities on critical path have zero float
- Any delay on critical path delays the project
- Focus management attention on critical activities
- Highlighted in red on Gantt chart

### Tips for Schedule Analysis

- Fix circular dependencies before calculating
- Review activities with negative float (schedule compression needed)
- Monitor near-critical paths (1-5 days float)
- Re-calculate after any changes

---

## EVMS Management

Earned Value Management System tracks program performance.

### Key EVMS Concepts

| Metric | Name | Description |
|--------|------|-------------|
| **BCWS** | Budgeted Cost of Work Scheduled | Planned value |
| **BCWP** | Budgeted Cost of Work Performed | Earned value |
| **ACWP** | Actual Cost of Work Performed | Actual cost |
| **BAC** | Budget at Completion | Total budget |

### Setting Up EVMS Periods

1. Navigate to "EVMS" tab
2. Click "Create Period"
3. Enter:
   - Period name (e.g., "January 2024")
   - Start date
   - End date
4. Click "Create"

### Entering Period Data

1. Open the EVMS period
2. For each WBS element, enter:
   - **BCWS**: What was planned to be done
   - **BCWP**: What was actually earned
   - **ACWP**: What it actually cost
3. Click "Save"
4. Review calculated metrics

### EVMS Dashboard Metrics

**Variances:**
- **CV (Cost Variance)** = BCWP - ACWP
  - Positive = Under budget
  - Negative = Over budget
- **SV (Schedule Variance)** = BCWP - BCWS
  - Positive = Ahead of schedule
  - Negative = Behind schedule

**Indices:**
- **CPI (Cost Performance Index)** = BCWP / ACWP
  - \>1.0 = Under budget
  - <1.0 = Over budget
- **SPI (Schedule Performance Index)** = BCWP / BCWS
  - \>1.0 = Ahead of schedule
  - <1.0 = Behind schedule

**Estimates:**
- **EAC (Estimate at Completion)** = BAC / CPI
- **ETC (Estimate to Complete)** = EAC - ACWP
- **VAC (Variance at Completion)** = BAC - EAC
- **TCPI (To-Complete Performance Index)** = (BAC - BCWP) / (BAC - ACWP)

### Approving Periods

1. Verify all data entered correctly
2. Click "Approve Period"
3. Approved periods become the baseline for trends

---

## Import & Export

### Importing from MS Project

1. In MS Project, export to XML:
   - File → Save As
   - Choose "XML" format
   - Save file

2. In Defense PM Tool:
   - Navigate to program
   - Click "Import" → "MS Project XML"
   - Drag and drop or select file
   - Click "Preview" to review
   - Click "Import" to save

**What gets imported:**
- Tasks (as activities)
- Dependencies (all types)
- WBS structure
- Milestones
- Constraints

**What doesn't import:**
- Resources and assignments
- Calendars (uses default)
- Custom fields
- Cost data (needs manual entry)

### Export Options

- **CSV**: Export activities and schedule data
- **PDF Reports**: Print CPR and other reports

---

## Reports

### Available Reports

#### CPR Format 1 (WBS Summary)

Contract Performance Report showing EVMS metrics by WBS element.

**Includes:**
- WBS hierarchy
- BCWS, BCWP, ACWP by element
- Variances (CV, SV)
- Performance indices
- Cumulative totals

**To generate:**
1. Navigate to "Reports" tab
2. Select "CPR Format 1"
3. Choose period (or use latest)
4. Click "Generate"
5. View online or download PDF

### Report Best Practices

- Generate reports after approving EVMS periods
- Review for accuracy before submission
- Archive historical reports
- Use consistent period boundaries

---

## Best Practices

### Schedule Management

1. **Start with WBS**: Build complete WBS before activities
2. **Use meaningful codes**: Activity codes should be traceable
3. **Define all dependencies**: No orphan activities
4. **Regular updates**: Update schedule weekly minimum
5. **Baseline management**: Save baseline before execution

### EVMS Compliance

1. **Consistent periods**: Use monthly or 4-week periods
2. **Timely data entry**: Enter data within 5 days of period close
3. **Review variances**: Investigate CV/SV > 10%
4. **Document assumptions**: Record basis for estimates
5. **Trend analysis**: Monitor CPI/SPI trends over time

### Data Quality

1. **No negative durations**: Duration must be >= 0
2. **No circular dependencies**: Will cause calculation errors
3. **Complete WBS mapping**: All activities should map to WBS
4. **Realistic estimates**: Use historical data when available
5. **Regular reconciliation**: Verify EVMS data matches actuals

### Team Collaboration

1. **Clear roles**: Define who updates what
2. **Version control**: Use program baseline features
3. **Change management**: Document schedule changes
4. **Communication**: Regular status meetings
5. **Training**: Ensure team understands EVMS concepts

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + S` | Save current form |
| `Ctrl + N` | New item (activity, WBS, etc.) |
| `Esc` | Close modal/Cancel |
| `Tab` | Navigate between fields |

---

## Getting Help

- **In-app help**: Click "?" icon for context help
- **Documentation**: See `/docs` folder
- **Support**: Contact your system administrator
- **Issues**: Report bugs via GitHub issues

---

*Last updated: January 2026*
