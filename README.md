# PathAtlas

PathAtlas es una herramienta de línea de comandos para recorrer directorios y
normalizar los nombres de archivos y carpetas. Permite trabajar sobre una ruta
específica o localizar una unidad por su punto de montaje. Por defecto muestra
una vista previa; los renombrados solo se aplican al añadir `--run`.

El proyecto también incluye funciones de Python para guardar árboles de
directorios en JSON y consultar estadísticas de archivos. Estas funciones se
invocan desde código; la CLI se encarga del renombrado.

## Características Principales

*   **Normalización y renombrado:**
    *   Convierte nombres y extensiones a minúsculas, elimina tildes, unifica espacios y guiones bajos como guiones y conserva signos compatibles como `+`, `#`, `!`, `%` y paréntesis.
    *   Elimina expresiones como `Copy of` y prefijos numéricos iniciales en nombres de carpetas.
    *   Gestión automática de colisiones agregando sufijos numéricos (ej: `nombre(1).txt`) para evitar sobrescribir archivos existentes.
    *   Procesa primero los archivos y después las carpetas, de mayor a menor profundidad y con orden alfabético dentro de cada nivel.
    *   Omite enlaces simbólicos y carpetas excluidas; solicita confirmación al aplicar un cambio que reduzca el nombre en más de cuatro caracteres.
*   **Configuración y vista previa:**
    *   Carga y valida `config.json` una vez por ejecución.
    *   Muestra los cambios agrupados por carpeta y permite revisarlos antes de usar `--run`.
*   **Funciones disponibles desde Python:**
    *   Construye árboles con diccionarios para directorios y `null` para archivos al serializarlos a JSON.
    *   Guarda las estructuras en un archivo JSON separado de la configuración.
    *   Consulta tamaño total, cantidad de archivos y fecha de la última modificación de los archivos de un directorio.

### Configuración Avanzada

La CLI lee `config.json` desde el directorio de trabajo actual, también al usar
el subcomando `path`. Ejecuta los comandos desde la raíz del repositorio.
Ejemplo de configuración:

```json
{
    "mount_point_label": "SSD",
    "ignore": [
        ".git",
        "__pycache__",
        "node_modules",
        "build",
        "dist"
    ]
}
```

*   **Esquema del JSON**:
    *   `mount_point_label`: Sufijo del punto de montaje que se buscará cuando no se indique una ruta. El subcomando `path` no requiere esta etiqueta.
    *   `ignore`: Lista de nombres exactos de carpetas que se omiten junto con todo su contenido durante el renombrado. La comparación distingue mayúsculas y minúsculas; no admite patrones ni rutas completas.
*   **Gestión de exclusiones**: Añade, por ejemplo, `.venv` o `venv` si hay entornos virtuales dentro de la ruta que vas a procesar. Los archivos y carpetas ocultos no se excluyen automáticamente.
*   Las claves `_comment_*` del archivo incluido son anotaciones; el cargador ignora las claves adicionales.

### Detección de Dispositivos y Puntos de Montaje (psutil)

`find_ssd_mount_point` (`core/mounts.py`) consulta `psutil.disk_partitions()` y
devuelve el primer punto de montaje cuya ruta, sin la barra final, termine en
`mount_point_label`. Por ejemplo, `SSD` coincide con `/media/usuario/SSD`.

La función devuelve un `Path` o `None`. El nombre de la función es histórico:
no comprueba si el dispositivo es un SSD ni consulta la etiqueta del sistema
de archivos. Si no encuentra una coincidencia, la CLI registra un error y
termina sin escanear.

| Parámetro | Tipo | Descripción |
| :--- | :--- | :--- |
| `label_ssd` | `str` | Sufijo del punto de montaje que se busca. |
| **Retorno** | `Path` / `None` | Un objeto `Path` del punto de montaje si se encuentra, o `None`. |

## Arquitectura y Entorno

