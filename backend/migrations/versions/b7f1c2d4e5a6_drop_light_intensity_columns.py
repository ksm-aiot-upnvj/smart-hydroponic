"""drop light_intensity columns from hydroponic_data

Revision ID: b7f1c2d4e5a6
Revises: 1a2b3c4d5e6f
Create Date: 2026-11-11 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7f1c2d4e5a6"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the never-populated light-intensity columns.

    No firmware sketch sends these fields and they are absent from every
    Pydantic schema, so they would always remain at their default of 0
    (audit finding AB-02). The generated ``light_intensity_avg`` column is
    dropped first because it depends on the two base columns.
    """
    op.drop_column("hydroponic_data", "light_intensity_avg")
    op.drop_column("hydroponic_data", "light_intensity_atas")
    op.drop_column("hydroponic_data", "light_intensity_bawah")


def downgrade() -> None:
    """Re-create the columns (empty)."""
    op.add_column(
        "hydroponic_data",
        sa.Column(
            "light_intensity_atas", sa.Integer(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "hydroponic_data",
        sa.Column(
            "light_intensity_bawah", sa.Integer(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "hydroponic_data",
        sa.Column(
            "light_intensity_avg",
            sa.DOUBLE_PRECISION(precision=53),
            sa.Computed(
                "((light_intensity_atas + light_intensity_bawah) / 2.0)",
                persisted=True,
            ),
        ),
    )
