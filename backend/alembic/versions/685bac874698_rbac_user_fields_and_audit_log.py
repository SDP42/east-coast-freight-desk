"""rbac user fields and audit log

Revision ID: 685bac874698
Revises: 04f1988023bf
Create Date: 2026-09-19 10:19:23.488958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '685bac874698'
down_revision: Union[str, Sequence[str], None] = '04f1988023bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=30), nullable=True),
        sa.Column('action', sa.String(length=40), nullable=False),
        sa.Column('detail', sa.Text(), nullable=False),
        sa.Column('allowed', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_log_action'), 'audit_log', ['action'], unique=False)
    op.create_index(op.f('ix_audit_log_created_at'), 'audit_log', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_log_user_id'), 'audit_log', ['user_id'], unique=False)
    op.add_column('users', sa.Column('persona', sa.String(length=30), nullable=True))
    op.add_column('users', sa.Column('assigned_ports', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))
    # Accounts created before RBAC stored their persona in `role`; keep that as the persona and start them as viewers.
    op.execute("UPDATE users SET persona = role WHERE role <> 'admin'")
    op.execute("UPDATE users SET role = 'viewer' WHERE role <> 'admin'")


def downgrade() -> None:
    op.drop_column('users', 'is_demo')
    op.drop_column('users', 'assigned_ports')
    op.drop_column('users', 'persona')
    op.drop_index(op.f('ix_audit_log_user_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_created_at'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_action'), table_name='audit_log')
    op.drop_table('audit_log')
