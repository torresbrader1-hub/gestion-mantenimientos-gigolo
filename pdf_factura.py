import textwrap

AZUL = (0.12, 0.23, 0.37)
BLANCO = (1, 1, 1)
NEGRO = (0, 0, 0)
GRIS = (0.42, 0.45, 0.50)


def _texto_pdf(texto):
    datos = str(texto).encode("cp1252", errors="replace")
    return datos.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _pesos(valor):
    return "$" + f"{valor:,.0f}".replace(",", ".")


class _Pagina:
    def __init__(self):
        self.operaciones = []

    def texto(self, x, y, contenido, tamano=10, negrita=False, color=NEGRO):
        fuente = b"F2" if negrita else b"F1"
        r, g, bl = color
        self.operaciones.append(
            b"%.2f %.2f %.2f rg BT /%s %d Tf %d %d Td (" % (r, g, bl, fuente, tamano, x, y)
            + _texto_pdf(contenido) + b") Tj ET"
        )

    def linea(self, x1, y1, x2, y2, grosor=0.6):
        self.operaciones.append(b"0.75 0.77 0.80 RG %.2f w %d %d m %d %d l S" % (grosor, x1, y1, x2, y2))

    def rectangulo(self, x, y, ancho, alto, color):
        r, g, bl = color
        self.operaciones.append(b"%.2f %.2f %.2f rg %d %d %d %d re f" % (r, g, bl, x, y, ancho, alto))

    def contenido(self):
        return b"\n".join(self.operaciones)


def _armar_pdf(contenido):
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(contenido) + contenido + b"\nendstream",
    ]
    salida = bytearray(b"%PDF-1.4\n")
    posiciones = []
    for numero, objeto in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n" % numero + objeto + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += b"xref\n0 %d\n" % (len(objetos) + 1)
    salida += b"0000000000 65535 f \n"
    for posicion in posiciones:
        salida += b"%010d 00000 n \n" % posicion
    salida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, inicio_xref)
    return bytes(salida)


def generar_pdf_factura(f):
    p = _Pagina()
    p.rectangulo(0, 752, 595, 90, AZUL)
    p.texto(40, 803, "GIGOLÓ ETDM S.A.", 22, True, BLANCO)
    p.texto(40, 781, "Sistema de Gestión de Mantenimiento de Maquinaria", 10, False, BLANCO)
    p.texto(420, 803, "FACTURA", 20, True, BLANCO)
    p.texto(420, 781, f["numero_factura"], 12, True, BLANCO)

    p.texto(40, 722, "Fecha de generación:", 10, True)
    p.texto(160, 722, f["fecha_generacion"][:16], 10)

    y = 690

    def seccion(titulo, filas, y):
        p.texto(40, y, titulo, 11, True, AZUL)
        p.linea(40, y - 5, 555, y - 5)
        y -= 24
        for etiqueta, valor in filas:
            p.texto(50, y, etiqueta, 10, True, GRIS)
            p.texto(200, y, valor, 10)
            y -= 17
        return y - 10

    y = seccion("DATOS DEL CLIENTE", [
        ("Nombre", f["cliente_nombre"]),
        ("Identificación", f["cliente_identificacion"]),
        ("Teléfono", f["cliente_telefono"]),
    ], y)

    y = seccion("DATOS DE LA MÁQUINA", [
        ("Placa", f["placa"]),
        ("Tipo", f["tipo_maquina"]),
        ("Marca", f["marca"] or "-"),
        ("Modelo", f["modelo"] or "-"),
    ], y)

    y = seccion("DETALLE DEL SERVICIO", [
        ("Mantenimiento", f["tipo_mantenimiento"]),
        ("Mecánico encargado", f["mecanico_nombre"]),
        ("Fecha de registro", (f["fecha_registro"] or "-")[:16]),
        ("Fecha de finalización", (f["fecha_finalizacion"] or "-")[:16]),
    ], y)

    p.texto(50, y, "Observaciones", 10, True, GRIS)
    lineas = textwrap.wrap(f["observaciones"] or "Sin observaciones", 75)[:4]
    for linea in lineas:
        p.texto(200, y, linea, 10)
        y -= 15
    y -= 20

    p.rectangulo(40, y - 45, 515, 55, (0.93, 0.95, 0.98))
    p.texto(60, y - 12, "TOTAL A PAGAR", 12, True, AZUL)
    p.texto(360, y - 20, _pesos(f["valor_total"]), 22, True, AZUL)

    p.linea(40, 60, 555, 60)
    p.texto(40, 42, "Documento generado por el Sistema de Gestión de Mantenimiento - GIGOLÓ ETDM S.A.", 8, False, GRIS)

    return _armar_pdf(p.contenido())