from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SlackAppConfig(BaseSettings):
    # Which channel should it post updates to?
    channel: str = "#emoji-papertrail"

    # Controls if we post about new aliases being created
    should_report_alias_changes: bool = True
    model_config = SettingsConfigDict(env_prefix="SLACK_APP_")


class Config(BaseSettings):
    # host & port env vars determined by Google App Engine
    host: str = Field("127.0.0.1", validation_alias="HOST")
    port: int = Field(8080, validation_alias="PORT")

    slack_app: SlackAppConfig = SlackAppConfig()
    model_config = SettingsConfigDict(env_prefix="EMOJI_PAPERTRAIL_", env_nested_delimiter="__")


config: Config = Config()  # type: ignore[reportGeneralTypeIssues]

if __name__ == "__main__":
    print(config.json(indent=4))
