import uuid
from app.models import Plan, UserCheckin


class TestPlan:
    """Test 90-day plan and check-in endpoints."""

    def _make_plan(self, db_session, test_user):
        plan = Plan(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            data={"phases": {}},
            phases={},
            current_phase="phase_1",
            current_week=1,
            current_day=0,
            is_active=True,
        )
        db_session.add(plan)
        db_session.commit()
        return plan

    def test_checkin_accepts_json_body(self, client, db_session, test_user, auth_token):
        """Regression: POST /plan/checkin must accept a JSON body
        (completed_tasks as list[str]), matching the iOS payload.
        Previously completed_tasks was declared as a query param and the
        JSON body was rejected with a 422."""
        self._make_plan(db_session, test_user)

        resp = client.post(
            "/api/v1/plan/checkin",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"completed_tasks": ["task-1"], "notes": "done"},
        )

        assert resp.status_code == 200
        # A check-in record should have been created
        checkin = (
            db_session.query(UserCheckin)
            .filter(UserCheckin.user_id == test_user.id)
            .first()
        )
        assert checkin is not None
        assert checkin.completed_tasks == ["task-1"]

    def test_checkin_empty_tasks(self, client, db_session, test_user, auth_token):
        """The iOS `checkin()` method sends completed_tasks: []."""
        self._make_plan(db_session, test_user)

        resp = client.post(
            "/api/v1/plan/checkin",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"completed_tasks": []},
        )

        assert resp.status_code == 200

    def test_checkin_without_active_plan_returns_404(
        self, client, auth_token, test_user
    ):
        resp = client.post(
            "/api/v1/plan/checkin",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"completed_tasks": []},
        )
        assert resp.status_code == 404
