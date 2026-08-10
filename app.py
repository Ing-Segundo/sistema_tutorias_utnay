from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from fpdf import FPDF
from functools import wraps
import jwt, shutil, os, threading, time

# Configuración adaptada para reconocer la carpeta 'assets' en Render/GitHub
app = Flask(__name__, static_folder='assets', static_url_path='/assets')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave_segura_sistema_tutorias_2026_utn')

CARPETA_BASE = os.path.abspath(os.path.dirname(__file__))
RUTA_DB = os.path.join(CARPETA_BASE, "sistema_tutorias.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{RUTA_DB}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
db = SQLAlchemy(app)

# ===================== MODELOS =====================
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    credencial = db.Column(db.String(20), unique=True, nullable=False)
    contrasena = db.Column(db.String(250), nullable=False)
    nombre_completo = db.Column(db.String(100), nullable=False)
    intentos_fallidos = db.Column(db.Integer, default=0)
    bloqueado = db.Column(db.Boolean, default=False)

class Alumno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), unique=True, nullable=False)
    id_tutor = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    rendimiento = db.Column(db.String(200), default="Sin registro")
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref=db.backref('perfil_alumno', uselist=False), single_parent=True)
    tutor = db.relationship('Usuario', foreign_keys=[id_tutor], backref='alumnos_asignados')

class Tutor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), unique=True, nullable=False)
    horario = db.Column(db.String(200), default="Lunes a Viernes 08:00 - 16:00")
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref=db.backref('perfil_tutor', uselist=False), single_parent=True)

class Tutoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey('alumno.id'), nullable=False)
    id_tutor = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)
    tema = db.Column(db.String(150), nullable=False)
    estado = db.Column(db.String(30), default="Solicitada")
    observaciones = db.Column(db.Text, default="")
    carrera = db.Column(db.String(100), default="")
    grupo = db.Column(db.String(20), default="")
    hr_inicio = db.Column(db.String(10), default="")
    hr_salida = db.Column(db.String(10), default="")
    motivo = db.Column(db.Text, default="")
    puntos_relevantes = db.Column(db.Text, default="")
    compromisos = db.Column(db.Text, default="")
    alumno = db.relationship('Alumno', backref='lista_tutorias')

class ConfiguracionRespaldos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activo = db.Column(db.Boolean, default=False)
    intervalo_horas = db.Column(db.Integer, default=24)
    ultima_ejecucion = db.Column(db.DateTime)

class Auditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    accion = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip = db.Column(db.String(50), nullable=False)
    usuario = db.Column(db.String(100))

# ===================== DATOS INICIALES =====================
TUTORES_INICIALES = [
    ("juan.tovar", "Juan Manuel Tovar Sánchez"),
    ("silvia.castrejon", "Silvia Sofia Castrejon Zarate")
]

