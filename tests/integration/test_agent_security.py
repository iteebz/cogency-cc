from unittest.mock import MagicMock, patch

from cc.agent import create_agent


@patch("cc.agent.GLM")
@patch("cc.agent.Config")
def test_security_configuration(mock_config_class, mock_glm):
    from cogency.core.config import Security

    mock_config = MagicMock()
    mock_config.provider = "glm"
    mock_config.identity = "code"
    mock_config.get_api_key.return_value = "test-key"
    mock_config_class.return_value = mock_config
    mock_glm.return_value = MagicMock()

    with patch("cc.cc_md.load", return_value=None):
        with patch("cc.agent.Agent") as mock_agent_class:
            create_agent(mock_config)

            call_args = mock_agent_class.call_args
            security = call_args.kwargs["security"]
            assert isinstance(security, Security)
            assert security.access == "project"
