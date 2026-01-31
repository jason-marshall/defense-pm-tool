# Defense PM Tool - User Guide

A comprehensive guide to using the Defense Program Management Tool v1.2.0 for schedule management, resource management, and EVMS compliance.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Programs](#programs)
3. [Work Breakdown Structure (WBS)](#work-breakdown-structure-wbs)
4. [Activities & Dependencies](#activities--dependencies)
5. [Schedule Analysis (CPM)](#schedule-analysis-cpm)
6. [Resource Management](#resource-management) *(New in v1.1.0)*
7. [Resource Cost Tracking](#resource-cost-tracking) *(New in v1.2.0)*
8. [Calendar Import](#calendar-import) *(New in v1.2.0)*
9. [Parallel Leveling](#parallel-leveling) *(New in v1.2.0)*
10. [Resource Pools](#resource-pools) *(New in v1.2.0)*
11. [EVMS Management](#evms-management)
12. [Baselines](#baselines)
13. [Monte Carlo Simulation](#monte-carlo-simulation)
14. [Scenario Planning](#scenario-planning)
15. [Import & Export](#import--export)
16. [Reports](#reports)
17. [Jira Integration](#jira-integration)
18. [API Access](#api-access)
19. [Best Practices](#best-practices)

> **For API/Integration Documentation**: See [API_GUIDE.md](API_GUIDE.md) for detailed API documentation for system integrators.

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

## Resource Management

*New in v1.1.0*

Resource management allows you to track labor, equipment, and materials, assign them to activities, and optimize schedules through resource leveling.

### Creating Resources

1. Navigate to your program
2. Click "Resources" tab
3. Click "Add Resource"
4. Fill in resource details:
   - **Code**: Unique identifier (e.g., "ENG-001")
   - **Name**: Descriptive name (e.g., "Senior Systems Engineer")
   - **Type**: Labor, Equipment, or Material
   - **Capacity per Day**: Hours available (default 8 for labor)
   - **Cost Rate**: Optional hourly cost for budgeting
5. Click "Create"

### Resource Types

| Type | Description | Capacity Unit |
|------|-------------|---------------|
| **Labor** | Human resources (engineers, technicians) | Hours/day |
| **Equipment** | Machinery, tools, test equipment | Hours/day |
| **Material** | Consumable supplies | Units/day |

### Assigning Resources to Activities

1. Open an activity's detail page
2. Click "Assign Resources" or the resource icon
3. In the Assignment Modal:
   - Select a resource from the dropdown
   - Enter allocation percentage (1.0 = 100%)
   - Optionally set specific start/end dates
4. Click "Assign"

**Allocation Examples:**
- **1.0 (100%)**: Full-time on this activity
- **0.5 (50%)**: Half-time, split with other work
- **2.0 (200%)**: Overtime, working double shifts

### Viewing Resource Loading

The Resource Histogram shows available vs. assigned hours over time.

1. Navigate to "Resources" tab
2. Select a resource
3. Click "View Histogram"
4. Set the date range to analyze
5. Choose granularity (Daily or Weekly)

**Reading the Histogram:**
- **Gray bars**: Available hours
- **Blue bars**: Assigned hours (within capacity)
- **Red bars**: Overallocated (assigned > available)

**Summary Statistics:**
- **Peak Utilization**: Maximum % used
- **Average Utilization**: Mean % over period
- **Overallocated Days**: Days exceeding capacity

### Gantt Resource View *(New in v1.2.0)*

The Gantt Resource View provides a visual, timeline-based view of resource assignments.

**Accessing the View:**
1. Navigate to your program
2. Click "Resources" tab
3. Click "Gantt View" (timeline icon)

**View Features:**
- **Resource Lanes**: Each resource shown as a horizontal row
- **Assignment Bars**: Activities displayed as colored bars on the timeline
- **Scale Options**: Switch between Day, Week, or Month view
- **Utilization Overlay**: Background color shows capacity usage

**Visual Indicators:**
- **Blue bars**: Normal assignments
- **Red bars**: Critical path activities
- **Orange striped bars**: Overallocated periods
- **Background intensity**: Utilization level (green=low, yellow=medium, red=high)

**Editing Assignments:**
- **Move**: Drag the bar center to change dates
- **Resize Start**: Drag the left edge to change start date
- **Resize End**: Drag the right edge to change end date
- **Delete**: Select bar and press Delete key

**Filtering Resources:**
1. Click the "Filters" button to expand the filter panel
2. Use the search box to find resources by name or code
3. Toggle resource types (Labor/Equipment/Material)
4. Check "Overallocated only" to focus on problem areas
5. Check "With assignments" to hide unassigned resources
6. Click "Clear All Filters" to reset

**Tips:**
- Hover over bars to see activity details and allocation percentage
- Use Week view for typical planning, Day view for detailed scheduling
- The filter panel shows counts for each filter option
- Changes are saved automatically after drag-drop

### Detecting Overallocations

Overallocation occurs when a resource is assigned more work than their capacity allows.

**Signs of Overallocation:**
- Red bars in the histogram
- Overallocation warnings in the dashboard
- Resource utilization > 100%

**Common Causes:**
- Multiple activities scheduled concurrently
- Unrealistic time estimates
- Resource assigned to too many programs

### Running Resource Leveling

Resource leveling automatically resolves overallocations by delaying non-critical activities.

1. Navigate to "Leveling" or "Resources" → "Leveling Panel"
2. Configure leveling options:
   - **Preserve Critical Path**: Never delay critical activities (recommended)
   - **Level Within Float**: Only delay within total float
   - **Max Iterations**: Limit algorithm cycles (default 100)
3. Click "Run Leveling"
4. Review proposed changes:
   - Activity shifts with original vs. new dates
   - Total schedule extension
   - Remaining overallocations
5. Select which shifts to apply (or select all)
6. Click "Apply Changes"

**Leveling Tips:**
- Always review changes before applying
- Check if schedule extension is acceptable
- Re-run CPM after leveling to update float
- Consider adding resources if leveling extends schedule too much

### Resource Management Best Practices

1. **Define all resources first**: Create resources before assignments
2. **Use realistic capacities**: Account for meetings, admin time
3. **Regular updates**: Update actual hours weekly
4. **Monitor utilization**: Keep resources at 70-85% target
5. **Level early**: Run leveling during planning phase
6. **Document assumptions**: Note resource allocation rationale

---

## Resource Cost Tracking

*New in v1.2.0*

Track actual costs from resource assignments for automatic EVMS ACWP calculation.

### Recording Actual Costs

1. Navigate to the activity or assignment
2. Click "Record Actuals" or the cost icon
3. Enter for each date worked:
   - **Date**: The work date
   - **Hours Worked**: Actual hours (for labor/equipment)
   - **Quantity Used**: Units consumed (for materials)
   - **Notes**: Optional work description
4. Click "Save Entry"

### Viewing Cost Summaries

**Activity Cost Breakdown:**
1. Open an activity
2. Click "Cost Summary" tab
3. View:
   - Planned vs. actual cost
   - Cost variance (under/over budget)
   - Percent spent
   - Resource-level breakdown

**WBS Cost Rollup:**
1. Navigate to WBS view
2. Click on a WBS element
3. View rolled-up costs from all child activities

**Program Cost Summary:**
1. Go to Program dashboard
2. Click "Cost Summary"
3. View total planned, actual, and variance by:
   - Resource type (Labor, Equipment, Material)
   - WBS breakdown

### EVMS Cost Integration

Sync resource costs to EVMS ACWP automatically:

1. Navigate to "EVMS" → "Periods"
2. Select the period to update
3. Click "Sync Resource Costs"
4. Review the sync results:
   - Updated ACWP value
   - Number of WBS elements updated
   - Any warnings
5. Confirm to apply

**Benefits of Automatic ACWP:**
- Eliminates manual data entry
- Ensures consistency between resource and EVMS data
- Reduces reporting errors
- Provides real-time cost visibility

---

## Calendar Import

*New in v1.2.0*

Import resource calendars from MS Project to set up working days and holidays.

### Supported Calendar Elements

| Element | Description |
|---------|-------------|
| **Working Days** | Standard Mon-Fri, custom configurations |
| **Holidays** | Non-working days (company holidays) |
| **Exceptions** | Custom overrides for specific dates |
| **Working Hours** | Per-day working time definitions |

### Importing Calendars

1. Prepare your MS Project XML file with calendar definitions
2. Navigate to "Resources" → "Import Calendars"
3. Click "Choose File" and select your XML file
4. Set the date range for calendar generation
5. Click "Preview Import"

**Preview Results:**
- List of calendars found in the file
- Resource mappings (which calendars apply to which resources)
- Total holidays/exceptions identified
- Any warnings or conflicts

6. Review the preview carefully
7. Click "Import" to apply

### After Import

- Resource calendars are created or updated
- Calendar entries are generated for the date range
- Histogram and leveling will respect non-working days

### Tips

- Export fresh calendar data from MS Project before importing
- Ensure resource names in MS Project match your system
- Re-import if you update calendars in MS Project
- Extend the date range for longer-duration programs

---

## Parallel Leveling

*New in v1.2.0*

Optimized resource leveling algorithm for complex multi-resource schedules.

### When to Use Parallel Leveling

| Scenario | Recommendation |
|----------|----------------|
| Simple schedule (<50 activities) | Serial leveling is sufficient |
| Many shared resources | Use parallel for better results |
| Multiple overallocations | Parallel handles complex conflicts better |
| Need minimal schedule extension | Compare both algorithms |

### Running Parallel Leveling

1. Navigate to "Resources" → "Leveling Panel"
2. Select "Parallel Algorithm" (if available)
3. Configure options:
   - **Preserve Critical Path**: Recommended ON
   - **Level Within Float**: Use available slack first
   - **Max Iterations**: Default 100
4. Click "Run Parallel Leveling"
5. Review results

### Comparing Algorithms

To decide between serial and parallel:

1. Click "Compare Algorithms"
2. Both algorithms run with the same options
3. Review the comparison:
   - Schedule extension (fewer days is better)
   - Activities shifted (fewer is less disruptive)
   - Success rate (conflicts resolved)
4. Note the recommended algorithm
5. Apply the preferred result

### Understanding Results

**Parallel leveling advantages:**
- Considers all resources simultaneously
- Builds complete conflict matrix upfront
- Uses multi-factor priority scoring
- Often finds shorter schedule extension

**The recommendation is based on:**
1. Schedule extension (primary factor)
2. Number of activities shifted
3. Remaining conflicts (if both incomplete)

---

## Resource Pools

*New in v1.2.0*

Share resources across multiple programs with cross-program conflict detection.

### What Are Resource Pools?

Resource pools allow organizations to:
- Share specialized resources across programs
- Detect scheduling conflicts between programs
- Manage enterprise-wide resource capacity
- Coordinate resource allocation centrally

### Creating a Resource Pool

1. Navigate to "Resource Pools" (in main navigation)
2. Click "Create Pool"
3. Enter:
   - **Code**: Unique identifier (e.g., "ENG-POOL")
   - **Name**: Descriptive name
   - **Description**: Purpose of the pool
4. Click "Create"

### Adding Resources to a Pool

1. Open the resource pool
2. Click "Add Member"
3. Select the resource to add
4. Set allocation percentage (what % of capacity is pooled)
5. Click "Add"

**Allocation Examples:**
- **100%**: Entire resource capacity is available to pool programs
- **50%**: Half capacity shared, half dedicated to home program

### Granting Program Access

1. Open the resource pool
2. Click "Access Control"
3. Click "Grant Access"
4. Select a program
5. Choose access level:
   - **READ**: View availability only
   - **ASSIGN**: Assign resources to activities
   - **MANAGE**: Add/remove pool members
6. Click "Grant"

### Checking Availability

1. Open the resource pool
2. Click "View Availability"
3. Set the date range
4. Review:
   - Per-resource available hours by day
   - Existing assignments across programs
   - Detected conflicts

### Detecting Cross-Program Conflicts

Conflicts occur when multiple programs over-assign a pooled resource.

**Conflict indicators:**
- Red highlighting in pool availability view
- Conflict count badge on pool
- Warnings when creating assignments

**Resolving conflicts:**
1. Identify the conflicting programs and dates
2. Coordinate with program managers
3. Adjust assignment dates or allocations
4. Re-run leveling if needed

### Before Assigning Pool Resources

Use "Check Conflict" before creating assignments:

1. In the assignment dialog, click "Check Availability"
2. Enter proposed dates and allocation
3. Review any conflicts that would result
4. Adjust dates or find alternative resources if needed

### Resource Pool Best Practices

1. **Central ownership**: Assign pool management to resource managers
2. **Clear naming**: Use consistent pool naming conventions
3. **Regular reviews**: Check pool availability weekly
4. **Communication**: Notify affected programs of changes
5. **Limit pool size**: Smaller pools are easier to manage
6. **Document policies**: Define pool access and priority rules

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

## Baselines

Baselines capture approved schedule and cost data at a point in time for performance measurement.

### Creating a Baseline

1. Navigate to your program
2. Click "Baselines" tab
3. Click "Create Baseline"
4. Enter:
   - **Name**: Baseline identifier (e.g., "PMB v1.0")
   - **Description**: Purpose of this baseline
   - **Type**: PMB (official), Forecast, or What-If
5. Click "Create"

### Baseline Types

| Type | Description | Use Case |
|------|-------------|----------|
| **PMB** | Performance Measurement Baseline | Official approved baseline |
| **Forecast** | Planning baseline | Budget forecasts |
| **What-If** | Scenario analysis | Temporary analysis |

### Comparing Baselines

1. Navigate to "Baselines" tab
2. Select two baselines to compare
3. Click "Compare"
4. Review differences in:
   - Schedule dates
   - Budget allocations
   - Activity changes

---

## Monte Carlo Simulation

Monte Carlo simulation provides probabilistic schedule and cost risk analysis.

### Setting Up Uncertainty

For each activity, define three-point estimates:

1. Navigate to activity details
2. Click "Risk" tab
3. Enter:
   - **Optimistic Duration**: Best case
   - **Most Likely Duration**: Expected duration
   - **Pessimistic Duration**: Worst case
4. Select distribution type:
   - **Triangular**: Simple 3-point
   - **PERT**: Weighted toward most likely (recommended)
   - **Normal**: Gaussian distribution
   - **Uniform**: Equal probability

### Running Simulation

1. Navigate to "Analysis" tab
2. Click "Monte Carlo Simulation"
3. Configure:
   - **Iterations**: 1,000-10,000 recommended
   - **Include Cost**: Yes/No
   - **Correlation**: Enable for related activities
4. Click "Run Simulation"

### Interpreting Results

| Metric | Description |
|--------|-------------|
| **P50** | 50% confidence level (median) |
| **P70** | 70% confidence of achieving |
| **P80** | 80% confidence (common target) |
| **P90** | 90% confidence (conservative) |
| **Sensitivity** | Activities most affecting outcome |

### Using Results

- **P80 Duration**: Use for realistic schedule commitments
- **Sensitivity Analysis**: Focus risk mitigation on top drivers
- **Critical Path Frequency**: Identify paths that become critical

---

## Scenario Planning

Scenario planning enables what-if analysis without affecting production data.

### Creating a Scenario

1. Navigate to "Scenarios" tab
2. Click "Create Scenario"
3. Enter:
   - **Name**: Scenario description
   - **Base**: Current schedule or existing baseline
4. Click "Create"

### Making Changes in Scenario

1. Open the scenario
2. Make changes:
   - Modify activity durations
   - Add/remove activities
   - Change dependencies
   - Adjust budgets
3. Changes are tracked automatically

### Analyzing Scenario

1. Click "Calculate" to run CPM
2. Click "Simulate" to run Monte Carlo
3. Compare to baseline:
   - Schedule impact
   - Cost impact
   - Risk changes

### Promoting Scenario

When a scenario is approved:

1. Click "Promote to Baseline"
2. Enter baseline name
3. Choose whether to apply to program
4. Click "Promote"

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
- **S-Curve**: Export as PNG or CSV

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

#### CPR Format 3 (Baseline Changes)

Log of all baseline changes with justifications.

#### CPR Format 5 (EVMS Summary)

Comprehensive EVMS performance summary with:
- Current period metrics
- Cumulative metrics
- Variance analysis
- EAC projections

#### S-Curve Report

Performance curves showing:
- BCWS (Planned Value)
- BCWP (Earned Value)
- ACWP (Actual Cost)
- Forecast projections

### Generating Reports

1. Navigate to "Reports" tab
2. Select report type
3. Choose period (or use latest)
4. Click "Generate"
5. View online or download PDF

---

## Jira Integration

Synchronize activities with Jira issues for agile teams.

### Setting Up Integration

1. Navigate to "Settings" → "Integrations"
2. Click "Add Jira Integration"
3. Enter:
   - **Jira URL**: Your Atlassian instance
   - **Project Key**: Jira project to sync
   - **Email**: Service account email
   - **API Token**: Jira API token
4. Configure sync direction:
   - **Jira → DPM**: Jira updates flow to DPM
   - **DPM → Jira**: DPM updates flow to Jira
   - **Bidirectional**: Both directions
5. Click "Save"

### Field Mapping

Map DPM fields to Jira custom fields:
- Duration → Custom field
- Percent Complete → Custom field
- Actual Cost → Custom field

### Syncing Data

- **Automatic**: Webhooks trigger on Jira changes
- **Manual**: Click "Sync Now" to force sync

### Variance Alerts

Configure alerts for performance thresholds:
- SPI below threshold
- CPI below threshold
- Notify via Slack or email

---

## API Access

For automated integrations and CI/CD pipelines.

### API Keys

1. Navigate to "Settings" → "API Keys"
2. Click "Create API Key"
3. Enter:
   - **Name**: Key purpose
   - **Scopes**: Limit permissions (optional)
   - **Expiration**: Days until expiry
4. **Save the key immediately** - it cannot be retrieved later

### Using API Keys

```bash
curl -H "X-API-Key: dpm_abc123_..." \
  https://api.defense-pm-tool.com/api/v1/programs
```

### API Documentation

- **Interactive Docs**: /docs (Swagger UI)
- **API Guide**: See [API_GUIDE.md](API_GUIDE.md)

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

*Defense PM Tool v1.1.0 - Last updated: February 2026*