*   **Python >= 3.13** y **`uv`** para gestionar el entorno y las dependencias.
*   **Dependencias declaradas en `pyproject.toml`:** `magic-python>=0.4.0`, `psutil>=7.2.2` y `pytest>=9.0.3`. La enumeración de particiones usa `psutil`; el flujo actual no importa `magic-python`.
*   **Desarrollo y pruebas:** el grupo `dev` incluye `pytest` y `pytest-mock`.
*   **Biblioteca estándar:** `pathlib`, `json`, `unicodedata` y `logging`, entre otros módulos. Las dependencias se fijan en `uv.lock`.

## Instalación y Uso

1.  **Requisitos:**
    *   Tener instalado Python 3.13 o superior.
    *   Tener instalado `uv` en el sistema.

2.  **Instalar dependencias:**
    Clona el repositorio y, dentro del directorio raíz, ejecuta:
    ```bash
    uv sync
    ```

3.  **Configurar y revisar los renombrados:**
    Ajusta `config.json` y ejecuta una vista previa sobre una carpeta:
    ```bash
    uv run main.py path "/ruta/Mis Archivos"
    ```

4.  **Aplicar los renombrados revisados:**
    ```bash
    uv run main.py path "/ruta/Mis Archivos" --run
    ```

Para usar la detección del punto de montaje configurado:

```bash
# Vista previa de la unidad
uv run main.py

# Aplicar cambios en la unidad configurada
uv run main.py --run
```

Comprueba la ruta seleccionada y las exclusiones antes de aplicar cambios.
La ejecución vuelve a escanear y calcular los destinos; la vista previa no
guarda un plan en disco. No se modifica el contenido de los archivos.

Para consultar las opciones de la CLI:

```bash
uv run main.py --help
uv run main.py path --help
```

## Organización por responsabilidad

| Módulo | Responsabilidad |
| :--- | :--- |
| `main.py` | Argumentos de la CLI, logging y coordinación del renombrado. |
| `core/config_loader.py` | Carga única y validación de la configuración JSON. |
| `core/mounts.py` | Detección del punto de montaje configurado. |
| `core/traversal.py` | Recorrido recursivo, exclusiones, selección de nombres y construcción del árbol. |
| `core/actions.py` | Orden de renombrado, resolución de colisiones y ejecución o vista previa. |
| `core/scanner.py` | Coordinación del escaneo de estructuras. |
| `core/structure_storage.py` | Lectura y guardado de estructuras en JSON. |
| `utils/text_utils.py` | Normalización de nombres. |
| `utils/file_metadata.py` | Consulta de tamaño, cantidad de archivos y última modificación. |
| `utils/formatting.py` | Formato de tamaños y fechas. |

Las pruebas se agrupan por módulo en `tests/`. El renombrado procesa primero los
archivos y después las carpetas, de mayor a menor profundidad. La vista previa
es el modo predeterminado; `uv run main.py --run` aplica los cambios.

Ejecuta toda la suite con `uv run pytest`.

### Salida de la CLI

La salida muestra la ruta de la carpeta una vez por grupo y después los pares
de nombres, tanto en vista previa como al aplicar los cambios:

```text
/ruta/Mis Archivos
Foto Verano.JPG -> foto-verano.jpg
Mi Informe.TXT -> mi-informe.txt
```

Los avisos y errores incluyen su nivel (`WARNING` o `ERROR`). La aplicación de
los cambios depende de `--run`; el formato de los pares es el mismo en ambos
modos.

### Trabajar sobre una ruta específica

El subcomando `path` permite indicar un directorio sin depender de la detección
de la unidad. Acepta rutas absolutas, relativas y `~`; la ruta debe existir y ser un
directorio. Las exclusiones de `config.json` también se aplican a este modo.

```bash
# Vista previa
uv run main.py path "/ruta/Mis Archivos"

# Aplicar los renombrados
uv run main.py path "/ruta/Mis Archivos" --run
```

Se procesan los archivos y subdirectorios dentro de la ruta indicada; el
directorio raíz conserva su nombre. Sin subcomando, `uv run main.py` sigue
buscando el punto de montaje configurado.

### Normalización y validación de renombrados

