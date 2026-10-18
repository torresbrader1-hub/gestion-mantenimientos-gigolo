from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection

ROLES = ("admin", "mecanico", "cliente")


class UsuarioService:

    def preparar_tabla(self):
        """Agrega las columnas de rol a la tabla usuarios si todavía no existen.
        Los usuarios que ya estaban creados quedan como 'admin'."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(usuarios)")
        columnas = {fila[1] for fila in cursor.fetchall()}
        if "rol" not in columnas:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT NOT NULL DEFAULT 'admin'")
        if "id_mecanico" not in columnas:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN id_mecanico INTEGER")
        if "id_cliente" not in columnas:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN id_cliente INTEGER")
        conn.commit()
        conn.close()

    def registrar_usuario(self, nombre, correo, contrasena, fecha_nacimiento):
        conn = get_connection()
        cursor = conn.cursor()
        hash_contrasena = generate_password_hash(contrasena)
        # El primer usuario del sistema es administrador; los demás se registran como cliente
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        rol = "admin" if cursor.fetchone()[0] == 0 else "cliente"
        try:
            cursor.execute(
                """INSERT INTO usuarios (nombre, correo, contrasena_hash, fecha_nacimiento, rol)
                   VALUES (?, ?, ?, ?, ?)""",
                (nombre, correo, hash_contrasena, fecha_nacimiento, rol)
            )
            conn.commit()
            nuevo_id = cursor.lastrowid
            conn.close()
            return nuevo_id, None
        except Exception:
            conn.close()
            return None, "Ese correo ya está registrado."

    def verificar_login(self, correo, contrasena):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id_usuario, nombre, contrasena_hash, rol, id_mecanico, id_cliente
               FROM usuarios WHERE correo = ?""",
            (correo,)
        )
        fila = cursor.fetchone()
        conn.close()

        if fila is None:
            return None

        id_usuario, nombre, hash_guardado, rol, id_mecanico, id_cliente = fila
        if check_password_hash(hash_guardado, contrasena):
            return {
                "id_usuario": id_usuario, "nombre": nombre, "rol": rol,
                "id_mecanico": id_mecanico, "id_cliente": id_cliente,
            }
        return None

    def listar_usuarios(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id_usuario, nombre, correo, rol, id_mecanico, id_cliente
               FROM usuarios ORDER BY id_usuario"""
        )
        filas = cursor.fetchall()
        conn.close()
        return filas

    def actualizar_rol(self, id_usuario, rol, id_mecanico, id_cliente):
        """Cambia el rol de un usuario y lo vincula con su mecánico o cliente.
        Devuelve None si todo salió bien, o un texto con el error."""
        if rol not in ROLES:
            return "El rol no es válido."

        if rol == "mecanico":
            if not id_mecanico:
                return "Para el rol Mecánico debes elegir el mecánico vinculado."
            id_cliente = None
        elif rol == "cliente":
            if not id_cliente:
                return "Para el rol Cliente debes elegir el cliente vinculado."
            id_mecanico = None
        else:
            id_mecanico = None
            id_cliente = None

        conn = get_connection()
        cursor = conn.cursor()

        # Siempre debe quedar al menos un administrador
        if rol != "admin":
            cursor.execute(
                "SELECT COUNT(*) FROM usuarios WHERE rol = 'admin' AND id_usuario != ?",
                (id_usuario,)
            )
            if cursor.fetchone()[0] == 0:
                conn.close()
                return "Debe existir al menos un administrador en el sistema."

        cursor.execute(
            "UPDATE usuarios SET rol = ?, id_mecanico = ?, id_cliente = ? WHERE id_usuario = ?",
            (rol, id_mecanico, id_cliente, id_usuario)
        )
        conn.commit()
        conn.close()
        return None