ALUMNOS_INICIALES = [
    ("TIC-310113", "Andrade Carlos Ricardo", "silvia.castrejon"),
    ("TIC-310095", "Beltrán Peña Samantha Milliani", "silvia.castrejon"),
    ("TIC-310099", "Fernández López Angela Ailin", "silvia.castrejon"),
    ("TIC-310134", "López Cabrera Luis Daniel", "silvia.castrejon"),
    ("TIC-310010", "Regino Ines Alan Andrés", "silvia.castrejon"),
    ("TIC-310060", "Ávalos Zendejas José Ramón", "silvia.castrejon"),
    ("TIC-310147", "Covarrubias García Dayron Antonio", "silvia.castrejon"),
    ("TIC-300012", "González Ruelas Fernanda", "silvia.castrejon"),
    ("TIC-310184", "Mora Yañez Jonathan Alexis", "silvia.castrejon"),
    ("TIC-310086", "Sánchez González Karen Alexa", "silvia.castrejon"),
    ("TIC-310009", "Zamora Partida Enrique Gael", "silvia.castrejon"),
    ("TIC-310159", "Cano Amparo Paul Mauricio", "silvia.castrejon"),
    ("TIC-310155", "García Medina Edwin Julian", "silvia.castrejon"),
    ("TIC-310185", "Martínez Elías Kevin Arturo", "silvia.castrejon"),
    ("TIC-310123", "Pérez Arias Adrián de Jesús", "silvia.castrejon"),
    ("TIC-310071", "Sandoval Guardado Miguel Ángel", "silvia.castrejon"),
    ("TIC-310046", "Segura Hernández Edgar Gabriel", "silvia.castrejon"),
    ("TIC-310042", "Ramírez Serna Gabriel Alejandro", "silvia.castrejon"),
    ("TIC-310150", "Robles Ramírez Jorge Alexander", "silvia.castrejon"),
    ("TIC-310001", "Rubio Romero Katherine Jais", "silvia.castrejon"),
    ("TI-310142", "Vázquez Cortez Jorge Alejandro", "silvia.castrejon"),
    
    ("TIC-310173", "Aguilar Núñez José Manuel", "silvia.castrejon"),
    ("TIC-310012", "Aranda Martínez Eimy Eileen", "silvia.castrejon"),
    ("TIC-310049", "Esparza Burgara Jesús Gabriel", "silvia.castrejon"),
    ("TIC-310089", "Gasga García Joana Michelle", "silvia.castrejon"),
    ("TIC-310148", "López Castillo Carlos Eduardo", "silvia.castrejon"),
    ("TIC-310029", "De la Paz Venegas Brandon Josué", "silvia.castrejon"),
    ("TIC-310035", "Aguilar Osuna Xandier Daniel", "silvia.castrejon"),
    ("TIC-310054", "Cañedo Segura Nephtis Adonahi", "silvia.castrejon"),
    ("TIC-310131", "Flores Luna Diego Sebastián", "silvia.castrejon"),
    ("TIC-310091", "González Torres Karol Emmanuel", "silvia.castrejon"),
    ("TIC-300099", "Ozuna Aguilar Karla Yadira", "silvia.castrejon"),
    ("TIC-310068", "Pérez Ruiz Julio Javier", "silvia.castrejon"),
    ("TIC-310153", "Ávila Ríos Rafael Humberto", "silvia.castrejon"),
    ("TIC-310182", "Reyna Villanueva David Arturo", "silvia.castrejon"),
    ("TIC-310040", "Gómez Nava Luis Ricardo", "silvia.castrejon"),
    ("TIC-310088", "Zepeda Aguilar Jazmín Lizeth", "silvia.castrejon"),
    ("TIC-310167", "Ornelas González Jesús Antonio", "silvia.castrejon"),
    ("TIC-310192", "Rodríguez de la Cruz Jesús Emmanuel", "silvia.castrejon"),
    ("TIC-310195", "Morales Bañuelos Alex Gilberto", "silvia.castrejon"),
    ("TIC-310059", "Ramos Díaz Aldair Alejandro", "silvia.castrejon"),
    ("TIC-310196", "Ruíz Encarnación Maximiliano", "silvia.castrejon"),
    ("TIC-310137", "Topete Fregoso José Armando", "silvia.castrejon"),
    ("TIC-310156", "Velasco Sánchez Raúl Mauricio", "silvia.castrejon"),
    ("TIC-310011", "Medina Delgado Alan Emir", "silvia.castrejon"),
    
    ("TIC-310072", "Araujo Robledo Alain Javier", "juan.tovar"),
    ("TIC-310048", "Cisneros Macías Alondra Guadalupe", "juan.tovar"),
    ("TIC-310143", "Flores Ochoa Kervin Geovanni", "juan.tovar"),
    ("TIC-310104", "Mendoza Salas Gilberto Alonso", "juan.tovar"),
    ("TIC-310116", "Ramos Rivera Yoel Guadalupe", "juan.tovar"),
    ("TIC-310166", "Bañuelos Vizcarra Román Alexis", "juan.tovar"),
    ("TIC-310097", "Estrada Parra Emiliano", "juan.tovar"),
    ("TIC-310190", "Montes Montes Pedro Vladimir", "juan.tovar"),
    ("TIC-310160", "Palomar Macías Kevin Abraham", "juan.tovar"),
    ("TIC-310037", "Velázquez Meza Axel", "juan.tovar"),
    ("TIC-300002", "Bernal Arias Diana Laura", "juan.tovar"),
    ("TIC-310085", "Díaz Hernández Cesar Andrés", "juan.tovar"),
    ("TIC-310025", "Moreno Avalos Anel Elizabeth", "juan.tovar"),
    ("TIC-310067", "Rivas Sierra José Manuel", "juan.tovar"),
    ("TIC-310047", "López Raygoza Christopher Wilfrido", "juan.tovar"),
    ("TIC-310114", "Plascencia Domínguez Christopher Martin", "juan.tovar"),
    ("TIC-260053", "Rodríguez Millán Gerardo Alberto", "juan.tovar"),
    ("TIC-310168", "Rosales García Sherlyn Vanessa", "juan.tovar"),
    ("TIC-310094", "Ruiz Mendoza Gilberto", "juan.tovar"),
    ("TIC-310102", "Topete Sánchez José Carlos", "juan.tovar"),
    
    ("TIC-310120", "Alvarado Rodríguez Alexis Ariel", "juan.tovar"),
    ("TIC-310020", "Barajas Rosales Erick Geovanny", "juan.tovar"),
    ("TIC-310128", "García Correa Bertha Odalys", "juan.tovar"),
    ("TIC-310163", "Guerrero Ponce Roque Joseph", "juan.tovar"),
    ("TIC-310016", "Raygosa Curiel Julissa Anahy", "juan.tovar"),
    ("TIC-310187", "Torres Rodríguez Emmanuel", "juan.tovar"),
    ("TIC-310103", "Arce Rosales Fernanda Dalet", "juan.tovar"),
    ("TIC-300089", "Cocco Malagón Christpher", "juan.tovar"),
    ("TIC-312001", "García Macías Jahir", "juan.tovar"),
    ("TIC-310151", "Gutiérrez Ruelas Nelly Jarei", "juan.tovar"),
    ("TIC-310055", "Ramírez Abrego Danna Giselle", "juan.tovar"),
    ("TIC-310087", "Segundo Lara Jeshua Miguel", "juan.tovar"),
    ("TIC-310188", "Bernal Hernández Brandon Eduardo", "juan.tovar"),
    ("TIC-310022", "Corona Pérez Alain Antonio", "juan.tovar"),
    ("TIC-310003", "Gonzalez Lares Alexandra Rubí", "juan.tovar"),
    ("TIC-310036", "Gutiérrez Zepeda Yorel Isaí", "juan.tovar"),
    ("TIC-310073", "Rivera Orozco Vanessa de Jesús", "juan.tovar"),
    ("TIC-310007", "Samaniego de León Andy Alexander", "juan.tovar"),
    ("TIC-310027", "Díaz Herrera Víctor Manuel", "juan.tovar"),
    ("TIC-310019", "Larios García Cristopher", "juan.tovar"),
    ("TIC-300133", "Marrujo Arellano Crystopher", "juan.tovar"),
    ("TIC-300170", "Navarro López Antonio Damián", "juan.tovar"),
    ("TIC-310121", "Peña Arvizu Jorge Gabriel", "juan.tovar"),
    ("TIC-310178", "Wu Barocio Alfonso Alejandro", "juan.tovar"),
]

