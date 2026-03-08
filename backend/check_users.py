import database, models
db = database.SessionLocal()
users = db.query(models.User).all()
print(f"Users in DB: {[u.email for u in users]}")
db.close()
