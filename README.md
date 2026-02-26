# FirmGen - Firma de imágenes con hash criptográfico

FirmGen permite:
- escribir metadatos de autoría,
- firmar criptográficamente el hash de la imagen,
- incrustar la firma en el mismo archivo (PNG/JPG),
- crear un paquete separado de evidencia (carpeta y ZIP opcional),
- verificar después que la imagen no fue alterada.

## Características

- Metadatos de autor: `Author`, `Copyright`, `Description`, `Software`.
- Firma criptográfica RSA-PSS sobre hash SHA-256.
- Firma embebida en metadatos:
  - PNG: campos `FG-*`.
  - JPG/JPEG: EXIF `MakerNote` (sin sobrescribir `UserComment`).
- Exportación de paquete de firma:
  - carpeta en `signed_packages/`
  - `manifest.json` con hash/firma/autor
  - copia de imagen firmada
  - `public_key.pem` opcional
  - ZIP opcional para compartir/archivar
- Verificación de integridad y autenticidad con llave pública.

## Requisitos

```bash
pip install -r requirements.txt
```

Dependencias principales:
- `pillow`
- `piexif`
- `cryptography`

## Uso interactivo (recomendado)

Ejecuta:

```bash
python main.py
```

El menú interactivo permite:
1. Firmar imagen (hash criptográfico + metadatos, sin tocar original por defecto).
2. Agregar solo metadatos (asistente, con firma hash opcional).
3. Leer metadatos.
4. Verificar firma incrustada.
5. Generar llaves RSA.
6. Crear paquete/ZIP de firma.
7. Editar perfil de autor.

Durante el firmado, el asistente te pregunta si deseas:
- guardar resultado en copia (`signed_outputs/`) u original,
- crear automáticamente paquete de evidencia (carpeta + ZIP).

## Flujo recomendado

1. Generar llaves RSA (opción 5).
2. Firmar la imagen (opción 1 o 2 con firma criptográfica activa).
3. Crear/descargar paquete de evidencia (automático al firmar u opción 6).
4. Verificar firma embebida (opción 4) usando la llave pública.

## Paquete de firma (separado del original)

Cada paquete contiene evidencia transportable de la firma:

- `manifest.json`: autor, timestamp, algoritmo, hash y firma.
- imagen firmada (copia).
- `public_key.pem` (si se proporciona).
- archivo `.zip` opcional con todo lo anterior.

Esto permite compartir la evidencia sin depender del archivo original de trabajo.

## Uso por código (API)

```python
from firmgen import FirmGen

firmgen = FirmGen("Tu Nombre", "tu@email.com", "Tu Empresa")

# 1) Crear/cargar llaves
firmgen.generate_keys("keys/private_key.pem", "keys/public_key.pem")
firmgen.load_private_key("keys/private_key.pem")
firmgen.load_public_key("keys/public_key.pem")

# 2) Agregar metadatos + firma criptográfica
firmgen.add_metadata(
    "img/mi_imagen.jpg",
    description="Imagen certificada",
    crypto_sign=True,
    hash_algorithm="sha256"
)

# 3) Verificar firma
firmgen.verify_embedded_signature("img/mi_imagen.jpg")

# 4) Exportar paquete separado (carpeta + zip)
firmgen.export_signature_package(
  signed_image_path="img/mi_imagen.jpg",
  output_dir="signed_packages",
  zip_output=True,
  public_key_path="keys/public_key.pem"
)
```

## Nota sobre la verificación

La verificación hace dos comprobaciones:
1. Recalcula el hash visual de la imagen y lo compara con el hash incrustado.
2. Valida la firma RSA-PSS con la llave pública.

Si los píxeles cambian, la verificación falla.

## Estructura del proyecto

```text
firmgen/
├── firmgen.py
├── main.py
├── user.py
├── requirements.txt
└── README.md
```

## Recomendaciones

- Guarda `private_key.pem` de forma segura.
- Comparte solo `public_key.pem` para verificación.
- Para lotes de imágenes, reutiliza el mismo par de llaves.
