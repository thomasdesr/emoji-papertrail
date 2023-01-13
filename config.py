from pydantic import BaseSettings, Field


class SlackAppConfig(BaseSettings):
    # Which channel should it post updates to?
    channel: str = "#emoji-papertrail"

    # Controls if we post about new aliases being created
    should_report_alias_changes: bool = True

    class Config:
        env_prefix = "SLACK_APP_"


class Config(BaseSettings):
    # host & port env vars determined by Google App Engine
    host: str = Field("127.0.0.1", env="HOST")
    port: int = Field(8080, env="PORT")

    slack_app: SlackAppConfig = SlackAppConfig()

    class Config:
        env_prefix = "EMOJI_PAPERTRAIL_"
        env_nested_delimiter = "__"


config: Config = Config()  # type: ignore[reportGeneralTypeIssues]

if __name__ == "__main__":
    print(config.json(indent=4))
