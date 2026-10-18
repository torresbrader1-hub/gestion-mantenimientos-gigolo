from datetime import datetime, date
from database import get_connection

PRECIOS = {
    "Preventivo": 300000,
    "General": 400000,
    "Correctivo": 500000,
}
PORCENTAJE_COMISION = 0.30
DURACION_HORAS = 2
JORNADA_HORAS = 8

TRANSICIONES = {
    "Pendiente": ("En proceso", "Cancelado"),
    "En proceso": ("Finalizado",),
}

CAMPOS_DETALLE = """
    mt.id_mantenimiento, ma.placa, cl.nombre, me.nombre,
    mt.tipo, mt.precio, mt.comision_mecanico, mt.estado,
    mt.observaciones, mt.id_mecanico, mt.fecha_registro, mt.fecha_finalizacion,
    mt.fecha_inicio, mt.fecha_salida, mt.duracion_horas, mt.pagado,
    mt.id_maquina, fa.id_factura, fa.estado_pago, mt.observaciones_cliente
"""

JOINS_DETALLE = """
    FROM mantenimientos mt
    JOIN maquinaria ma ON mt.id_maquina = ma.id_maquina
    LEFT JOIN clientes cl ON ma.id_cliente_propietario = cl.id_cliente
    JOIN mecanicos me ON mt.id_mecanico = me.id_mecanico
    LEFT JOIN facturas fa ON fa.id_mantenimiento = mt.id_mantenimiento
"""


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class MantenimientoService:

    def registrar_mantenimiento(self, id_maquina, id_mecanico, tipo, observaciones):
        precio = PRECIOS.get(tipo, 0)
        comision = precio * PORCENTAJE_COMISION

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO mantenimientos
               (id_maquina, id_mecanico, tipo, precio, comision_mecanico, observaciones,
                estado, fecha_registro, duracion_horas)
               VALUES (?, ?, ?, ?, ?, ?, 'Pendiente', ?, ?)""",
            (id_maquina, id_mecanico, tipo, precio, comision, observaciones, ahora(), DURACION_HORAS)
        )
        nuevo_id = cursor.lastrowid
        cursor.execute("UPDATE mecanicos SET disponible = 0 WHERE id_mecanico = ?", (id_mecanico,))
        cursor.execute("UPDATE maquinaria SET estado = 'En mantenimiento' WHERE id_maquina = ?", (id_maquina,))
        conn.commit()
        conn.close()
        return nuevo_id

    def consultar_mantenimientos(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {CAMPOS_DETALLE} {JOINS_DETALLE} ORDER BY mt.id_mantenimiento DESC")
        filas = cursor.fetchall()
        conn.close()
        return filas

    def consultar_por_estado(self, estado):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {CAMPOS_DETALLE} {JOINS_DETALLE} WHERE mt.estado = ? ORDER BY mt.id_mantenimiento DESC",
            (estado,)
        )
        filas = cursor.fetchall()
        conn.close()
        return filas

    def consultar_por_maquina(self, id_maquina):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {CAMPOS_DETALLE} {JOINS_DETALLE} WHERE mt.id_maquina = ? ORDER BY mt.id_mantenimiento DESC",
            (id_maquina,)
        )
        filas = cursor.fetchall()
        conn.close()
        return filas

    def buscar_por_id(self, id_mantenimiento):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {CAMPOS_DETALLE} {JOINS_DETALLE} WHERE mt.id_mantenimiento = ?",
            (id_mantenimiento,)
        )
        fila = cursor.fetchone()
        conn.close()
        return fila

    def buscar(self, consulta, estado=None):
        condiciones = [
            "ma.placa LIKE ?",
            "cl.nombre LIKE ?",
            "me.nombre LIKE ?",
            "mt.tipo LIKE ?"
        ]
        patron = f"%{consulta}%"
        parametros = [patron, patron, patron, patron]

        if consulta.isdigit():
            condiciones.append("mt.id_mantenimiento = ?")
            parametros.append(int(consulta))

        sql = f"SELECT {CAMPOS_DETALLE} {JOINS_DETALLE} WHERE (" + " OR ".join(condiciones) + ")"

        if estado:
            sql += " AND mt.estado = ?"
            parametros.append(estado)

        sql += " ORDER BY mt.id_mantenimiento DESC"

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, parametros)
        filas = cursor.fetchall()
        conn.close()
        return filas

    def consultar_por_mecanico(self, id_mecanico):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {CAMPOS_DETALLE} {JOINS_DETALLE} WHERE mt.id_mecanico = ? ORDER BY mt.id_mantenimiento DESC",
            (id_mecanico,)
        )
        filas = cursor.fetchall()
        conn.close()
        return filas

    def mecanicos_ocupados(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT id_mecanico FROM mantenimientos WHERE estado IN ('Pendiente', 'En proceso')"
        )
        ids = {fila[0] for fila in cursor.fetchall()}
        conn.close()
        return ids

    def contar_mantenimientos(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM mantenimientos")
        total = cursor.fetchone()[0]
        conn.close()
        return total

    def actualizar_observaciones(self, id_mantenimiento, observaciones):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE mantenimientos SET observaciones = ? WHERE id_mantenimiento = ?",
            (observaciones, id_mantenimiento)
        )
        conn.commit()
        conn.close()
    def actualizar_observaciones_cliente(self, id_mantenimiento, texto):
        """El cliente indica qué quiere que se haga en su máquina.
        Solo se puede cambiar mientras el trabajo no haya terminado."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE mantenimientos SET observaciones_cliente = ?
               WHERE id_mantenimiento = ? AND estado IN ('Pendiente', 'En proceso')""",
            (texto.strip()[:500], id_mantenimiento)
        )
        cambiado = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return cambiado
    
    def cambiar_estado(self, id_mantenimiento, nuevo_estado):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT estado, id_mecanico, id_maquina FROM mantenimientos WHERE id_mantenimiento = ?",
            (id_mantenimiento,)
        )
        fila = cursor.fetchone()
        if not fila:
            conn.close()
            return False

        estado_actual, id_mecanico, id_maquina = fila
        if nuevo_estado not in TRANSICIONES.get(estado_actual, ()):
            conn.close()
            return False

        if nuevo_estado == "En proceso":
            cursor.execute(
                "UPDATE mantenimientos SET estado = ?, fecha_inicio = ? WHERE id_mantenimiento = ?",
                (nuevo_estado, ahora(), id_mantenimiento)
            )
        elif nuevo_estado == "Finalizado":
            cursor.execute(
                "UPDATE mantenimientos SET estado = ?, fecha_finalizacion = ? WHERE id_mantenimiento = ?",
                (nuevo_estado, ahora(), id_mantenimiento)
            )
            cursor.execute("UPDATE mecanicos SET disponible = 1 WHERE id_mecanico = ?", (id_mecanico,))
            cursor.execute("UPDATE maquinaria SET estado = 'Listo para entrega' WHERE id_maquina = ?", (id_maquina,))
        elif nuevo_estado == "Cancelado":
            cursor.execute(
                "UPDATE mantenimientos SET estado = ? WHERE id_mantenimiento = ?",
                (nuevo_estado, id_mantenimiento)
            )
            cursor.execute("UPDATE mecanicos SET disponible = 1 WHERE id_mecanico = ?", (id_mecanico,))
            cursor.execute("UPDATE maquinaria SET estado = 'Disponible' WHERE id_maquina = ?", (id_maquina,))

        conn.commit()
        conn.close()
        return True

    def registrar_salida(self, id_mantenimiento):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT estado, fecha_salida, id_maquina FROM mantenimientos WHERE id_mantenimiento = ?",
            (id_mantenimiento,)
        )
        fila = cursor.fetchone()
        if not fila or fila[0] != "Finalizado" or fila[1]:
            conn.close()
            return False

        cursor.execute(
            "UPDATE mantenimientos SET fecha_salida = ? WHERE id_mantenimiento = ?",
            (ahora(), id_mantenimiento)
        )
        cursor.execute("UPDATE maquinaria SET estado = 'Disponible' WHERE id_maquina = ?", (fila[2],))
        conn.commit()
        conn.close()
        return True

    def horas_hoy_por_mecanico(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id_mecanico, SUM(duracion_horas) FROM mantenimientos
               WHERE estado != 'Cancelado' AND date(fecha_registro) = ?
               GROUP BY id_mecanico""",
            (date.today().isoformat(),)
        )
        resultado = {fila[0]: fila[1] for fila in cursor.fetchall()}
        conn.close()
        return resultado

    def contar_finalizados_por_mecanico(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_mecanico, COUNT(*) FROM mantenimientos WHERE estado = 'Finalizado' GROUP BY id_mecanico"
        )
        resultado = {fila[0]: fila[1] for fila in cursor.fetchall()}
        conn.close()
        return resultado

    def ingresos_por_servicio(self, fecha_inicio=None, fecha_fin=None):
        sql = "SELECT tipo, COUNT(*), SUM(precio) FROM mantenimientos WHERE estado = 'Finalizado'"
        parametros = []

        if fecha_inicio:
            sql += " AND date(fecha_finalizacion) >= date(?)"
            parametros.append(fecha_inicio)

        if fecha_fin:
            sql += " AND date(fecha_finalizacion) <= date(?)"
            parametros.append(fecha_fin)

        sql += " GROUP BY tipo"

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, parametros)
        datos = {fila[0]: (fila[1], fila[2]) for fila in cursor.fetchall()}
        conn.close()

        return [
            (tipo, datos.get(tipo, (0, 0))[0], datos.get(tipo, (0, 0))[1])
            for tipo in PRECIOS
        ]