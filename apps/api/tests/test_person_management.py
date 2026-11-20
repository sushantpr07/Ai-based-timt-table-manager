from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import (Department, Faculty, Institution, Role, Section, Semester,
                        Student, AcademicTerm, User)
from app.security import create_access_token
from test_client_auth import authenticate_client


def test_admin_can_edit_faculty_and_student_records():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with testing_session() as db:
        institution = Institution(name="Example University")
        db.add(institution); db.flush()
        department = Department(institution_id=institution.id, name="Engineering", code="ENG")
        db.add(department); db.flush()
        admin = User(institution_id=institution.id, email="admin@example.invalid", full_name="Admin",
                     password_hash="unused", role=Role.college_admin)
        faculty_account = User(institution_id=institution.id, department_id=department.id,
                               email="faculty@example.invalid", full_name="Old Faculty Name",
                               password_hash="unused", role=Role.faculty)
        student_account = User(institution_id=institution.id, department_id=department.id,
                               email="student@example.invalid", full_name="Old Student Name",
                               password_hash="unused", role=Role.student)
        db.add_all([admin, faculty_account, student_account]); db.flush()
        term = AcademicTerm(institution_id=institution.id, name="Fall", academic_year="2026-27")
        db.add(term); db.flush()
        semester = Semester(department_id=department.id, term_id=term.id, number=1)
        db.add(semester); db.flush()
        section_a = Section(semester_id=semester.id, name="A", strength=30)
        section_b = Section(semester_id=semester.id, name="B", strength=28)
        db.add_all([section_a, section_b]); db.flush()
        faculty = Faculty(user_id=faculty_account.id, department_id=department.id, max_weekly_periods=18)
        student = Student(user_id=student_account.id, section_id=section_a.id, student_number="S-100")
        db.add_all([faculty, student]); db.commit()
        token = create_access_token(admin)
        department_id = department.id
        faculty_id, student_id, target_section_id = faculty.id, student.id, section_b.id

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            authenticate_client(client, token)
            faculty_response = client.patch(f"/api/v1/campus/people/faculty/{faculty_id}", json={
                "full_name": "Updated Faculty", "department_id": str(department_id), "max_weekly_periods": 20,
            })
            assert faculty_response.status_code == 200
            assert faculty_response.json()["max_weekly_periods"] == 20

            availability = client.put(f"/api/v1/campus/people/faculty/{faculty_id}/availability", json={
                "unavailable": [{"day": 6, "period": 13}]
            })
            assert availability.status_code == 200
            saved_availability = client.get(f"/api/v1/campus/people/faculty/{faculty_id}/availability")
            assert saved_availability.status_code == 200
            assert saved_availability.json()["unavailable"] == [{"day": 6, "period": 13}]

            student_response = client.patch(f"/api/v1/campus/people/students/{student_id}", json={
                "full_name": "Updated Student", "section_id": str(target_section_id), "student_number": "S-200",
            })
            assert student_response.status_code == 200
            assert student_response.json()["section_id"] == str(target_section_id)
            assert student_response.json()["student_number"] == "S-200"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
