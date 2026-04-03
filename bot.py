# bot.py
import logging
import json
import re
import random
import string
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from database import Database

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
BOT_USERNAME = os.environ.get("BOT_USERNAME")

logging.basicConfig(level=logging.INFO)

class QuizBot:
    def __init__(self):
        self.db = Database()
        self.quiz = {}
        self.pregunta = {}
        self.estado_creacion = None
    
    def _parsear_fecha(self, texto):
        try:
            return datetime.strptime(texto.upper(), '%d/%m/%Y %I:%M %p')
        except:
            return None
    
    def _formato_mostrar(self, dt):
        return dt.strftime('%d/%m/%Y %I:%M %p')
    
    async def start(self, update, ctx):
        try:
            args = ctx.args
            if args:
                quiz_code = args[0]
                await self._iniciar_desde_enlace(update, ctx, quiz_code)
            else:
                await update.message.reply_text("Bot de Quizzes\n\n/crear_quiz - Crear\n/ayuda - Ayuda")
        except Exception as e:
            await update.message.reply_text("Error: " + str(e))
    
    async def _iniciar_desde_enlace(self, update, ctx, quiz_code):
        quiz = self.db.get_quiz_by_code(quiz_code)
        if not quiz:
            await update.message.reply_text("Quiz no encontrado")
            return
        await update.message.reply_text(
            quiz['nombre'] + "\n\nHaz clic para participar:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("PARTICIPAR", callback_data="participar_" + str(quiz['id']))]
            ])
        )
    
    async def button_handler(self, update, ctx):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data.startswith("participar_"):
            quiz_id = int(data.split("_")[1])
            ctx.args = [str(quiz_id)]
            await self.participar(update, ctx)
        elif data.startswith("enlace_"):
            quiz_id = int(data.split("_")[1])
            quiz = self.db.get_quiz(quiz_id)
            if quiz:
                codigo = quiz.get('codigo', "quiz_" + str(quiz_id))
                enlace = "https://t.me/" + BOT_USERNAME + "?start=" + codigo
                await query.edit_message_text(
                    "ENLACE:\n\n" + quiz['nombre'] + "\n\n" + enlace + "\n\nCodigo: " + codigo,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("VOLVER", callback_data="ver_quiz_" + str(quiz_id))]
                    ])
                )
        elif data.startswith("ver_quiz_"):
            quiz_id = int(data.split("_")[2])
            await self.ver_quiz_detalle(update, ctx, quiz_id)
        elif data == "volver_menu":
            await self.mis_quizzes(update, ctx)
    
    async def ayuda(self, update, ctx):
        await update.message.reply_text("Comandos:\n/crear_quiz - Crear\n/mis_quizzes - Ver\n/enlace <ID> - Enlace")
    
    async def crear_quiz(self, update, ctx):
        self.quiz = {'preguntas': []}
        self.estado_creacion = 'MATERIA'
        await update.message.reply_text("MATERIA o ASIGNATURA:\n\nEj: Matematicas, Historia")
    
    async def procesar_creacion(self, update, ctx):
        texto = update.message.text
        
        if self.estado_creacion == 'MATERIA':
            self.quiz['materia'] = texto
            self.estado_creacion = 'NOMBRE'
            await update.message.reply_text("Materia: " + texto + "\n\nNOMBRE del quiz:\n\nEj: Examen Parcial 1")
        elif self.estado_creacion == 'NOMBRE':
            self.quiz['nombre'] = texto
            self.estado_creacion = 'INICIO'
            await update.message.reply_text("Nombre: " + texto + "\n\nINICIO:\nFormato: DD/MM/YYYY HH:MM AM/PM\nEj: 20/03/2026 02:00 PM")
        elif self.estado_creacion == 'INICIO':
            inicio_dt = self._parsear_fecha(texto)
            if not inicio_dt:
                await update.message.reply_text("Formato incorrecto.\n\nUsa: DD/MM/YYYY HH:MM AM/PM")
                return
            if inicio_dt <= datetime.now():
                await update.message.reply_text("Debe ser en el futuro.")
                return
            self.quiz['inicio'] = texto
            self.quiz['inicio_dt'] = inicio_dt
            self.estado_creacion = 'FIN'
            await update.message.reply_text("Inicio: " + self._formato_mostrar(inicio_dt) + "\n\nFIN:\nFormato: DD/MM/YYYY HH:MM AM/PM")
        elif self.estado_creacion == 'FIN':
            fin_dt = self._parsear_fecha(texto)
            if not fin_dt:
                await update.message.reply_text("Formato incorrecto.")
                return
            if fin_dt <= self.quiz['inicio_dt']:
                await update.message.reply_text("Fin debe ser despues del inicio.")
                return
            self.quiz['fin'] = texto
            self.quiz['fin_dt'] = fin_dt
            self.estado_creacion = 'PREGUNTA'
            await update.message.reply_text("PRIMERA PREGUNTA:")
        elif self.estado_creacion == 'PREGUNTA':
            if texto.upper() == 'SI':
                self.pregunta = {}
                await update.message.reply_text("Siguiente pregunta:")
            elif texto.upper() == 'NO':
                await self._guardar_quiz(update)
            else:
                self.pregunta = {'texto': texto, 'opciones': []}
                self.estado_creacion = 'OPC_A'
                await update.message.reply_text("Opcion A:")
        elif self.estado_creacion == 'OPC_A':
            self.pregunta['opciones'].append(texto)
            self.estado_creacion = 'OPC_B'
            await update.message.reply_text("Opcion B:")
        elif self.estado_creacion == 'OPC_B':
            self.pregunta['opciones'].append(texto)
            self.estado_creacion = 'OPC_C'
            await update.message.reply_text("Opcion C:")
        elif self.estado_creacion == 'OPC_C':
            self.pregunta['opciones'].append(texto)
            self.estado_creacion = 'OPC_D'
            await update.message.reply_text("Opcion D:")
        elif self.estado_creacion == 'OPC_D':
            self.pregunta['opciones'].append(texto)
            self.estado_creacion = 'CORRECTA'
            await update.message.reply_text("Respuesta correcta (A/B/C/D):")
        elif self.estado_creacion == 'CORRECTA':
            if texto.upper() not in ['A', 'B', 'C', 'D']:
                await update.message.reply_text("Usa A, B, C o D:")
                return
            self.quiz['preguntas'].append({'pregunta': self.pregunta['texto'], 'opciones': self.pregunta['opciones'], 'correcta': texto.upper()})
            self.estado_creacion = 'MAS_PREG'
            await update.message.reply_text("Pregunta " + str(len(self.quiz['preguntas'])) + " lista!\n\nOtra? (SI/NO):")
        elif self.estado_creacion == 'MAS_PREG':
            if texto.upper() == 'SI':
                self.estado_creacion = 'PREGUNTA'
                await update.message.reply_text("Siguiente pregunta:")
            elif texto.upper() == 'NO':
                await self._guardar_quiz(update)
            else:
                await update.message.reply_text("Responde SI o NO:")
    
    async def _guardar_quiz(self, update):
        try:
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            materia = self.quiz['materia']
            nombre = self.quiz['nombre']
            
            qid = self.db.save_quiz(materia, nombre, self.quiz['preguntas'], self.quiz['inicio'], self.quiz['fin'], codigo)
            
            self.quiz = {}
            self.pregunta = {}
            self.estado_creacion = None
            
            enlace_correcto = "https://t.me/" + BOT_USERNAME + "?start=" + codigo
            
            await update.message.reply_text(
                "✅ QUIZ CREADO!\n\n"
                "📚 Materia: " + materia + "\n"
                "📝 Nombre: " + nombre + "\n"
                "🆔 ID: " + str(qid) + "\n"
                "🔑 Codigo: " + codigo + "\n\n"
                "🔗 ENLACE:\n" + enlace_correcto + "\n\n"
                "💡 Comparte en tu grupo"
            )
        except Exception as e:
            await update.message.reply_text("Error: " + str(e))
            self.estado_creacion = None
    
    async def participar(self, update, ctx):
        try:
            query = update.callback_query if update.callback_query else None
            qid = int(ctx.args[0])
        except:
            if query:
                await query.edit_message_text("Quiz no valido")
            else:
                await update.message.reply_text("Quiz no valido")
            return
        
        quiz = self.db.get_quiz(qid)
        if not quiz:
            if query:
                await query.edit_message_text("Quiz no encontrado")
            else:
                await update.message.reply_text("Quiz no encontrado")
            return
        
        user_id = update.effective_user.id
        if self.db.user_already_responded(qid, user_id):
            if query:
                await query.edit_message_text("Ya respondiste este quiz")
            else:
                await update.message.reply_text("Ya respondiste este quiz")
            return
        
        if not quiz.get('activo'):
            if query:
                await query.edit_message_text("Quiz desactivado")
            else:
                await update.message.reply_text("Quiz desactivado")
            return
        
        now = datetime.now()
        inicio_dt = self._parsear_fecha(quiz['inicio'])
        fin_dt = self._parsear_fecha(quiz['fin'])
        
        if not inicio_dt or not fin_dt:
            if query:
                await query.edit_message_text("Error en fechas")
            else:
                await update.message.reply_text("Error en fechas")
            return
        
        if now < inicio_dt:
            msg = "Inicia: " + self._formato_mostrar(inicio_dt)
            if query:
                await query.edit_message_text(msg)
            else:
                await update.message.reply_text(msg)
            return
        
        if now > fin_dt:
            msg = "Finalizo: " + self._formato_mostrar(fin_dt)
            if query:
                await query.edit_message_text(msg)
            else:
                await update.message.reply_text(msg)
            return
        
        ctx.user_data['quiz_id'] = qid
        ctx.user_data['paso_registro'] = 'NOMBRE'
        
        msg = (quiz['materia'] + "\n" + 
               quiz['nombre'] + "\n\n" + 
               "Finaliza: " + self._formato_mostrar(fin_dt) + 
               "\n\n1. Tu NOMBRE:")
        
        if query:
            await query.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)
    
    async def procesar_registro(self, update, ctx):
        if 'quiz_id' not in ctx.user_data:
            return
        qid = ctx.user_data['quiz_id']
        paso = ctx.user_data.get('paso_registro', 'NOMBRE')
        texto = update.message.text.strip()
        
        if paso == 'NOMBRE':
            ctx.user_data['nombre'] = texto
            ctx.user_data['paso_registro'] = 'APELLIDO'
            await update.message.reply_text("2. Tu APELLIDO:")
        
        elif paso == 'APELLIDO':
            ctx.user_data['apellido'] = texto
            ctx.user_data['paso_registro'] = 'CEDULA'
            await update.message.reply_text("3. Tu CEDULA (solo numeros):")
        
        elif paso == 'CEDULA':
            if not texto.isdigit():
                await update.message.reply_text("Cedula debe ser solo numeros:")
                return
            ctx.user_data['cedula'] = texto
            
            quiz = self.db.get_quiz(qid)
            preguntas = json.loads(quiz['preguntas'])
            ctx.user_data['total'] = len(preguntas)
            ctx.user_data['pregunta_actual'] = 0
            ctx.user_data['respuestas'] = {}
            ctx.user_data['paso_registro'] = 'RESPUESTA_PREGUNTA'
            
            await self._mostrar_pregunta(update, ctx, 0)
    
    async def _mostrar_pregunta(self, update, ctx, indice):
        qid = ctx.user_data['quiz_id']
        quiz = self.db.get_quiz(qid)
        preguntas = json.loads(quiz['preguntas'])
        
        if indice >= len(preguntas):
            await self._finalizar_quiz(update, ctx)
            return
        
        pregunta = preguntas[indice]
        letras = ['A', 'B', 'C', 'D']
        
        msg = "📝 PREGUNTA " + str(indice + 1) + " de " + str(len(preguntas)) + "\n\n"
        msg += pregunta['pregunta'] + "\n\n"
        
        for j, op in enumerate(pregunta['opciones']):
            msg += letras[j] + ") " + op + "\n"
        
        msg += "\n✍️ Tu respuesta (A, B, C o D):"
        
        await update.message.reply_text(msg)
    
    async def procesar_respuesta_pregunta(self, update, ctx):
        if ctx.user_data.get('paso_registro') != 'RESPUESTA_PREGUNTA':
            return
        
        texto = update.message.text.strip().upper()
        
        if texto not in ['A', 'B', 'C', 'D']:
            await update.message.reply_text("❌ Responde con A, B, C o D:")
            return
        
        qid = ctx.user_data['quiz_id']
        indice = ctx.user_data.get('pregunta_actual', 0)
        respuestas = ctx.user_data.get('respuestas', {})
        
