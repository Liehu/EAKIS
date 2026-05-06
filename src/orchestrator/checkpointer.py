class PostgresCheckpointer:
    def __init__(self, db_url: str) -> None:
        self.db_url = db_url
        # TODO: initialize connection pool
