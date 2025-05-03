from flask import Flask, render_template, request, redirect, url_for
import os
from dotenv import load_dotenv
from datetime import datetime
from flask import send_from_directory

# Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# Definir la carpeta donde se almacenarán los backups
BACKUP_FOLDER = os.path.join(os.getcwd(), "backups")  # Usamos la ruta absoluta
os.makedirs(BACKUP_FOLDER, exist_ok=True)

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
    backups = os.listdir(BACKUP_FOLDER)
    backups.sort(reverse=True)  # Ordenar los backups de más reciente a más antiguo
    return render_template("index.html", backups=backups)

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(BACKUP_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
