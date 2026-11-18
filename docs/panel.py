"""Interfaz de PlantaControl ejecutada por Python en el navegador."""

from collections import Counter
import csv
from html import escape
from io import StringIO
from statistics import mean
from urllib.parse import quote

from control import FECHA_INICIAL, PARTIDAS, ULTIMA_MEDICION, analizar, fecha_valida

_callbacks = []


def texto(valor):
    if valor is None:
        return '—'
    if isinstance(valor, float):
        return f'{valor:.2f}'.replace('.', ',')
    return escape(str(valor))


def tabla(filas, nombre):
    encabezados = ''.join(f'<th scope="col">{texto(c)}</th>' for c in filas[0])
    cuerpo = ''.join(
        '<tr>' + ''.join(f'<td>{texto(v)}</td>' for v in fila.values()) + '</tr>'
        for fila in filas
    )
    return (f'<div class="tabla" tabindex="0" role="region" aria-label="{nombre}">'
            f'<table><thead><tr>{encabezados}</tr></thead><tbody>{cuerpo}</tbody></table></div>')


def descarga(filas, nombre):
    archivo = StringIO()
    escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]), delimiter=';')
    escritor.writeheader()
    escritor.writerows(filas)
    url = 'data:text/csv;charset=utf-8,' + quote('\ufeff' + archivo.getvalue())
    return f'<a class="boton" download="PlantaControl_{nombre}.csv" href="{url}">{nombre} CSV</a>'


def barra(valor, clase, escala=100):
    if valor is None:
        return '<span>—</span>'
    ancho = max(0, min(100, valor * 100 / escala))
    return (f'<span class="pista" aria-hidden="true">'
            f'<i class="{clase}" style="width:{ancho}%"></i></span><span>{texto(valor)}</span>')


def graficos(resumen):
    filas = ''.join(
        f'<tr><th scope="row">{fila["Departamento"]}</th>'
        f'<td><div class="barra">{barra(fila["Avance real (%)"], "real")}</div></td>'
        f'<td><div class="barra">{barra(fila["Avance programado (%)"], "programado")}</div></td>'
        f'<td><div class="barra">{barra(fila["Partidas atrasadas"], "atraso", len(PARTIDAS))}</div></td></tr>'
        for fila in resumen
    )
    return (
        '<div class="tabla" tabindex="0" role="region" aria-label="Gráficos de avance">'
        '<table class="graficos"><thead><tr><th scope="col">Depto.</th>'
        '<th scope="col">Real (%)</th><th scope="col">Programado (%)</th>'
        '<th scope="col">Partidas atrasadas</th></tr></thead>'
        f'<tbody>{filas}</tbody></table></div>'
    )


def matriz_avance(detalle):
    ancho = len(PARTIDAS)
    matriz = []
    filas = []
    for inicio in range(0, len(detalle), ancho):
        partidas = detalle[inicio:inicio + ancho]
        departamento = partidas[0]['Departamento']
        registro = {'Departamento': departamento}
        celdas = []
        for partida in partidas:
            numero = partida['Nº partida']
            real = partida['Avance real (%)']
            registro[str(numero)] = real
            luminosidad = 96 - real * .56
            color_texto = '#fff' if real >= 65 else '#172f35'
            nombre = escape(partida['Partida'], quote=True)
            celdas.append(
                f'<td title="{nombre}" style="background:hsl(172 57% {luminosidad}%);'
                f'color:{color_texto}">{real:g}</td>'
            )
        matriz.append(registro)
        filas.append(f'<tr><th scope="row">{departamento}</th>{"".join(celdas)}</tr>')
    columnas = ''.join(
        f'<th scope="col" title="{escape(partida, quote=True)}">{numero:02d}</th>'
        for numero, partida in enumerate(PARTIDAS, 1)
    )
    html = ('<div class="tabla" tabindex="0" role="region" aria-label="Matriz de avance">'
            f'<table class="matriz"><thead><tr><th scope="col">Depto.</th>{columnas}</tr></thead>'
            f'<tbody>{"".join(filas)}</tbody></table></div>')
    return html, matriz


