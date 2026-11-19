"""Zonas de consulta trazadas sobre el plano D13f, revisión A."""

# Coordenadas del recorte sobre una vista de la hoja a escala 0,55.
# Cada zona corresponde a la unidad 400 + departamento del plano.
RECORTE = (134, 183, 991, 567)
ZONAS = {
    '01': ((367, 509, 499, 509, 499, 624, 367, 624, 367, 589, 384, 565, 367, 565), (442, 580)),
    '02': ((337, 648, 414, 648, 414, 625, 460, 625, 460, 739, 337, 739), (415, 694)),
    '03': ((212, 624, 337, 624, 337, 739, 230, 739, 230, 729, 212, 729), (271, 661)),
    '04': ((212, 507, 337, 507, 337, 623, 212, 623), (268, 564)),
    '05': ((212, 389, 337, 389, 337, 506, 212, 506), (268, 466)),
    '06': ((212, 265, 231, 265, 231, 245, 399, 245, 399, 367, 361, 367, 337, 352, 337, 388, 212, 388), (286, 306)),
    '07': ((400, 235, 510, 235, 510, 368, 400, 368), (451, 304)),
    '08': ((511, 255, 528, 255, 528, 235, 635, 235, 635, 368, 511, 368), (567, 304)),
    '09': ((637, 235, 753, 235, 753, 368, 692, 368, 667, 352, 637, 352), (697, 303)),
    '10': ((755, 255, 766, 255, 766, 235, 923, 235, 923, 246, 931, 246, 931, 368, 839, 368, 815, 350, 815, 368, 755, 368), (843, 301)),
    '11': ((932, 245, 1099, 245, 1099, 263, 1111, 263, 1111, 384, 993, 384, 993, 366, 932, 366), (1016, 304)),
    '12': ((994, 385, 1111, 385, 1111, 500, 1099, 500, 1099, 518, 932, 518, 932, 399, 971, 399, 971, 420, 994, 420), (1019, 465)),
    '13': ((815, 399, 931, 399, 931, 511, 922, 511, 922, 530, 755, 530, 755, 413, 815, 413), (843, 480)),
    '14': ((638, 399, 754, 399, 754, 529, 638, 529), (683, 479)),
    '15': ((519, 399, 579, 399, 579, 419, 603, 419, 603, 399, 637, 399, 637, 529, 519, 529), (566, 473)),
}


def visor_plano(resumen):
    x, y, ancho, alto = RECORTE
    unidades = []
    for fila in resumen:
        depto = fila['Departamento']
        contorno, (cx, cy) = ZONAS[depto]
        puntos = ' '.join(f'{a},{b}' for a, b in zip(contorno[::2], contorno[1::2]))
        unidad = 400 + int(depto)
        atrasadas = fila['Partidas atrasadas']
        real = fila['Avance real (%)']
        estado = 'con-atrasos' if atrasadas else 'terminado' if real == 100 else 'en-curso'
        unidades.append(f'''
          <g class="unidad {estado}" role="button" tabindex="0" aria-controls="registro-plano" aria-expanded="false"
             data-depto="{depto}" aria-label="Departamento {unidad}, {atrasadas} partidas atrasadas">
            <title>Depto. {unidad} · {real:g} % de avance · {atrasadas} atrasadas</title>
            <polygon points="{puntos}"/>
            <rect x="{cx-16}" y="{cy-10}" width="32" height="20" rx="6"/>
            <text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central">{unidad}</text>
          </g>
        ''')
    return f'''
      <section id="plano" aria-labelledby="titulo-plano">
        <div class="plano-cabecera">
          <div><h2 id="titulo-plano">Plano interactivo · Piso 4</h2>
            <p>Selecciona un departamento para registrar avance o consultar sus partidas.</p></div>
          <div class="plano-controles" role="group" aria-label="Zoom del plano">
            <button type="button" data-zoom="-1" aria-label="Alejar plano">−</button>
            <button type="button" data-zoom="0">Ajustar</button>
            <button type="button" data-zoom="1" aria-label="Acercar plano">+</button>
          </div>
        </div>
        <div class="plano-visor" role="region" aria-label="Plano desplazable" tabindex="0">
          <svg id="plano-dibujo" viewBox="{x} {y} {ancho} {alto}" role="group"
               aria-label="Plano de tabiques D13f, departamentos 401 a 415">
            <image x="{x}" y="{y}" width="{ancho}" height="{alto}"
                   preserveAspectRatio="none" href="plano-piso-4.webp"/>
            {''.join(unidades)}
          </svg>
        </div>
        <div id="registro-plano" hidden></div>
        <ul class="plano-leyenda" aria-label="Estados del plano">
          <li class="en-curso">Sin atrasos</li>
          <li class="con-atrasos">Con atrasos</li>
          <li class="terminado">Terminado</li>
        </ul>
      </section>
    '''