def inicializar_base_datos():
    with app.app_context():
        db.create_all()
        if not ConfiguracionRespaldos.query.first(): 
            db.session.add(ConfiguracionRespaldos())
            
        usr_coord = Usuario.query.filter_by(credencial="coordinador").first()
        if not usr_coord:
            admin = Usuario(tipo="coordinador", credencial="coordinador", nombre_completo="Coordinador General", contrasena=generate_password_hash("clave_coordinador"))
            db.session.add(admin)
        else:
            usr_coord.contrasena = generate_password_hash("clave_coordinador")
            usr_coord.bloqueado = False

        mapa_tutores = {}

        for cred, nombre in TUTORES_INICIALES:
            usr = Usuario.query.filter_by(credencial=cred).first()
            if not usr:
                usr = Usuario(
                    tipo="tutor", 
                    credencial=cred, 
                    nombre_completo=nombre, 
                    contrasena=generate_password_hash(cred)
                )
                db.session.add(usr)
                db.session.flush()
                db.session.add(Tutor(usuario_id=usr.id))
            else:
                usr.contrasena = generate_password_hash(cred)
                usr.bloqueado = False
                usr.intentos_fallidos = 0
            mapa_tutores[cred] = usr.id
                
        for cred, nombre, cred_tutor in ALUMNOS_INICIALES:
            usr = Usuario.query.filter_by(credencial=cred).first()
            id_tutor_asignado = mapa_tutores.get(cred_tutor)

            if not usr:
                usr = Usuario(
                    tipo="alumno", 
                    credencial=cred, 
                    nombre_completo=nombre, 
                    contrasena=generate_password_hash(cred)
                )
                db.session.add(usr)
                db.session.flush()
                db.session.add(Alumno(usuario_id=usr.id, id_tutor=id_tutor_asignado, rendimiento="Sin registro"))
            else:
                usr.contrasena = generate_password_hash(cred)
                usr.bloqueado = False
                usr.intentos_fallidos = 0
                if usr.perfil_alumno:
                    usr.perfil_alumno.id_tutor = id_tutor_asignado

        db.session.commit()

inicializar_base_datos()

# ===================== RESPALDOS =====================
CARPETA_RESPALDOS = os.path.join(CARPETA_BASE, "respaldos")
os.makedirs(CARPETA_RESPALDOS, exist_ok=True)

