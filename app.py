import os
from functools import wraps 
from flask import Flask, render_template, request, redirect, url_for, session, Response
from database import inicializar_base_datos
from validaciones import validar_identificacion, validar_nombre, validar_telefono
from pdf_factura import generar_pdf_factura
from servicio.cliente_service import ClienteService
from servicio.maquinaria_service import MaquinariaService, CATEGORIAS, ESTADOS
from servicio.mecanico_service import MecanicoService
from servicio.mantenimiento_service import MantenimientoService, PRECIOS, JORNADA_HORAS, DURACION_HORAS
from servicio.usuario_service import UsuarioService
from servicio.pago_service import PagoService
from servicio.factura_service import FacturaService
from servicio.reporte_service import ReporteService
from servicio.alerta_service import AlertaService

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-solo-para-desarrollo")

cliente_service = ClienteService()
maquinaria_service = MaquinariaService()
mecanico_service = MecanicoService()
mantenimiento_service = MantenimientoService()
usuario_service = UsuarioService()
pago_service = PagoService()
factura_service = FacturaService()
reporte_service = ReporteService()
alerta_service = AlertaService()


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session or "rol" not in session:
            session.clear()
            return redirect(url_for("login"))
        return vista(*args, **kwargs)
    return envoltura


def roles_requeridos(*roles):
    """Deja entrar solo a los usuarios cuyo rol esté en la lista."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if "usuario_id" not in session or "rol" not in session:
                session.clear()
                return redirect(url_for("login"))
            if session.get("rol") not in roles:
                return redirect(url_for("sin_permiso"))
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def es_admin():
    return session.get("rol") == "admin"


def ids_mantenimientos_propios():
    """IDs de los mantenimientos asignados al mecánico que inició sesión."""
    filas = mantenimiento_service.consultar_por_mecanico(session.get("id_mecanico"))
    return {fila[0] for fila in filas}


def ids_maquinas_propias():
    """IDs de las máquinas del cliente que inició sesión."""
    filas = maquinaria_service.consultar_por_cliente(session.get("id_cliente"))
    return {fila[0] for fila in filas}

def ids_mantenimientos_de_cliente():
    """IDs de los mantenimientos de las máquinas del cliente que inició sesión."""
    ids = set()
    for id_maquina in ids_maquinas_propias():
        for fila in mantenimiento_service.consultar_por_maquina(id_maquina):
            ids.add(fila[0])
    return ids

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        correo = request.form["correo"]
        contrasena = request.form["contrasena"]
        fecha_nacimiento = request.form.get("fecha_nacimiento", "")
        nuevo_id, error = usuario_service.registrar_usuario(nombre, correo, contrasena, fecha_nacimiento)
        if error:
            return render_template("registro.html", error=error)
        return redirect(url_for("login"))
    return render_template("registro.html", error=None)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"]
        contrasena = request.form["contrasena"]
        usuario = usuario_service.verificar_login(correo, contrasena)
        if usuario:
            session["usuario_id"] = usuario["id_usuario"]
            session["usuario_nombre"] = usuario["nombre"]
            session["rol"] = usuario["rol"]
            session["id_mecanico"] = usuario["id_mecanico"]
            session["id_cliente"] = usuario["id_cliente"]
            return redirect(url_for("index"))
        return render_template("login.html", error="Correo o contraseña incorrectos.")
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def datos_panel_cliente(id_cliente):
    """Reúne lo que ve el cliente en su panel: sus datos, máquinas, mantenimientos y facturas."""
    cliente = cliente_service.buscar_por_id(id_cliente)
    if not cliente:
        return None
    maquinas = maquinaria_service.consultar_por_cliente(id_cliente)
    mantenimientos = []
    for maquina in maquinas:
        mantenimientos.extend(mantenimiento_service.consultar_por_maquina(maquina[0]))
    mantenimientos.sort(key=lambda fila: fila[0], reverse=True)

    activos = [m for m in mantenimientos if m[7] in ("Pendiente", "En proceso")]
    por_pagar = [m for m in mantenimientos if m[17] and m[18] != "Pagada"]
    return {
        "cliente": cliente, "maquinas": maquinas, "mantenimientos": mantenimientos[:10],
        "total_activos": len(activos), "facturas_pendientes": len(por_pagar),
        "total_por_pagar": sum(m[5] for m in por_pagar),
    }


def datos_panel_mecanico(id_mecanico):
    """Reúne lo que ve el mecánico en su panel: trabajos, horas del día y comisión."""
    mecanico = mecanico_service.buscar_por_id(id_mecanico)
    if not mecanico:
        return None
    asignados = mantenimiento_service.consultar_por_mecanico(id_mecanico)
    por_atender = sorted((m for m in asignados if m[7] in ("Pendiente", "En proceso")), key=lambda m: m[0])
    finalizados = [m for m in asignados if m[7] == "Finalizado"]
    horas_hoy = mantenimiento_service.horas_hoy_por_mecanico().get(id_mecanico, 0) or 0
    generada = sum(m[6] for m in finalizados)
    pagada = sum(m[6] for m in finalizados if m[15])
    return {
        "mecanico": mecanico, "por_atender": por_atender, "finalizados": finalizados[:10],
        "total_finalizados": len(finalizados), "horas_hoy": horas_hoy, "jornada": JORNADA_HORAS,
        "porcentaje_jornada": min(100, round(horas_hoy / JORNADA_HORAS * 100)),
        "comision_generada": generada, "comision_pagada": pagada,
        "comision_pendiente": generada - pagada,
    }

@app.route("/")
@login_requerido
def index():
    rol = session.get("rol")
    if rol == "mecanico":
        datos = datos_panel_mecanico(session.get("id_mecanico")) if session.get("id_mecanico") else None
        if not datos:
            return redirect(url_for("sin_permiso"))
        return render_template("mecanico_panel.html", **datos)
    if rol == "cliente":
        datos = datos_panel_cliente(session.get("id_cliente")) if session.get("id_cliente") else None
        if not datos:
            return redirect(url_for("sin_permiso"))
        return render_template("cliente_panel.html", **datos)

    total_clientes = len(cliente_service.consultar_clientes())
    total_maquinas = len(maquinaria_service.consultar_maquinas())
    total_mecanicos = len(mecanico_service.consultar_mecanicos())
    disponibles = len(mecanico_service.consultar_disponibles())
    total_mantenimientos = mantenimiento_service.contar_mantenimientos()
    return render_template(
        "index.html",
        total_clientes=total_clientes, total_maquinas=total_maquinas,
        total_mecanicos=total_mecanicos, disponibles=disponibles,
        total_mantenimientos=total_mantenimientos,
        usuario_nombre=session.get("usuario_nombre"),
    )


@app.route("/clientes")
@roles_requeridos("admin")
def clientes():
    busqueda = request.args.get("q", "").strip()
    if busqueda:
        lista = cliente_service.buscar(busqueda)
    else:
        lista = cliente_service.consultar_clientes()
    return render_template("clientes.html", clientes=lista, busqueda=busqueda)

@app.route("/clientes/nuevo", methods=["GET", "POST"])
@roles_requeridos("admin")
def nuevo_cliente():
    if request.method == "POST":
        identificacion = request.form.get("identificacion", "").strip()
        nombre = " ".join(request.form.get("nombre", "").split())
        telefono = request.form.get("telefono", "").strip()

        errores = [e for e in (
            validar_identificacion(identificacion),
            validar_nombre(nombre),
            validar_telefono(telefono),
        ) if e]
        if errores:
            return render_template("cliente_form.html", errores=errores, datos=request.form)

        cliente_service.registrar_cliente(identificacion, nombre, telefono)
        return redirect(url_for("clientes"))
    return render_template("cliente_form.html", errores=[], datos={})


@app.route("/clientes/editar/<int:id_cliente>", methods=["GET", "POST"])
@roles_requeridos("admin")
def editar_cliente(id_cliente):
    cliente = cliente_service.buscar_por_id(id_cliente)
    if not cliente:
        return redirect(url_for("clientes"))

    if request.method == "POST":
        nombre = " ".join(request.form.get("nombre", "").split())
        telefono = request.form.get("telefono", "").strip()

        errores = [e for e in (validar_nombre(nombre), validar_telefono(telefono)) if e]
        if errores:
            return render_template("cliente_editar.html", cliente=cliente, errores=errores, datos=request.form)

        cliente_service.modificar_cliente(id_cliente, nombre, telefono)
        return redirect(url_for("clientes"))
    return render_template("cliente_editar.html", cliente=cliente, errores=[], datos={})

@app.route("/clientes/<int:id_cliente>")
@roles_requeridos("admin", "cliente")
def detalle_cliente(id_cliente):
    if session.get("rol") == "cliente":
        return redirect(url_for("index"))
    if not es_admin() and id_cliente != session.get("id_cliente"):
        return redirect(url_for("sin_permiso"))
    cliente = cliente_service.buscar_por_id(id_cliente)
    if not cliente:
        return redirect(url_for("clientes"))
    maquinas = maquinaria_service.consultar_por_cliente(id_cliente)
    return render_template("cliente_detalle.html", cliente=cliente, maquinas=maquinas)

@app.route("/clientes/<int:id_cliente>/maquinaria")
@roles_requeridos("admin", "cliente")
def maquinaria_por_cliente(id_cliente):
    if not es_admin() and id_cliente != session.get("id_cliente"):
        return redirect(url_for("sin_permiso"))
    cliente = cliente_service.buscar_por_id(id_cliente)
    lista = maquinaria_service.consultar_por_cliente(id_cliente)
    return render_template("maquinaria_por_cliente.html", cliente=cliente, maquinas=lista)



@app.route("/maquinaria")
@roles_requeridos("admin")
def maquinaria():
    categoria = request.args.get("categoria")
    estado = request.args.get("estado")
    lista = maquinaria_service.consultar_maquinas(categoria, estado)
    return render_template(
        "maquinaria.html", maquinas=lista, categorias=CATEGORIAS, estados=ESTADOS,
        categoria_actual=categoria, estado_actual=estado,
    )
@app.route("/maquinaria/categorias")
@roles_requeridos("admin")
def maquinaria_categorias():
    conteos = maquinaria_service.contar_por_categoria()
    return render_template("maquinaria_categorias.html", conteos=conteos)

@app.route("/maquinaria/nueva", methods=["GET", "POST"])
@roles_requeridos("admin")
def nueva_maquina():
    if request.method == "POST":
        placa = request.form["placa"]
        tipo = request.form["tipo"]
        marca = request.form["marca"]
        modelo = request.form["modelo"]
        id_cliente = request.form["id_cliente"]
        maquinaria_service.registrar_maquina(placa, tipo, marca, modelo, id_cliente)
        return redirect(url_for("maquinaria"))
    lista_clientes = cliente_service.consultar_clientes()
    return render_template("maquina_form.html", clientes=lista_clientes)


@app.route("/maquinaria/editar/<int:id_maquina>", methods=["GET", "POST"])
@roles_requeridos("admin")
def editar_maquina(id_maquina):
    if request.method == "POST":
        tipo = request.form["tipo"]
        marca = request.form["marca"]
        modelo = request.form["modelo"]
        maquinaria_service.modificar_maquina(id_maquina, tipo, marca, modelo)
        return redirect(url_for("maquinaria"))
    maquina = maquinaria_service.buscar_por_id(id_maquina)
    return render_template("maquina_editar.html", maquina=maquina)



@app.route("/mecanicos")
@roles_requeridos("admin")
def mecanicos():
    lista = mecanico_service.consultar_mecanicos()
    return render_template(
        "mecanicos.html", mecanicos=lista,
        carga=mantenimiento_service.horas_hoy_por_mecanico(),
        finalizados=mantenimiento_service.contar_finalizados_por_mecanico(),
        jornada=JORNADA_HORAS,
        ocupados=mantenimiento_service.mecanicos_ocupados(),
    )


@app.route("/mecanicos/nuevo", methods=["GET", "POST"])
@roles_requeridos("admin")
def nuevo_mecanico():
    if request.method == "POST":
        identificacion = request.form.get("identificacion", "").strip()
        nombre = " ".join(request.form.get("nombre", "").split())
        telefono = request.form.get("telefono", "").strip()

        errores = [e for e in (
            validar_identificacion(identificacion),
            validar_nombre(nombre),
            validar_telefono(telefono),
        ) if e]
        if not errores and mecanico_service.existe_identificacion(identificacion):
            errores.append("Ya existe un mecánico registrado con esa identificación.")

        if errores:
            return render_template("mecanico_form.html", errores=errores, datos=request.form)

        mecanico_service.registrar_mecanico(identificacion, nombre, telefono)
        return redirect(url_for("mecanicos"))
    return render_template("mecanico_form.html", errores=[], datos={})


@app.route("/mecanicos/editar/<int:id_mecanico>", methods=["GET", "POST"])
@roles_requeridos("admin")
def editar_mecanico(id_mecanico):
    mecanico = mecanico_service.buscar_por_id(id_mecanico)
    if not mecanico:
        return redirect(url_for("mecanicos"))

    if request.method == "POST":
        nombre = " ".join(request.form.get("nombre", "").split())
        telefono = request.form.get("telefono", "").strip()

        errores = [e for e in (validar_nombre(nombre), validar_telefono(telefono)) if e]
        if errores:
            return render_template("mecanico_editar.html", mecanico=mecanico, errores=errores, datos=request.form)

        mecanico_service.modificar_mecanico(id_mecanico, nombre, telefono)
        return redirect(url_for("mecanicos"))
    return render_template("mecanico_editar.html", mecanico=mecanico, errores=[], datos={})


@app.route("/mecanicos/<int:id_mecanico>/perfil")
@roles_requeridos("admin", "mecanico")
def perfil_mecanico(id_mecanico):
    if session.get("rol") == "mecanico":
        return redirect(url_for("index"))
    if not es_admin() and id_mecanico != session.get("id_mecanico"):
        return redirect(url_for("sin_permiso"))
    mecanico = mecanico_service.buscar_por_id(id_mecanico)
    if not mecanico:
        return redirect(url_for("mecanicos"))
    carga_hoy = mantenimiento_service.horas_hoy_por_mecanico().get(id_mecanico, 0)
    finalizados = mantenimiento_service.contar_finalizados_por_mecanico().get(id_mecanico, 0)
    resumen = pago_service.resumen_mecanico(id_mecanico)
    pagos = pago_service.consultar_pagos_por_mecanico(id_mecanico)[:5]
    asignados = mantenimiento_service.consultar_por_mecanico(id_mecanico)
    return render_template(
        "mecanico_perfil.html", mecanico=mecanico, carga_hoy=carga_hoy,
        jornada=JORNADA_HORAS, finalizados=finalizados, resumen=resumen, pagos=pagos,
        asignados=asignados,
    )

@app.route("/mecanicos/<int:id_mecanico>/toggle")
@roles_requeridos("admin")
def toggle_mecanico(id_mecanico):
    lista = mecanico_service.consultar_mecanicos()
    actual = next((m for m in lista if m[0] == id_mecanico), None)
    if actual:
        quiere_disponible = not actual[4]
        if quiere_disponible and id_mecanico in mantenimiento_service.mecanicos_ocupados():
            return redirect(url_for("mecanicos"))
        mecanico_service.cambiar_disponibilidad(id_mecanico, quiere_disponible)
    return redirect(url_for("mecanicos"))



@app.route("/mantenimientos")
@roles_requeridos("admin", "mecanico")
def mantenimientos():
    busqueda = request.args.get("q", "").strip()
    estado = request.args.get("estado")

    lista = mantenimiento_service.buscar(busqueda, estado)
    if not es_admin():
        propios = ids_mantenimientos_propios()
        lista = [fila for fila in lista if fila[0] in propios]

    return render_template(
        "mantenimientos.html",
        mantenimientos=lista,
        busqueda=busqueda,
        filtro_actual=estado
    )


def contexto_form_mantenimiento(error=None):
    horas = mantenimiento_service.horas_hoy_por_mecanico()
    asignables = [
        m for m in mecanico_service.consultar_disponibles()
        if horas.get(m[0], 0) + DURACION_HORAS <= JORNADA_HORAS
    ]
    maquinas_libres = maquinaria_service.consultar_disponibles()
    return {
        "maquinas": maquinas_libres, "mecanicos": asignables, "horas": horas, "jornada": JORNADA_HORAS,
        "total_maquinas": len(maquinaria_service.consultar_maquinas()),
        "hay_maquinas": len(maquinas_libres) > 0, "hay_mecanicos": len(asignables) > 0, "error": error,
    }


@app.route("/mantenimientos/nuevo", methods=["GET", "POST"])
@roles_requeridos("admin")
def nuevo_mantenimiento():
    contexto = contexto_form_mantenimiento()

    if request.method == "POST":
        id_maquina = request.form.get("id_maquina")
        id_mecanico = request.form.get("id_mecanico")
        tipo = request.form.get("tipo")
        observaciones = request.form.get("observaciones", "").strip()

        ids_maquinas = [str(m[0]) for m in contexto["maquinas"]]
        ids_mecanicos = [str(m[0]) for m in contexto["mecanicos"]]
        if id_maquina not in ids_maquinas or id_mecanico not in ids_mecanicos or tipo not in PRECIOS:
            contexto["error"] = "Debes elegir una máquina disponible, un mecánico disponible y un tipo de mantenimiento válido."
            return render_template("mantenimiento_form.html", **contexto)

        mantenimiento_service.registrar_mantenimiento(id_maquina, id_mecanico, tipo, observaciones)
        return redirect(url_for("mantenimientos"))

    return render_template("mantenimiento_form.html", **contexto)


@app.route("/mantenimientos/<int:id_mantenimiento>/estado/<estado>")
@roles_requeridos("admin", "mecanico")
def cambiar_estado_mantenimiento(id_mantenimiento, estado):
    if not es_admin():
        if id_mantenimiento not in ids_mantenimientos_propios() or estado.lower() == "cancelado":
            return redirect(url_for("sin_permiso"))
    mantenimiento_service.cambiar_estado(id_mantenimiento, estado)
    if not es_admin():
        return redirect(url_for("index"))
    return redirect(url_for("mantenimientos"))


@app.route("/mantenimientos/<int:id_mantenimiento>/observaciones", methods=["GET", "POST"])
@roles_requeridos("admin", "mecanico")
def editar_observaciones(id_mantenimiento):
    if not es_admin() and id_mantenimiento not in ids_mantenimientos_propios():
        return redirect(url_for("sin_permiso"))
    if request.method == "POST":
        observaciones = request.form["observaciones"]
        mantenimiento_service.actualizar_observaciones(id_mantenimiento, observaciones)
        if not es_admin():
            return redirect(url_for("index"))
        return redirect(url_for("mantenimientos"))
    mantenimiento = mantenimiento_service.buscar_por_id(id_mantenimiento)
    return render_template("mantenimiento_observaciones.html", mantenimiento=mantenimiento)

@app.route("/mantenimientos/<int:id_mantenimiento>/solicitud", methods=["GET", "POST"])
@roles_requeridos("cliente")
def solicitud_cliente(id_mantenimiento):
    if id_mantenimiento not in ids_mantenimientos_de_cliente():
        return redirect(url_for("sin_permiso"))
    mantenimiento = mantenimiento_service.buscar_por_id(id_mantenimiento)
    if request.method == "POST":
        mantenimiento_service.actualizar_observaciones_cliente(
            id_mantenimiento, request.form.get("observaciones_cliente", "")
        )
        return redirect(url_for("index"))
    return render_template("mantenimiento_solicitud.html", m=mantenimiento)

@app.route("/mantenimientos/<int:id_mantenimiento>/detalle")
@roles_requeridos("admin", "mecanico")
def detalle_mantenimiento(id_mantenimiento):
    if not es_admin() and id_mantenimiento not in ids_mantenimientos_propios():
        return redirect(url_for("sin_permiso"))
    mantenimiento = mantenimiento_service.buscar_por_id(id_mantenimiento)
    return render_template("mantenimiento_detalle.html", m=mantenimiento)


@app.route("/mantenimientos/<int:id_mantenimiento>/salida")
@login_requerido
def registrar_salida_maquinaria(id_mantenimiento):
    if not factura_service.esta_pagada(id_mantenimiento):
        return redirect(url_for("generar_factura", id_mantenimiento=id_mantenimiento))
    mantenimiento_service.registrar_salida(id_mantenimiento)
    return redirect(url_for("mantenimientos"))

@app.route("/mantenimientos/consulta", methods=["GET", "POST"])
@roles_requeridos("admin")
def consulta_rapida_mantenimiento():
    resultado = None
    error = None
    if request.method == "POST":
        id_texto = request.form.get("id_mantenimiento", "").strip()
        if id_texto.isdigit():
            resultado = mantenimiento_service.buscar_por_id(int(id_texto))
        if not resultado:
            error = "No se encontró ningún mantenimiento con ese ID."
    return render_template("mantenimiento_consulta.html", resultado=resultado, error=error)


@app.route("/maquinaria/<int:id_maquina>/historial")
@roles_requeridos("admin", "cliente")
def historial_maquina(id_maquina):
    if not es_admin() and id_maquina not in ids_maquinas_propias():
        return redirect(url_for("sin_permiso"))
    maquina = maquinaria_service.buscar_por_id(id_maquina)
    lista = mantenimiento_service.consultar_por_maquina(id_maquina)
    return render_template("maquina_historial.html", maquina=maquina, mantenimientos=lista)



@app.route("/mantenimientos/<int:id_mantenimiento>/factura")
@roles_requeridos("admin")
def generar_factura(id_mantenimiento):
    id_factura = factura_service.generar_factura(id_mantenimiento)
    if id_factura is None:
        return redirect(url_for("mantenimientos"))
    return redirect(url_for("ver_factura", id_factura=id_factura))


@app.route("/facturas")
@roles_requeridos("admin")
def facturas():
    lista = factura_service.consultar_facturas()
    return render_template("facturas.html", facturas=lista)


@app.route("/facturas/<int:id_factura>")
@login_requerido
def ver_factura(id_factura):
    factura = factura_service.obtener_factura(id_factura)
    if not factura:
        return redirect(url_for("facturas"))
    if session.get("rol") == "cliente" and factura["id_cliente"] != session.get("id_cliente"):
        return redirect(url_for("sin_permiso"))
    return render_template("factura_detalle.html", f=factura)


@app.route("/facturas/<int:id_factura>/pdf")
@login_requerido
def descargar_factura_pdf(id_factura):
    factura = factura_service.obtener_factura(id_factura)
    if not factura:
        return redirect(url_for("facturas"))
    if session.get("rol") == "cliente" and factura["id_cliente"] != session.get("id_cliente"):
        return redirect(url_for("sin_permiso"))
    pdf = generar_pdf_factura(factura)
    return Response(
        pdf, mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{factura["numero_factura"]}.pdf"'},
    )

@app.route("/facturas/<int:id_factura>/cobrar", methods=["POST"])
@login_requerido
def cobrar_factura(id_factura):
    metodo_pago = request.form.get("metodo_pago", "")
    factura_service.registrar_cobro(id_factura, metodo_pago)
    return redirect(url_for("ver_factura", id_factura=id_factura))


@app.route("/ingresos")
@roles_requeridos("admin")
def ingresos():
    fecha_inicio = request.args.get("fecha_inicio") or None
    fecha_fin = request.args.get("fecha_fin") or None
    filas = mantenimiento_service.ingresos_por_servicio(fecha_inicio, fecha_fin)
    return render_template(
        "ingresos.html", filas=filas,
        total_cantidad=sum(f[1] for f in filas), total_ingresos=sum(f[2] for f in filas),
        fecha_inicio=fecha_inicio or "", fecha_fin=fecha_fin or "",
    )



@app.route("/pagos")
@roles_requeridos("admin")
def pagos():
    lista = pago_service.consultar_pagos()
    return render_template("pagos.html", pagos=lista)


@app.route("/pagos/nuevo", methods=["GET", "POST"])
@roles_requeridos("admin")
def nuevo_pago():
    lista_mecanicos = mecanico_service.consultar_mecanicos()

    if request.method == "POST":
        id_mecanico = request.form["id_mecanico"]
        fecha_inicio = request.form["fecha_inicio"]
        fecha_fin = request.form["fecha_fin"]
        error = pago_service.validar_periodo(fecha_inicio, fecha_fin)
        if error:
            return render_template("pago_form.html", mecanicos=lista_mecanicos, error=error)
        detalle, cantidad, valor_total = pago_service.calcular_pago(id_mecanico, fecha_inicio, fecha_fin)
        mecanico = mecanico_service.buscar_por_id(id_mecanico)
        return render_template(
            "pago_calculo.html", mecanico=mecanico, detalle=detalle, cantidad=cantidad,
            valor_total=valor_total, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
        )

    return render_template("pago_form.html", mecanicos=lista_mecanicos, error=None)


@app.route("/pagos/registrar", methods=["POST"])
@roles_requeridos("admin")
def registrar_pago():
    id_mecanico = request.form["id_mecanico"]
    fecha_inicio = request.form["fecha_inicio"]
    fecha_fin = request.form["fecha_fin"]
    ids = [int(i) for i in request.form.getlist("ids_mantenimiento") if i.isdigit()]
    if pago_service.validar_periodo(fecha_inicio, fecha_fin):
        return redirect(url_for("nuevo_pago"))
    id_pago = pago_service.registrar_pago(id_mecanico, fecha_inicio, fecha_fin, ids)
    if id_pago:
        return redirect(url_for("detalle_pago", id_pago=id_pago))
    return redirect(url_for("pagos"))


@app.route("/pagos/<int:id_pago>")
@roles_requeridos("admin")
def detalle_pago(id_pago):
    pago, detalle = pago_service.obtener_pago(id_pago)
    if not pago:
        return redirect(url_for("pagos"))
    return render_template("pago_detalle.html", pago=pago, detalle=detalle)


@app.route("/mecanicos/<int:id_mecanico>/pagos")
@roles_requeridos("admin", "mecanico")
def pagos_por_mecanico(id_mecanico):
    if not es_admin() and id_mecanico != session.get("id_mecanico"):
        return redirect(url_for("sin_permiso"))
    mecanico = mecanico_service.buscar_por_id(id_mecanico)
    lista = pago_service.consultar_pagos_por_mecanico(id_mecanico)
    resumen = pago_service.resumen_mecanico(id_mecanico)
    return render_template("mecanico_pagos.html", mecanico=mecanico, pagos=lista, resumen=resumen)



@app.route("/reportes")
@roles_requeridos("admin")
def reportes():
    fecha_inicio = request.args.get("fecha_inicio") or None
    fecha_fin = request.args.get("fecha_fin") or None
    datos = reporte_service.generar_reporte(fecha_inicio, fecha_fin)
    ingresos_tipo = mantenimiento_service.ingresos_por_servicio(fecha_inicio, fecha_fin)
    maximo = max([f[2] for f in ingresos_tipo] + [1])
    servicios = reporte_service.detalle_servicios(fecha_inicio, fecha_fin)
    return render_template(
        "reportes.html", datos=datos, ingresos_tipo=ingresos_tipo, maximo=maximo, servicios=servicios,
        fecha_inicio=fecha_inicio or "", fecha_fin=fecha_fin or "",
    )


@app.route("/reportes/exportar.csv")
@roles_requeridos("admin")
def exportar_reporte_csv():
    fecha_inicio = request.args.get("fecha_inicio") or None
    fecha_fin = request.args.get("fecha_fin") or None
    datos = reporte_service.generar_reporte(fecha_inicio, fecha_fin)
    ingresos_tipo = mantenimiento_service.ingresos_por_servicio(fecha_inicio, fecha_fin)

    lineas = ["Reporte General - GIGOLO ETDM S.A."]
    lineas.append(f"Periodo:,{fecha_inicio or 'Sin inicio'},{fecha_fin or 'Sin fin'}")
    lineas.append("")
    lineas.append("Indicador,Valor")
    lineas.append(f"Mantenimientos realizados,{datos['cantidad_mantenimientos']}")
    lineas.append(f"Maquinas atendidas,{datos['maquinas_atendidas']}")
    lineas.append(f"Ingresos generados,{datos['ingresos_total']:.0f}")
    lineas.append(f"Pagado a mecanicos,{datos['pagos_total']:.0f}")
    lineas.append("")
    lineas.append("Tipo de servicio,Cantidad,Ingresos")
    for tipo, cantidad, ingresos in ingresos_tipo:
        lineas.append(f"{tipo},{cantidad},{ingresos:.0f}")

    csv_texto = "\n".join(lineas)
    return Response(
        csv_texto, mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="reporte_gigolo.csv"'},
    )


@app.route("/alertas")
@roles_requeridos("admin")
def alertas():
    datos = alerta_service.generar_alertas()
    return render_template("alertas.html", datos=datos)

@app.route("/sin-permiso")
@login_requerido
def sin_permiso():
    rol = session.get("rol")
    sin_vincular = (rol == "mecanico" and not session.get("id_mecanico")) or \
                   (rol == "cliente" and not session.get("id_cliente"))
    return render_template("sin_permiso.html", sin_vincular=sin_vincular)


def mostrar_usuarios(error=None, ok=None):
    return render_template(
        "usuarios.html",
        usuarios=usuario_service.listar_usuarios(),
        mecanicos=mecanico_service.consultar_mecanicos(),
        clientes=cliente_service.consultar_clientes(),
        error=error, ok=ok,
    )


@app.route("/usuarios")
@roles_requeridos("admin")
def usuarios():
    return mostrar_usuarios()


@app.route("/usuarios/<int:id_usuario>/rol", methods=["POST"])
@roles_requeridos("admin")
def cambiar_rol_usuario(id_usuario):
    rol = request.form.get("rol", "")
    id_mecanico = request.form.get("id_mecanico", "")
    id_cliente = request.form.get("id_cliente", "")
    id_mecanico = int(id_mecanico) if id_mecanico.isdigit() else None
    id_cliente = int(id_cliente) if id_cliente.isdigit() else None

    error = usuario_service.actualizar_rol(id_usuario, rol, id_mecanico, id_cliente)
    if error:
        return mostrar_usuarios(error=error)
    return mostrar_usuarios(ok="Rol actualizado. El usuario verá el cambio al volver a iniciar sesión.")


inicializar_base_datos()
usuario_service.preparar_tabla()

if __name__ == "__main__":
    app.run(debug=True)