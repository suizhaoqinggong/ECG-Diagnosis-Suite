import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.models.health import HealthJob, HealthAsset, HealthFinding

# Create a separate Base for health models to avoid FK issues with missing tables
Base = declarative_base()

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="module")
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(HealthJob.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(HealthJob.metadata.drop_all)


async def test_health_job_persistence():
    """Test that HealthJob can be saved and retrieved from database"""
    async with async_session() as session:
        # Create test job
        job = HealthJob(
            name="ECG Analysis Batch #123",
            status="pending",
            payload={"batch_id": "123", "source": "upload"},
            priority=1,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        # Verify it was saved
        assert job.id is not None
        assert job.name == "ECG Analysis Batch #123"
        assert job.status == "pending"
        assert job.payload["batch_id"] == "123"

        # Query it back
        retrieved = await session.get(HealthJob, job.id)
        assert retrieved is not None
        assert retrieved.name == job.name


async def test_health_asset_persistence():
    """Test that HealthAsset can be saved and retrieved with foreign key to HealthJob"""
    async with async_session() as session:
        # Create parent job
        job = HealthJob(
            name="ECG Analysis Batch #124",
            status="completed",
        )
        session.add(job)
        await session.commit()

        # Create asset linked to job
        asset = HealthAsset(
            job_id=job.id,
            asset_type="ecg_image",
            file_path="/data/uploads/ecg123.png",
            metadata={"patient_id": "P001", "age": 55},
            hash="sha256:abcdef123456",
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)

        assert asset.id is not None
        assert asset.job_id == job.id
        assert asset.asset_type == "ecg_image"
        assert asset.metadata["patient_id"] == "P001"

        # Verify relationship
        await session.refresh(job, ["assets"])
        assert len(job.assets) == 1
        assert job.assets[0].id == asset.id


async def test_health_finding_persistence():
    """Test that HealthFinding can be saved and retrieved with foreign keys"""
    async with async_session() as session:
        # Create parent job and asset
        job = HealthJob(name="ECG Analysis Batch #125", status="completed")
        session.add(job)
        await session.commit()

        asset = HealthAsset(
            job_id=job.id,
            asset_type="ecg_signal",
            file_path="/data/uploads/ecg124.dat",
        )
        session.add(asset)
        await session.commit()

        # Create finding
        finding = HealthFinding(
            job_id=job.id,
            asset_id=asset.id,
            finding_type="diagnosis",
            title="窦性心律",
            description="正常心电图表现",
            severity="normal",
            icd_code="I49.9",
            confidence=0.98,
            metadata={"lead": "II", "duration": 800},
        )
        session.add(finding)
        await session.commit()
        await session.refresh(finding)

        assert finding.id is not None
        assert finding.job_id == job.id
        assert finding.asset_id == asset.id
        assert finding.title == "窦性心律"
        assert finding.severity == "normal"
        assert finding.confidence == 0.98

        # Verify relationships
        await session.refresh(job, ["findings"])
        assert len(job.findings) == 1
        await session.refresh(asset, ["findings"])
        assert len(asset.findings) == 1
