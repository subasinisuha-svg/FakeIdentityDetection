import sqlite3


def create_database():
    connection = sqlite3.connect("documents.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            id_number TEXT,
            status TEXT
        )
    """)

    # Check whether risk_score column already exists
    cursor.execute("PRAGMA table_info(documents)")
    columns = [column[1] for column in cursor.fetchall()]

    # Add the column without deleting existing records
    if "risk_score" not in columns:
        cursor.execute("""
            ALTER TABLE documents
            ADD COLUMN risk_score INTEGER DEFAULT 0
        """)

    connection.commit()
    connection.close()


def save_document(name, id_number, status, risk_score=0):
    connection = sqlite3.connect("documents.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO documents
        (name, id_number, status, risk_score)
        VALUES (?, ?, ?, ?)
        """,
        (name, id_number, status, risk_score)
    )

    connection.commit()
    connection.close()

    print("Document details saved successfully!")


def get_all_documents():
    connection = sqlite3.connect("documents.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM documents ORDER BY id DESC"
    )

    records = cursor.fetchall()
    connection.close()

    return records


def search_documents(search_term):
    connection = sqlite3.connect("documents.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM documents
        WHERE name LIKE ? OR id_number LIKE ?
        ORDER BY id DESC
    """, (f"%{search_term}%", f"%{search_term}%"))

    records = cursor.fetchall()
    connection.close()

    return records


def check_duplicate_id(id_number):
    connection = sqlite3.connect("documents.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM documents WHERE id_number = ?",
        (id_number,)
    )

    count = cursor.fetchone()[0]
    connection.close()

    return count > 0


def view_documents():
    connection = sqlite3.connect("documents.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM documents ORDER BY id DESC"
    )

    records = cursor.fetchall()

    for record in records:
        print(record)

    connection.close()


if __name__ == "__main__":
    create_database()
    view_documents()