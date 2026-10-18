from database import get_connection


class MecanicoService:

    def registrar_mecanico(self, identificacion, nombre, telefono):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO mecanicos (identificacion, nombre, telefono, disponible, jornada_horas)
               VALUES (?, ?, ?, 1, 8)""",
            (identificacion, nombre, telefono)
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
        conn.close()
        return nuevo_id

    def existe_identificacion(self, identificacion):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM mecanicos WHERE identificacion = ?", (identificacion,))
        existe = cursor.fetchone() is not None
        conn.close()
        return existe

    def consultar_mecanicos(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_mecanico, identificacion, nombre, telefono, disponible FROM mecanicos ORDER BY id_mecanico"
        )
        filas = cursor.fetchall()
        conn.close()
        return filas

    def buscar_por_id(self, id_mecanico):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_mecanico, identificacion, nombre, telefono, disponible FROM mecanicos WHERE id_mecanico = ?",
            (id_mecanico,)
        )
        fila = cursor.fetchone()
        conn.close()
        return fila

    def modificar_mecanico(self, id_mecanico, nombre, telefono):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE mecanicos SET nombre = ?, telefono = ? WHERE id_mecanico = ?",
            (nombre, telefono, id_mecanico)
        )
        conn.commit()
        actualizado = cursor.rowcount > 0
        conn.close()
        return actualizado

    def consultar_disponibles(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_mecanico, identificacion, nombre, telefono, disponible FROM mecanicos WHERE disponible = 1"
        )
        filas = cursor.fetchall()
        conn.close()
        return filas

    def cambiar_disponibilidad(self, id_mecanico, disponible):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE mecanicos SET disponible = ? WHERE id_mecanico = ?",
            (1 if disponible else 0, id_mecanico)
        )
        conn.commit()
        conn.close()