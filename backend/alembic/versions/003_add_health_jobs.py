"""Add health jobs, assets, and findings tables

Revision ID: 003_add_health_jobs
Revises: 002_initial_tables
Create Date: 2026-04-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_health_jobs'
down_revision = '002_add_chat_message_title'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create health_jobs table
    op.create_table(
        'health_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('failed', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_health_jobs_id'), 'health_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_health_jobs_name'), 'health_jobs', ['name'], unique=False)
    op.create_index(op.f('ix_health_jobs_status'), 'health_jobs', ['status'], unique=False)

    # Create health_assets table
    op.create_table(
        'health_assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('asset_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('hash', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['health_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_health_assets_asset_type'), 'health_assets', ['asset_type'], unique=False)
    op.create_index(op.f('ix_health_assets_hash'), 'health_assets', ['hash'], unique=False)
    op.create_index(op.f('ix_health_assets_id'), 'health_assets', ['id'], unique=False)
    op.create_index(op.f('ix_health_assets_job_id'), 'health_assets', ['job_id'], unique=False)

    # Create health_findings table
    op.create_table(
        'health_findings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('finding_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('icd_code', sa.String(length=50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['health_assets.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['health_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_health_findings_asset_id'), 'health_findings', ['asset_id'], unique=False)
    op.create_index(op.f('ix_health_findings_finding_type'), 'health_findings', ['finding_type'], unique=False)
    op.create_index(op.f('ix_health_findings_id'), 'health_findings', ['id'], unique=False)
    op.create_index(op.f('ix_health_findings_icd_code'), 'health_findings', ['icd_code'], unique=False)
    op.create_index(op.f('ix_health_findings_job_id'), 'health_findings', ['job_id'], unique=False)
    op.create_index(op.f('ix_health_findings_severity'), 'health_findings', ['severity'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_health_findings_severity'), table_name='health_findings')
    op.drop_index(op.f('ix_health_findings_job_id'), table_name='health_findings')
    op.drop_index(op.f('ix_health_findings_icd_code'), table_name='health_findings')
    op.drop_index(op.f('ix_health_findings_id'), table_name='health_findings')
    op.drop_index(op.f('ix_health_findings_finding_type'), table_name='health_findings')
    op.drop_index(op.f('ix_health_findings_asset_id'), table_name='health_findings')
    op.drop_table('health_findings')

    op.drop_index(op.f('ix_health_assets_job_id'), table_name='health_assets')
    op.drop_index(op.f('ix_health_assets_id'), table_name='health_assets')
    op.drop_index(op.f('ix_health_assets_hash'), table_name='health_assets')
    op.drop_index(op.f('ix_health_assets_asset_type'), table_name='health_assets')
    op.drop_table('health_assets')

    op.drop_index(op.f('ix_health_jobs_status'), table_name='health_jobs')
    op.drop_index(op.f('ix_health_jobs_name'), table_name='health_jobs')
    op.drop_index(op.f('ix_health_jobs_id'), table_name='health_jobs')
    op.drop_table('health_jobs')
