"""Every link to a person's data has an index, so deleting a row (or an account, which
cascades through every table) never scans a whole table to find what points at it."""

from sqlalchemy import PrimaryKeyConstraint, Table, UniqueConstraint

from app.models import Base
from app.services import export


def _leading_columns(table: Table) -> set[str]:
    firsts = {list(index.columns)[0].name for index in table.indexes if index.columns}
    # A foreign key constraint isn't an index; only these come with one.
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint | PrimaryKeyConstraint):
            columns = list(constraint.columns)
            if columns:
                firsts.add(columns[0].name)
    return firsts


def test_every_link_to_a_persons_data_is_indexed() -> None:
    """Shared reference tables (such as the 66 archetypes) are left out: they're small, and
    nothing a person deletes is ever linked from them."""
    persons = {entry.table.name for entry in export.owned_tables()} | {"users"}
    missing = [
        f"{table.name}.{fk.parent.name} -> {fk.column.table.name}"
        for table in Base.metadata.sorted_tables
        if table.name not in export.SHARED
        for fk in table.foreign_keys
        if fk.column.table.name in persons and fk.parent.name not in _leading_columns(table)
    ]

    assert missing == []