def tarea_respaldo_automatico():
    while True:
        with app.app_context():
            try:
                cfg = ConfiguracionRespaldos.query.first()
                if cfg and cfg.activo:
                    ahora = datetime.now(timezone.utc)
                    if not cfg.ultima_ejecucion or (ahora - cfg.ultima_ejecucion.replace(tzinfo=timezone.utc)).total_seconds() >= cfg.intervalo_horas * 3600:
                        nombre = f"respaldo_{ahora.strftime('%Y%m%d_%H%M%S')}.db"
                        destino = os.path.join(CARPETA_RESPALDOS, nombre)
                        if os.path.exists(RUTA_DB):
                            shutil.copy2(RUTA_DB, destino)
                            cfg.ultima_ejecucion = ahora
                            db.session.commit()
            except Exception as e:
                print(f"Error en tarea de respaldo: {e}")
        time.sleep(3600)

threading.Thread(target=tarea_respaldo_automatico, daemon=True).start()

# ===================== FUNCIONES AUXILIARES =====================
def generar_pdf(datos, titulo, columnas):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, titulo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    anchos = [40, 50, 40, 50]
    for i, col in enumerate(columnas):
        pdf.cell(anchos[i], 8, col.encode('latin-1', 'replace').decode('latin-1'), border=1, align="C")
    pdf.ln()
    pdf.set_font("Arial", "", 9)
    for fila in datos:
        for i, celda in enumerate(fila):
            texto = str(celda).encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(anchos[i], 8, texto, border=1, align="C")
        pdf.ln()
    ruta = os.path.join(CARPETA_BASE, f"reporte_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
    pdf.output(ruta)
    return ruta

# ===================== JWT COMPLEMENTARIO =====================
JWT_ALGORITMO = "HS256"
JWT_MINUTOS_EXPIRACION = 30

def generar_token(usuario):
    payload = {
        "uid": usuario.id,
        "rol": usuario.tipo,
        "nombre": usuario.nombre_completo,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_MINUTOS_EXPIRACION)
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm=JWT_ALGORITMO)

def obtener_token_peticion():
    token = request.cookies.get("token")
    if token: 
        return token
    encabezado = request.headers.get("Authorization", "")
    if encabezado.startswith("Bearer "): 
        return encabezado.split(" ", 1)[1]
    return None

def requiere_rol(*roles_permitidos):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if "uid" in session and (not roles_permitidos or session.get("rol") in roles_permitidos):
                g.uid, g.rol, g.nombre = session["uid"], session["rol"], session.get("nombre")
                return vista(*args, **kwargs)
            token = obtener_token_peticion()
            if not token: 
                return redirect(url_for("login"))
            try:
                payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=[JWT_ALGORITMO])
            except jwt.ExpiredSignatureError:
                flash("Tu sesión ha expirado", "error")
                return redirect(url_for("login"))
            except jwt.InvalidTokenError:
                flash("Sesión inválida", "error")
                return redirect(url_for("login"))
            if roles_permitidos and payload["rol"] not in roles_permitidos:
                return redirect(url_for("login"))
            g.uid, g.rol, g.nombre = payload["uid"], payload["rol"], payload["nombre"]
            return vista(*args, **kwargs)
        return envoltura
    return decorador

# ===================== LOGIN =====================
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    ip = request.remote_addr
    if request.method == "POST":
        cred = request.form["credencial"].strip()
        passw = request.form["contrasena"].strip()
        usuario = Usuario.query.filter_by(credencial=cred).first()
        if not usuario or not check_password_hash(usuario.contrasena, passw):
            flash("Credenciales incorrectas", "error")
            return redirect(url_for("login"))
        if usuario.bloqueado:
            flash("Usuario bloqueado", "error")
            return redirect(url_for("login"))
        usuario.intentos_fallidos = 0
        db.session.add(Auditoria(accion=f"INGRESO: {usuario.tipo}", ip=ip, usuario=usuario.nombre_completo))
        db.session.commit()
        session["uid"], session["rol"], session["nombre"] = usuario.id, usuario.tipo, usuario.nombre_completo
        token = generar_token(usuario)
        respuesta = redirect(url_for(f"panel_{usuario.tipo}"))
        respuesta.set_cookie("token", token, httponly=True, samesite="Lax", secure=request.is_secure, max_age=JWT_MINUTOS_EXPIRACION * 60)
        flash(f"Bienvenido {usuario.nombre_completo}", "success")
        return respuesta
    return render_template("login.html")

