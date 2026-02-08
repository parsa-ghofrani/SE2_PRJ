from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0463ce9bda97"
down_revision = "cbd5b9fc2c8f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add column as nullable first to avoid issues with existing rows
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))

    # Backfill existing users with a non-empty placeholder
    op.execute("UPDATE users SET password_hash = 'DISABLED' WHERE password_hash IS NULL")

    # Then enforce NOT NULL
    op.alter_column("users", "password_hash", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "password_hash")
