// Arranque del intérprete. La interfaz y los cálculos viven en Python.
async function iniciar() {
  try {
    const python = await loadPyodide();
    for (const archivo of ["datos.py", "control.py", "plano.py", "configuracion.py", "mediciones.py", "panel.py"]) {
      const respuesta = await fetch(archivo);
      if (!respuesta.ok) throw new Error(`${archivo}: ${respuesta.status}`);
      python.FS.writeFile(archivo, await respuesta.text());
    }
    await python.runPythonAsync("import panel; await panel.iniciar()");
  } catch (error) {
    const estado = document.getElementById("carga") ?? document.getElementById("mensaje");
    estado.textContent = "No se pudo iniciar PlantaControl. Comprueba la conexión y recarga la página.";
    console.error(error);
  } finally {
    document.getElementById("app").setAttribute("aria-busy", "false");
  }
}
iniciar();