@app.route("/salir")
def salir():
    session.clear()
    respuesta = redirect("/")
    respuesta.delete_cookie("token")
    return respuesta

# ===================== ALUMNO =====================
@app.route("/panel-alumno")
@requiere_rol("alumno")
def panel_alumno():
    alumno = Alumno.query.filter_by(usuario_id=g.uid).first()
    tutorias = Tutoria.query.filter_by(id_alumno=alumno.id).order_by(Tutoria.fecha.desc()).all() if alumno else []
    return render_template("alumno.html", alumno=alumno, tutorias=tutorias)

@app.route("/solicitar-tutoria", methods=["POST"])
@requiere_rol("alumno")
def solicitar_tutoria():
    alumno = Alumno.query.filter_by(usuario_id=g.uid).first()
    try:
        fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d")
    except (ValueError, KeyError):
        flash("La fecha proporcionada no es válida", "error")
        return redirect(url_for("panel_alumno"))

    tema = request.form.get("tema", "").strip()
    if not tema:
        flash("El tema no puede estar vacío", "error")
        return redirect(url_for("panel_alumno"))

    nueva = Tutoria(id_alumno=alumno.id, id_tutor=alumno.id_tutor, fecha=fecha, tema=tema, estado="Solicitada")
    db.session.add(nueva)
    db.session.commit()
    flash("Solicitud enviada al tutor correctamente", "success")
    return redirect(url_for("panel_alumno"))

@app.route("/reportes-alumno")
@requiere_rol("alumno")
def reportes_alumno():
    alumno = Alumno.query.filter_by(usuario_id=g.uid).first()
    mis_tutorias = Tutoria.query.filter_by(id_alumno=alumno.id).all() if alumno else []
    total = len(mis_tutorias)
    realizadas = sum(1 for t in mis_tutorias if t.estado == "Realizada")
    pendientes = sum(1 for t in mis_tutorias if t.estado in ["Solicitada", "Confirmada", "Asignada por tutor"])
    return render_template("reportes_alumno.html", total=total, realizadas=realizadas, pendientes=pendientes, tutorias=mis_tutorias)

# ===================== TUTOR =====================
@app.route("/panel-tutor")
@requiere_rol("tutor")
def panel_tutor():
    tutor = Tutor.query.filter_by(usuario_id=g.uid).first()
    tutorias = Tutoria.query.filter_by(id_tutor=g.uid).order_by(Tutoria.fecha.desc()).all()
    alumnos = Alumno.query.filter_by(id_tutor=g.uid).all()
    return render_template("tutor.html", tutor=tutor, alumnos=alumnos, tutorias=tutorias)

@app.route("/tutor/aceptar/<int:id>")
@requiere_rol("tutor")
def aceptar_tutoria(id):
    tut = Tutoria.query.get_or_404(id)
    if tut.id_tutor != g.uid:
        flash("No tienes permiso para esta tutoría", "error")
        return redirect(url_for("panel_tutor"))
    tut.estado = "Asignada por tutor"
    db.session.commit()
    flash("Tutoría aceptada y lista para iniciar", "success")
    return redirect(url_for("panel_tutor"))

@app.route("/tutor/editar-tutoria/<int:id>", methods=["GET"])
@requiere_rol("tutor")
def form_editar_tutoria(id):
    tut = Tutoria.query.get_or_404(id)
    if tut.id_tutor != g.uid:
        flash("No tienes permiso para editar esta tutoría", "error")
        return redirect(url_for("panel_tutor"))
    return render_template("editar_tutoria.html", tutoria=tut)

@app.route("/tutor/editar-tutoria/<int:id>", methods=["POST"])
@requiere_rol("tutor")
def editar_tutoria(id):
    tut = Tutoria.query.get_or_404(id)
    if tut.id_tutor != g.uid:
        flash("No tienes permiso para modificar esta tutoría", "error")
        return redirect(url_for("panel_tutor"))
    try:
        tut.fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d")
    except (ValueError, KeyError):
        flash("Fecha inválida", "error")
        return redirect(url_for("panel_tutor"))
    tut.tema = request.form.get("tema", tut.tema)
    tut.estado = request.form.get("estado", tut.estado)
    tut.observaciones = request.form.get("observaciones", tut.observaciones)
    db.session.commit()
    flash("Tutoría actualizada", "success")
    return redirect(url_for("panel_tutor"))

@app.route("/tutor/actualizar-horario", methods=["POST"])
@requiere_rol("tutor")
def actualizar_horario():
    tutor = Tutor.query.filter_by(usuario_id=g.uid).first()
    if tutor:
        tutor.horario = request.form.get("horario", tutor.horario)
        db.session.commit()
        flash("Horario actualizado", "success")
    return redirect(url_for("panel_tutor"))

