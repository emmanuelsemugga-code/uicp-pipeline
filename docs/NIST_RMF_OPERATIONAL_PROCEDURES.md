---

```markdown
# NIST AI RMF ALIGNMENT — BLOCK 3: OPERATIONAL PROCEDURES & DEPLOYMENT

## QUARTERLY ASSESSMENT PROCEDURE

### Timing: Every Q1, Q2, Q3, Q4 (or before audits/customer requests)

**Lead:** Compliance Officer
**Participants:** CTO, Ops Lead, Tech Liaison
**Duration:** 4 hours (assessment) + 2 hours (documentation)
**Output:** NIST RMF Compliance Report (markdown + JSON)

---

### Step 1: Prepare (1 hour)

**Compliance Officer:**
- [ ] Schedule assessment meeting (calendar block 4 hours)
- [ ] Review last quarter's results (if exists)
- [ ] List any changes since last assessment:
  - New features deployed? (affects GOVERN/MAP)
  - Incident occurred? (affects MANAGE)
  - Monitoring improvements? (affects MEASURE)
  - Policy changes? (affects GOVERN)

**Tech Liaison:**
- [ ] Prepare documentation updates
  - Any new architecture docs?
  - Updated security model?
  - New operational procedures?
- [ ] List evidence sources for each control
  - Which GAPs completed this quarter?
  - Which policies updated?

**Ops Lead:**
- [ ] Export monitoring metrics (last 90 days)
  - Uptime data, incident count, alert frequency
  - Cache hit rates (if using GAP-38)
  - Constraint evaluation latency

---

### Step 2: Assessment Meeting (3 hours)

**Run assessment:**

```python
from app.nist_ai_rmf import NISTAssessment, RMFReportGenerator

assessment = NISTAssessment()
results = assessment.assess_all()

generator = RMFReportGenerator(assessment)
report_md = generator.to_markdown()
