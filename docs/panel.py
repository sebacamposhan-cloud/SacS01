"""Interfaz de PlantaControl ejecutada por Python en el navegador."""

from asyncio import ensure_future
from collections import Counter
import csv
from datetime import timedelta
from functools import lru_cache
from html import escape
from io import StringIO
from statistics import mean
from urllib.parse import quote
from uuid import uuid4

from control import FECHA_INICIAL, PARTIDAS, ULTIMA_MEDICION, analizar, fecha_valida
from mediciones import HistorialMediciones
from plano import visor_plano

_callbacks = []
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


async def iniciar():
    from js import Object, document, window
    from pyodide.ffi import JsException, create_proxy

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
    unidad_plano = ''
    numero_partida = 1
    historial = HistorialMediciones()
    pendiente = None

    @lru_cache(maxsize=16)
    def datos_a_fecha(fecha):
        return analizar(fecha, historial.registros)

    def ultima_medicion():
        ultima_registrada = max((r['fecha'] for r in historial.registros), default=ULTIMA_MEDICION)
        return max(ULTIMA_MEDICION, ultima_registrada)

    async def recargar_historial():
        anteriores = historial.registros
        await historial.cargar()
        if historial.registros != anteriores:
            datos_a_fecha.cache_clear()

    def informar(mensaje):
        document.getElementById('mensaje').textContent = mensaje

    def registrar_en_plano():
        panel = document.getElementById('registro-plano')
        for zona in pantalla.querySelectorAll('.unidad'):
            activa = zona.getAttribute('data-depto') == unidad_plano
            zona.setAttribute('aria-expanded', str(activa).lower())
        panel.hidden = not unidad_plano
        if not unidad_plano:
            panel.innerHTML = ''
            return
        detalle, _ = datos_a_fecha(corte.isoformat())
        filas = [p for p in detalle if p['Departamento'] == unidad_plano]
        opciones = ''.join(
            f'<option value="{p["Nº partida"]}">{texto(p["Partida"])}</option>'
            for p in filas
        )
        modo = 'Historial compartido' if historial.compartido else 'Guardado en este navegador'
        panel.innerHTML = f'''
          <div class="registro-titulo">
            <h2>Departamento {numero_depto(unidad_plano)}</h2>
            <button type="button" class="secundario" data-cerrar-registro aria-label="Cerrar registro">×</button>
          </div>
          <form id="medicion" aria-label="Registrar avance">
            <h3>Registrar avance</h3>
            <small>Fecha de medición · {corte:%d/%m/%Y} · {modo}</small>
            <label for="partida-registro">Partida</label>
            <select id="partida-registro">{opciones}</select>
            <p id="avance-registrado"></p>
            <label for="avance-registro">Nuevo avance (%)</label>
            <input id="avance-registro" type="number" min="0" max="100" step="any" required>
            <label><input id="terminada-registro" type="checkbox"> Marcar como terminada</label>
            <label for="nota-registro">Observaciones</label>
            <textarea id="nota-registro" maxlength="500" rows="2"></textarea>
            <button id="guardar-medicion" type="submit">Guardar medición</button>
            <p id="estado-registro" role="status"></p>
          </form>
          <button type="button" class="enlace" data-ver-partidas>Ver las 27 partidas</button>
        '''
        document.getElementById('partida-registro').value = str(numero_partida)
        cargar_partida()

    def cargar_partida():
        detalle, _ = datos_a_fecha(corte.isoformat())
        partida = next(p for p in detalle if p['Departamento'] == unidad_plano
                       and p['Nº partida'] == numero_partida)
        avance = partida['Avance real (%)']
        document.getElementById('avance-registro').value = str(avance)
        document.getElementById('terminada-registro').checked = avance == 100
        document.getElementById('nota-registro').value = partida['Observaciones']
        document.getElementById('avance-registrado').textContent = f'Avance registrado · {avance:g} %'

    def recordar_plano():
        nonlocal posicion_plano, posicion_pagina_plano
        visor = pantalla.querySelector('.plano-visor')
        posicion_plano = (visor.scrollLeft, visor.scrollTop)
        posicion_pagina_plano = (window.scrollX, window.scrollY)

    async def guardar_medicion(formulario, datos):
        nonlocal pendiente
        estado = document.getElementById('estado-registro')
        boton = document.getElementById('guardar-medicion')
        boton.disabled = True
        estado.textContent = 'Guardando…'
        if pendiente is None or any(pendiente[campo] != valor for campo, valor in datos.items()):
            pendiente = dict(datos, id=str(uuid4()))
        medicion = pendiente
        try:
            await historial.guardar(medicion)
        except (OSError, ValueError, JsException):
            estado.textContent = 'No se pudo confirmar el guardado. Puedes volver a intentarlo.'
            boton.disabled = False
            return
        pendiente = None
        mensaje = 'Medición guardada.'
        if historial.compartido:
            try:
                await recargar_historial()
            except (OSError, ValueError, JsException):
                if not any(r['id'] == medicion['id'] for r in historial.registros):
                    historial.registros.append(medicion)
                mensaje = 'Medición guardada. La sincronización del historial quedó pendiente.'
        datos_a_fecha.cache_clear()
        if formulario.isConnected:
            recordar_plano()
            mostrar()
            window.scrollTo(*posicion_pagina_plano)
            document.getElementById('estado-registro').textContent = mensaje
            document.getElementById('guardar-medicion').focus(opciones_foco)
        else:
            informar(mensaje)

    def enviar_medicion(event):
        if document.getElementById('guardar-medicion').disabled:
            return
        datos = {
            'departamento': unidad_plano,
            'partida': numero_partida,
            'fecha': corte.isoformat(),
            'avance': float(document.getElementById('avance-registro').value),
            'observaciones': document.getElementById('nota-registro').value.strip(),
        }
        ensure_future(guardar_medicion(event.target, datos))


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
        if pagina != 'plano' and corte.isoformat() > ultima_medicion():
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
            <small>Última medición disponible · {ultima_medicion()}</small>
          </form>
          {aviso}{contenido}
        '''
        if pagina == 'plano':
            ajustar_zoom()
            document.querySelector('.plano-visor').scrollTo(*posicion_plano)
            registrar_en_plano()
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

    async def cambiar_fecha(formulario, seleccion):
        nonlocal corte
        boton = document.getElementById('actualizar')
        boton.disabled = True
        aviso = ''
        try:
            await recargar_historial()
        except (OSError, ValueError, JsException):
            aviso = ' No se pudo sincronizar el historial.'
        if formulario.isConnected:
            if pagina == 'plano':
                recordar_plano()
            corte = seleccion
            mostrar()
            document.getElementById('actualizar').focus(opciones_foco)
            informar(f'Resultados al {corte:%d-%m-%Y}.{aviso}')

    def actualizar(event):
        event.preventDefault()
        if event.target.id == 'medicion':
            enviar_medicion(event)
            return
        seleccion = fecha_valida(document.getElementById('fecha').value)
        if seleccion is not None and not document.getElementById('actualizar').disabled:
            ensure_future(cambiar_fecha(event.target, seleccion))

    def cambiar(event):
        nonlocal departamento, solo_atrasadas, numero_partida
        campo = event.target.id
        if campo == 'partida-registro':
            numero_partida = int(event.target.value)
            cargar_partida()
            return
        if campo == 'terminada-registro':
            if event.target.checked:
                document.getElementById('avance-registro').value = '100'
            elif document.getElementById('avance-registro').valueAsNumber == 100:
                document.getElementById('avance-registro').value = ''
            return
        if campo == 'departamento':
            departamento = event.target.value
        elif campo == 'solo-atrasadas':
            solo_atrasadas = event.target.checked
        else:
            return
        mostrar_partidas()

    def abrir_unidad(unidad):
        nonlocal departamento, solo_atrasadas, posicion_avance, unidad_origen
        nonlocal unidad_plano, numero_partida
        clave = unidad.getAttribute('data-depto')
        if pagina == 'plano':
            unidad_plano, numero_partida = clave, 1
            registrar_en_plano()
            document.getElementById('partida-registro').focus()
            return
        departamento = unidad_origen = clave
        posicion_avance = (window.scrollX, window.scrollY)
        _, resumen = datos_a_fecha(corte.isoformat())
        solo_atrasadas = any(p['Departamento'] == departamento and p['Partidas atrasadas']
                             for p in resumen)
        navegar('partidas')

    def pulsar(event):
        nonlocal vista, zoom, posicion_avance, unidad_plano, departamento, unidad_origen, solo_atrasadas
        control = event.target.closest(
            '[data-ir], [data-vista], [data-depto], [data-zoom], [data-ver-partidas], [data-cerrar-registro]'
        )
        if not control:
            return
        if control.hasAttribute('data-ir'):
            if pagina == 'avance':
                posicion_avance = (window.scrollX, window.scrollY)
            navegar(control.getAttribute('data-ir'))
        elif control.hasAttribute('data-vista'):
            vista = control.getAttribute('data-vista')
            mostrar_partidas()
        elif control.hasAttribute('data-ver-partidas'):
            recordar_plano()
            departamento = unidad_origen = unidad_plano
            solo_atrasadas = False
            unidad_plano = ''
            navegar('partidas')
        elif control.hasAttribute('data-cerrar-registro'):
            cerrar_registro()
        elif control.hasAttribute('data-depto'):
            abrir_unidad(control)
        else:
            paso = int(control.getAttribute('data-zoom'))
            zoom = max(0, min(3, zoom + paso)) if paso else 0
            ajustar_zoom()

    def cerrar_registro():
        nonlocal unidad_plano
        anterior, unidad_plano = unidad_plano, ''
        registrar_en_plano()
        pantalla.querySelector(f'[data-depto="{anterior}"]').focus(opciones_foco)

    def entrada(event):
        if event.target.id == 'avance-registro':
            document.getElementById('terminada-registro').checked = event.target.valueAsNumber == 100

    def teclado(event):
        if event.key == 'Escape' and unidad_plano and pagina == 'plano':
            cerrar_registro()
            return
        unidad = event.target.closest('.unidad')
        if unidad and event.key in ('Enter', ' '):
            event.preventDefault()
            abrir_unidad(unidad)

    for evento, funcion in (('submit', actualizar), ('change', cambiar),
                            ('click', pulsar), ('keydown', teclado), ('input', entrada)):
        callback = create_proxy(funcion)
        _callbacks.append(callback)
        pantalla.addEventListener(evento, callback)
    try:
        await recargar_historial()
    except (OSError, ValueError, JsException):
        mostrar()
        informar('No se pudo cargar el historial de mediciones. Usa Actualizar para volver a intentarlo.')
    else:
        corte = fecha_valida(max(FECHA_INICIAL, ultima_medicion()))
        mostrar()
