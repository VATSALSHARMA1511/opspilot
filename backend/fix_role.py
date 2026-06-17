from sqlalchemy import create_engine, text
import os

engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    conn.execute(text("UPDATE users SET role='admin' WHERE email='Vats@admin.com'"))
    conn.commit()
print('Done')