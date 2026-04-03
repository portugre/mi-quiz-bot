# database.py
import sqlite3
import json
import os

class Database:
    def __init__(self, db_name="quizzes.db"):
        self.db_name = db_name
        self._crear_tablas()
    
    def _get_connection(self):
        """Obtener conexión a la base de datos"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _crear_tablas(self):
        """Crear las tablas si no existen"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Tabla de quizzes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                materia TEXT NOT NULL,
                nombre TEXT NOT NULL,
                preguntas TEXT NOT NULL,
                inicio TEXT NOT NULL,
                fin TEXT NOT NULL,
                codigo TEXT UNIQUE NOT NULL,
                activo BOOLEAN DEFAULT 0,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de respuestas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS respuestas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                nombre_completo TEXT NOT NULL,
                respuestas TEXT NOT NULL,
                puntuacion INTEGER NOT NULL,
                fecha_respuesta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quiz_id) REFERENCES quizzes (id),
                UNIQUE (quiz_id, user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_quiz(self, materia, nombre, preguntas, inicio, fin, codigo):
        """Guardar un nuevo quiz y retornar su ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        preguntas_json = json.dumps(preguntas)
        
        cursor.execute('''
            INSERT INTO quizzes (materia, nombre, preguntas, inicio, fin, codigo, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (materia, nombre, preguntas_json, inicio, fin, codigo, 0))
        
        quiz_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return quiz_id
    
    def get_quiz(self, quiz_id):
        """Obtener un quiz por su ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM quizzes WHERE id = ?', (quiz_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_quiz_by_code(self, codigo):
        """Obtener un quiz por su código único"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM quizzes WHERE codigo = ?', (codigo,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_quizzes(self):
        """Obtener todos los quizzes"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM quizzes ORDER BY creado_en DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_quiz_status(self, quiz_id, activo):
        """Activar o desactivar un quiz"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE quizzes SET activo = ? WHERE id = ?
        ''', (1 if activo else 0, quiz_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
    
    def user_already_responded(self, quiz_id, user_id):
        """Verificar si un usuario ya respondió un quiz"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM respuestas 
            WHERE quiz_id = ? AND user_id = ?
        ''', (quiz_id, user_id))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def save_response(self, quiz_id, user_id, nombre_completo, respuestas, puntuacion):
        """Guardar la respuesta de un usuario a un quiz"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        respuestas_json = json.dumps(respuestas)
        
        try:
            cursor.execute('''
                INSERT INTO respuestas (quiz_id, user_id, nombre_completo, respuestas, puntuacion)
                VALUES (?, ?, ?, ?, ?)
            ''', (quiz_id, user_id, nombre_completo, respuestas_json, puntuacion))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # El usuario ya respondió este quiz
            return False
        finally:
            conn.close()
    
    def get_responses_by_quiz(self, quiz_id):
        """Obtener todas las respuestas de un quiz"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM respuestas WHERE quiz_id = ? ORDER BY fecha_respuesta ASC
        ''', (quiz_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_user_response(self, quiz_id, user_id):
        """Obtener la respuesta de un usuario específico a un quiz"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM respuestas WHERE quiz_id = ? AND user_id = ?
        ''', (quiz_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    # ========================================
    # ✅ MÉTODO PARA ELIMINAR QUIZ (NUEVO)
    # ========================================
    def delete_quiz(self, quiz_id):
        """
        Eliminar un quiz y todas sus respuestas asociadas.
        Retorna True si se eliminó correctamente, False si no existe.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Primero eliminar las respuestas (por clave foránea)
            cursor.execute('DELETE FROM respuestas WHERE quiz_id = ?', (quiz_id,))
            
            # Luego eliminar el quiz
            cursor.execute('DELETE FROM quizzes WHERE id = ?', (quiz_id,))
            
            conn.commit()
            return cursor.rowcount > 0  # Retorna True si se eliminó algo
            
        except Exception as e:
            print(f"Error al eliminar quiz {quiz_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_all_quizzes(self):
        """⚠️ ELIMINAR TODOS LOS QUIZZES (Solo para desarrollo)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM respuestas')
            cursor.execute('DELETE FROM quizzes')
            conn.commit()
            return True
        except Exception as e:
            print(f"Error al eliminar todos los quizzes: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def close(self):
        """Cerrar conexión (método de compatibilidad)"""
        pass  # SQLite maneja conexiones automáticamente