@app.route("/tutor/crear-tutoria", methods=["POST"])
@requiere_rol("tutor")
def crear_tutoria():
    try:
        raw_id_alumno = request.form.get("id_alumno")
        raw_fecha = request.form.get("fecha")
        tema = request.form.get("tema", "").strip()

        if not raw_id_alumno or not raw_fecha or not tema:
            flash("Todos los campos marcados son obligatorios", "error")
            return redirect(url_for("panel_tutor"))

        id_alumno = int(raw_id_alumno)
        fecha = datetime.strptime(raw_fecha, "%Y-%m-%d")

        alumno = Alumno.query.get(id_alumno)
        if not alumno:
            flash("El alumno seleccionado no existe", "error")
            return redirect(url_for("panel_tutor"))

        nueva = Tutoria(
            id_alumno=id_alumno, 
            id_tutor=g.uid, 
            fecha=fecha, 
            tema=tema, 
            estado="Asignada por tutor"
        )
        db.session.add(nueva)
        db.session.commit()
        flash("Tutoría creada exitosamente", "success")
    except ValueError:
        db.session.rollback()
        flash("Formato de datos no válido (verifique la fecha o selección del alumno)", "error")
    except Exception as e:
        db.session.rollback()
        flash("Ocurrió un error inesperado al procesar la tutoría", "error")

    return redirect(url_for("panel_tutor"))

@app.route("/tutor/completar/<int:id>")
@requiere_rol("tutor")
def completar_tutoria(id):
    tut = Tutoria.query.get_or_404(id)
    if tut.id_tutor != g.uid:
        flash("No tienes permiso para modificar esta tutoría", "error")
        return redirect(url_for("panel_tutor"))
    tut.estado = "Realizada"
    db.session.commit()
    flash("Tutoría marcada como realizada", "success")
    return redirect(url_for("panel_tutor"))

@app.route("/reporte-tutor-pdf")
@requiere_rol("tutor")
def reporte_tutor_pdf():
    tutor = Tutor.query.filter_by(usuario_id=g.uid).first()
    tutorias = Tutoria.query.filter_by(id_tutor=g.uid).all()
    datos = [(t.alumno.usuario.nombre_completo if t.alumno and t.alumno.usuario else 'Sin Alumno', t.fecha.strftime("%d/%m/%Y"), t.tema, t.estado) for t in tutorias]
    ruta = generar_pdf(datos, f"Tutorías a mi cargo - {tutor.usuario.nombre_completo if tutor and tutor.usuario else ''}", ["Alumno", "Fecha", "Tema", "Estado"])
    return send_file(ruta, as_attachment=True, download_name="tutorias_tutor.pdf")

@app.route("/reportes-tutor")
@requiere_rol("tutor")
def reportes_tutor():
    tutor = Tutor.query.filter_by(usuario_id=g.uid).first()
    mis_tutorias = Tutoria.query.filter_by(id_tutor=g.uid).all()
    mis_alumnos = Alumno.query.filter_by(id_tutor=g.uid).count()
    total = len(mis_tutorias)
    realizadas = sum(1 for t in mis_tutorias if t.estado == "Realizada")
    pendientes = sum(1 for t in mis_tutorias if t.estado in ["Solicitada", "Confirmada", "Asignada por tutor"])
    return render_template("reportes_tutor.html", total=total, realizadas=realizadas, pendientes=pendientes, alumnos=mis_alumnos, tutorias=mis_tutorias)

@app.route("/coordinador/actualizar-asignacion-masiva")
@requiere_rol("coordinador")
def actualizar_asignacion_masiva():
    mapa_tutores = {}
    for cred, nombre in TUTORES_INICIALES:
        usr = Usuario.query.filter_by(credencial=cred).first()
        if usr:
            mapa_tutores[cred] = usr.id

    actualizados = 0
    for cred, nombre, cred_tutor in ALUMNOS_INICIALES:
        usr = Usuario.query.filter_by(credencial=cred).first()
        id_tutor_asignado = mapa_tutores.get(cred_tutor)
        
        if usr and usr.perfil_alumno:
            usr.perfil_alumno.id_tutor = id_tutor_asignado
            actualizados += 1
            
    db.session.commit()
    flash(f"Se actualizaron {actualizados} asignaciones de tutorías correctamente.", "success")
    return redirect(url_for("panel_coordinador"))

