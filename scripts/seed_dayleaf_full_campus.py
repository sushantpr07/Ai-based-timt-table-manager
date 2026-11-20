import sys
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

from app.db import SessionLocal
from app.models import (
    Institution, Department, AcademicTerm, Semester, Section,
    Subject, TeachingAssignment, Room, User, Faculty, Student,
    FacultyAvailability, Role
)
from app.security import hash_password

def seed_full_campus():
    db = SessionLocal()
    try:
        print("🌱 Seeding Dayleaf Campus Structure...")

        # 1. Institution
        inst = db.query(Institution).first()
        if not inst:
            inst = Institution(name="Dayleaf University")
            db.add(inst)
            db.flush()
        else:
            inst.name = "Dayleaf University"
            db.flush()

        # 2. Departments
        departments_data = [
            ("Computer Science & Engineering", "CSE"),
            ("Cybersecurity", "CYS"),
            ("Data Science & AI", "DS"),
            ("Electronics & Communication", "ECE"),
        ]
        dept_map = {}
        for name, code in departments_data:
            dept = db.query(Department).filter_by(institution_id=inst.id, code=code).first()
            if not dept:
                dept = Department(institution_id=inst.id, name=name, code=code)
                db.add(dept)
                db.flush()
            else:
                dept.name = name
                db.flush()
            dept_map[code] = dept
        print(f"✅ {len(dept_map)} Departments ready.")

        # 3. Academic Terms
        terms_data = [
            ("Fall Semester 2026-27", "2026-27", True),
            ("Spring Semester 2026-27", "2026-27", False),
        ]
        term_map = {}
        for name, year, is_curr in terms_data:
            term = db.query(AcademicTerm).filter_by(institution_id=inst.id, name=name, academic_year=year).first()
            if not term:
                term = AcademicTerm(institution_id=inst.id, name=name, academic_year=year, is_current=is_curr)
                db.add(term)
                db.flush()
            else:
                term.is_current = is_curr
                db.flush()
            term_map[name] = term
        current_term = term_map["Fall Semester 2026-27"]
        print(f"✅ Academic Terms ready. Current: {current_term.name}")

        # 4. Classrooms & Labs
        rooms_data = [
            # Classrooms & Lecture Halls
            ("LH-101 (Turing Hall)", 80, "classroom"),
            ("LH-102 (Lovelace Hall)", 80, "classroom"),
            ("LH-201 (Shannon Hall)", 65, "classroom"),
            ("LH-202 (Neumann Hall)", 65, "classroom"),
            ("LH-301 (Babbage Hall)", 70, "classroom"),
            ("LH-302 (Ramanujan Hall)", 70, "classroom"),
            ("Audi-1 (Main Auditorium)", 250, "classroom"),
            ("Audi-2 (Seminar Hall A)", 120, "classroom"),
            ("Seminar Hall B", 80, "classroom"),
            # Labs
            ("AI & Deep Learning Lab", 75, "lab"),
            ("Cyber Security & SOC Lab", 75, "lab"),
            ("Big Data Analytics Lab", 75, "lab"),
            ("Software Engineering Studio", 75, "lab"),
            ("Cloud & Networks Lab", 75, "lab"),
            ("VLSI & Embedded Systems Lab", 75, "lab"),
        ]
        room_objs = []
        for r_name, cap, r_type in rooms_data:
            r = db.query(Room).filter_by(institution_id=inst.id, name=r_name).first()
            if not r:
                r = Room(institution_id=inst.id, name=r_name, capacity=cap, room_type=r_type)
                db.add(r)
                db.flush()
            else:
                r.capacity = cap
                r.room_type = r_type
                db.flush()
            room_objs.append(r)
        print(f"✅ {len(room_objs)} Classrooms and Labs ready.")

        # 5. Semesters & Sections
        sections_map = {}
        for code, dept in dept_map.items():
            for sem_num in [3, 5]:
                sem = db.query(Semester).filter_by(department_id=dept.id, term_id=current_term.id, number=sem_num).first()
                if not sem:
                    sem = Semester(department_id=dept.id, term_id=current_term.id, number=sem_num)
                    db.add(sem)
                    db.flush()
                # Sections
                sec_names = ["A", "B"] if code == "CSE" else ["A"]
                for s_name in sec_names:
                    sec = db.query(Section).filter_by(semester_id=sem.id, name=s_name).first()
                    if not sec:
                        sec = Section(semester_id=sem.id, name=s_name, strength=60)
                        db.add(sec)
                        db.flush()
                    sections_map[f"{code}_S{sem_num}_{s_name}"] = sec
        print(f"✅ {len(sections_map)} Sections ready across semesters.")

        # 6. People: HODs, Faculty, Students
        default_pwd = hash_password("Dayleaf@2026")

        # HODs
        hods_data = [
            ("Dr. Rajesh Raman", "hod.cse@dayleaf.edu", "CSE"),
            ("Dr. Aditi Rao", "hod.cys@dayleaf.edu", "CYS"),
            ("Dr. Neha Kulkarni", "hod.ds@dayleaf.edu", "DS"),
            ("Dr. Vikram Malhotra", "hod.ece@dayleaf.edu", "ECE"),
        ]
        for name, email, dcode in hods_data:
            u = db.query(User).filter_by(email=email).first()
            if not u:
                u = User(
                    institution_id=inst.id,
                    department_id=dept_map[dcode].id,
                    email=email,
                    full_name=name,
                    password_hash=default_pwd,
                    role=Role.hod,
                    is_active=True,
                    email_verified=True,
                )
                db.add(u)
                db.flush()
            else:
                u.full_name = name
                u.role = Role.hod
                u.department_id = dept_map[dcode].id
                db.flush()

        # Faculty Members
        faculty_roster = [
            # CSE
            ("Prof. Arjun Menon", "arjun.menon@dayleaf.edu", "CSE", ["M.Tech, Ph.D", "Data Structures", "Algorithms"], 18),
            ("Dr. Kavya Iyer", "kavya.iyer@dayleaf.edu", "CSE", ["Ph.D", "Databases", "Distributed Systems"], 18),
            ("Dr. Rohan Shah", "rohan.shah@dayleaf.edu", "CSE", ["Ph.D", "Operating Systems", "Compilers"], 16),
            ("Prof. Sneha Verma", "sneha.verma@dayleaf.edu", "CSE", ["M.Tech", "Web Systems", "Cloud"], 18),
            # CYS
            ("Prof. Kunal Deshmukh", "kunal.deshmukh@dayleaf.edu", "CYS", ["M.Tech", "Ethical Hacking", "SOC"], 18),
            ("Dr. Ananya Sen", "ananya.sen@dayleaf.edu", "CYS", ["Ph.D", "Network Defense", "Cryptography"], 16),
            # DS
            ("Prof. Vivek Nair", "vivek.nair@dayleaf.edu", "DS", ["M.Tech", "Machine Learning", "Neural Nets"], 18),
            ("Dr. Meera Joshi", "meera.joshi@dayleaf.edu", "DS", ["Ph.D", "Data Mining", "Statistics"], 18),
            ("Dr. Karan Shah", "karan.shah@dayleaf.edu", "DS", ["Ph.D", "Big Data", "NLP"], 16),
            # ECE
            ("Prof. Pooja Hegde", "pooja.hegde@dayleaf.edu", "ECE", ["M.Tech", "VLSI Design", "Embedded"], 18),
            ("Dr. Amit Bhargav", "amit.bhargav@dayleaf.edu", "ECE", ["Ph.D", "Wireless Systems", "IoT"], 16),
        ]

        faculty_objs = {}
        for name, email, dcode, quals, max_periods in faculty_roster:
            u = db.query(User).filter_by(email=email).first()
            if not u:
                u = User(
                    institution_id=inst.id,
                    department_id=dept_map[dcode].id,
                    email=email,
                    full_name=name,
                    password_hash=default_pwd,
                    role=Role.faculty,
                    is_active=True,
                    email_verified=True,
                )
                db.add(u)
                db.flush()
            fac = db.query(Faculty).filter_by(user_id=u.id).first()
            if not fac:
                fac = Faculty(
                    user_id=u.id,
                    department_id=dept_map[dcode].id,
                    max_weekly_periods=max_periods,
                    qualifications=quals
                )
                db.add(fac)
                db.flush()
            faculty_objs[email] = fac

            # Add basic availability (Mon-Fri, periods 0-5)
            for d in range(5):
                for p in range(6):
                    avail = db.query(FacultyAvailability).filter_by(faculty_id=fac.id, day=d, period=p).first()
                    if not avail:
                        # Friday afternoon reserved for research
                        is_avail = not (d == 4 and p >= 4)
                        avail = FacultyAvailability(faculty_id=fac.id, day=d, period=p, is_available=is_avail)
                        db.add(avail)
            db.flush()
        print(f"✅ {len(faculty_objs)} Faculty members configured with availability rules.")

        # 7. Subjects
        subjects_data = [
            # CSE S3
            ("CSE", "CS201", "Data Structures & Algorithms", 4, "classroom"),
            ("CSE", "CS202", "Database Management Systems", 3, "classroom"),
            ("CSE", "CS203", "Discrete Mathematics", 3, "classroom"),
            ("CSE", "CS204", "Data Structures Laboratory", 1, "lab"),
            ("CSE", "CS205", "DBMS Laboratory", 1, "lab"),
            # CSE S5
            ("CSE", "CS301", "Operating Systems", 4, "classroom"),
            ("CSE", "CS302", "Computer Networks", 3, "classroom"),
            ("CSE", "CS303", "Software Engineering Studio", 1, "lab"),
            ("CSE", "CS304", "Networks & Cloud Laboratory", 1, "lab"),
            # CYS S3
            ("CYS", "CY201", "Cyber Defense Fundamentals", 4, "classroom"),
            ("CYS", "CY202", "Network Protocols & Architecture", 3, "classroom"),
            ("CYS", "CY203", "SOC & Packet Analysis Lab", 1, "lab"),
            # DS S3
            ("DS", "DS201", "Foundations of Data Science", 4, "classroom"),
            ("DS", "DS202", "Applied Statistical Methods", 3, "classroom"),
            ("DS", "DS203", "Python Analytics & ML Lab", 1, "lab"),
            # ECE S3
            ("ECE", "EC201", "Signals & Linear Systems", 4, "classroom"),
            ("ECE", "EC202", "Digital Electronics & Logic", 3, "classroom"),
            ("ECE", "EC203", "Microcontrollers & IoT Lab", 1, "lab"),
        ]

        subject_map = {}
        for dcode, code, sname, sessions, rtype in subjects_data:
            s = db.query(Subject).filter_by(department_id=dept_map[dcode].id, code=code).first()
            if not s:
                s = Subject(department_id=dept_map[dcode].id, code=code, name=sname, weekly_sessions=sessions, room_type=rtype)
                db.add(s)
                db.flush()
            else:
                s.name = sname
                s.weekly_sessions = sessions
                s.room_type = rtype
                db.flush()
            subject_map[code] = s
        print(f"✅ {len(subject_map)} Core subjects and laboratories created.")

        # 8. Teaching Assignments (Connecting Subject + Section + Faculty)
        assignments = [
            # CSE S3 Sec A
            ("CS201", "CSE_S3_A", "arjun.menon@dayleaf.edu", 4, 1),
            ("CS202", "CSE_S3_A", "kavya.iyer@dayleaf.edu", 3, 1),
            ("CS203", "CSE_S3_A", "rohan.shah@dayleaf.edu", 3, 1),
            ("CS204", "CSE_S3_A", "arjun.menon@dayleaf.edu", 1, 2),
            ("CS205", "CSE_S3_A", "kavya.iyer@dayleaf.edu", 1, 2),
            # CSE S3 Sec B
            ("CS201", "CSE_S3_B", "arjun.menon@dayleaf.edu", 4, 1),
            ("CS202", "CSE_S3_B", "kavya.iyer@dayleaf.edu", 3, 1),
            ("CS203", "CSE_S3_B", "rohan.shah@dayleaf.edu", 3, 1),
            ("CS204", "CSE_S3_B", "arjun.menon@dayleaf.edu", 1, 2),
            ("CS205", "CSE_S3_B", "kavya.iyer@dayleaf.edu", 1, 2),
            # CSE S5 Sec A
            ("CS301", "CSE_S5_A", "rohan.shah@dayleaf.edu", 4, 1),
            ("CS302", "CSE_S5_A", "sneha.verma@dayleaf.edu", 3, 1),
            ("CS303", "CSE_S5_A", "sneha.verma@dayleaf.edu", 1, 2),
            ("CS304", "CSE_S5_A", "rohan.shah@dayleaf.edu", 1, 2),
            # CYS S3 Sec A
            ("CY201", "CYS_S3_A", "kunal.deshmukh@dayleaf.edu", 4, 1),
            ("CY202", "CYS_S3_A", "ananya.sen@dayleaf.edu", 3, 1),
            ("CY203", "CYS_S3_A", "kunal.deshmukh@dayleaf.edu", 1, 2),
            # DS S3 Sec A
            ("DS201", "DS_S3_A", "vivek.nair@dayleaf.edu", 4, 1),
            ("DS202", "DS_S3_A", "meera.joshi@dayleaf.edu", 3, 1),
            ("DS203", "DS_S3_A", "vivek.nair@dayleaf.edu", 1, 2),
            # ECE S3 Sec A
            ("EC201", "ECE_S3_A", "pooja.hegde@dayleaf.edu", 4, 1),
            ("EC202", "ECE_S3_A", "amit.bhargav@dayleaf.edu", 3, 1),
            ("EC203", "ECE_S3_A", "pooja.hegde@dayleaf.edu", 1, 2),
        ]

        assignment_count = 0
        for scode, sec_key, fac_email, sessions, duration in assignments:
            subj = subject_map[scode]
            sec = sections_map[sec_key]
            fac = faculty_objs[fac_email]
            ta = db.query(TeachingAssignment).filter_by(subject_id=subj.id, section_id=sec.id, faculty_id=fac.id).first()
            if not ta:
                ta = TeachingAssignment(
                    subject_id=subj.id,
                    section_id=sec.id,
                    faculty_id=fac.id,
                    sessions_per_week=sessions,
                    duration_periods=duration
                )
                db.add(ta)
            else:
                ta.sessions_per_week = sessions
                ta.duration_periods = duration
            assignment_count += 1
        db.flush()
        print(f"✅ {assignment_count} Teaching assignments linked.")

        # 9. Students
        students_roster = [
            ("Aarav Sharma", "aarav.sharma@dayleaf.edu", "CSE_S3_A", "DL2026CSE001"),
            ("Diya Patel", "diya.patel@dayleaf.edu", "CSE_S3_A", "DL2026CSE002"),
            ("Ishaan Verma", "ishaan.verma@dayleaf.edu", "CSE_S3_A", "DL2026CSE003"),
            ("Ananya Gupta", "ananya.gupta@dayleaf.edu", "CSE_S3_B", "DL2026CSE051"),
            ("Kabir Singh", "kabir.singh@dayleaf.edu", "CSE_S3_B", "DL2026CSE052"),
            ("Riya Sen", "riya.sen@dayleaf.edu", "CYS_S3_A", "DL2026CYS001"),
            ("Aditya Roy", "aditya.roy@dayleaf.edu", "CYS_S3_A", "DL2026CYS002"),
            ("Tanvi Mehta", "tanvi.mehta@dayleaf.edu", "DS_S3_A", "DL2026DS001"),
            ("Siddharth Rao", "siddharth.rao@dayleaf.edu", "DS_S3_A", "DL2026DS002"),
            ("Kavita Nair", "kavita.nair@dayleaf.edu", "ECE_S3_A", "DL2026ECE001"),
        ]
        student_count = 0
        for sname, semail, sec_key, roll_no in students_roster:
            sec = sections_map[sec_key]
            sem = db.query(Semester).get(sec.semester_id)
            u = db.query(User).filter_by(email=semail).first()
            if not u:
                u = User(
                    institution_id=inst.id,
                    department_id=sem.department_id,
                    email=semail,
                    full_name=sname,
                    password_hash=default_pwd,
                    role=Role.student,
                    is_active=True,
                    email_verified=True,
                )
                db.add(u)
                db.flush()
            stu = db.query(Student).filter_by(user_id=u.id).first()
            if not stu:
                stu = Student(user_id=u.id, section_id=sec.id, student_number=roll_no)
                db.add(stu)
            student_count += 1
        db.flush()
        print(f"✅ {student_count} Student records active.")

        db.commit()
        print("🎉 Full Dayleaf Campus Structure successfully seeded!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding campus structure: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_full_campus()
