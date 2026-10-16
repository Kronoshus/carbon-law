# Carbon Law

Carbon Law is an open, free-budget operational model and automation system for a California estate planning law firm. It combines:

1. A practical paralegal workflow answer for taking ownership of an estate planning matter.
2. A scalable department plan for 30 to 100 active estate planning matters.
3. A website/app surface to track matters, tasks, attorney review, client communication, document status, appointments, and changes.
4. A prompt-library pipeline for California estate planning documents.
5. Interrupt/change-control rules so any matter can be modified at any time.

## What this repository does

- Organizes estate planning work from intake to signed documents.
- Tracks every matter in a standard stage model.
- Shows which matters are progressing, stalled, or need immediate attention.
- Keeps every task, owner, due date, and blocker visible.
- Supports interruption and change requests without losing history.
- Automates reminders and rescheduling.
- Maintains a realistic paralegal-style status report.
- Aims to operate on free tools and budget-friendly automation.

## Free-budget tool stack

- GitHub Pages or Vercel free tier for the web app.
- GitHub Issues/Projects for workflow tracking.
- Google Sheets or Airtable free tier for matter tracking if not self-hosted.
- Cal.com free tier or Calendly free tier for scheduling.
- ntfy.sh for free push notifications.
- Clio Manage/Grow if already licensed; otherwise Google Workspace + open source forms.
- CourtListener API for legal research cross-checks.
- Juralio ideas for matter and document structure where useful.

## Operating principle

Every matter moves through the same named stages. Every stage has an owner, a due date, a checklist, a blocker field, and a next action. No matter skips a stage silently.

## Core stages

1. Intake and Conflicts
2. Attorney Scope Review
3. Client Document Collection
4. Trust/Wills/POA Drafting
5. Exception and Update Intake
6. Attorney Review and Revision
7. Client Review and Signing Readiness
8. Funding and Asset Transfer Guidance
9. Execution and Notarization
10. Closing, Delivery, and Follow-Up

## Fast status reporting

A Friday 4 p.m. report can be produced in about five minutes because every matter has one current stage, one owner, one due date, and one next action in a single tracker.
