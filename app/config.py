from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://autograder:autograder_dev@localhost:5432/autograder"
    secret_key: str = "change-me-in-production"
    debug: bool = True

    # LTI 1.3 config — blank means dev-mode bypass is active
    lti_issuer: str = ""
    lti_client_id: str = ""
    lti_deployment_id: str = ""
    lti_jwks_url: str = ""
    lti_oidc_auth_url: str = ""

    # AGS grade passback
    # dry_run records what would post without calling Canvas (dev default);
    # live requires lti_token_url, lti_client_id, and lti_tool_private_key.
    ags_mode: str = "dry_run"  # live | dry_run | disabled
    lti_token_url: str = ""
    lti_tool_private_key: str = ""  # PEM, RS256

    @property
    def lti_configured(self) -> bool:
        return bool(self.lti_issuer and self.lti_client_id)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
