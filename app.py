import sqlite3
from flask import Flask, jsonify, request, render_template

# i've decided to create an application for managing books inventory, as i am currently in need of one at home
# the app gives the ability to store the books with their titles, authors, etc. and most importantly
# the shelf number that it resides on
# the id-s autoincrement with each new addition


app = Flask(__name__)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/books/insert')
def displayInsert():
    return render_template('insert.html')


@app.route('/books/delete')
def displayDelete():
    return render_template('delete.html')


@app.route('/books/update')
def displayUpdate():
    return render_template('update.html')


def get_db_connection():
    conn = sqlite3.connect('BooksInventory.db')
    conn.row_factory = sqlite3.Row
    return conn


def insert_initial_books():
    books_to_insert = [('დიდგორის ცაზე ფრენდა ის ჯვარი', 'გოჩა მანველიძე', 'ისტორიული რომანი', 1, 2010, 'ქართული'),
                       ('ალქიმიკოსი', 'პაულო კოელიო', 'ფენტეზი, სათავგადასავლო', 3, 2016, 'ქართული')]

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, author TEXT, genre TEXT, shelf INT, 
    production_year INT, language TEXT)''')

    # checking if the table is empty before inserting
    cursor.execute("SELECT COUNT(*) FROM books")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.executemany('''
                            INSERT INTO books(title, author, genre, shelf, production_year, language)
                            VALUES (?,?,?,?,?,?)
                            ''', books_to_insert)
        connection.commit()
    connection.close()


@app.route('/books/insert', methods=['POST'])
def insert():
    # data = request.get_json()

    shelf = request.form['shelf']
    prod_year = request.form['prod_year']

    if shelf is not None:
        if len(shelf.strip()) == 0:
            shelf = 0
        else:
            shelf = int(shelf)
    if prod_year is not None:
        if len(prod_year.strip()) == 0:
            prod_year = 0
        else:
            prod_year = int(prod_year)

    data = {
        "title": request.form['title'],
        "author": request.form['author'],
        "genre": request.form['genre'],
        "shelf": shelf,
        "production_year": prod_year,
        "language": request.form['language']
    }

    # checking if the request contains at least one of the required fields
    required_fields = ['title', 'author', 'genre', 'shelf', 'production_year', 'language']
    if not any(field in data for field in required_fields):
        return jsonify({"error": "At least one of the required fields is missing"}), 400

    # validating data types
    if 'shelf' in data and not isinstance(data['shelf'], int):
        return jsonify({"error": "Invalid data type for shelf"}), 400
    if 'production_year' in data and not isinstance(data['production_year'], int):
        return jsonify({"error": "Invalid data type for production_year"}), 400

    # checking if the production year is positive
    if 'production_year' in data and data['production_year'] < 0:
        return jsonify({"error": "Production year must be a positive integer"}), 400

    # checking if the inputed book already exists and asking if they want to add it again
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM books WHERE title=? AND author=? AND language=? AND production_year=?",
                   (data.get('title'), data.get('author'), data.get('language'), data.get('production_year')))
    existing_book = cursor.fetchone()
    connection.close()

    if existing_book:
        confirmation_required = request.json.get('confirmation', '').lower()
        if confirmation_required != 'yes':
            return jsonify({"error": "Book already exists in the database. Please confirm to proceed."}), 400

    # otherwise casually adding the new book to the db
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''INSERT INTO books(title, author, genre, shelf, production_year, language)
                      VALUES (?, ?, ?, ?, ?, ?)''',
                   (data.get('title'), data.get('author'), data.get('genre'), data.get('shelf'),
                    data.get('production_year'), data.get('language')))
    connection.commit()
    connection.close()

    return jsonify({"message": "Book inserted successfully"}), 201


@app.route('/books/getBooks', methods=['GET'])
def getBooks():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    connection.close()

    books_dicts = [dict(book) for book in books]

    return jsonify(books_dicts)


@app.route('/books/getBook/<int:id>', methods=['GET'])
def getBook(id):
    # if the id is not inputed
    if not id:
        return jsonify({"error": "id is required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM books WHERE id=?", (id,))
    book = cursor.fetchone()
    connection.close()

    # checking if the book with the given id exists
    if book is None:
        return jsonify({"error": "Book not found"}), 404

    return jsonify(dict(book))


@app.route('/books/update>', methods=['PUT', 'POST'])
def update():
    id = int(request.form['id'])
    key_to_update = request.form['key_to_update']
    new_value = request.form['new']
    connection = get_db_connection()
    cursor = connection.cursor()

    # checks for the valid inputs
    if not id:
        return jsonify({"error": "ID to update is required"}), 400
    if not key_to_update:
        return jsonify({"error": "Key to update is required"}), 400
    if key_to_update not in ['title', 'author', 'genre', 'shelf', 'production_year', 'language', 'id']:
        return jsonify({"error": "Invalid key to update"}), 400
    if new_value is None:
        return jsonify({"error": f"New value for key '{key_to_update}' is required"}), 400

    # checking if the given key is id and if so, checking if the inputed id value already exists in the db or not
    if key_to_update == 'id':
        cursor.execute("SELECT * FROM books WHERE id=?", (new_value,))
        exists = cursor.fetchone()
        if exists:
            return jsonify({"error": "id already exists, choose a different one"})

    # check for if the book with the given id exists, if not, add the new book
    cursor.execute("SELECT id FROM books WHERE id=?", (id,))
    existing_id = cursor.fetchone()
    if not existing_id:
        cursor.execute(f"INSERT INTO books(id, {key_to_update}) VALUES (?,?)", (id, new_value,))
        connection.commit()
        connection.close()
        return jsonify({"message": "book added successfully, please fill in the missing values later manually"}), 200

    # otherwise casually update a book with the given parameters
    cursor.execute(f'''UPDATE books
                        SET {key_to_update}=?
                        WHERE id=?''',
                   (new_value, id))
    connection.commit()
    connection.close()

    return jsonify({"message": f"Book {key_to_update} updated successfully"}), 200


@app.route('/books/delete/<int:id>', methods=['DELETE'])
def deleteBook(id):

    # check if the id is provided, if not, return an error
    if not id:
        return jsonify({"error": "id is required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    # checking if the book exists or not, if not, return an error
    cursor.execute("SELECT * FROM books WHERE id=?", (id,))
    book = cursor.fetchone()
    if book is None:
        connection.close()
        return jsonify({"error": "Book not found"}), 404

    # if everything is fine, casually delete the book with the given parameters
    cursor.execute("DELETE FROM books WHERE id=?", (id,))
    connection.commit()
    connection.close()
    return jsonify({"message": "Book deleted successfully"}), 201


if __name__ == '__main__':
    insert_initial_books()
    app.run(debug=True)
