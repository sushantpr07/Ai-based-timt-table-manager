from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies import ensure_institution, ensure_manager
from app.models import Role, User


def test_hod_can_manage_records_inside_their_department():
    department_id = uuid4()
    user = User(role=Role.hod, department_id=department_id)
    ensure_manager(user, department_id)


def test_hod_cannot_manage_another_department():
    user = User(role=Role.hod, department_id=uuid4())
    with pytest.raises(HTTPException) as exc:
        ensure_manager(user, uuid4())
    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", [Role.faculty, Role.student])
def test_faculty_and_students_cannot_manage_campus_records(role):
    user = User(role=role, department_id=uuid4())
    with pytest.raises(HTTPException) as exc:
        ensure_manager(user, user.department_id)
    assert exc.value.status_code == 403


def test_non_super_admin_cannot_cross_institution_boundary():
    user = User(role=Role.college_admin, institution_id=uuid4())
    with pytest.raises(HTTPException) as exc:
        ensure_institution(user, uuid4())
    assert exc.value.status_code == 404


def test_super_admin_can_manage_multiple_institutions():
    user = User(role=Role.super_admin, institution_id=None)
    ensure_institution(user, uuid4())
