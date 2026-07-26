import app.database  # noqa: F401
from app.models import Base


EXPECTED = {
    "users": {"ix_users_last_activity"},
    "chat_groups": {"ix_chat_groups_report_due"},
    "group_members": {"ix_group_members_user_seen", "ix_group_members_chat_xp"},
    "engagement_notifications": {"ix_engagement_notifications_status_claimed"},
    "vip_invoice_intents": {"ix_vip_invoice_status_created"},
}


def test_production_indexes_exist_in_model_metadata() -> None:
    for table_name, expected_names in EXPECTED.items():
        table = Base.metadata.tables[table_name]
        names = {index.name for index in table.indexes}
        assert expected_names <= names
        assert None not in names
