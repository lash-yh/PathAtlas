# File Organizer & Scanner

Este proyecto es una herramienta para el escaneo, renombrado seguro de archivos y directorios, y la generación de estructuras en formato JSON. Su enfoque principal es la manipulación de nombres evitando colisiones y el soporte para identificar puntos de montaje en discos SSD.

## Características Principales

*   **Renombrado Seguro y Limpieza:**
    *   `resolve_name_path`: Renombra archivos y carpetas eliminando tildes (usando normalización Unicode) y normalizando espacios, conservando signos como `+`, `#`, `!`, `%` y paréntesis, convirtiéndolos en formatos uniformes (en minúsculas, separados por guiones).
    *   Gestión automática de colisiones agregando sufijos numéricos (ej: `nombre(1).txt`) para evitar sobrescribir archivos existentes.
*   **Escaneo y Generación de Estructuras (JSON):**
    *   Escanea de forma recursiva un directorio y genera una representación en árbol (diccionario) de toda su estructura.
    *   Soporte para listas de exclusión (ignorar ciertas carpetas) cargadas desde un archivo de configuración JSON.
    *   Carga única del JSON (`config_loader.py`) por ejecución y consultas posteriores en memoria, sin caché global.
    *   Guardado automático de la estructura escaneada en un archivo de configuración (`save_structure_directories`).

### Configuración Avanzada

El sistema de escaneo se puede controlar a través del archivo `config.json`. A continuación un ejemplo típico de configuración para entornos de desarrollo:

```json
{
    "_comment_mount_point_label": "Etiqueta que identifica un disco de almacenamiento SSD en el sistema. Se usa para resolver rutas.",
    "mount_point_label": "SSD",
    "_comment_ignore": "Lista de nombres de carpetas que el escáner omitirá recursivamente.",
    "ignore": [
        ".git",
        "__pycache__",
        "node_modules"
    ]
}
```

*   **Esquema del JSON**:
    *   `mount_point_label`: Especifica la etiqueta del disco que el sistema intentará localizar como unidad de almacenamiento rápido SSD.
    *   `ignore`: Un arreglo de strings con los nombres de las carpetas a omitir.
*   **Gestión de Exclusiones**: Para añadir nuevas carpetas que no desees escanear (por ejemplo, entornos virtuales), simplemente añade su nombre al array de `ignore`. El escáner automáticamente saltará estas carpetas y no procesará su contenido de forma recursiva.

### Detección de Dispositivos y Puntos de Montaje (psutil)

El proyecto interactúa fuertemente con el sistema de archivos y hardware mediante la librería externa **psutil**.

*   **`find_ssd_mount_point` (`core/mounts.py`)**: Utiliza `psutil.disk_partitions()` para realizar una enumeración eficiente de las particiones del sistema.
    *   **Lógica y Filtrado**: Itera sobre todas las particiones conectadas, y realiza una limpieza en las rutas (`rstrip('/')`). Finalmente, compara cada punto de montaje contra la etiqueta (`mount_point_label`) que configuramos, devolviendo la partición que finaliza con esta etiqueta.
    *   **Retorno Tipado**: Aunque `psutil` retorna resultados como cadenas de texto convencionales (strings), esta función encapsula inmediatamente el valor dentro de un objeto `Path` (`pathlib`), asegurando la consistencia y mantenibilidad del uso de rutas en todo el proyecto.

| Parámetro | Tipo | Descripción |
| :--- | :--- | :--- |
| `label_ssd` | `str` | La etiqueta del disco que deseamos encontrar. |
| **Retorno** | `Path` / `None` | Un objeto `Path` del punto de montaje si se encuentra, o `None`. |

## Arquitectura y Entorno

Este proyecto ha sido desarrollado con los siguientes requisitos en mente:

*   **Python >= 3.13:** Utiliza las características más recientes de Python y validaciones rigurosas de tipo (Type Hinting) en todo el código fuente, mejorando el uso del IDE y la prevención de errores.
*   **Gestor de Paquetes `uv`:** Las dependencias del proyecto se gestionan de manera ultrarrápida utilizando `uv`. La instalación y el aislamiento de dependencias se configuran de forma automatizada mediante el uso del archivo `uv.lock`, asegurando reproducibilidad determinista en sistemas operativos robustos como Fedora.
*   **Librerías Estándar:** Se prioriza el uso de la biblioteca estándar, especialmente `pathlib` (para manejo avanzado de rutas multiplataforma) y `json` (para las estructuras de directorios y configuración).
*   **`psutil`:** La única dependencia externa requerida (`psutil>=7.2.2`) utilizada para la enumeración de particiones y puntos de montaje.
*   **Optimizado para Btrfs:** Aunque la lógica principal (como la detección en hardware mediante psutil o la gestión de rutas con pathlib) es netamente multiplataforma, el proyecto está validado de forma específica para sistemas de archivos Btrfs.

## Instalación y Uso

1.  **Requisitos:**
    *   Tener instalado Python 3.13 o superior.
    *   Tener instalado `uv` en el sistema.

2.  **Instalar dependencias:**
    Clona el repositorio y, dentro del directorio raíz, ejecuta:
    ```bash
    uv sync
    ```

3.  **Ejecutar el proyecto:**
    Ejecuta una vista previa de los renombrados usando `uv`:
    ```bash
    uv run main.py
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

### Trabajar sobre una ruta específica

El subcomando `path` permite indicar un directorio sin depender de la detección
del SSD. Acepta rutas absolutas, relativas y `~`; la ruta debe existir y ser un
directorio. Las exclusiones de `config.json` también se aplican a este modo.

```bash
# Vista previa
uv run main.py path "/ruta/Mis Archivos"

# Aplicar los renombrados
uv run main.py path "/ruta/Mis Archivos" --run
```

Se procesan los archivos y subdirectorios dentro de la ruta indicada; el
directorio raíz conserva su nombre. Sin subcomando, `uv run main.py` sigue
buscando el SSD configurado.

### Normalización y validación de renombrados

La limpieza conserva símbolos y puntuación como `+`, `#`, `!`, `%`, `&`,
paréntesis y puntos. En Linux también conserva `?` y `*`; en otros sistemas
los sustituye por separadores. Los caracteres `<>:"/\\|` y los de control
se sustituyen por separadores. Se mantienen las reglas de minúsculas,
eliminación de tildes, espacios/guiones bajos a guiones y eliminación de
prefijos numéricos en directorios.

Ejemplos:

- `Programación en C++ y C#.TXT` → `programacion-en-c++-y-c#.txt`.
- En Linux, `A!.TXT` → `a!.txt` y `A?.TXT` → `a?.txt`.
- Un sufijo de colisión como `archivo(1).txt` se conserva en ejecuciones posteriores.

Antes de modificar el lote se validan todos los nombres y se reservan los
destinos para archivos y directorios. La vista previa y la ejecución usan
ese mismo procedimiento; con el mismo estado inicial asignan los mismos
destinos. Los nombres vacíos o inválidos se registran como errores y se
omiten, continuando con los demás elementos. Los enlaces simbólicos se
omiten como origen y cuentan como destinos ocupados, incluso si están rotos.

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

Las funciones internas ya no reciben la ruta del JSON:

```python
from pathlib import Path
from core.config_loader import load_config
from core.traversal import get_name_files
from core.scanner import scanner_structure_directories

config = load_config(Path("config.json"))
files = list(get_name_files(Path("/ruta"), config["ignore"]))
scanner_structure_directories(
    Path("/ruta"), config["ignore"], Path("structure.json")
)
```
