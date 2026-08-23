from app.database import Base, engine
import app.models  # noqa: F401  registers User on Base before create_all runs

Base.metadata.create_all(engine)
print("Tables created.")
