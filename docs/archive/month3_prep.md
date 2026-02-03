# ARCHIVED: Month 3 Preparation Checklist

> **ARCHIVE NOTICE**: This document is historical and was used during Month 3 planning (January 2026).
> All items in this checklist have been completed. See v1.0.0 release notes for final implementation details.
> Archived: March 2026

---

# Month 3 Preparation Checklist

> Month 3 Focus: Compliance & Polish
> Timeline: Weeks 9-12 (Days 57-84)

---

## Dependencies to Install

### Week 9 (Reports)
- [x] `reportlab` - PDF generation
- [x] `weasyprint` (optional) - HTML to PDF conversion

### Week 10 (Jira Integration)
- [x] `jira` - Jira REST API client
- [x] `atlassian-python-api` (alternative)

```bash
# Add to requirements.txt
reportlab>=4.0.0
jira>=3.5.0
```

---

## API Endpoints to Create

### Week 9: Reports
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reports/cpr-format5/{program_id}` | POST | Generate CPR Format 5 report |
| `/reports/variance-analysis/{program_id}` | GET | Variance analysis report |
| `/reports/{report_id}/pdf` | GET | Export report as PDF |
| `/reports/{report_id}/audit` | GET | Report generation audit trail |

### Week 10: Jira Integration
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/integrations/jira/connect` | POST | Configure Jira connection |
| `/integrations/jira/sync` | POST | Sync work packages with Jira |
| `/integrations/jira/status` | GET | Integration status |
| `/integrations/jira/issues` | GET | List linked issues |

