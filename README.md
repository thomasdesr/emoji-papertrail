# Emoji Papertrail

A slackbot that was built to notify a channel whenever a new emoji is created. Like this:

![demo-of-slack-message](https://user-images.githubusercontent.com/681004/212451950-a9357dca-5caa-4559-8c29-9e6f9e47c2a4.png)

### Limitations

Currently this bot isn't able to tell you _which_ user created the emoji. Unfortunately Slack seems to think being able to make an API call and see who uploaded an Emoji is an enterprise only feature. The pieces are in place to support that if someone wants to send a PR to add support for both the regular workspace [`emoji.list`](https://api.slack.com/methods/emoji.list) as well as the Enterprise Tier-only [`admin.list.emoji`](https://api.slack.com/methods/admin.emoji.list) call.

# Deployment

## Bot itself

The bot is a normal FastAPI python application. It is intended to be run in Google App Engine, but can be run by anything capable of running a Python ASGI application.

On App engine, this mostly:
1. Clone the repository
2. Create an `app.env_variables.yaml` and populate the two Slack App Credentials as defined in the config and `app.yaml`.
3. Run `gcloud app deploy`

From there you can grab the application's URL and set it as your Slack App URL.

## Slack Connection

Slack supports "App Manifests" to make it easier to manage configuration of Slack Apps; here is an example one you can modify to suit your needs:
```yaml
display_information:
  name: Emoji Papertrail
  description: Friendly bot that monitors for new Emoji in our Slack
  background_color: "#323335"
  long_description: "Scribe responsible for monitoring for new Emoji in our slack.
    It gets notifications whenever a new emoji is created and shares the good
    news with #emoji-papertrail for all the rest of us to see."
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

Configuration is provided to the bot via environment variables.

### Required:

You must pass in the credentials used by this bot to interact with slack:

* `SLACK_BOT_TOKEN`
* `SLACK_SIGNING_SECRET`

### Optional

You can modify the behavior of the bot in the following ways:

#### HTTP Server
| Environment Variable | Description | Default Value |
| - | - | - |
| `HOST` | Host the Webhook listener will bind to. This are unnamespaced to meet App Engine's default behavior.  | `127.0.0.1` |
| `PORT` | Port the Webhook listener will bind to. This are unnamespaced to meet App Engine's default behavior. | `8080` |

#### Slack Bot

These will all be prefixed with `EMOJI_PAPERTRAIL_SLACK_APP`.
| Environment Variable | Description | Default Value |
| - | - | - |
| `EMOJI_PAPERTRAIL_SLACK_APP__CHANNEL` | Which channel should the bot post its updates to | `#emoji-papertrail` |
| `EMOJI_PAPERTRAIL_SLACK_APP__SHOULD_REPORT_ALIAS_CHANGES` | Should we post about alias updates. | `true` |
