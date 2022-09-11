"""environment: Games project operating environment details."""
from pydantic import BaseSettings

MAJOR_VERSION = 1
COMPATIBILITY_VERSION = 0
VERSION = f"{MAJOR_VERSION}.{COMPATIBILITY_VERSION}"


class Settings(BaseSettings):
    """Configuration settings for the project.

    These environment variables are used to configure the project. Environment
    variables are first read from the project root level ".env.dev" file,
    then from the ".env" file, then from the system environment, overwriting
    previously supplied values if necessary.
    """

    postgres_host: str
    postgres_db: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    test_db: str = "test_db"
    in_mem_db: bool = False
    echo_db: bool = False

    class Config:
        """Configuration for the parent class."""

        extra = "forbid"
        env_file = ".env.dev", ".env"  # The latter file takes precedence
        env_file_encoding = "utf8"


settings = Settings()
