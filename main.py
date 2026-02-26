from firmgen import FirmGen
import os


def ask(prompt, default=None):
    if default:
        value = input(f"{prompt} [{default}]: ").strip()
        return value if value else default
    return input(f"{prompt}: ").strip()


def ask_yes_no(prompt, default=True):
    suffix = "[S/n]" if default else "[s/N]"
    value = input(f"{prompt} {suffix}: ").strip().lower()
    if not value:
        return default
    return value in ("s", "si", "sí", "y", "yes")


def ensure_keys_loaded(firmgen, keys_dir="keys"):
    private_key_path = os.path.join(keys_dir, "private_key.pem")
    public_key_path = os.path.join(keys_dir, "public_key.pem")

    os.makedirs(keys_dir, exist_ok=True)

    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        if firmgen.load_private_key(private_key_path) and firmgen.load_public_key(public_key_path):
            print("✓ Llaves cargadas correctamente")
            return True

    if ask_yes_no("No se encontraron llaves válidas. ¿Deseas generarlas ahora?", default=True):
        generated = firmgen.generate_keys(private_key_path, public_key_path)
        if not generated:
            return False
        return firmgen.load_private_key(private_key_path) and firmgen.load_public_key(public_key_path)

    print("⚠️  Operación cancelada: se requieren llaves para firma criptográfica")
    return False


def validate_image_path(image_path):
    if not image_path:
        print("⚠️  Debes ingresar una ruta de imagen")
        return False
    if not os.path.exists(image_path):
        print(f"⚠️  Archivo no encontrado: {image_path}")
        return False
    if not image_path.lower().endswith((".png", ".jpg", ".jpeg")):
        print("⚠️  Solo se soportan formatos PNG/JPG/JPEG")
        return False
    return True


def option_sign_full(firmgen):
    image_path = ask("Ruta de imagen a firmar")
    if not validate_image_path(image_path):
        return

    use_watermark = ask_yes_no("¿Agregar marca de agua visible?", default=False)
    crypto_sign = ask_yes_no("¿Firmar hash criptográfico e incrustarlo en metadatos?", default=True)
    description = ask("Descripción", default="Imagen certificada digitalmente")

    if use_watermark:
        signature_path = ask("Ruta de imagen de firma (PNG recomendado)")
        if not os.path.exists(signature_path):
            print(f"⚠️  No existe la firma visual: {signature_path}")
            return
        if not firmgen.load_signature(signature_path):
            print("⚠️  No se pudo cargar la imagen de firma")
            return

    if crypto_sign and not ensure_keys_loaded(firmgen):
        return

    output_path = ask("Ruta de salida", default=image_path)
    success = firmgen.sign_image(
        input_image_path=image_path,
        output_image_path=output_path,
        description=description,
        crypto_sign=crypto_sign,
        hash_algorithm="sha256",
    )

    if success:
        print("\n📋 Metadatos resultantes:")
        firmgen.read_metadata(output_path)


def option_metadata_only(firmgen):
    image_path = ask("Ruta de imagen")
    if not validate_image_path(image_path):
        return

    description = ask("Descripción", default="Imagen certificada")
    crypto_sign = ask_yes_no("¿Firmar hash criptográfico e incrustarlo?", default=True)

    if crypto_sign and not ensure_keys_loaded(firmgen):
        return

    if firmgen.add_metadata(
        image_path,
        description=description,
        crypto_sign=crypto_sign,
        hash_algorithm="sha256",
    ):
        print("✓ Operación completada")


def option_verify_signature(firmgen):
    image_path = ask("Ruta de imagen a verificar")
    if not validate_image_path(image_path):
        return

    public_key_path = ask("Ruta de llave pública", default="keys/public_key.pem")
    if not os.path.exists(public_key_path):
        print(f"⚠️  Llave pública no encontrada: {public_key_path}")
        return

    if not firmgen.load_public_key(public_key_path):
        return

    firmgen.verify_embedded_signature(image_path)


def option_read_metadata(firmgen):
    image_path = ask("Ruta de imagen")
    if not validate_image_path(image_path):
        return
    firmgen.read_metadata(image_path)


def option_generate_keys(firmgen):
    keys_dir = ask("Directorio para llaves", default="keys")
    private_key_path = os.path.join(keys_dir, "private_key.pem")
    public_key_path = os.path.join(keys_dir, "public_key.pem")
    os.makedirs(keys_dir, exist_ok=True)

    password = ask("Password para llave privada (opcional)", default="")
    password = password if password else None

    firmgen.generate_keys(private_key_path, public_key_path, password=password)


def print_menu():
    print("\n" + "=" * 60)
    print("MENÚ FIRMGEN")
    print("=" * 60)
    print("1) Firmar imagen completa (marca de agua + metadatos + firma hash)")
    print("2) Agregar solo metadatos (opcional firma hash)")
    print("3) Leer metadatos de imagen")
    print("4) Verificar firma criptográfica incrustada")
    print("5) Generar llaves RSA")
    print("0) Salir")


def main():
    print("=" * 60)
    print("CERTIFICADOR DE IMÁGENES - FirmGen")
    print("Firma visual + metadatos + firma criptográfica del hash")
    print("=" * 60)

    name = ask("Nombre del autor", default="Tu Nombre")
    email = ask("Email", default="tu.email@ejemplo.com")
    enterprise = ask("Empresa/Institución", default="")

    firmgen = FirmGen(name=name, email=email, enterprise=enterprise)

    while True:
        print_menu()
        option = ask("Elige una opción", default="1")

        if option == "1":
            option_sign_full(firmgen)
        elif option == "2":
            option_metadata_only(firmgen)
        elif option == "3":
            option_read_metadata(firmgen)
        elif option == "4":
            option_verify_signature(firmgen)
        elif option == "5":
            option_generate_keys(firmgen)
        elif option == "0":
            print("👋 Hasta luego")
            break
        else:
            print("⚠️  Opción no válida")


if __name__ == "__main__":
    main()


