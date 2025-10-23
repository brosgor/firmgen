from firmgen import FirmGen

if __name__ == "__main__":
    print("="*60)
    print("CERTIFICADOR DE IMÁGENES - FirmGen")
    print("Agrega metadatos para certificar que un archivo es tuyo")
    print("="*60)
    
    # 1. Configura TU información personal
    firmgen = FirmGen(
        name="Tu Nombre",                    # 👈 CAMBIA esto
        email="tu.email@ejemplo.com",        # 👈 CAMBIA esto
        enterprise="Tu Empresa"              # 👈 CAMBIA esto
    )
    
    # 2. Archivo que quieres certificar (PNG o JPG)
    archivo = "img/firmation.png"  # 👈 CAMBIA por tu archivo
    
    print(f"\n� Certificando archivo: {archivo}")
    print(f"Autor: {firmgen.name}")
    print(f"Email: {firmgen.email}")
    print(f"Empresa: {firmgen.enterprise}\n")
    
    # 3. Agregar metadatos de certificación
    firmgen.add_metadata(
        archivo,
        description="Imagen certificada digitalmente como propiedad de su autor"
    )
    
    # 4. Verificar que se agregaron los metadatos
    print("\n📋 Verificando metadatos agregados:")
    firmgen.read_metadata(archivo)
    
    print("✅ ¡LISTO! Tu archivo está certificado.")
    print("\n💡 Para verificar:")
    print("   - Click derecho > Propiedades > pestaña Metadatos")
    print(f"   - O ejecuta: exiftool {archivo}")
    print(f"   - O para PNG: identify -verbose {archivo} | grep -i 'author\\|copyright'")


