# Gestión de Mantenimientos – GIGOLÓ ETDM S.A.

Sistema web para gestionar el mantenimiento de maquinaria: clientes, máquinas, mecánicos, mantenimientos, pagos a mecánicos, facturación y reportes. Incluye tres roles con permisos distintos.

## Tecnologías

- Python 3 y Flask
- SQLite
- HTML, CSS y plantillas Jinja2

## Instalación

1. Clona el repositorio:

```
   git clone https://github.com/USUARIO/REPO.git
   cd REPO
```

2. Instala las dependencias:

```
   python -m pip install -r requirements.txt
```

## Uso

1. (Opcional) Define una clave secreta para las sesiones:

```
   $env:SECRET_KEY = "una_clave_larga_y_aleatoria"
```

2. Ejecuta `python app.py`.
3. Abre http://127.0.0.1:5000 en el navegador.
4. Regístrate: el primer usuario queda como Administrador. Los siguientes quedan como Cliente y el administrador les asigna el rol desde la sección Usuarios.

La base de datos `gigolo.db` se crea sola la primera vez que se ejecuta la aplicación.

## Autores

- Brader Torres
- Angel Ojeda
- Jose Tordecilla