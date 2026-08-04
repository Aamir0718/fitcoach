"""Add analytics models for nutrition logs, streaks, personal records, and activity logs.

Revision ID: 006
Revises: 005
Create Date: 2026-08-03

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add new columns to workouts table
    op.add_column('workouts', sa.Column('total_sets', sa.Integer(), nullable=True))
    op.add_column('workouts', sa.Column('total_reps', sa.Integer(), nullable=True))
    op.add_column('workouts', sa.Column('calories_estimate', sa.Float(), nullable=True))
    op.add_column('workouts', sa.Column('completion_percentage', sa.Float(), nullable=True))
    
    # Create nutrition_logs table
    op.create_table(
        'nutrition_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('meal_name', sa.String(length=200), nullable=True),
        sa.Column('calories', sa.Float(), nullable=True),
        sa.Column('protein', sa.Float(), nullable=True),
        sa.Column('carbs', sa.Float(), nullable=True),
        sa.Column('fats', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_nutrition_logs_user_date', 'nutrition_logs', ['user_id', 'date'])
    
    # Create streaks table
    op.create_table(
        'streaks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('current_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('longest_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_workout_date', sa.Date(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('idx_streaks_user', 'streaks', ['user_id'])
    
    # Create personal_records table
    op.create_table(
        'personal_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('exercise_name', sa.String(length=200), nullable=False),
        sa.Column('best_weight_kg', sa.Float(), nullable=True),
        sa.Column('best_reps', sa.Integer(), nullable=True),
        sa.Column('best_weight_date', sa.Date(), nullable=True),
        sa.Column('best_reps_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pr_user_exercise', 'personal_records', ['user_id', 'exercise_name'])
    
    # Create activity_logs table
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.String(length=20), nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_activity_logs_user_date', 'activity_logs', ['user_id', 'date'])


def downgrade():
    # Drop new tables
    op.drop_index('idx_activity_logs_user_date', 'activity_logs')
    op.drop_table('activity_logs')
    
    op.drop_index('idx_pr_user_exercise', 'personal_records')
    op.drop_table('personal_records')
    
    op.drop_index('idx_streaks_user', 'streaks')
    op.drop_table('streaks')
    
    op.drop_index('idx_nutrition_logs_user_date', 'nutrition_logs')
    op.drop_table('nutrition_logs')
    
    # Drop new columns from workouts table
    op.drop_column('workouts', 'completion_percentage')
    op.drop_column('workouts', 'calories_estimate')
    op.drop_column('workouts', 'total_reps')
    op.drop_column('workouts', 'total_sets')