La limpieza conserva símbolos y puntuación como `+`, `#`, `!`, `%`, `&`,
paréntesis y puntos. En Linux también conserva `?` y `*`; en otros sistemas
los sustituye por separadores. Los caracteres `<>:"/\\|` y los de control
se sustituyen por separadores. Se mantienen las reglas de minúsculas,
eliminación de tildes, espacios/guiones bajos a guiones y eliminación de
prefijos numéricos en directorios. También se eliminan expresiones `Copy of`
(incluidas las variantes con guiones o guiones bajos) y puntos finales.

Ejemplos:

- `Programación en C++ y C#.TXT` → `programacion-en-c++-y-c#.txt`.
- `Copy of Informe.TXT` → `informe.txt`.
- Carpeta `01. Mis Documentos` → `mis-documentos`.
- En Linux, `A!.TXT` → `a!.txt` y `A?.TXT` → `a?.txt`.
- Un sufijo de colisión como `archivo(1).txt` se conserva en ejecuciones posteriores.

Antes de modificar el lote se validan todos los nombres y se reservan los
destinos para archivos y directorios. La vista previa y la ejecución usan
ese mismo procedimiento; con el mismo estado inicial asignan los mismos
destinos. Los nombres vacíos o inválidos se registran como errores y se
omiten, continuando con los demás elementos. Los enlaces simbólicos se
omiten como origen y cuentan como destinos ocupados, incluso si están rotos.

### Confirmación por pérdida de caracteres

Si la limpieza reduce el nombre en más de 4 caracteres, se muestran el nombre
original, el destino, el nombre limpio, las longitudes y el porcentaje de
reducción. Por ejemplo, `Copy of Informe.TXT` → `informe.txt` pierde 8 de
19 caracteres (42.1%). El cálculo incluye la extensión y excluye los sufijos
añadidos por colisiones, para que estos no oculten la pérdida.

En la vista previa solo se muestra el aviso. Con `--run`, cada renombrado
que supere el umbral requiere responder `s` o `sí` (también acepta `y` o
`yes`). Una respuesta vacía, negativa o una entrada no disponible omite ese
renombrado y continúa con el lote. Los renombrados de los demás elementos,
incluidos los de carpetas contenedoras, siguen su curso.

Esta medida expresa reducción de longitud; no evalúa el significado de lo
eliminado ni cuenta como pérdida los cambios de mayúsculas o tildes que
mantienen la longitud.

### Carga de configuración

`main()` carga y valida `config.json` una sola vez mediante `load_config()`.
Las consultas de `ignore` y `mount_point_label` usan el resultado en memoria;
los recorridos reciben las exclusiones directamente, sin abrir el JSON.
Cambiar el archivo durante el proceso no modifica la configuración de ese lote.
Cada nueva ejecución vuelve a cargar el archivo, sin estado global compartido.

El JSON debe ser un objeto; `ignore` debe ser una lista de strings y
`mount_point_label`, si se proporciona, un string no vacío o `null`.
Si falta `ignore`, se usa una lista vacía. La etiqueta solo es obligatoria
para detectar una unidad; el subcomando `path` no la necesita. Si el archivo
falta, no puede leerse o es inválido, la CLI registra el error y termina
con código 2 antes de escanear o renombrar.

### Generar una estructura JSON desde Python

La CLI no exporta estructuras automáticamente. Para crear una instantánea,
carga las exclusiones y llama al escáner con una ruta de salida explícita:

```python
from pathlib import Path
from core.config_loader import load_config
from core.scanner import scanner_structure_directories

config = load_config(Path("config.json"))
scanner_structure_directories(
    Path("/ruta"), config["ignore"], Path("structure.json")
)
```

El JSON usa el nombre normalizado del directorio raíz como clave y conserva
los nombres originales de sus elementos. Los directorios se representan con
objetos y los archivos con `null`; se omiten enlaces simbólicos y elementos
cuyo nombre esté en `ignore`. Este escaneo no renombra archivos ni carpetas.

