from unittest.mock import patch, MagicMock

from app.gmail.client import send_email


@patch("app.gmail.client.build")
@patch("app.gmail.client.get_gmail_credentials")
def test_send_email(mock_credentials, mock_build):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    result = send_email(
        to="customer@example.com",
        subject="Payment reminder",
        body="Hello, this is a test.",
    )

    assert result is True
    mock_service.users().messages().send.assert_called_once()