# ===================== TUTORÍA INDIVIDUAL =====================
@app.route("/iniciar-tutoria/<int:id>")
@requiere_rol("tutor")
def iniciar_tutoria(id):
    tutoria = Tutoria.query.get_or_404(id)
    if tutoria.id_tutor != g.uid:
        flash("No tienes permiso para esta tutoría", "error")
        return redirect(url_for("panel_tutor"))
    tutoria.estado = "En proceso"
    db.session.commit()
    flash("Tutoría iniciada correctamente", "success")
    return redirect(url_for("ver_tutoria_individual", id=id))

@app.route("/tutoria-individual/<int:id>", methods=["GET", "POST"])
@requiere_rol("tutor", "alumno")
def ver_tutoria_individual(id):
    tutoria = Tutoria.query.get_or_404(id)
    if g.rol == "tutor" and tutoria.id_tutor != g.uid:
        flash("No tienes acceso", "error")
        return redirect(url_for("panel_tutor"))
    if g.rol == "alumno":
        alumno = Alumno.query.filter_by(usuario_id=g.uid).first()
        if not alumno or tutoria.id_alumno != alumno.id:
            flash("No tienes acceso", "error")
            return redirect(url_for("panel_alumno"))
    if request.method == "POST":
        tutoria.carrera = request.form.get("carrera", tutoria.carrera)
        tutoria.grupo = request.form.get("grupo", tutoria.grupo)
        tutoria.hr_inicio = request.form.get("hr_inicio", tutoria.hr_inicio)
        tutoria.hr_salida = request.form.get("hr_salida", tutoria.hr_salida)
        tutoria.motivo = ", ".join(request.form.getlist("motivo")) or tutoria.motivo
        tutoria.puntos_relevantes = request.form.get("puntos_relevantes", tutoria.puntos_relevantes)
        tutoria.compromisos = request.form.get("compromisos", tutoria.compromisos)
        tutoria.observaciones = request.form.get("observaciones", tutoria.observaciones)
        if g.rol == "tutor":
            tutoria.estado = "Realizada"
        db.session.commit()
        flash("Cambios guardados correctamente", "success")
        return redirect(url_for("ver_tutoria_individual", id=id))
    return render_template("tutoria_individual.html", tutoria=tutoria)

@app.route("/descargar-ficha-tutoria-pdf/<int:id>")
@requiere_rol("tutor", "alumno")
def descargar_ficha_tutoria_pdf(id):
    tutoria = Tutoria.query.get_or_404(id)
    if g.rol == "tutor" and tutoria.id_tutor != g.uid:
        flash("No tienes permiso", "error")
        return redirect(url_for("panel_tutor"))
    datos = [
        ["Alumno", tutoria.alumno.usuario.nombre_completo if tutoria.alumno and tutoria.alumno.usuario else "N/A"],
        ["Fecha", tutoria.fecha.strftime("%d/%m/%Y") if tutoria.fecha else "N/A"],
        ["Tema", tutoria.tema],
        ["Estado", tutoria.estado]
    ]
    ruta = generar_pdf(datos, f"Ficha de Tutoría #{tutoria.id}", ["Campo", "Detalle"])
    return send_file(ruta, as_attachment=True, download_name=f"ficha_tutoria_{tutoria.id}.pdf")

# ===================== COORDINADOR =====================
@app.route("/panel-coordinador")
@requiere_rol("coordinador")
def panel_coordinador():
    return render_template("coordinador.html", 
                           usuarios=Usuario.query.all(), 
                           tutorias=Tutoria.query.all(),
                           auditoria=Auditoria.query.order_by(Auditoria.fecha.desc()).limit(30).all(),
                           respaldos=os.listdir(CARPETA_RESPALDOS), 
                           cfg=ConfiguracionRespaldos.query.first())

@app.route("/reportes")
@requiere_rol("coordinador")
def reportes():
    return render_template("reportes.html",
                           total_tutorias=Tutoria.query.count(), 
                           solicitadas=Tutoria.query.filter_by(estado="Solicitada").count(),
                           confirmadas=Tutoria.query.filter_by(estado="Confirmada").count(), 
                           realizadas=Tutoria.query.filter_by(estado="Realizada").count(),
                           asignadas=Tutoria.query.filter_by(estado="Asignada por tutor").count(), 
                           total_alumnos=Usuario.query.filter_by(tipo="alumno").count(),
                           total_tutores=Usuario.query.filter_by(tipo="tutor").count(), 
                           total_coordinadores=Usuario.query.filter_by(tipo="coordinador").count(),
                           activos=Usuario.query.filter_by(bloqueado=False).count(), 
                           bloqueados=Usuario.query.filter_by(bloqueado=True).count())