Si el archivo de salida ya contiene un objeto JSON válido, se actualizan sus claves
de primer nivel con la estructura nueva. Una raíz con la misma clave se
reemplaza; las otras se conservan. Si el JSON existente está mal formado,
el guardado termina sin sobrescribirlo. Sin `structure_path`, el escáner
recorre el árbol pero no escribe una instantánea.

Las estadísticas se consultan por separado con
`utils.file_metadata.get_directory_stats(Path("/ruta"))`, que devuelve
`total_size`, `file_count` y `last_modified`. Esa función no recibe la lista
de exclusiones y no forma parte de la salida de la CLI.

## Experimentos de rendimiento

Los siguientes prototipos y resultados locales se conservan como referencia;
no están integrados en el flujo de renombrado de la CLI.

### Experimento: nombres en lotes de 50 con hilos

`experiments/batch_names.py` compara el flujo actual con un prototipo que
normaliza lotes de 50 nombres de forma secuencial o con 2, 4 y 8 hilos.
La CLI sigue usando el flujo actual. El GIL ya está activo en el intérprete
medido; no es una función que se añada al renombrador.

Para reproducir las mediciones sin tocar unidades reales:

```bash
.venv/bin/python -m experiments.batch_names --names 10000 --files 1000 --repeats 5
.venv/bin/python -m pytest tests/test_batch_experiment.py
```

Resultados locales con Python 3.13.12, GIL activo y 12 CPU lógicas, usando
medianas de cinco repeticiones. Los datos completos están en
[`experiments/batch_names_results.json`](experiments/batch_names_results.json).

| Variante | Normalizar 10 000 nombres | Escanear y renombrar 1000 archivos |
| :--- | ---: | ---: |
| Actual | 101.4 ms | 72.4 ms |
| Lotes de 50, secuencial con caché | 101.6 ms | 72.2 ms |
| Lotes de 50, 2 hilos con caché | 113.3 ms | 72.7 ms |
| Lotes de 50, 4 hilos con caché | 113.0 ms | 70.6 ms |
| Lotes de 50, 8 hilos con caché | 125.8 ms | 73.9 ms |

Todos los modos produjeron los mismos destinos y contenidos. Las pruebas
también cubren lotes vacíos e incompletos, colisiones entre lotes, exclusiones,
carpetas anidadas, vista previa, enlaces simbólicos y confirmaciones en el hilo
principal. Las reservas de destinos y los renombrados se mantienen secuenciales;
se paraleliza únicamente el cálculo de nombres.

La normalización aislada fue entre un 11% y un 24% más lenta con hilos. Las
diferencias del flujo completo son pequeñas y se solapan entre repeticiones;
no demuestran una mejora consistente. Las variantes por lotes reutilizan los
nombres mediante una caché, por lo que cualquier diferencia con el flujo
actual incluye ese cambio; la variante secuencial con caché permite compararlo.

El tiempo incluye escaneo, normalización, creación del pool, planificación y
renombrado. Excluye creación y borrado de datos, salida de logging y espera
humana de confirmaciones. Los archivos son pequeños, temporales y locales:
estas cifras no representan el rendimiento de un SSD externo ni de una unidad
de red. Los lotes agrupan el trabajo, pero el prototipo sigue guardando el plan
completo en memoria.

### Experimento: reutilizar el trabajo de obtención de rutas

`experiments/acquisition_reuse.py` compara el flujo actual con dos prototipos:
reutilizar los nombres calculados durante los dos recorridos existentes y,
además, obtener archivos y directorios en un único recorrido. La CLI conserva
su implementación actual. El experimento solo modifica árboles temporales.

Se encontraron estas repeticiones:

| Trabajo | Flujo actual | Recomendación |
| :--- | :--- | :--- |
| Enumeración del árbol | Una vez para archivos y otra para directorios | Unificar la obtención, manteniendo listas separadas para ordenar |
| Limpieza de cada nombre seleccionado | Obtención, planificación y aviso de pérdida | Calcular en la obtención y transportar el nombre limpio |
| Tipo del origen y enlaces simbólicos | Obtención y acciones posteriores | Conservar comprobaciones actuales: el origen puede cambiar |
| Disponibilidad del destino | Planificación y ejecución | Conservar ambas; un destino puede ocuparse después del plan |
| Reservas de destinos | Planificación global | Mantener después de ordenar, compartidas entre archivos y directorios |
| Confirmación de pérdida de caracteres | Antes de ejecutar cada cambio | Reutilizar el nombre limpio sin sufijo de colisión; mantener la confirmación |

