from database import get_connection

TIPOS_POR_CATEGORIA = {
    "Agrícola": ["Tractor", "Cosechadora", "Sembradora"],
    "Industrial": ["Compresor", "Generador Eléctrico", "Montacargas"],
    "Construcción": ["Excavadora", "Retroexcavadora", "Volqueta"],
}
CATEGORIAS = list(TIPOS_POR_CATEGORIA.keys())
ESTADOS = ["Disponible", "En mantenimiento", "Listo para entrega"]

SELECT_MAQUINAS = """
    SELECT m.id_maquina, m.placa, m.tipo, m.marca, m.modelo, m.estado,
           c.nombre, m.id_cliente_propietario, m.categoria
    FROM maquinaria m
    LEFT JOIN clientes c ON m.id_cliente_propietario = c.id_cliente
"""


def categoria_de(tipo):
    for categoria, tipos in TIPOS_POR_CATEGORIA.items():
        if tipo in tipos:
            return categoria
    return "Sin clasificar"


class MaquinariaService:

    def registrar_maquina(self, placa, tipo, marca, modelo, id_cliente):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO maquinaria (placa, tipo, marca, modelo, id_cliente_propietario, estado, categoria)
               VALUES (?, ?, ?, ?, ?, 'Disponible', ?)""",
            (placa, tipo, marca, modelo, id_cliente, categoria_de(tipo))
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
        conn.close()
        return nuevo_id

    def consultar_maquinas(self, categoria=None, estado=None):
        condiciones = []
        parametros = []
        if categoria:
            condiciones.append("m.categoria = ?")
            parametros.append(categoria)
        if estado:
            condiciones.append("m.estado = ?")
            parametros.append(estado)
        sql = SELECT_MAQUINAS
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY m.id_maquina"
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, parametros)
        filas = cursor.fetchall()
        conn.close()
        return filas
    
    def consultar_disponibles(self):
        return self.consultar_maquinas(estado="Disponible")

    def contar_por_categoria(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT categoria, COUNT(*) FROM maquinaria GROUP BY categoria")
        conteos = {fila[0]: fila[1] for fila in cursor.fetchall()}
        conn.close()
        return [(c, conteos.get(c, 0)) for c in CATEGORIAS]

    def buscar_por_id(self, id_maquina):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id_maquina, placa, tipo, marca, modelo, estado, id_cliente_propietario, categoria
               FROM maquinaria WHERE id_maquina = ?""",
            (id_maquina,)
        )
        fila = cursor.fetchone()
        conn.close()
        return fila

    def consultar_por_cliente(self, id_cliente):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_maquina, placa, tipo, marca, modelo, estado FROM maquinaria WHERE id_cliente_propietario = ?",
            (id_cliente,)
        )
        filas = cursor.fetchall()
        conn.close()
        return filas

    def modificar_maquina(self, id_maquina, tipo, marca, modelo):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE maquinaria SET tipo = ?, marca = ?, modelo = ?, categoria = ? WHERE id_maquina = ?",
            (tipo, marca, modelo, categoria_de(tipo), id_maquina)
        )
        conn.commit()
        actualizado = cursor.rowcount > 0
        conn.close()
        return actualizado