### Week 11: Scenarios
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scenarios/{id}/compare` | GET | Compare with baseline |
| `/scenarios/{id}/promote` | POST | Promote scenario to baseline |
| `/scenarios/{id}/history` | GET | Scenario change history |

---

## Database Migrations Needed

### Week 9: Variance Tracking
```sql
-- VarianceExplanation table
CREATE TABLE variance_explanations (
    id UUID PRIMARY KEY,
    program_id UUID REFERENCES programs(id),
    wbs_id UUID REFERENCES wbs(id),
    period_id UUID REFERENCES evms_periods(id),
    variance_type VARCHAR(20),  -- 'schedule' or 'cost'
    variance_amount DECIMAL(15,2),
    variance_percent DECIMAL(8,4),
    explanation TEXT NOT NULL,
    corrective_action TEXT,
    expected_resolution DATE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- ReportAudit table
CREATE TABLE report_audit (
    id UUID PRIMARY KEY,
    report_type VARCHAR(50),
    program_id UUID REFERENCES programs(id),
    generated_by UUID REFERENCES users(id),
    generated_at TIMESTAMP DEFAULT NOW(),
    parameters JSONB,
    file_path VARCHAR(500)
);
```

### Week 10: Jira Integration
```sql
-- JiraIntegration table
CREATE TABLE jira_integrations (
    id UUID PRIMARY KEY,
    program_id UUID REFERENCES programs(id),
    jira_url VARCHAR(255) NOT NULL,
    project_key VARCHAR(20) NOT NULL,
    api_token_encrypted BYTEA,
    sync_enabled BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP,
    sync_status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- JiraMapping table
CREATE TABLE jira_mappings (
    id UUID PRIMARY KEY,
    integration_id UUID REFERENCES jira_integrations(id),
    wbs_id UUID REFERENCES wbs(id),
    jira_issue_key VARCHAR(50),
    sync_direction VARCHAR(20),  -- 'to_jira', 'from_jira', 'bidirectional'
    last_synced_at TIMESTAMP
);
```

---

## External Service Setup

### Jira Integration
- [x] Customer provides Jira API credentials
- [x] Test Jira instance for development (Jira Cloud free tier)
- [x] Define field mappings (WBS -> Epic, Activity -> Issue)
- [x] Configure webhook for real-time sync

### PDF Generation
- [x] Design PDF templates for each report format
- [x] Define page layouts and branding
- [x] Test rendering with sample data

---

## Risk Triggers to Watch

| Week | Green | Yellow | Red |
|------|-------|--------|-----|
| 9 | CPR 1,3,5 generating | Only Format 1,3 | No reports generating |
| 10 | Jira syncing | Read-only sync | Not connecting to Jira |
| 11 | Scenarios <10s | Scenarios slow (>30s) | Corrupting baseline |
| 12 | Coverage 80%+ | Coverage 70-79% | Security vulnerabilities |

---

## Week-by-Week Goals

### Week 9: Reports (Days 57-63)
**Goal**: All CPR formats generating with variance explanations

Tasks:
- [x] Complete CPR Format 5 implementation
- [x] Add variance explanation CRUD
- [x] Implement PDF export for all formats
- [x] Add report generation audit trail
- [x] 20+ new tests

Exit Criteria:
- Format 1, 3, 5 all generating correctly
- Variance explanations persisted
- PDF export working
- Audit trail capturing all generations

### Week 10: Jira Integration (Days 64-70)
**Goal**: Bi-directional sync with Jira

Tasks:
- [x] Jira REST API client wrapper
- [x] Work package to Epic sync
- [x] Activity to Issue sync
- [x] Automatic issue creation from variance alerts
- [x] Webhook handler for real-time updates
- [x] 15+ new tests

Exit Criteria:
- Can connect to Jira instance
- WBS syncs as Epics
- Activities sync as Issues
- Variance alerts create Issues
- Changes reflect within 1 minute

### Week 11: What-if Views (Days 71-77)
**Goal**: Scenario comparison and promotion

Tasks:
- [x] Scenario comparison endpoint
- [x] Side-by-side comparison view
- [x] Impact visualization (delta analysis)
- [x] Scenario promotion workflow
- [x] History tracking for promotions
- [x] 15+ new tests

Exit Criteria:
- Can compare any scenario to baseline
- Visual diff of schedule/cost changes
- Promotion creates new baseline
- Full history of changes

### Week 12: Security & Final (Days 78-84)
**Goal**: Production-ready security and documentation

Tasks:
- [x] Security audit (OWASP Top 10)
- [x] Input validation hardening
- [x] Rate limiting on all endpoints
- [x] API key authentication option
- [x] Final documentation review
- [x] Performance verification
- [x] 10+ security tests

Exit Criteria:
- No critical/high vulnerabilities
- All inputs validated
- Rate limits enforced
- Documentation complete
- 80%+ coverage maintained
- All benchmarks passing

---

## Month 3 Success Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Test Count | 1700+ | 2400+ |
| Coverage | >=80% | 80%+ |
| CPR Formats | 1, 3, 5 complete | Complete |
| Jira Sync | Bi-directional | Complete |
| Report Export | PDF working | Complete |
| Security | No critical issues | Pass |
| Performance | All targets met | Pass |

---

## Files Created/Modified

### New Service Files
- `src/services/report_pdf_generator.py`
- `src/services/jira_client.py`
- `src/services/jira_sync.py`
- `src/services/scenario_comparison.py`

### New Repository Files
- `src/repositories/variance_explanation.py`
- `src/repositories/jira_integration.py`
- `src/repositories/report_audit.py`

### New Schema Files
- `src/schemas/variance_explanation.py`
- `src/schemas/jira_integration.py`
- `src/schemas/report_audit.py`

### New Model Files
- `src/models/variance_explanation.py`
- `src/models/jira_integration.py`
- `src/models/report_audit.py`

### New Test Files
- `tests/unit/test_report_pdf.py`
- `tests/unit/test_jira_client.py`
- `tests/integration/test_jira_sync.py`
- `tests/integration/test_scenario_comparison.py`
- `tests/e2e/test_month3_reports.py`

---

*Original Document: January 2026*
*Archived: March 2026*
*Month 3 Complete - v1.0.0 Released*
