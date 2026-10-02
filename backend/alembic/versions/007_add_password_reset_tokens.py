"""Add password_reset_tokens table.

Closes an account-takeover hole: reset-password previously accepted any
string as reset_token and never checked it. This table lets verify-otp
(purpose=reset) issue a real single-use, expiring, hashed token that
reset-password now validates.

Revision ID: 007
Revises: 006
Create Date: 2026-08-09

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index('idx_reset_tokens_email', 'password_reset_tokens', ['email'])
    op.create_index(op.f('ix_password_reset_tokens_token_hash'), 'password_reset_tokens', ['token_hash'])


def downgrade():
    op.drop_index(op.f('ix_password_reset_tokens_token_hash'), 'password_reset_tokens')
    op.drop_index('idx_reset_tokens_email', 'password_reset_tokens')
    op.drop_table('password_reset_tokens')
