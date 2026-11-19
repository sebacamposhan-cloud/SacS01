# PlantaControl

Panel del taller de control de avance de obra. Incluye 405 registros de demostración para 15 departamentos y 27 partidas. Permite cambiar la fecha de control, consultar el avance real y programado, filtrar partidas por departamento y descargar detalle, resumen y matriz en CSV.

## Plano interactivo

El visor representa el piso 4 del plano de tabiques D13f (revisión A). Los departamentos 401–415 corresponden a los registros 01–15. Selecciona una zona con el ratón o con Tab y Enter. El formulario permite registrar el porcentaje de una partida a la fecha de control, marcarla como terminada o abrir la lista de sus 27 partidas. Puedes ampliar y desplazar el plano.

La base gráfica es un recorte del PDF de referencia. Las áreas seleccionables fueron trazadas sobre el plano y son zonas de consulta, sin validez como medición CAD.

## Registro compartido con Supabase

1. Crea un proyecto en Supabase y ejecuta `supabase/migrations/001_mediciones.sql` en el editor SQL del proyecto.
2. Escribe la URL del proyecto y su clave **Publishable** en `docs/configuracion.py` y activa la configuración con un despliegue de GitHub Pages. Usa únicamente la clave publicable.
3. Guarda una medición desde el plano y compruébala en otro navegador al abrir PlantaControl o pulsar **Actualizar** en la fecha de control.

La configuración corresponde a un tablero abierto. Quien tenga acceso al sitio puede consultar y añadir mediciones. Cada guardado añade un registro al historial. Para una misma partida y fecha, se usa la última medición guardada. Las mediciones se reflejan desde su fecha en el plano, Avance, lista, Kanban y Carta Gantt.

Con la configuración vacía, el formulario guarda las mediciones en el navegador y lo indica en el plano. Las mediciones de ese modo quedan en el PC donde se introdujeron.

## Continuar el desarrollo

- `docs/index.html` y `docs/inicio.js` cargan Pyodide y llaman a `panel.iniciar()`.
- `docs/panel.py` contiene la navegación, el avance del piso, la lista de partidas, Kanban, Gantt y las exportaciones. `docs/plano.py` conserva el plano y las zonas pulsables.
- `docs/control.py` calcula avance y atrasos a partir del historial. La interfaz reutiliza ese resultado entre vistas.
- En el navegador, verifica **Plano → 407 → Ver las 27 partidas → Volver al plano** y **Avance → departamento atrasado → Kanban → Carta Gantt**. Los botones de vista comparten departamento, fecha y filtro. Las descargas están en **Avance → Informes y CSV**.

## Abrir desde un PC

Desde la raíz del repositorio, con Python 3 instalado:

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

Abre [PlantaControl local](http://127.0.0.1:8000/) en el navegador. La página descarga Pyodide desde jsDelivr y ejecuta Python en el navegador. Los datos y cálculos permanecen en el navegador. Para abrirla desde otro equipo de confianza en la misma red, cambia `127.0.0.1` por `0.0.0.0` y usa la IP local del PC que ejecuta el comando.

## Publicar en GitHub Pages

1. Abre [Settings → Pages del repositorio SacS01](https://github.com/sebacamposhan-cloud/SacS01/settings/pages) con la cuenta que administra el repositorio.
2. En **Build and deployment**, selecciona **Deploy from a branch** como fuente.
3. En **Branch**, elige **main** y **/docs**, y pulsa **Save**.

GitHub publicará automáticamente los archivos de `docs/` al guardar y cuando se actualice `main`. Cuando aparezca **Visit site** en la configuración del repositorio, abre [PlantaControl](https://sebacamposhan-cloud.github.io/SacS01/).

La lógica, los datos, los gráficos, la interfaz dinámica y los CSV están escritos en Python. HTML y CSS definen la estructura inicial y el estilo. Un archivo JavaScript pequeño inicia el intérprete. No se requiere instalar paquetes Python, crear cuentas de usuario en el panel ni operar un servidor de aplicación o una base de datos.