def contenido(corte):
    detalle, resumen = analizar(corte)
    programados = [p['Avance programado (%)'] for p in detalle
                   if p['Avance programado (%)'] is not None]
    estados = Counter(p['Estado'] for p in detalle)
    indicadores = [
        ('Avance real promedio', f'{texto(mean(p["Avance real (%)"] for p in detalle))} %'),
        ('Avance programado promedio', f'{texto(mean(programados))} %' if programados else '—'),
        ('Partidas terminadas', estados['Terminada']),
        ('Partidas atrasadas', sum(n for estado, n in estados.items() if estado.startswith('Atraso'))),
    ]
    tarjetas = ''.join(f'<div><dt>{nombre}</dt><dd>{valor}</dd></div>'
                       for nombre, valor in indicadores)
    aviso = ''
    if corte > ULTIMA_MEDICION:
        aviso = ('<p class="aviso">El avance real corresponde a la última medición disponible. '
                 'El avance programado se calcula a la fecha seleccionada.</p>')
    mapa, matriz = matriz_avance(detalle)
    distribucion = [{'Estado': estado, 'Cantidad': cantidad}
                    for estado, cantidad in estados.most_common()]
    opciones = ''.join(f'<option value="{fila["Departamento"]}">{fila["Departamento"]}</option>'
                       for fila in resumen)
    return f'''
      {aviso}
      <dl class="indicadores">{tarjetas}</dl>
      <section><h2>Avance por departamento</h2>{graficos(resumen)}</section>
      <section><h2>Resumen de los 15 departamentos</h2>{tabla(resumen, "Resumen")}</section>
      <section><h2>Detalle de las partidas</h2>
        <label for="departamento">Departamento</label>
        <select id="departamento"><option value="">Todos</option>{opciones}</select>
        <div id="detalle"></div>
      </section>
      <section><h2>Matriz de avance real (%)</h2>{mapa}</section>
      <section><h2>Distribución de estados</h2>{tabla(distribucion, "Estados")}</section>
      <section><h2>Exportar datos</h2><div class="descargas">
        {descarga(detalle, "Detalle")}{descarga(resumen, "Resumen")}{descarga(matriz, "Matriz")}
      </div></section>
      <details><summary>Metodología</summary>
        <ol><li>Cargar el respaldo de los 15 departamentos y 27 partidas.</li>
        <li>Elegir la fecha de control y consultar el historial de avance real.</li>
        <li>Calcular el avance programado de lunes a viernes, sin descontar feriados.</li>
        <li>Clasificar atrasos y generar indicadores, gráficos y CSV.</li></ol>
      </details>
    ''', detalle


def iniciar():
    from js import document
    from pyodide.ffi import create_proxy

    app = document.getElementById('app')
    app.innerHTML = f'''
      <h1>Control de avance</h1>
      <p class="descripcion">15 departamentos · 27 partidas por departamento · 405 registros</p>
      <form id="filtros">
        <label for="fecha">Fecha de control</label>
        <input id="fecha" type="date" value="{FECHA_INICIAL}" required>
        <button>Actualizar</button>
        <small>Última medición disponible · {ULTIMA_MEDICION}</small>
      </form>
      <p id="mensaje" role="status"></p>
      <div id="resultados"></div>
    '''
    detalle = []

    def mostrar_detalle():
        filtro = document.getElementById('departamento').value
        filas = [fila for fila in detalle if not filtro or fila['Departamento'] == filtro]
        document.getElementById('detalle').innerHTML = tabla(filas, 'Detalle de partidas')

    def actualizar(event=None):
        nonlocal detalle
        if event is not None:
            event.preventDefault()
        mensaje = document.getElementById('mensaje')
        fecha = fecha_valida(document.getElementById('fecha').value)
        if fecha is None:
            mensaje.textContent = 'Selecciona una fecha de control válida.'
            return
        filtro = document.getElementById('departamento')
        seleccionado = filtro.value if filtro else '01'
        html, detalle = contenido(fecha.isoformat())
        document.getElementById('resultados').innerHTML = html
        document.getElementById('departamento').value = seleccionado
        mostrar_detalle()
        mensaje.textContent = f'Resultados al {fecha:%d-%m-%Y}'

    def cambiar_departamento(event):
        if event.target.id == 'departamento':
            mostrar_detalle()

    _callbacks.extend(create_proxy(funcion) for funcion in (actualizar, cambiar_departamento))
    document.getElementById('filtros').addEventListener('submit', _callbacks[0])
    document.getElementById('resultados').addEventListener('change', _callbacks[1])
    actualizar()
