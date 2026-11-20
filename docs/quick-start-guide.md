# CampusFlow quick start

Open [CampusFlow](http://127.0.0.1:3010) while the local web and API servers are running.

The preview is sample-only. Real department and term choices appear after you sign in and add them in **Academics**; an empty choice now tells you where to go next.

## 1. Create the college administrator account

Choose **Create campus workspace**. Enter your college name, your name, email, and a password of at least 12 characters. This first account is the college administrator. Sign in with it.

## 2. Add the college structure

Open **Academics** and add these in order:

1. Departments, such as Computer Science.
2. An academic term, such as Fall 2026.
3. Semesters and sections, such as Semester 1, Section A.
4. Subjects for each department.

## 3. Add rooms and teaching staff

- Open **Classrooms** and add rooms/labs. Enter room type and capacity so the scheduler can choose suitable spaces.
- Open **People** to invite HODs and faculty, add students, and set faculty unavailable periods.
- Open **Academics → Teaching assignments**. Connect each subject, section, and faculty member; set weekly frequency and consecutive period length.

**Email note:** local email delivery is not configured. Inviting users and sending password-reset emails require SMTP settings. You can still create and use the first college administrator account.

## 4. Generate and publish a timetable

1. Open **Timetable** and select the academic term and department.
2. Choose the weekdays and number of periods, then select **Generate**.
3. Review any conflict messages. They explain if a faculty member, room, or section is unavailable or if a room does not fit.
4. Drag a session to move it. Use the suggested open slots/rooms, then **Undo** or **Redo** if needed.
5. A college administrator can publish a conflict-free draft. An HOD submits it for approval first; the administrator then approves and publishes it.

## 5. Use the AI planner and reports

- In **AI planner**, select a term and department and ask a question or request a draft. Confirm a proposed draft before it is generated. Without an LLM key, the assistant uses guided responses; timetable validity still comes from the optimizer.
- **Analytics** and reports show campus summaries and schedule, faculty-load, room-use, and conflict data. Use CSV export to download a report.
- **Notifications**, **Audit log**, and **Settings** contain updates, administrative change history, and profile/institution preferences.

## Roles

- **College admin:** sets up the campus, manages all campus data, and publishes timetables.
- **HOD:** manages their department and submits timetables for approval.
- **Faculty:** views assigned/published schedules and manages availability where permitted.
- **Student:** views their section's published schedule.
- **Super admin:** creates institutions and their initial college administrators.
