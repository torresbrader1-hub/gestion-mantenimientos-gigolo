from datetime import datetime
from database import get_connection

METODOS_PAGO = ("Efectivo", "Transferencia")


class FacturaService:

    def generar_factura(self, id_mantenimiento):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT estado, precio FROM mantenimientos WHERE id_mantenimiento = ?",
            (id_mantenimiento,)
        )
        fila = cursor.fetchone()
        if not fila or fila[0] != "Finalizado":
            conn.close()
            return None

        cursor.execute("SELECT id_factura FROM facturas WHERE id_mantenimiento = ?", (id_mantenimiento,))
        existente = cursor.fetchone()
        if existente:
            conn.close()
            return existente[0]

        cursor.execute(
            """INSERT INTO facturas (numero_factura, id_mantenimiento, fecha_generacion, valor_total)
               VALUES ('', ?, ?, ?)""",
            (id_mantenimiento, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fila[1])
        )
        id_factura = cursor.lastrowid
        cursor.execute(
            "UPDATE facturas SET numero_factura = ? WHERE id_factura = ?",
            (f"FAC-{id_factura:04d}", id_factura)
        )
        conn.commit()
        conn.close()
        return id_factura

    def obtener_factura(self, id_factura):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fa.id_factura, fa.numero_factura, fa.fecha_generacion, fa.valor_total,
                   mt.id_mantenimiento, mt.tipo, mt.observaciones, mt.fecha_registro, mt.fecha_finalizacion,
                   ma.placa, ma.tipo, ma.marca, ma.modelo,
                   cl.nombre, cl.identificacion, cl.telefono, me.nombre,
                   fa.estado_pago, fa.metodo_pago, fa.fecha_pago,
                   ma.id_cliente_propietario, ma.id_maquina, mt.fecha_salida
            FROM facturas fa
            JOIN mantenimientos mt ON fa.id_mantenimiento = mt.id_mantenimiento
            JOIN maquinaria ma ON mt.id_maquina = ma.id_maquina
            LEFT JOIN clientes cl ON ma.id_cliente_propietario = cl.id_cliente
            JOIN mecanicos me ON mt.id_mecanico = me.id_mecanico
            WHERE fa.id_factura = ?
        """, (id_factura,))
        f = cursor.fetchone()
        conn.close()
        if not f:
            return None
        return {
            "id_factura": f[0], "numero_factura": f[1], "fecha_generacion": f[2], "valor_total": f[3],
            "id_mantenimiento": f[4], "tipo_mantenimiento": f[5], "observaciones": f[6],
            "fecha_registro": f[7], "fecha_finalizacion": f[8],
            "placa": f[9], "tipo_maquina": f[10], "marca": f[11], "modelo": f[12],
            "cliente_nombre": f[13] or "Sin asignar", "cliente_identificacion": f[14] or "-",
            "cliente_telefono": f[15] or "-", "mecanico_nombre": f[16],
            "estado_pago": f[17] or "Pendiente", "metodo_pago": f[18], "fecha_pago": f[19],
            "id_cliente": f[20], "id_maquina": f[21], "fecha_salida": f[22],
        }

    def consultar_facturas(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fa.id_factura, fa.numero_factura, fa.fecha_generacion, cl.nombre,
                   ma.placa, mt.tipo, fa.valor_total, mt.id_mantenimiento, fa.estado_pago
            FROM facturas fa
            JOIN mantenimientos mt ON fa.id_mantenimiento = mt.id_mantenimiento
            JOIN maquinaria ma ON mt.id_maquina = ma.id_maquina
            LEFT JOIN clientes cl ON ma.id_cliente_propietario = cl.id_cliente
            ORDER BY fa.id_factura DESC
        """)
        filas = cursor.fetchall()
        conn.close()
        return filas

    def registrar_cobro(self, id_factura, metodo_pago):
        """El cliente pagó en el taller: marca la factura como Pagada.
        Devuelve None si salió bien, o un texto con el error."""
        if metodo_pago not in METODOS_PAGO:
            return "Elige si el pago fue en efectivo o por transferencia."
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT estado_pago FROM facturas WHERE id_factura = ?", (id_factura,))
        fila = cursor.fetchone()
        if not fila:
            conn.close()
            return "La factura no existe."
        if fila[0] == "Pagada":
            conn.close()
            return "Esta factura ya está pagada."
        cursor.execute(
            "UPDATE facturas SET estado_pago = 'Pagada', metodo_pago = ?, fecha_pago = ? WHERE id_factura = ?",
            (metodo_pago, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_factura)
        )
        conn.commit()
        conn.close()
        return None

    def esta_pagada(self, id_mantenimiento):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT estado_pago FROM facturas WHERE id_mantenimiento = ?", (id_mantenimiento,))
        fila = cursor.fetchone()
        conn.close()
        return fila is not None and fila[0] == "Pagada"