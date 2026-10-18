from database import get_connection


class ClienteService:

    def registrar_cliente(self, identificacion, nombre, telefono):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (identificacion, nombre, telefono) VALUES (?, ?, ?)",
            (identificacion, nombre, telefono)
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
        conn.close()
        return nuevo_id

    def consultar_clientes(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_cliente, identificacion, nombre, telefono FROM clientes ORDER BY id_cliente")
        filas = cursor.fetchall()
        conn.close()
        return filas

    def buscar(self, consulta):
        conn = get_connection()
        cursor = conn.cursor()
        patron = f"%{consulta}%"
        cursor.execute(
            """SELECT id_cliente, identificacion, nombre, telefono FROM clientes
               WHERE nombre LIKE ? OR identificacion LIKE ? ORDER BY id_cliente""",
            (patron, patron)
        )
        filas = cursor.fetchall()
        conn.close()
        return filas
    
    def buscar_por_id(self, id_cliente):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_cliente, identificacion, nombre, telefono FROM clientes WHERE id_cliente = ?",
            (id_cliente,)
        )
        fila = cursor.fetchone()
        conn.close()
        return fila

    def modificar_cliente(self, id_cliente, nuevo_nombre, nuevo_telefono):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE clientes SET nombre = ?, telefono = ? WHERE id_cliente = ?",
            (nuevo_nombre, nuevo_telefono, id_cliente)
        )
        conn.commit()
        actualizado = cursor.rowcount > 0
        conn.close()
        return actualizado