import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "gigolo.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_base_datos():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
            identificacion TEXT NOT NULL,
            nombre TEXT NOT NULL,
            telefono TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maquinaria (
            id_maquina INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL,
            tipo TEXT NOT NULL,
            marca TEXT,
            modelo TEXT,
            id_cliente_propietario INTEGER,
            estado TEXT DEFAULT 'Disponible',
            categoria TEXT,
            FOREIGN KEY (id_cliente_propietario) REFERENCES clientes(id_cliente)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mecanicos (
            id_mecanico INTEGER PRIMARY KEY AUTOINCREMENT,
            identificacion TEXT NOT NULL,
            nombre TEXT NOT NULL,
            telefono TEXT,
            disponible INTEGER DEFAULT 1,
            jornada_horas INTEGER DEFAULT 8
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mantenimientos (
            id_mantenimiento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_maquina INTEGER NOT NULL,
            id_mecanico INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            precio REAL NOT NULL,
            comision_mecanico REAL NOT NULL,
            observaciones TEXT,
            estado TEXT DEFAULT 'Pendiente',
            fecha_registro TEXT,
            fecha_inicio TEXT,
            fecha_finalizacion TEXT,
            fecha_salida TEXT,
            duracion_horas INTEGER DEFAULT 2,
            pagado INTEGER DEFAULT 0,
            FOREIGN KEY (id_maquina) REFERENCES maquinaria(id_maquina),
            FOREIGN KEY (id_mecanico) REFERENCES mecanicos(id_mecanico)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT NOT NULL UNIQUE,
            contrasena_hash TEXT NOT NULL,
            fecha_nacimiento TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id_pago INTEGER PRIMARY KEY AUTOINCREMENT,
            id_mecanico INTEGER NOT NULL,
            fecha_inicio_periodo TEXT NOT NULL,
            fecha_fin_periodo TEXT NOT NULL,
            cantidad_mantenimientos INTEGER NOT NULL,
            valor_total REAL NOT NULL,
            fecha_pago TEXT NOT NULL,
            FOREIGN KEY (id_mecanico) REFERENCES mecanicos(id_mecanico)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id_factura INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_factura TEXT,
            id_mantenimiento INTEGER NOT NULL UNIQUE,
            fecha_generacion TEXT NOT NULL,
            valor_total REAL NOT NULL,
            FOREIGN KEY (id_mantenimiento) REFERENCES mantenimientos(id_mantenimiento)
        )
    """)

    columnas = [fila[1] for fila in cursor.execute("PRAGMA table_info(mantenimientos)")]
    if "id_pago" not in columnas:
        cursor.execute("ALTER TABLE mantenimientos ADD COLUMN id_pago INTEGER")
   
    if "observaciones_cliente" not in columnas:
        cursor.execute("ALTER TABLE mantenimientos ADD COLUMN observaciones_cliente TEXT")

    columnas_fac = [fila[1] for fila in cursor.execute("PRAGMA table_info(facturas)")]
    if "estado_pago" not in columnas_fac:
        cursor.execute("ALTER TABLE facturas ADD COLUMN estado_pago TEXT NOT NULL DEFAULT 'Pendiente'")
    if "metodo_pago" not in columnas_fac:
        cursor.execute("ALTER TABLE facturas ADD COLUMN metodo_pago TEXT")
    if "fecha_pago" not in columnas_fac:
        cursor.execute("ALTER TABLE facturas ADD COLUMN fecha_pago TEXT")
    conn.commit()
    conn.close()