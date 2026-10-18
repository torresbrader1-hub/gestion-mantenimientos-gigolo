from datetime import datetime, date
from database import get_connection

DIAS_SEMANA = 7


class PagoService:

    def validar_periodo(self, fecha_inicio, fecha_fin):
        try:
            inicio = date.fromisoformat(fecha_inicio)
            fin = date.fromisoformat(fecha_fin)
        except (ValueError, TypeError):
            return "Debes indicar un periodo con fechas válidas."
        if fin < inicio:
            return "La fecha final no puede ser anterior a la inicial."
        if (fin - inicio).days + 1 > DIAS_SEMANA:
            return "El pago es semanal: el periodo no puede superar los 7 días."
        return None

    def calcular_pago(self, id_mecanico, fecha_inicio, fecha_fin):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_mantenimiento, tipo, precio, comision_mecanico, fecha_finalizacion
            FROM mantenimientos
            WHERE id_mecanico = ?
              AND estado = 'Finalizado'
              AND pagado = 0
              AND date(fecha_finalizacion) BETWEEN date(?) AND date(?)
            ORDER BY fecha_finalizacion
        """, (id_mecanico, fecha_inicio, fecha_fin))
        detalle = cursor.fetchall()
        conn.close()
        cantidad = len(detalle)
        valor_total = sum(fila[3] for fila in detalle)
        return detalle, cantidad, valor_total

    def registrar_pago(self, id_mecanico, fecha_inicio, fecha_fin, ids_mantenimiento):
        if not ids_mantenimiento:
            return None
        conn = get_connection()
        cursor = conn.cursor()
        marcas = ",".join("?" * len(ids_mantenimiento))
        cursor.execute(
            f"""SELECT id_mantenimiento, comision_mecanico FROM mantenimientos
                WHERE id_mecanico = ? AND estado = 'Finalizado' AND pagado = 0
                  AND id_mantenimiento IN ({marcas})""",
            [id_mecanico, *ids_mantenimiento]
        )
        filas = cursor.fetchall()
        if not filas:
            conn.close()
            return None

        cantidad = len(filas)
        valor_total = sum(fila[1] for fila in filas)
        fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO pagos (id_mecanico, fecha_inicio_periodo, fecha_fin_periodo,
                                cantidad_mantenimientos, valor_total, fecha_pago)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_mecanico, fecha_inicio, fecha_fin, cantidad, valor_total, fecha_pago))
        id_pago = cursor.lastrowid

        ids_pagados = [fila[0] for fila in filas]
        marcas_pagados = ",".join("?" * len(ids_pagados))
        cursor.execute(
            f"UPDATE mantenimientos SET pagado = 1, id_pago = ? WHERE id_mantenimiento IN ({marcas_pagados})",
            [id_pago, *ids_pagados]
        )
        conn.commit()
        conn.close()
        return id_pago

    def obtener_pago(self, id_pago):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id_pago, p.id_mecanico, me.nombre, p.fecha_inicio_periodo, p.fecha_fin_periodo,
                   p.cantidad_mantenimientos, p.valor_total, p.fecha_pago
            FROM pagos p JOIN mecanicos me ON p.id_mecanico = me.id_mecanico
            WHERE p.id_pago = ?
        """, (id_pago,))
        pago = cursor.fetchone()
        if not pago:
            conn.close()
            return None, []
        cursor.execute("""
            SELECT mt.id_mantenimiento, ma.placa, mt.tipo, mt.precio, mt.comision_mecanico, mt.fecha_finalizacion
            FROM mantenimientos mt JOIN maquinaria ma ON mt.id_maquina = ma.id_maquina
            WHERE mt.id_pago = ? ORDER BY mt.fecha_finalizacion
        """, (id_pago,))
        detalle = cursor.fetchall()
        conn.close()
        return pago, detalle

    def consultar_pagos(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id_pago, me.nombre, p.fecha_inicio_periodo, p.fecha_fin_periodo,
                   p.cantidad_mantenimientos, p.valor_total, p.fecha_pago
            FROM pagos p JOIN mecanicos me ON p.id_mecanico = me.id_mecanico
            ORDER BY p.id_pago DESC
        """)
        filas = cursor.fetchall()
        conn.close()
        return filas

    def consultar_pagos_por_mecanico(self, id_mecanico):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id_pago, me.nombre, p.fecha_inicio_periodo, p.fecha_fin_periodo,
                   p.cantidad_mantenimientos, p.valor_total, p.fecha_pago
            FROM pagos p JOIN mecanicos me ON p.id_mecanico = me.id_mecanico
            WHERE p.id_mecanico = ? ORDER BY p.id_pago DESC
        """, (id_mecanico,))
        filas = cursor.fetchall()
        conn.close()
        return filas

    def resumen_mecanico(self, id_mecanico):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(comision_mecanico), 0),
                   COALESCE(SUM(CASE WHEN pagado = 1 THEN comision_mecanico ELSE 0 END), 0),
                   COALESCE(SUM(CASE WHEN pagado = 0 THEN comision_mecanico ELSE 0 END), 0)
            FROM mantenimientos WHERE id_mecanico = ? AND estado = 'Finalizado'
        """, (id_mecanico,))
        generado, pagado, pendiente = cursor.fetchone()
        conn.close()
        return {"generado": generado, "pagado": pagado, "pendiente": pendiente}