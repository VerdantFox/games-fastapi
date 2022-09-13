# Games-FastAPI

Example FastAPI application for CRUD operations of food games against a database.

## Blog posts that (will) use this application

- Build FastAPI postgres game API
- Test the API
- Handling app dependencies
- My top linting tools for a python app
- Deploy a FastAPI application to DigitalOcean with docker compose and nginx
- Run GitHub actions pipeline to lint and test a Postgres application
- Run GitLab-CI pipeline to lint and test a Postgres application
- Continuous deployment for FastAPI application in DigitalOcean
- SQLModel migrations
- FastAPI Authentication and permissions

## Environment

The app has utility scripts written in bash. You will need a shell environment to run those scripts. The standard terminal should work for Mac or Linux. For Windows, I recommend running the scripts in a [Git bash shell](https://www.atlassian.com/git/tutorials/git-bash) or similar.

The app is python. It was written for python 3.10, though it should work for python 3.9 as well. To get started, install python 3.10. Then create and activate a python 3.10 [virtual environment](https://docs.python.org/3/library/venv.html). With an activated python 3.10 virtual environment, pip install the project requirments.

```bash
pip install -r requirements.txt
```

## Running the app in development

To run the app in development, you'll need to have an activated python 3.10 virtual environment with the app requirements.txt files pip installed. See [environment](#environment) above for details. To run the app in development mode run `./utils/run-dev.sh` or simply `uvicorn api.app:app --reload`. Then open a web browser to `http://127.0.0.1:8000` or `localhost:8000`.

## Running static checkers

Games-FastAPI app files are statically checked for style, bugs, and common security flaws with the `pre-commit` package. You can run those static checkers with `./utils/pre-commit.sh` or by running `pre-commit install` followed by `pre-commit run --all-files`.

## CI/CD

CI is handled by github actions. Actions run on commits to the `main` branch. The job steps for these actions can be found at `.github/workflows/run-full-ci.yml`. They include running the `pre-commit` static checkers and `pytest`s. If those steps pass, the `main` branched is rebased onto the `release-branch`. A crontab job runs every 5 minutes on the host machine scanning for changes to the release branch. If a change exists, the host will run `utils/deploy.sh` to deploy the code changes. The script deploys changes by updating the local `release-branch` and running `docker compose` commands to update and restart the docker containers that run the `fastapi` app and `nginx`. The `utils/deploy.sh` script can also be run manually from the host server to (re-)deploy at any time.

## App description

The app is very rudimentary at this point. There are 2 endpoints. All endpoint details are describe in detailed swagger documentation by the `/docs` endpoint.
