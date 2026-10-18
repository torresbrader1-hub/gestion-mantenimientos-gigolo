from database import get_connection


class ReporteService:

    def generar_reporte(self, fecha_inicio=None, fecha_fin=None):
        conn = get_connection()
        cursor = conn.cursor()

        condiciones = ["estado = 'Finalizado'"]
        parametros = []
        if fecha_inicio:
            condiciones.append("date(fecha_finalizacion) >= date(?)")
            parametros.append(fecha_inicio)
        if fecha_fin:
            condiciones.append("date(fecha_finalizacion) <= date(?)")
            parametros.append(fecha_fin)
        where = " AND ".join(condiciones)

        cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(precio),0) FROM mantenimientos WHERE {where}", parametros)
        cantidad_mantenimientos, ingresos_total = cursor.fetchone()

        cursor.execute(f"SELECT COUNT(DISTINCT id_maquina) FROM mantenimientos WHERE {where}", parametros)
        maquinas_atendidas = cursor.fetchone()[0]

        condiciones_pago = []
        parametros_pago = []
        if fecha_inicio:
            condiciones_pago.append("date(fecha_pago) >= date(?)")
            parametros_pago.append(fecha_inicio)
        if fecha_fin:
            condiciones_pago.append("date(fecha_pago) <= date(?)")
            parametros_pago.append(fecha_fin)
        where_pago = (" WHERE " + " AND ".join(condiciones_pago)) if condiciones_pago else ""
        cursor.execute(f"SELECT COALESCE(SUM(valor_total),0) FROM pagos{where_pago}", parametros_pago)
        pagos_total = cursor.fetchone()[0]

        conn.close()
        return {
            "cantidad_mantenimientos": cantidad_mantenimientos,
            "ingresos_total": ingresos_total,
            "maquinas_atendidas": maquinas_atendidas,
            "pagos_total": pagos_total,
        }

    def detalle_servicios(self, fecha_inicio=None, fecha_fin=None):
        condiciones = ["mt.estado = 'Finalizado'"]
        parametros = []
        if fecha_inicio:
            condiciones.append("date(mt.fecha_finalizacion) >= date(?)")
            parametros.append(fecha_inicio)
        if fecha_fin:
            condiciones.append("date(mt.fecha_finalizacion) <= date(?)")
            parametros.append(fecha_fin)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT mt.id_mantenimiento, mt.fecha_finalizacion, ma.placa, cl.nombre,
                   mt.tipo, me.nombre, mt.precio
            FROM mantenimientos mt
            JOIN maquinaria ma ON mt.id_maquina = ma.id_maquina
            LEFT JOIN clientes cl ON ma.id_cliente_propietario = cl.id_cliente
            JOIN mecanicos me ON mt.id_mecanico = me.id_mecanico
            WHERE {" AND ".join(condiciones)}
            ORDER BY mt.fecha_finalizacion DESC
        """, parametros)
        filas = cursor.fetchall()
        conn.close()
        return filas
    