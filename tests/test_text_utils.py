import pytest
from pathlib import Path
from utils.text_utils import clean_name, clean_file_name, clean_directory_name

def test_clean_name_critical_case() -> None:
    # Caso crítico especificado por el usuario
    assert clean_name("C++ Programación") == "c++-programacion"

def test_clean_name_accents_and_special() -> None:
    assert clean_name("¡Hola, Mundo!") == "¡hola,-mundo!"
    assert clean_name("Árbol de decisión") == "arbol-de-decision"
    assert clean_name("pingüino") == "pinguino"
    assert clean_name("100% real no fake") == "100%-real-no-fake"

def test_clean_name_multiple_spaces_and_underscores() -> None:
    assert clean_name("  nombre   con   espacios  ") == "nombre-con-espacios"
    assert clean_name("nombre_con_guion_bajo") == "nombre-con-guion-bajo"
    assert clean_name("nombre--con_-_varios") == "nombre-con-varios"

def test_clean_file_name_preserves_extension() -> None:
    # Verificar que se preserve la extensión del archivo en minúsculas
    path = Path("Mis Documentos/Reporte Anual 2023.PDF")
    assert clean_file_name(path) == "reporte-anual-2023.pdf"

    path_no_ext = Path("ArchivoSinExtension")
    assert clean_file_name(path_no_ext) == "archivosinextension"

    path_complex = Path("Video_Tutorial_C++.mp4")
    assert clean_file_name(path_complex) == "video-tutorial-c++.mp4"

def test_clean_directory_name_removes_numeric_prefixes() -> None:
    # Validar la eliminación de prefijos numéricos
    path1 = Path("01. Carpeta")
    assert clean_directory_name(path1) == "carpeta"

    path2 = Path("123 - Otra Carpeta")
    assert clean_directory_name(path2) == "otra-carpeta"

    path3 = Path("05. Directorio")
    assert clean_directory_name(path3) == "directorio"

    # Caso donde el número no está al inicio
    path4 = Path("Carpeta 01")
    assert clean_directory_name(path4) == "carpeta-01"
