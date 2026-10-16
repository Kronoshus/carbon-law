# Part 2: Building a Scalable Estate Planning Department

## 1. Caseload management

### 30 active matters
Use a single tracker with 18 core fields:
1. Matter ID
2. Client
3. Stage
4. Owner
5. Attorney reviewer
6. Due date
7. Last client contact
8. Next client contact
9. Next action
10. Blocker
11. Document status
12. Title status
13. Funding status
14. Appointment status
15. Risk level
16. Notes
17. Priority
18. Friday report flag

### 30 to 100 matters
Changes at scale:
- Move from spreadsheets to a validated database.
- Add views by stage, owner, attorney, and due date.
- Add recurring reminders.
- Add automated status calculations.
- Add document generation jobs.
- Add client portal or secure form links.
- Add cancellation and rescheduling workflow.
- Add audit log for every change.
- Add bottleneck reports.
- Add capacity reports.

## 2. Systems and workflows

### Standard matter stages
1. Intake and conflicts
2. Attorney scope review
3. Client data collection
4. Drafting
5. Review queue
6. Client review
7. Signing preparation
8. Execution
9. Funding follow-up
10. Closed

### Standard checklists
- New matter intake checklist
- Conflicts checklist
- Client questionnaire checklist
- Property and title checklist
- Trust drafting checklist
- Will drafting checklist
- Power of attorney checklist
- Attorney review checklist
- Client review checklist
- Signing execution checklist
- Funding checklist
- Client delivery checklist
- Post-execution follow-up checklist

### Templates
- Engagement letter
- Client questionnaire
- Status update email
- Document review cover email
- Signing instructions
- Funding guide
- Post-signing checklist
- Change request form
- Cancellation/rescheduling email
- Friday status report

## 3. Automation and technology

### Existing software
Clio Grow:
- Intake forms
- Client onboarding
- Conflict capture
- Lead status

Clio Manage:
- Matters
- Tasks
- Time
- Contacts
- Documents

Asana:
- Department roadmap
- Recurring checklists
- Capacity board

LexisNexis:
- Legal research
- Form and case validation

### Recommended additions (free or low cost)
- GitHub for docs, templates, prompt libraries, and audit history
- Google Sheets or Airtable as a flexible tracker
- ntfy.sh for phone notifications
- Cal.com for scheduling
- Zapier or Make.com free tier for simple automations
- DocuSign free trial or low-cost e-sign only where allowed
- Open-source forms for client intake
- Juralio-inspired matter structure if useful
- CourtListener for research and legal source checks

### Automations
1. New intake creates a matter record.
2. Matter record creates standard task set.
3. Attorney review task creates a reminder.
4. Missing client data triggers follow-up.
5. Overdue task escalates in daily standup.
6. Appointment booking sends confirmation and preparation instructions.
7. Cancellation or rescheduling updates the tracker.
8. Completed signing triggers funding checklist.
9. Weekly report auto-generates from the tracker.
10. Change request creates a revision task.

## 4. Deadlines and accountability

### Daily
- Review overdue tasks.
- Review pending attorney reviews.
- Review waiting-on-client matters.
- Review unconfirmed appointments.

### Weekly
- Monday capacity review.
- Friday status report.
- Bottleneck review.
- Client communication audit.

### Accountability object
Every task has:
- Owner
- Due date
- Status
- Blocker
- Escalation path
- Proof of completion

## 5. Client experience

- Same-day acknowledgment of new intake.
- Status update every five business days at minimum.
- One named point of contact.
- Plain-language instructions for funding.
- Clear signing appointment reminders.
- Easy reschedule option.
- No legal advice given by email unless attorney-approved.

## 6. Capacity and bottlenecks

### Likely bottlenecks
1. Attorney review capacity.
2. Home title and funding follow-up.
3. Client response delays.
4. Document revisions from late updates.
5. Notary and signing coordination.
6. Insurance and account beneficiary changes after execution.

### Mitigation
- Batch attorney review packets weekly.
- Use standard review summaries.
- Use client instructions templates.
- Create follow-up owner pools.
- Track client response deadlines.
- Lock document versions before attorney review.

## 7. First 30 days

### Week 1
- Define matter stages.
- Define field set.
- Build the matter tracker.
- Build intake and conflict templates.
- Build daily and weekly review routine.

### Week 2
- Train paralegals on tracker.
- Load current matters.
- Create document version rules.
- Create change request process.
- Build status update templates.

### Week 3
- Add automation for appointment reminders.
- Add overdue task alerts.
- Add Friday report.
- Pilot with 10 matters.
- Review failure points.

### Week 4
- Fix workflow gaps.
- Add capacity dashboard.
- Add client portal links if useful.
- Formalize bottlenecks list.
- Publish standard operating procedure.

### Information needed from the firm
- Approved engagement terms
- Attorney review turnaround standard
- Preferred scheduling method
- Document template set
- Security and client portal requirements
- Clio configuration
- Staffing and role definitions

## 8. Friday 4 p.m. report on 100 active clients

### How quickly?
About five to ten minutes if the tracker is current.

### Report contents
- Total active matters
- Matters by stage
- Matters due this week
- Overdue matters
- Attorney review queue
- Client response overdue
- Scheduling pending
- Signing completed
- Funding pending
- High-risk matters
- Top blockers
- Capacity by paralegal
- Next-week forecast

### How the system identifies status
- Green: stage due date not reached and no blockers.
- Yellow: at risk or waiting on client.
- Red: overdue, blocked, or high-risk.
- Blue: waiting on attorney.
- Grey: inactive or on hold.

## 9. Practical department model
The department should not start with 100 matters on day one. It should start with a 30-matter pilot, fix process errors, then scale to 60 and 100. Weekly reporting and bottleneck review should be built before volume increases.
