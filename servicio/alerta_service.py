from datetime import date
from database import get_connection
from servicio.mantenimiento_service import JORNADA_HORAS


class AlertaService:

    def mecanicos_a_tope_hoy(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT me.id_mecanico, me.nombre, SUM(mt.duracion_horas) AS horas
            FROM mantenimientos mt
            JOIN mecanicos me ON mt.id_mecanico = me.id_mecanico
            WHERE mt.estado != 'Cancelado' AND date(mt.fecha_registro) = ?
            GROUP BY me.id_mecanico
            HAVING horas >= ?
        """, (date.today().isoformat(), JORNADA_HORAS))
        filas = cursor.fetchall()
        conn.close()
        return filas

    def finalizados_sin_factura(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT mt.id_mantenimiento, ma.placa, mt.tipo, cl.nombre
            FROM mantenimientos mt
            JOIN maquinaria ma ON mt.id_maquina = ma.id_maquina
            LEFT JOIN clientes cl ON ma.id_cliente_propietario = cl.id_cliente
            LEFT JOIN facturas fa ON fa.id_mantenimiento = mt.id_mantenimiento
            WHERE mt.estado = 'Finalizado' AND fa.id_factura IS NULL
            ORDER BY mt.id_mantenimiento DESC
        """)
        filas = cursor.fetchall()
        conn.close()
        return filas

    def maquinas_en_mantenimiento(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.id_maquina, m.placa, m.tipo, c.nombre
            FROM maquinaria m
            LEFT JOIN clientes c ON m.id_cliente_propietario = c.id_cliente
            WHERE m.estado = 'En mantenimiento'
        """)
        filas = cursor.fetchall()
        conn.close()
        return filas

    def generar_alertas(self):
        return {
            "mecanicos_tope": self.mecanicos_a_tope_hoy(),
            "sin_factura": self.finalizados_sin_factura(),
            "maquinas_ocupadas": self.maquinas_en_mantenimiento(),
        }