@app.route("/coordinador/crear-usuario", methods=["POST"])
@requiere_rol("coordinador")
def crear_usuario():
    tipo = request.form["tipo"]
    cred = request.form["credencial"]
    nombre = request.form["nombre"]
    clave = request.form["contrasena"]
    if Usuario.query.filter_by(credencial=cred).first():
        flash("Credencial ya existe", "error")
        return redirect(url_for("panel_coordinador"))
    nuevo = Usuario(tipo=tipo, credencial=cred, nombre_completo=nombre, contrasena=generate_password_hash(clave))
    db.session.add(nuevo)
    db.session.flush()
    if tipo == "alumno": 
        db.session.add(Alumno(usuario_id=nuevo.id, id_tutor=None))
    if tipo == "tutor": 
        db.session.add(Tutor(usuario_id=nuevo.id))
    db.session.add(Auditoria(accion=f"CREÓ USUARIO: {cred}", ip=request.remote_addr, usuario=g.nombre))
    db.session.commit()
    flash("Usuario creado correctamente", "success")
    return redirect(url_for("panel_coordinador"))

@app.route("/coordinador/asignar-tutor/<int:id_alumno>", methods=["POST"])
@requiere_rol("coordinador")
def asignar_tutor(id_alumno):
    alumno = Alumno.query.get_or_404(id_alumno)
    id_tutor = request.form.get("id_tutor")
    alumno.id_tutor = int(id_tutor) if id_tutor else None
    db.session.commit()
    flash("Tutor asignado correctamente", "success")
    return redirect(url_for("panel_coordinador"))

@app.route("/coordinador/cambiar-estado/<int:id>")
@requiere_rol("coordinador")
def cambiar_estado(id):
    usuario = Usuario.query.get_or_404(id)
    usuario.bloqueado = not usuario.bloqueado
    usuario.intentos_fallidos = 0
    db.session.commit()
    flash("Estado actualizado", "success")
    return redirect(url_for("panel_coordinador"))

@app.route("/coordinador/respaldo-manual")
@requiere_rol("coordinador")
def respaldo_manual():
    nombre = f"respaldo_manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    destino = os.path.join(CARPETA_RESPALDOS, nombre)
    shutil.copy2(RUTA_DB, destino)
    db.session.add(Auditoria(accion="RESPALDO MANUAL", ip=request.remote_addr, usuario=g.nombre))
    db.session.commit()
    flash("Respaldo creado correctamente", "success")
    return redirect(url_for("panel_coordinador"))

@app.route("/coordinador/restaurar/<nombre>")
@requiere_rol("coordinador")
def restaurar(nombre):
    origen = os.path.join(CARPETA_RESPALDOS, nombre)
    if os.path.exists(origen):
        shutil.copy2(origen, RUTA_DB)
        flash("Base restaurada correctamente", "success")
    else:
        flash("Archivo no encontrado", "error")
    return redirect(url_for("panel_coordinador"))

@app.route("/coordinador/eliminar-respaldo/<nombre>")
@requiere_rol("coordinador")
def eliminar_respaldo(nombre):
    ruta = os.path.join(CARPETA_RESPALDOS, nombre)
    if os.path.exists(ruta):
        os.remove(ruta)
        db.session.add(Auditoria(accion=f"ELIMINÓ RESPALDO: {nombre}", ip=request.remote_addr, usuario=g.nombre))
        db.session.commit()
        flash("Archivo de respaldo eliminado", "success")
    else:
        flash("El archivo no existe", "error")
    return redirect(url_for("panel_coordinador"))

@app.route("/coordinador/config-respaldos", methods=["POST"])
@requiere_rol("coordinador")
def config_respaldos():
    cfg = ConfiguracionRespaldos.query.first()
    if cfg:
        cfg.activo = "activo" in request.form
        cfg.intervalo_horas = int(request.form["intervalo"])
        db.session.commit()
        flash("Configuración guardada", "success")
    return redirect(url_for("panel_coordinador"))

@app.route("/reporte-general-pdf")
@requiere_rol("coordinador")
def reporte_general_pdf():
    datos = [(u.tipo.upper(), u.credencial, u.nombre_completo, "Bloqueado" if u.bloqueado else "Activo") for u in Usuario.query.all()]
    ruta = generar_pdf(datos, "Reporte General de Usuarios", ["Rol", "Credencial", "Nombre", "Estado"])
    return send_file(ruta, as_attachment=True, download_name="reporte_general.pdf")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
