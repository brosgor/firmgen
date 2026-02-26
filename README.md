# FirmGen - Firma de imágenes con hash criptográfico

FirmGen permite:
- agregar marca de agua visible,
- escribir metadatos de autoría,
- firmar criptográficamente el hash de la imagen,
- incrustar la firma en el mismo archivo (PNG/JPG),
- verificar después que la imagen no fue alterada.

## Características

- Marca de agua visual opcional.
- Metadatos de autor: `Author`, `Copyright`, `Description`, `Software`.
- Firma criptográfica RSA-PSS sobre hash SHA-256.
- Firma embebida en metadatos:
  - PNG: campos `FG-*`.
  - JPG/JPEG: EXIF `MakerNote` (sin sobrescribir `UserComment`).
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
1. Firmar imagen completa (marca de agua + metadatos + firma hash).
2. Agregar solo metadatos (con firma hash opcional).
3. Leer metadatos.
4. Verificar firma incrustada.
5. Generar llaves RSA.

## Flujo recomendado

1. Generar llaves RSA (opción 5).
2. Firmar la imagen (opción 1 o 2 con firma criptográfica activa).
3. Verificar firma embebida (opción 4) usando la llave pública.

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
