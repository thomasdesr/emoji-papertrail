import os

import uvicorn
import yaml

if __name__ == "__main__":
    with open("./app.env_variables.yaml") as f:
        env_variables = yaml.safe_load(f)["env_variables"]

    for key, value in env_variables.items():
        os.environ[key] = value

    from config import config
    from main import app

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
    )
