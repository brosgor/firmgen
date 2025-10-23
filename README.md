# FirmGen - Sistema de Firma Digital de Imágenes

Sistema para firmar digitalmente tus imágenes con marca de agua y metadatos EXIF que certifican la autoría.

## 🎯 Características

- ✅ **Marca de agua visible**: Agrega tu firma visual a las imágenes
- ✅ **Metadatos EXIF**: Inserta tu información en los metadatos de la imagen
- ✅ **Certificación de autoría**: Verifica que la imagen es tuya viendo las propiedades
- ✅ **Personalizable**: Controla posición, tamaño y opacidad de la firma
- ✅ **Múltiples formatos**: Compatible con JPG, PNG, etc.

## 📦 Instalación

```bash
# Instalar las dependencias necesarias
pip install Pillow piexif
```

## 🚀 Uso Básico

### 1. Configurar tu información

```python
from main import FirmGen

# Crear instancia con TU información
firmgen = FirmGen(
    name="Tu Nombre",
    email="tu.email@ejemplo.com",
    enterprise="Tu Empresa"
)

# Cargar tu imagen de firma
firmgen.load_signature("img/firmation.png")
```

### 2. Firmar una imagen (marca de agua + metadatos)

```python
# Firmar imagen completa
firmgen.sign_image(
    input_image_path="img/mi_foto.jpg",
    output_image_path="img/mi_foto_firmada.jpg",
    position='bottom-right',  # bottom-right, bottom-left, top-right, top-left, center
    opacity=0.7,              # 0.0 (transparente) a 1.0 (opaco)
    scale=0.15,               # Tamaño respecto a la imagen (0.0 a 1.0)
    description="Foto certificada y firmada"
)
```

### 3. Solo agregar metadatos (sin marca visible)

```python
# Solo metadatos EXIF
firmgen.add_metadata(
    "img/mi_imagen.jpg",
    description="Imagen certificada"
)
```

### 4. Solo agregar marca de agua

```python
# Solo marca visual
firmgen.add_watermark(
    input_image_path="img/original.jpg",
    output_image_path="img/con_marca.jpg",
    position='center',
    opacity=0.5,
    scale=0.2
)
```

### 5. Leer metadatos de una imagen

```python
# Ver información de certificación
firmgen.read_metadata("img/mi_imagen_firmada.jpg")
```

## 📋 Verificar la Firma

### En Linux (interfaz gráfica)
1. Click derecho sobre la imagen
2. Seleccionar "Propiedades"
3. Ir a la pestaña "Imagen" o "Metadatos"
4. Verás: Autor, Copyright, Descripción, etc.

### Con comando de terminal
```bash
# Instalar exiftool
sudo apt install libimage-exiftool-perl

# Ver metadatos
exiftool imagen_firmada.jpg
```

### Con el script Python
```python
firmgen.read_metadata("imagen_firmada.jpg")
```

## 📁 Estructura del Proyecto

```
firmgen/
├── main.py              # Clase principal FirmGen
├── user.py              # Clase User con información del usuario
├── ejemplo_uso.py       # Script de ejemplo
├── README.md            # Este archivo
└── img/
    ├── firmation.png    # Tu imagen de firma
    └── ...              # Tus imágenes a firmar
```

## 🔧 Parámetros Disponibles

### Posiciones de firma
- `'bottom-right'`: Esquina inferior derecha (predeterminado)
- `'bottom-left'`: Esquina inferior izquierda
- `'top-right'`: Esquina superior derecha
- `'top-left'`: Esquina superior izquierda
- `'center'`: Centro de la imagen

### Opacidad
- `0.0`: Completamente transparente
- `1.0`: Completamente opaco
- Recomendado: `0.5` a `0.8`

### Escala
- `0.0` a `1.0`: Tamaño respecto a la imagen original
- Recomendado: `0.1` a `0.2` para firmas discretas

## 💡 Ejemplos de Uso

### Firma discreta para fotos profesionales
```python
firmgen.sign_image(
    "foto.jpg", "foto_firmada.jpg",
    position='bottom-right',
    opacity=0.5,
    scale=0.1
)
```

### Marca de agua prominente para protección
```python
firmgen.sign_image(
    "diseño.png", "diseño_protegido.png",
    position='center',
    opacity=0.3,
    scale=0.4
)
```

### Solo certificación con metadatos (sin marca visible)
```python
firmgen.add_metadata("documento.jpg", "Documento oficial certificado")
```

## 📝 Notas Importantes

- Los metadatos EXIF permanecen en la imagen incluso si se comparte
- La marca de agua visible es permanente (forma parte de los píxeles)
- Puedes combinar ambos métodos para máxima protección
- Los metadatos pueden verse con la mayoría de visores de imágenes

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Siéntete libre de mejorar el código.

## 📄 Licencia

Este proyecto es de código abierto y está disponible para uso personal y comercial.
