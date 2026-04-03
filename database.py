# database.py
import sqlite3
import json

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('quizzes.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS quizzes (id INTEGER PRIMARY KEY AUTOINCREMENT, materia TEXT NOT NULL, nombre TEXT NOT NULL, codigo TEXT UNIQUE, preguntas TEXT NOT NULL, inicio TEXT NOT NULL, fin TEXT NOT NULL, activo INTEGER DEFAULT 0, creado_en TEXT DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS respuestas (id INTEGER PRIMARY KEY AUTOINCREMENT, quiz_id INTEGER NOT NULL, user_id INTEGER NOT NULL, username TEXT, respuestas TEXT, puntaje INTEGER, fecha_respuesta TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(quiz_id, user_id))')
        self.conn.commit()
    
    def save_quiz(self, materia, nombre, preguntas, inicio, fin, codigo):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO quizzes (materia, nombre, codigo, preguntas, inicio, fin) VALUES (?, ?, ?, ?, ?, ?)', (materia, nombre, codigo, json.dumps(preguntas), inicio, fin))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_quiz(self, quiz_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM quizzes WHERE id = ?', (quiz_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_quiz_by_code(self, codigo):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM quizzes WHERE codigo = ?', (codigo,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_all_quizzes(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM quizzes ORDER BY id DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def update_quiz_status(self, quiz_id, activo):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE quizzes SET activo = ? WHERE id = ?', (1 if activo else 0, quiz_id))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def user_already_responded(self, quiz_id, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM respuestas WHERE quiz_id = ? AND user_id = ?', (quiz_id, user_id))
        return cursor.fetchone() is not None
    
    def save_response(self, quiz_id, user_id, username, respuestas, puntaje):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO respuestas (quiz_id, user_id, username, respuestas, puntaje) VALUES (?, ?, ?, ?, ?)', (quiz_id, user_id, username, json.dumps(respuestas), puntaje))
        self.conn.commit()
    
    def close(self):
        self.conn.close()