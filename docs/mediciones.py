"""Persistencia de mediciones para el navegador."""

import json

from configuracion import SUPABASE_CLAVE_PUBLICABLE, SUPABASE_URL

CLAVE_LOCAL = 'plantacontrol.mediciones.v1'


class HistorialMediciones:
    def __init__(self):
        self.compartido = bool(SUPABASE_URL and SUPABASE_CLAVE_PUBLICABLE)
        self.registros = []

    async def solicitar(self, query, **opciones):
        from js import AbortSignal
        from pyodide.http import pyfetch

        headers = {
            'apikey': SUPABASE_CLAVE_PUBLICABLE,
            'Content-Type': 'application/json',
        }
        headers.update(opciones.pop('headers', {}))
        respuesta = await pyfetch(
            f'{SUPABASE_URL.rstrip("/")}/rest/v1/mediciones?{query}',
            headers=headers, signal=AbortSignal.timeout(8000), **opciones,
        )
        if not respuesta.ok:
            raise OSError(f'Supabase devolvió HTTP {respuesta.status}')
        return respuesta

    async def cargar(self):
        if not self.compartido:
            from js import localStorage
            self.registros = json.loads(localStorage.getItem(CLAVE_LOCAL) or '[]')
            return

        registros = []
        ultimo = 0
        while True:
            respuesta = await self.solicitar(
                f'select=*&orden=gt.{ultimo}&order=orden.asc&limit=200'
            )
            lote = await respuesta.json()
            if not lote:
                break
            registros.extend(lote)
            ultimo = lote[-1]['orden']
        self.registros = registros

    async def guardar(self, medicion):
        if self.compartido:
            await self.solicitar(
                'on_conflict=id', method='POST', body=json.dumps(medicion),
                headers={'Prefer': 'resolution=ignore-duplicates,return=minimal'},
            )
            # El servidor ordena las mediciones concurrentes.
            return

        from js import localStorage
        await self.cargar()
        if not any(fila['id'] == medicion['id'] for fila in self.registros):
            registros = [*self.registros, medicion]
            localStorage.setItem(CLAVE_LOCAL, json.dumps(registros))
            self.registros = registros
