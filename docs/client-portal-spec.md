# Client-Facing Web Portal Specification

The client portal is part of the public website. It must allow:
- Secure intake questionnaire submission
- Document upload
- Status view with plain-language stage
- Appointment booking
- Appointment cancellation
- Appointment rescheduling
- Change request submission
- Messaging or request log
- Funding checklist download
- Final document download when approved

## Security requirements
- No public document links without authentication.
- Every upload is tied to matter ID.
- Audit log for every action.
- Role-based access for client, paralegal, attorney.

## Free-budget version 1
- Typeform or Google Forms for intake
- Cal.com for scheduling
- Google Drive secured folders for documents
- Web app for status and task tracking
- Email notifications for all changes
