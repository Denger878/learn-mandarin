from db import repo
from ingest.loader import ingest_file

conn = repo.connect()
repo.init_db(conn)
print(ingest_file(conn, "cratch/sample.txt"))