from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
import pyodbc
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = "clave_secreta_predeterminada"

# Función para conectar a la base de datos
def get_db_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    
    conn = pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={user};PWD={password}'
    )
    return conn

# Ruta principal para la exportación de datos (existente)
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Obtener mes y año de los filtros del formulario
        month = request.form.get("month")
        year = request.form.get("year")

        # Crear el nombre del archivo de backup
        backup_name = f"VTA-{month}-{year}.bak"
        backup_path = os.path.join(BACKUP_FOLDER, backup_name)

        # Obtener las credenciales de la base de datos desde el archivo .env
        server = os.getenv("DB_SERVER")
        database = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

        # Ejecutar el comando sqlcmd para realizar el backup
        command = f'sqlcmd -S {server} -U {user} -P {password} -Q "BACKUP DATABASE [{database}] TO DISK=\'{os.path.abspath(backup_path)}\'"'
        os.system(command)

        # Redirigir de vuelta a la página principal
        return redirect(url_for("index"))

    # Obtener el listado de backups generados
    BACKUP_FOLDER = os.path.join(os.getcwd(), "backups")
    os.makedirs(BACKUP_FOLDER, exist_ok=True)
    backups = os.listdir(BACKUP_FOLDER)
    backups.sort(reverse=True)  # Ordenar los backups de más reciente a más antiguo
    return render_template("index.html", backups=backups)

# Nueva ruta para listar productos
@app.route("/productos", methods=["GET"])
def listar_productos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta para obtener todos los productos
        cursor.execute("SELECT id_pro, nom_pro, pre_pro FROM producto ORDER BY nom_pro")
        productos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template("productos.html", productos=productos)
    except Exception as e:
        flash(f"Error al cargar productos: {str(e)}", "error")
        return redirect(url_for("index"))

# Ruta para editar precio de producto
@app.route("/productos/editar/<int:id_producto>", methods=["GET", "POST"])
def editar_producto(id_producto):
    # ID de usuario fijo (1) como se solicitó
    id_usuario = 1
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == "POST":
            nuevo_precio = request.form.get("nuevo_precio")
            
            # Validar que el precio sea un número válido
            try:
                nuevo_precio = float(nuevo_precio)
                if nuevo_precio <= 0:
                    raise ValueError("El precio debe ser mayor que cero")
            except ValueError:
                flash("Por favor ingresa un precio válido", "error")
                return redirect(url_for("editar_producto", id_producto=id_producto))
            
            # Actualizar el precio (esto activará el trigger)
            cursor.execute(
                "UPDATE producto SET pre_pro = ? WHERE id_pro = ?",
                (nuevo_precio, id_producto)
            )
            
            # Asignación del ID de usuario a 1 en caso de ser necesario para auditoría o registros
            # cursor.execute("UPDATE auditoria SET id_usuario = ? WHERE id_producto = ?", (id_usuario, id_producto))
            
            conn.commit()
            flash("Precio actualizado correctamente", "success")
            return redirect(url_for("listar_productos"))
        else:
            # Obtener información del producto
            cursor.execute(
                "SELECT id_pro, nom_pro, pre_pro FROM producto WHERE id_pro = ?",
                (id_producto,)
            )
            producto = cursor.fetchone()
            
            if not producto:
                flash("Producto no encontrado", "error")
                return redirect(url_for("listar_productos"))
            
            # Obtener historial de cambios de precio
            cursor.execute(
                """
                SELECT a.fecha, a.hora, a.precio_anterior, a.precio_nuevo, a.host_name, u.nom_usu  
                FROM auditoria a
                INNER JOIN usuario u ON a.id_usuario = u.id_usu
                WHERE a.id_prod = ? 
                ORDER BY a.fecha DESC, a.hora DESC
                """,
                (id_producto,)
            )
            historial = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return render_template(
                "editar_producto.html", 
                producto=producto, 
                historial=historial
            )
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("listar_productos"))

@app.route('/download/<path:filename>')
def download_file(filename):
    BACKUP_FOLDER = os.path.join(os.getcwd(), "backups")
    return send_from_directory(BACKUP_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
