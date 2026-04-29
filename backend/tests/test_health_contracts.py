from app.models.enums import MessageType


def test_health_report_message_type_is_registered():
    assert MessageType.HEALTH_REPORT == "health_report"
