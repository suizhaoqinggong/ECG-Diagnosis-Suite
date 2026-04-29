from app.models.health import HealthJob, HealthAsset, HealthFinding


def test_health_models_expose_expected_tablenames():
    assert HealthJob.__tablename__ == "health_jobs"
    assert HealthAsset.__tablename__ == "health_assets"
    assert HealthFinding.__tablename__ == "health_findings"


def test_health_job_columns():
    columns = {c.name for c in HealthJob.__table__.columns}
    assert "id" in columns
    assert "user_id" in columns
    assert "session_id" in columns
    assert "status" in columns
    assert "message" in columns
    assert "error_detail" in columns
    assert "result_payload" in columns


def test_health_asset_columns():
    columns = {c.name for c in HealthAsset.__table__.columns}
    assert "id" in columns
    assert "job_id" in columns
    assert "kind" in columns
    assert "filename" in columns
    assert "stored_path" in columns


def test_health_finding_columns():
    columns = {c.name for c in HealthFinding.__table__.columns}
    assert "id" in columns
    assert "job_id" in columns
    assert "source_type" in columns
    assert "title" in columns
    assert "severity" in columns
    assert "action_hint" in columns
    assert "payload" in columns
