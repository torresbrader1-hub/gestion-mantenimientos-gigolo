import re

SOLO_DIGITOS = re.compile(r"[0-9]+")
SOLO_LETRAS = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+")


def validar_identificacion(valor):
    valor = (valor or "").strip()
    if not valor:
        return "La identificación es obligatoria."
    if not SOLO_DIGITOS.fullmatch(valor):
        return "La identificación solo puede contener números (sin letras, espacios ni símbolos)."
    if not 5 <= len(valor) <= 12:
        return "La identificación debe tener entre 5 y 12 dígitos."
    return None


def validar_nombre(valor):
    valor = " ".join((valor or "").split())
    if not valor:
        return "El nombre es obligatorio."
    if not SOLO_LETRAS.fullmatch(valor):
        return "El nombre solo puede contener letras (sin números ni símbolos)."
    if not 3 <= len(valor) <= 50:
        return "El nombre debe tener entre 3 y 50 letras."
    return None


def validar_telefono(valor):
    valor = (valor or "").strip()
    if not valor:
        return "El teléfono es obligatorio."
    if not SOLO_DIGITOS.fullmatch(valor):
        return "El teléfono solo puede contener números (sin letras, espacios ni símbolos)."
    if not 7 <= len(valor) <= 10:
        return "El teléfono debe tener entre 7 y 10 dígitos."
    return None