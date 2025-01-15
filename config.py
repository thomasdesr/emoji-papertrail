from pydantic import Field, RedisDsn, Secret, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EMOJI_PAPERTRAIL_")

    # host & port env vars determined by Google App Engine
    host: str = Field(default="127.0.0.1", validation_alias="HOST")
    port: int = Field(default=8080, validation_alias="PORT")

    request_id_http_header: str = "Fly-Request-Id"


class SlackAppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SLACK_APP_")

    # Which channel should it post updates to?
    channel: str = "#emoji-papertrail"

    # Controls if we post about new aliases being created
    should_report_alias_changes: bool = True

    redis_host: RedisDsn | None = None


class BotTokenConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOT_")

    token: str


class SlackOAuthConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OAUTH_")

    client_id: Secret[str]
    client_secret: Secret[str]

    bot_scopes: list[str] = Field(alias="_bot_scopes", default=["emoji:read", "chat:write"])
    user_scopes: list[str] = Field(
        alias="_user_scopes",
        default=["admin.teams:read", "emoji:read", "users:read"],
    )


def try_load_settings[T: BaseSettings](settings_class: type[T]) -> T | None:
    try:
        return settings_class()
    except ValidationError:
        return None


server_config: ServerConfig = ServerConfig()
app_config: SlackAppConfig = SlackAppConfig()
app_credentials = try_load_settings(BotTokenConfig) or try_load_settings(SlackOAuthConfig) or None

if __name__ == "__main__":
    print(server_config.model_dump_json(indent=4))  # noqa: T201
    print(app_config.model_dump_json(indent=4))  # noqa: T201
    print(app_credentials.model_dump() if app_credentials else None)  # noqa: T201
