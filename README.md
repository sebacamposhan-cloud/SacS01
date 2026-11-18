# PlantaControl

Panel del taller de control de avance de obra. Incluye 405 registros de demostración para 15 departamentos y 27 partidas. Permite cambiar la fecha de control, consultar el avance real y programado, filtrar partidas por departamento y descargar detalle, resumen y matriz en CSV.

## Abrir desde un PC

Desde la raíz del repositorio, con Python 3 instalado:

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

Abre [PlantaControl local](http://127.0.0.1:8000/) en el navegador. La página descarga Pyodide desde jsDelivr y ejecuta Python en el navegador. Los datos y cálculos permanecen en el navegador. Para abrirla desde otro equipo de confianza en la misma red, cambia `127.0.0.1` por `0.0.0.0` y usa la IP local del PC que ejecuta el comando.

## Publicar en GitHub Pages

En el repositorio, elige **Settings → Pages → Build and deployment → Source → GitHub Actions**. Luego ejecuta **Publicar PlantaControl en GitHub Pages** en la pestaña **Actions**. GitHub indicará la URL publicada en el despliegue. Si el repositorio es privado, la disponibilidad de Pages depende del plan de GitHub.

La lógica, los datos, los gráficos, la interfaz dinámica y los CSV están escritos en Python. HTML y CSS definen la estructura inicial y el estilo. Un archivo JavaScript pequeño inicia el intérprete. No se requiere instalar paquetes Python, crear cuentas de usuario en el panel ni operar un servidor de aplicación o una base de datos.
