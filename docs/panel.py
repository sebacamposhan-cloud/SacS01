"""Interfaz de PlantaControl ejecutada por Python en el navegador."""

from collections import Counter
import csv
from datetime import timedelta
from functools import lru_cache
from html import escape
from io import StringIO
from statistics import mean
from urllib.parse import quote

from control import FECHA_INICIAL, PARTIDAS, ULTIMA_MEDICION, analizar, fecha_valida
from plano import visor_plano

_callbacks = []
datos_a_fecha = lru_cache(maxsize=16)(analizar)
VISTAS = {'lista': 'Lista', 'kanban': 'Kanban', 'gantt': 'Carta Gantt'}
APARTADOS = {'plano': 'Plano', 'avance': 'Avance', 'partidas': 'Partidas', 'informes': 'Informes y CSV'}


def numero_depto(clave):
    return str(400 + int(clave))


def departamentos_visibles(filas):
    return [dict(fila, Departamento=numero_depto(fila['Departamento'])) for fila in filas]


def atrasada(partida):
    return partida['Estado'].startswith('Atraso')


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
        f'<tr><th scope="row"><button class="enlace" data-depto="{fila["Departamento"]}" '
        f'aria-label="Ver partidas del departamento {numero_depto(fila["Departamento"])}">'
        f'{numero_depto(fila["Departamento"])}</button></th>'
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
        departamento = numero_depto(partidas[0]['Departamento'])
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


def vista_avance(detalle, resumen):
    reales = [p['Avance real (%)'] for p in detalle]
    programados = [p['Avance programado (%)'] for p in detalle if p['Avance programado (%)'] is not None]
    esperado = f'{texto(mean(programados))} %' if programados else '—'
    return f'''
      <dl class="indicadores">
        <div><dt>Avance real del piso</dt><dd>{texto(mean(reales))} %</dd></div>
        <div><dt>Avance programado del piso</dt><dd>{esperado}</dd></div>
      </dl>
      <section><h2>Avance por departamento</h2>{graficos(resumen)}</section>
      <button type="button" class="secundario" data-ir="informes">Informes y CSV</button>
    '''


def vista_informes(detalle, resumen):
    mapa, matriz = matriz_avance(detalle)
    detalle = departamentos_visibles(detalle)
    resumen = departamentos_visibles(resumen)
    estados = Counter(p['Estado'] for p in detalle)
    distribucion = [{'Estado': estado, 'Cantidad': cantidad}
                    for estado, cantidad in estados.most_common()]
    return f'''
      <section><h2>Exportar datos</h2><div class="descargas">
        {descarga(detalle, "Detalle")}{descarga(resumen, "Resumen")}{descarga(matriz, "Matriz")}
      </div></section>
      <details><summary>Resumen de departamentos</summary>{tabla(resumen, "Resumen")}</details>
      <details><summary>Matriz de avance real (%)</summary>{mapa}</details>
      <details><summary>Distribución de estados</summary>{tabla(distribucion, "Estados")}</details>
      <details><summary>Metodología</summary>
        <p>El avance real se toma del historial a la fecha de control.
        El avance programado se calcula de lunes a viernes, sin descontar feriados.</p>
      </details>
    '''


def tarjeta_kanban(partida):
    brecha = ''
    if atrasada(partida):
        brecha = f'<span class="marca-atraso">{texto(-partida["Desviación (pp)"])} pp de atraso</span>'
    return f'''
      <li class="tarjeta-partida">
        <strong>{texto(partida["Partida"])}</strong>
        <span>Depto. {partida["Departamento"]} · {texto(partida["Avance real (%)"])} % real</span>
        {brecha}
      </li>
    '''


def kanban(filas):
    columnas = {'Pendiente': [], 'En ejecución': [], 'Terminada': []}
    for partida in filas:
        real = partida['Avance real (%)']
        estado = 'Terminada' if real >= 100 else 'En ejecución' if real > 0 else 'Pendiente'
        columnas[estado].append(tarjeta_kanban(partida))
    return '<div class="kanban">' + ''.join(
        f'<section><h2>{estado} · {len(tarjetas)}</h2>'
        + (f'<ul>{"".join(tarjetas)}</ul>' if tarjetas else '<p>Sin partidas</p>') + '</section>'
        for estado, tarjetas in columnas.items()
    ) + '</div>'