La caché del prototipo distingue `(ruta, es_directorio)`. Una ruta que cambia
de directorio a archivo necesita las reglas de archivo: `01. Informe` se
convierte en `informe` como directorio y en `01.-informe` como archivo. Por eso
no basta con recordar el nombre usando solo la ruta. Tampoco conviene resolver
colisiones durante el recorrido: cambiaría el orden de asignación de sufijos.
Se mantienen archivos primero y directorios de mayor a menor profundidad.

Para reproducir:

```bash
.venv/bin/python -m experiments.acquisition_reuse --files 1000 --repeats 7
.venv/bin/python -m experiments.acquisition_reuse --files 5000 --repeats 5
.venv/bin/python -m pytest tests/test_acquisition_reuse.py
```

Resultados locales, Python 3.13.12, medianas de siete repeticiones para 1000
archivos, más casos auxiliares. Las variantes se alternan en orden aleatorio;
las dos escalas se miden por separado para evitar competencia entre benchmarks.

| Variante | Vista previa | Escaneo y renombrado |
| :--- | ---: | ---: |
| Actual | 61.86 ms | 75.41 ms |
| Reutilizar nombres, dos recorridos | 53.75 ms | 66.01 ms |
| Reutilizar nombres, un recorrido | 48.16 ms | 58.84 ms |

El último prototipo reduce el tiempo mediano un 22.2% en vista previa y un
22.0% al renombrar. La instrumentación, ejecutada fuera de las mediciones,
registra 3006 → 1003 llamadas de limpieza de archivos y 26 → 13 llamadas a
`iterdir`. Son llamadas de Python, no un conteo de operaciones físicas del disco.
Los datos y muestras están en
[`experiments/acquisition_reuse_results.json`](experiments/acquisition_reuse_results.json).

Las 29 pruebas del nuevo experimento comparan destinos, contenidos y mensajes;
cubren colisiones, exclusiones, nombres inválidos, enlaces rotos, carpetas
anidadas, vista previa y confirmaciones aceptadas/rechazadas. También simulan
orígenes eliminados, convertidos en enlaces o cambiados de tipo después de la
obtención, destinos ocupados después del escaneo y después de planificar, y
orígenes convertidos en enlaces durante la confirmación.

La recomendación es transportar datos preparados desde la obtención hasta el
plan, incluyendo ruta, tipo observado y nombre limpio, y conservar las
validaciones del estado del disco en planificación y ejecución. La caché usa
memoria adicional proporcional a los nombres registrados. Los tiempos incluyen
obtención, ordenación, planificación y ejecución; excluyen creación y borrado
del árbol, instrumentación, salida de logging y espera humana. Los archivos
son pequeños y locales: estas cifras no estiman el rendimiento de una unidad
externa o de red ni garantizan protección atómica contra cambios concurrentes
entre la última comprobación y `rename`.

Con 5000 archivos y cinco repeticiones se obtuvieron estas medianas:

| Variante | Vista previa | Escaneo y renombrado |
| :--- | ---: | ---: |
| Actual | 325.63 ms | 385.05 ms |
| Reutilizar nombres, dos recorridos | 276.00 ms | 344.90 ms |
| Reutilizar nombres, un recorrido | 249.24 ms | 308.19 ms |

La reducción del último prototipo fue del 23.5% en vista previa y del 20.0%
al renombrar, con los mismos resultados finales en todas las variantes.
Muestras completas en
[`experiments/acquisition_reuse_5000_results.json`](experiments/acquisition_reuse_5000_results.json).
Validación conjunta registrada al realizar el experimento:
`.venv/bin/python -m pytest`, **169 pruebas correctas**.
