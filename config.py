from datetime import timedelta

from pydantic import Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class SlackAppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SLACK_APP_")

    # Which channel should it post updates to?
    channel: str = "#emoji-papertrail"

    # Controls if we post about new aliases being created
    should_report_alias_changes: bool = True

    # If we recieve seemingly duplicate webhooks within this interval, do not post about it.
    duplicate_emoji_webhook_debounce_interval: timedelta = timedelta(seconds=5)

    redis_host: RedisDsn | None = None


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EMOJI_PAPERTRAIL_", env_nested_delimiter="__"
    )

    # host & port env vars determined by Google App Engine
    host: str = Field("127.0.0.1", validation_alias="HOST")
    port: int = Field(8080, validation_alias="PORT")

    slack_app: SlackAppConfig = SlackAppConfig()


config: Config = Config()  # type: ignore[reportGeneralTypeIssues]

if __name__ == "__main__":
    print(config.json(indent=4))
