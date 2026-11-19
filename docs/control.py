"""Cálculos de avance del taller, con la biblioteca estándar de Python."""

import base64
from datetime import date, timedelta
import gzip
import json
from statistics import mean

from datos import DATOS_COMPRIMIDOS, PARTIDAS

DATOS = json.loads(gzip.decompress(base64.b64decode(DATOS_COMPRIMIDOS)))
DEPARTAMENTOS = [str(x) for x in range(401, 416)]
ULTIMA_MEDICION = max(h['date'] for h in DATOS['history'])
FECHA_INICIAL = DATOS['cutDate']

def etiqueta_depto(clave_interna):
    """Muestra 01 a 15; las claves 401 a 415 nunca se imprimen."""
    return f"{int(clave_interna) - 400:02d}"

def fecha_valida(texto):
    try:
        return date.fromisoformat(str(texto))
    except (ValueError, TypeError):
        return None

def dias_habiles_inclusivos(inicio, fin):
    """Días de lunes a viernes, con ambos extremos incluidos; sin feriados."""
    if inicio is None or fin is None or fin < inicio:
        return 0
    semanas, resto = divmod((fin - inicio).days + 1, 7)
    return semanas * 5 + sum((inicio.weekday() + offset) % 7 < 5
                             for offset in range(resto))

def avance_esperado(inicio_texto, termino_texto, corte):
    """Reproduce la regla lineal por días hábiles del HTML original."""
    inicio = fecha_valida(inicio_texto)
    termino = fecha_valida(termino_texto)
    if inicio is None or termino is None or inicio > termino:
        return None
    if corte < inicio:
        return 0.0
    if corte >= termino:
        return 100.0
    total = dias_habiles_inclusivos(inicio, termino)
    if total == 0:
        return 0.0
    ejecutados = dias_habiles_inclusivos(inicio, corte)
    return round(100.0 * ejecutados / total, 2)

def dias_vencidos(inicio_texto, termino_texto, corte, avance_real):
    inicio, termino = fecha_valida(inicio_texto), fecha_valida(termino_texto)
    if inicio is None or termino is None or inicio > termino or avance_real >= 100 or corte <= termino:
        return 0
    return dias_habiles_inclusivos(termino + timedelta(days=1), corte)

def clasificar(real, esperado):
    if esperado is not None and real < esperado:
        brecha = esperado - real
        if brecha <= 10: return 'Atraso leve'
        if brecha <= 20: return 'Atraso moderado'
        if brecha <= 35: return 'Atraso alto'
        return 'Atraso crítico'
    if real >= 100: return 'Terminada'
    if real > 0: return 'En ejecución'
    return 'Pendiente'

def avances_a_fecha(corte):
    """Usa el historial cuando la fecha es anterior al último registro disponible."""
    historico = DATOS.get('history', [])
    if not historico:
        return {}
    if corte.isoformat() >= ULTIMA_MEDICION:
        # La medición real no se inventa para fechas futuras: se conserva la última observada.
        return {(d, i): float(e['real']) for d in DEPARTAMENTOS
                for i, e in enumerate(DATOS['entries'][d])}
    anteriores = [h for h in historico if h['date'] <= corte.isoformat()]
    anteriores.sort(key=lambda h: (h['date'], h.get('when', '')))
    avances = {}
    for h in anteriores:
        avances[(str(h['d']), int(h['i']))] = float(h['real'])
    return avances

def analizar(fecha_corte='2026-11-12', mediciones=()):
    """Genera detalle por partida y resumen por departamento."""
    corte = fecha_valida(fecha_corte)
    if corte is None:
        raise ValueError('Fecha de control incorrecta: utiliza AAAA-MM-DD.')
    reales = avances_a_fecha(corte)
    registradas = {}
    for medicion in mediciones:
        if medicion['fecha'] > fecha_corte:
            continue
        clave = (medicion['departamento'], medicion['partida'])
        anterior = registradas.get(clave)
        if anterior is None or medicion['fecha'] >= anterior['fecha']:
            registradas[clave] = medicion
    filas = []
    for d in DEPARTAMENTOS:
        for i, e in enumerate(DATOS['entries'][d]):
            medicion = registradas.get((etiqueta_depto(d), i + 1))
            real = float(medicion['avance']) if medicion else reales.get((d, i), 0.0)
            nota = medicion['observaciones'] if medicion else e.get('note') or ''
            esperado = avance_esperado(e.get('start'), e.get('end'), corte)
            desviacion = None if esperado is None else round(real - esperado, 2)
            filas.append({
                'Departamento': etiqueta_depto(d),
                'Nº partida': i + 1,
                'Partida': PARTIDAS[i],
                'Inicio programado': e.get('start') or '',
                'Término programado': e.get('end') or '',
                'Fecha de control': fecha_corte,
                'Avance real (%)': real,
                'Avance programado (%)': esperado,
                'Desviación (pp)': desviacion,
                'Días hábiles vencidos': dias_vencidos(e.get('start'),e.get('end'),corte,real),
                'Estado': clasificar(real, esperado),
                'Observaciones': nota
            })
    resumen = []
    for indice, departamento in enumerate(DEPARTAMENTOS):
        inicio = indice * len(PARTIDAS)
        partidas = filas[inicio:inicio + len(PARTIDAS)]
        reales = [p['Avance real (%)'] for p in partidas]
        programados = [p['Avance programado (%)'] for p in partidas
                       if p['Avance programado (%)'] is not None]
        real = mean(reales)
        programado = mean(programados) if programados else None
        resumen.append({
            'Departamento': etiqueta_depto(departamento),
            'Avance real (%)': round(real, 2),
            'Avance programado (%)': None if programado is None else round(programado, 2),
            'Partidas terminadas': sum(p['Estado'] == 'Terminada' for p in partidas),
            'Partidas en ejecución': sum(0 < valor < 100 for valor in reales),
            'Partidas pendientes': sum(valor == 0 for valor in reales),
            'Partidas atrasadas': sum(p['Estado'].startswith('Atraso') for p in partidas),
            'Partidas vencidas': sum(p['Días hábiles vencidos'] > 0 for p in partidas),
            'Desviación (pp)': None if programado is None else round(real - programado, 2),
        })
    return filas, resumen
