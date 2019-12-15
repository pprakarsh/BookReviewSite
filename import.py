import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    if not f:
        print("File could not bee opened")
        return
    reader = csv.reader(f)
    if not reader:
        print("cannot read csv file")
        return
    count = 0
    for isbn, title, author, year in reader:
        if count == 0:
            count = 1
            continue
        year_int = int(year)
        db.execute("INSERT INTO  book(isbn, title, author, year ) VALUES (:isbn, :title, :author, :year)",
                {"isbn": isbn, "title": title, "author": author, "year": year_int})
        print(f"inserted {isbn}, {title}, {author}, {year_int}")
    db.commit()                                                                
#        print(f"year: {year}")
#        break

if __name__ == "__main__":
    main()