def gantt(filas, corte):
    periodos = [(fecha_valida(p['Inicio programado']), fecha_valida(p['Término programado']))
                for p in filas]
    validos = [(inicio, fin) for inicio, fin in periodos if inicio and fin and inicio <= fin]
    marcas = ''
    linea = ''
    if validos:
        inicio_eje = min(corte, min(inicio for inicio, _ in validos))
        fin_eje = max(corte, max(fin for _, fin in validos))
        dias = (fin_eje - inicio_eje).days + 1
        paso = max(1, (dias + 5) // 6)
        marcas = ''.join(
            f'<span style="left:{100 * dia / dias:.3f}%">{inicio_eje + timedelta(days=dia):%d/%m/%y}</span>'
            for dia in range(0, dias, paso)
        )
        posicion = 100 * (corte - inicio_eje).days / dias
        linea = f'<i class="linea-corte" style="left:{posicion:.3f}%" aria-hidden="true"></i>'

    renglones = []
    for partida, (inicio, fin) in zip(filas, periodos):
        if inicio and fin and inicio <= fin:
            izquierda = 100 * (inicio - inicio_eje).days / dias
            ancho = 100 * ((fin - inicio).days + 1) / dias
            periodo = f'{inicio:%d/%m/%Y} a {fin:%d/%m/%Y}'
            grafico = (f'<span class="intervalo" role="img" aria-label="Programado del {periodo}" '
                       f'title="{periodo}" style="left:{izquierda:.3f}%;width:{ancho:.3f}%"></span>')
        else:
            grafico = '<span class="sin-programacion">Sin programación</span>'
        renglones.append(
            f'<tr><th scope="row">{texto(partida["Partida"])}</th>'
            f'<td>{partida["Departamento"]}</td><td>{texto(partida["Avance real (%)"])} %</td>'
            f'<td><div class="pista-gantt">{grafico}{linea}</div></td></tr>'
        )
    return f'''
      <p class="leyenda-gantt"><span>▰ Período programado</span> <span>│ Fecha de control · {corte:%d/%m/%Y}</span></p>
      <div class="tabla" tabindex="0" role="region" aria-label="Carta Gantt">
        <table class="gantt"><thead><tr>
          <th scope="col">Partida</th><th scope="col">Depto.</th><th scope="col">Avance real</th>
          <th scope="col" aria-label="Calendario programado"><div class="eje-gantt">{marcas}</div></th>
        </tr></thead><tbody>{''.join(renglones)}</tbody></table>
      </div>
    '''


def iniciar():
    from js import Object, document, window
    from pyodide.ffi import create_proxy

    app = document.getElementById('app')
    app.innerHTML = '<div id="pantalla"></div><p id="mensaje" role="status"></p>'
    pantalla = document.getElementById('pantalla')
    opciones_foco = Object.new()
    opciones_foco.preventScroll = True
    pagina, origen = 'inicio', 'inicio'
    corte = fecha_valida(FECHA_INICIAL)
    departamento, vista, solo_atrasadas = '01', 'lista', False
    zoom = 0
    posicion_plano = (0, 0)
    posicion_pagina_plano = (0, 0)
    posicion_avance = (0, 0)
    unidad_origen = ''

    def ajustar_zoom():
        ancho = (100, 135, 180, 240)[zoom]
        dibujo = document.getElementById('plano-dibujo')
        dibujo.style.width = f'{ancho}%'
        dibujo.style.minWidth = f'{6 * ancho}px'

    def mostrar_partidas():
        detalle, _ = datos_a_fecha(corte.isoformat())
        filas = departamentos_visibles([
            p for p in detalle if (not departamento or p['Departamento'] == departamento)
            and (not solo_atrasadas or atrasada(p))
        ])
        for boton in pantalla.querySelectorAll('[data-vista]'):
            boton.setAttribute('aria-pressed', str(boton.getAttribute('data-vista') == vista).lower())
        if not filas:
            contenido = '<p>No hay partidas atrasadas para esta selección.</p>'
        elif vista == 'lista':
            contenido = tabla(filas, 'Detalle de partidas')
        elif vista == 'kanban':
            contenido = kanban(filas)
        else:
            contenido = gantt(filas, corte)
        document.getElementById('detalle').innerHTML = contenido
        document.getElementById('cantidad').textContent = f'{len(filas)} partidas'

    def mostrar():
        document.getElementById('mensaje').textContent = ''
        if pagina == 'inicio':
            botones = ''.join(
                f'<button type="button" data-ir="{clave}">{APARTADOS[clave]}'
                '<span aria-hidden="true">›</span></button>'
                for clave in ('plano', 'avance', 'partidas')
            )
            pantalla.innerHTML = f'<div class="inicio"><h1 tabindex="-1">¿Qué quieres consultar?</h1>{botones}</div>'
            return

        detalle, resumen = datos_a_fecha(corte.isoformat())
        volver = {'plano': 'al plano', 'avance': 'a Avance', 'inicio': 'al inicio'}
        destino = origen if pagina == 'partidas' else 'avance' if pagina == 'informes' else 'inicio'
        aviso = ''
        if pagina != 'plano' and corte.isoformat() > ULTIMA_MEDICION:
            aviso = '<p class="aviso">El avance real corresponde a la última medición disponible.</p>'
        if pagina == 'plano':
            contenido = visor_plano(resumen)
        elif pagina == 'avance':
            contenido = vista_avance(detalle, resumen)
        elif pagina == 'informes':
            contenido = vista_informes(detalle, resumen)
        else:
            opciones = ''.join(
                f'<option value="{p["Departamento"]}">{numero_depto(p["Departamento"])}</option>'
                for p in resumen
            )
            botones = ''.join(
                f'<button type="button" data-vista="{clave}">{titulo}</button>'
                for clave, titulo in VISTAS.items()
            )
            contenido = f'''
              <section class="partidas">
                <div class="controles-partidas">
                  <label for="departamento">Departamento</label>
                  <select id="departamento"><option value="">Todos</option>{opciones}</select>
                  <label><input id="solo-atrasadas" type="checkbox"> Solo atrasadas</label>
                  <span id="cantidad" role="status"></span>
                </div>
                <div class="vistas" role="group" aria-label="Vista de partidas">{botones}</div>
                <div id="detalle"></div>
              </section>
            '''
        pantalla.innerHTML = f'''
          <div class="titulo-vista">
            <button type="button" class="secundario" data-ir="{destino}">← Volver {volver[destino]}</button>
            <h1 tabindex="-1">{APARTADOS[pagina]}</h1>
          </div>
          <form id="filtros">
            <label for="fecha">Fecha de control</label>
            <input id="fecha" type="date" value="{corte.isoformat()}" required>
            <button id="actualizar" type="submit">Actualizar</button>
            <small>Última medición disponible · {ULTIMA_MEDICION}</small>
          </form>
          {aviso}{contenido}
        '''
        if pagina == 'plano':
            ajustar_zoom()
            document.querySelector('.plano-visor').scrollTo(*posicion_plano)
        elif pagina == 'partidas':
            document.getElementById('departamento').value = departamento
            document.getElementById('solo-atrasadas').checked = solo_atrasadas
            mostrar_partidas()

    def navegar(destino):
        nonlocal pagina, origen, vista, solo_atrasadas
        anterior = pagina
        if destino == 'partidas':
            origen, vista = anterior, 'lista'
            if anterior == 'inicio':
                solo_atrasadas = False
        pagina = destino
        mostrar()
        regresa_a_unidad = anterior == 'partidas' and destino == origen and origen != 'inicio'
        selector = f'[data-depto="{unidad_origen}"]' if regresa_a_unidad else 'h1'
        pantalla.querySelector(selector).focus(opciones_foco)
        if destino == 'plano' and regresa_a_unidad:
            window.scrollTo(*posicion_pagina_plano)
        elif destino == 'avance' and anterior in ('partidas', 'informes'):
            window.scrollTo(*posicion_avance)
        else:
            window.scrollTo(0, 0)

    def actualizar(event):
        nonlocal corte, posicion_plano
        event.preventDefault()
        seleccion = fecha_valida(document.getElementById('fecha').value)
        if seleccion is None:
            return
        if pagina == 'plano':
            visor = document.querySelector('.plano-visor')
            posicion_plano = (visor.scrollLeft, visor.scrollTop)
        corte = seleccion
        mostrar()
        document.getElementById('actualizar').focus(opciones_foco)
        document.getElementById('mensaje').textContent = f'Resultados al {corte:%d-%m-%Y}'

    def cambiar(event):
        nonlocal departamento, solo_atrasadas
        if event.target.id == 'departamento':
            departamento = event.target.value
        elif event.target.id == 'solo-atrasadas':
            solo_atrasadas = event.target.checked
        else:
            return
        mostrar_partidas()

    def abrir_unidad(unidad):
        nonlocal departamento, solo_atrasadas, posicion_plano, posicion_avance, unidad_origen
        nonlocal posicion_pagina_plano
        departamento = unidad.getAttribute('data-depto')
        unidad_origen = departamento
        solo_atrasadas = False
        if pagina == 'plano':
            visor = document.querySelector('.plano-visor')
            posicion_plano = (visor.scrollLeft, visor.scrollTop)
            posicion_pagina_plano = (window.scrollX, window.scrollY)
        else:
            posicion_avance = (window.scrollX, window.scrollY)
            _, resumen = datos_a_fecha(corte.isoformat())
            solo_atrasadas = any(p['Departamento'] == departamento and p['Partidas atrasadas']
                                 for p in resumen)
        navegar('partidas')

    def pulsar(event):
        nonlocal vista, zoom, posicion_avance
        control = event.target.closest('[data-ir], [data-vista], [data-depto], [data-zoom]')
        if not control:
            return
        if control.hasAttribute('data-ir'):
            if pagina == 'avance':
                posicion_avance = (window.scrollX, window.scrollY)
            navegar(control.getAttribute('data-ir'))
        elif control.hasAttribute('data-vista'):
            vista = control.getAttribute('data-vista')
            mostrar_partidas()
        elif control.hasAttribute('data-depto'):
            abrir_unidad(control)
        else:
            paso = int(control.getAttribute('data-zoom'))
            zoom = max(0, min(3, zoom + paso)) if paso else 0
            ajustar_zoom()

    def teclado(event):
        unidad = event.target.closest('.unidad')
        if unidad and event.key in ('Enter', ' '):
            event.preventDefault()
            abrir_unidad(unidad)

    for evento, funcion in (('submit', actualizar), ('change', cambiar),
                            ('click', pulsar), ('keydown', teclado)):
        callback = create_proxy(funcion)
        _callbacks.append(callback)
        pantalla.addEventListener(evento, callback)
    mostrar()
