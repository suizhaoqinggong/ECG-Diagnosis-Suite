import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.health import HealthJob, HealthAsset, HealthFinding
from app.models.db_models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_health_job_persistence():
    """Test that HealthJob can be saved and retrieved from database"""
    async with async_session() as session:
        job = HealthJob(
            id="job-test-001",
            user_id=None,
            session_id=None,
            status="queued",
            message="Queued",
            result_payload={"batch_id": "123"},
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        assert job.id == "job-test-001"
        assert job.status == "queued"
        assert job.message == "Queued"
        assert job.result_payload["batch_id"] == "123"

        retrieved = await session.get(HealthJob, "job-test-001")
        assert retrieved is not None
        assert retrieved.status == job.status


async def test_health_asset_persistence():
    """Test that HealthAsset can be saved and retrieved with foreign key to HealthJob"""
    async with async_session() as session:
        job = HealthJob(
            id="job-test-002",
            status="completed",
            message="Completed",
        )
        session.add(job)
        await session.commit()

        asset = HealthAsset(
            id="asset-test-001",
            job_id="job-test-002",
            kind="ecg_signal",
            filename="record.dat",
            stored_path="/data/uploads/health/job-test-002/record.dat",
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)

        assert asset.id == "asset-test-001"
        assert asset.job_id == "job-test-002"
        assert asset.kind == "ecg_signal"
        assert asset.filename == "record.dat"

        await session.refresh(job, ["assets"])
        assert len(job.assets) == 1
        assert job.assets[0].id == asset.id


async def test_health_finding_persistence():
    """Test that HealthFinding can be saved and retrieved with foreign keys"""
    async with async_session() as session:
        job = HealthJob(id="job-test-003", status="completed", message="Completed")
        session.add(job)
        await session.commit()

        finding = HealthFinding(
            id="finding-test-001",
            job_id="job-test-003",
            source_type="lab",
            title="LDL 偏高",
            severity="medium",
            action_hint="recheck",
            payload={"value": 4.9, "unit": "mmol/L"},
        )
        session.add(finding)
        await session.commit()
        await session.refresh(finding)

        assert finding.id == "finding-test-001"
        assert finding.job_id == "job-test-003"
        assert finding.source_type == "lab"
        assert finding.title == "LDL 偏高"
        assert finding.severity == "medium"
        assert finding.action_hint == "recheck"
        assert finding.payload["value"] == 4.9

        await session.refresh(job, ["findings"])
        assert len(job.findings) == 1
        assert job.findings[0].id == finding.id
