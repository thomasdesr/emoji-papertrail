# Emoji Papertrail

A Slackbot that notifies a channel whenever a new emoji is created. Like this:

![demo-of-slack-message](https://user-images.githubusercontent.com/681004/212451950-a9357dca-5caa-4559-8c29-9e6f9e47c2a4.png)

## Deployment

### Bot Deployment

The bot is a FastAPI Python application that can be deployed on platforms like Fly.io or Google App Engine, or any environment capable of running a Python ASGI application.

On Google App Engine:

1. Clone the repository.
2. Create an `app.env_variables.yaml` file and populate the required Slack App credentials as defined in `config.py` and `app.yaml`.
3. Run:
   ```sh
   gcloud app deploy
   ```

Once deployed, retrieve the application's URL and set it as your Slack App request URL.

### Slack Connection

Slack supports "App Manifests" to manage Slack App configurations. Below is an example manifest you can modify:

```yaml
display_information:
  name: Emoji Papertrail
  description: Friendly neighborhood spider bot that monitors for new Emoji in our Slack
  background_color: "#323335"
  long_description: "Scribe responsible for monitoring for new Emoji in our Slack. It gets notifications whenever a new emoji is created and shares the good news with #emoji-papertrail for all the rest of us to see."
features:
  bot_user:
    display_name: Emoji Papertrail
    always_online: false
oauth_config:
  scopes:
    user:
      - users:read
    bot:
      - emoji:read
      - chat:write
settings:
  event_subscriptions:
    request_url: <your bot's HTTPS server endpoint>
    bot_events:
      - emoji_changed
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
```

## Configuration

Configuration is provided via environment variables. Below is a breakdown of required and optional settings.

### Required Environment Variables

These credentials are needed for the bot to interact with non-enterprise Slacks:

- `SLACK_BOT_TOKEN`
- `SLACK_SIGNING_SECRET`

### Optional Configuration

You can customize the bot’s behavior using these variables:

#### HTTP Server Configuration

| Environment Variable | Description                                                           | Default Value |
| -------------------- | --------------------------------------------------------------------- | ------------- |
| `HOST`               | Host for the webhook listener. Matches App Engine's default behavior. | `127.0.0.1`   |
| `PORT`               | Port for the webhook listener. Matches App Engine's default behavior. | `8080`        |

#### Slack Bot Configuration

| Environment Variable                    | Description                                      | Default Value       |
| --------------------------------------- | ------------------------------------------------ | ------------------- |
| `SLACK_APP_CHANNEL`                     | Channel where the bot posts updates              | `#emoji-papertrail` |
| `SLACK_APP_SHOULD_REPORT_ALIAS_CHANGES` | Whether to report alias updates (`true`/`false`) | `true`              |

#### Redis Configuration (Optional)

Emoji Papertrail uses Redis for two primary purposes:

- To prevent duplicate notifications when Slack sends multiple events for the same emoji addition
- To store OAuth handshake access and refresh tokens when used with an Enterprise Slack Workspace

| Environment Variable   | Description          | Default Value |
| ---------------------- | -------------------- | ------------- |
| `SLACK_APP_REDIS_HOST` | Redis Connection URL | `None`        |

#### Slack OAuth Configuration

If you're connecting this to an Enterprise Slack Workspace to view which user imported an emoji, set the following:

| Environment Variable  | Description                                       | Default Value                                      |
| --------------------- | ------------------------------------------------- | -------------------------------------------------- |
| `OAUTH_CLIENT_ID`     | Slack OAuth Client ID                             | `None`                                             |
| `OAUTH_CLIENT_SECRET` | Slack OAuth Client Secret                         | `None`                                             |
| `OAUTH_BOT_SCOPES`    | Permissions the bot asks for (usually not needed) | `["emoji:read", "chat:write"]`                     |
| `OAUTH_USER_SCOPES`   | Permissions for user tokens (usually not needed)  | `["admin.teams:read", "emoji:read", "users:read"]` |

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
