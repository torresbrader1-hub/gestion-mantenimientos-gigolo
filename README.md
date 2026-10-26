# Gestión de Mantenimientos – GIGOLÓ ETDM S.A.

Sistema web para gestionar el mantenimiento de maquinaria: clientes, máquinas, mecánicos, mantenimientos, pagos a mecánicos, facturación y reportes. Incluye tres roles con permisos distintos.

## Tecnologías

- Python 3 y Flask
- SQLite
- HTML, CSS y plantillas Jinja2

## Instalación

1. Clona el repositorio:

```
   git clone https://github.com/torresbrader1-hub/gestion-mantenimientos-gigolo.git
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
3. Abre (http://127.0.0.1:5000)en el navegador.
4. Regístrate: el primer usuario queda como Administrador. Los siguientes quedan como Cliente y el administrador les asigna el rol desde la sección Usuarios.

La base de datos `gigolo.db` se crea sola la primera vez que se ejecuta la aplicación.

## Roles y permisos

| Rol | Qué puede hacer |
|---|---|
| Administrador | Gestiona clientes, maquinaria, mecánicos, mantenimientos, pagos, facturas y su cobro, reportes, alertas y usuarios |
| Mecánico | Ve sus trabajos asignados, los acepta, inicia y finaliza, edita observaciones y consulta su comisión y pagos |
| Cliente | Ve sus máquinas, escribe su solicitud, consulta las observaciones del taller y el estado de sus facturas, y descarga el PDF |
## Autores

- Brader Torres
- Angel Ojeda
- Jose Tordecilla