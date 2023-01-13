import os

import uvicorn
import yaml

if __name__ == "__main__":
    with open("./app.env_variables.yaml") as f:
        env_variables = yaml.safe_load(f)["env_variables"]

    for key, value in env_variables.items():
        os.environ[key] = value

    from main import app

    uvicorn.run(
        app,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 8080)),
    )
