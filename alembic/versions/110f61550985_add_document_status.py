"""add document status

Revision ID: 110f61550985
Revises: 
Create Date: 2026-08-28 18:33:41.555019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '110f61550985'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


document_status_enum = sa.Enum('processing', 'ready', 'failed', name='document_status')


def upgrade() -> None:
    """Upgrade schema."""
    # Postgres enum types aren't auto-created by add_column the way create_table
    # does it automatically — has to be created explicitly first.
    document_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'documents',
        sa.Column(
            'status',
            document_status_enum,
            nullable=False,
            server_default='ready',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'status')
    document_status_enum.drop(op.get_bind(), checkfirst=True)
