# Interrupt and Change Control

Clients change their minds. This system supports that without losing history.

## Change request record
Every change request includes:
- Matter ID
- Request date
- Requested by
- Change type
- Affected documents
- Affected stages
- Required attorney decision Y/N
- Impact on timeline
- Status
- Owner
- Resolution date

## Change types
1. Beneficiary change
2. Fiduciary change
3. Asset change
4. Guardian change
5. Distribution age change
6. Title change
7. Contact or address change
8. Appointment change
9. Document scope change
10. Full restart

## Process rule
No direct edit to a final document without a change request. Drafts may be edited freely before attorney review. After attorney review, every edit requires a change request or attorney instruction.

## Interruption handling
If interrupted during signing prep:
- Pause the matter.
- Mark stage as "On Hold - Change Pending."
- Preserve last approved version.
- Create revised task list.
- Notify client and attorney.
- Recalculate target date.
