from firmgen import FirmGen
import os
import shutil
from datetime import datetime


def ask(prompt, default=None):
    if default is not None:
        value = input(f"{prompt} [{default}]: ").strip()
        return value if value else default
    return input(f"{prompt}: ").strip()


def ask_yes_no(prompt, default=True):
    suffix = "[S/n]" if default else "[s/N]"
    value = input(f"{prompt} {suffix}: ").strip().lower()
    if not value:
        return default
    return value in ("s", "si", "sí", "y", "yes")


def choose_option(prompt, options):
    print(prompt)
    for key, label in options:
        print(f"  {key}) {label}")

    valid = {key for key, _ in options}
    while True:
        value = input("Selecciona una opción: ").strip()
        if value in valid:
            return value
        print("⚠️  Opción inválida, intenta de nuevo.")


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


def get_default_signed_path(image_path):
    os.makedirs("signed_outputs", exist_ok=True)
    image_name = os.path.basename(image_path)
    stem, ext = os.path.splitext(image_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join("signed_outputs", f"{stem}_firmada_{timestamp}{ext}")


def ask_image_path(prompt_text):
    while True:
        image_path = ask(prompt_text)
        if validate_image_path(image_path):
            return image_path

        if not ask_yes_no("¿Deseas intentar otra ruta?", default=True):
            return None


def edit_author_profile(firmgen):
    print("\n🧾 Perfil actual")
    print(f"- Nombre: {firmgen.name}")
    print(f"- Email: {firmgen.email}")
    print(f"- Empresa: {firmgen.enterprise}")

    firmgen.set_info(
        ask("Nombre", default=firmgen.name or ""),
        ask("Email", default=firmgen.email or ""),
        ask("Empresa/Institución", default=firmgen.enterprise or ""),
    )
    print("✓ Perfil actualizado")


def option_sign_full(firmgen):
    print("\n🖊️  Asistente de firmado")
    image_path = ask_image_path("Ruta de imagen ORIGINAL a firmar")
    if not image_path:
        return

    print("\nLa imagen original no se modifica por defecto.")
    output_mode = choose_option(
        "¿Dónde guardar el resultado firmado?",
        [
            ("1", "Crear copia en signed_outputs (recomendado)"),
            ("2", "Elegir ruta de salida manual"),
            ("3", "Sobrescribir archivo original"),
        ],
    )

    if output_mode == "1":
        output_path = get_default_signed_path(image_path)
    elif output_mode == "2":
        output_path = ask("Ruta de salida", default=get_default_signed_path(image_path))
    else:
        output_path = image_path

    crypto_sign = ask_yes_no("¿Firmar hash criptográfico e incrustarlo en metadatos?", default=True)
    description = ask("Descripción", default="Imagen certificada digitalmente")

    if crypto_sign and not ensure_keys_loaded(firmgen):
        return

    if output_path != image_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        shutil.copy2(image_path, output_path)

    success = firmgen.add_metadata(
        output_path,
        description=description,
        crypto_sign=crypto_sign,
        hash_algorithm="sha256",
    )

    if success:
        print(f"✓ Imagen firmada guardada en: {output_path}")

        if crypto_sign:
            build_package = ask_yes_no(
                "¿Crear paquete separado con evidencia de firma (carpeta + ZIP)?",
                default=True,
            )
            if build_package:
                public_key_path = ask("Ruta de llave pública para incluir en el paquete", default="keys/public_key.pem")
                package_dir = ask("Directorio base de paquetes", default="signed_packages")
                create_zip = ask_yes_no("¿Crear también ZIP del paquete?", default=True)
                firmgen.export_signature_package(
                    signed_image_path=output_path,
                    output_dir=package_dir,
                    zip_output=create_zip,
                    public_key_path=public_key_path if os.path.exists(public_key_path) else None,
                )

        print("\n📋 Metadatos resultantes:")
        firmgen.read_metadata(output_path)


def option_metadata_only(firmgen):
    print("\n🧩 Asistente de metadatos")
    source_image = ask_image_path("Ruta de imagen ORIGINAL")
    if not source_image:
        return

    output_mode = choose_option(
        "¿Aplicar metadatos sobre copia o original?",
        [
            ("1", "Crear copia en signed_outputs (recomendado)"),
            ("2", "Elegir ruta de salida manual"),
            ("3", "Sobrescribir original"),
        ],
    )

    if output_mode == "1":
        image_path = get_default_signed_path(source_image)
        with open(source_image, "rb") as src, open(image_path, "wb") as dst:
            dst.write(src.read())
    elif output_mode == "2":
        image_path = ask("Ruta de salida", default=get_default_signed_path(source_image))
        with open(source_image, "rb") as src, open(image_path, "wb") as dst:
            dst.write(src.read())
    else:
        image_path = source_image

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
        print(f"✓ Operación completada en: {image_path}")

        if crypto_sign and ask_yes_no("¿Crear paquete separado de firma para esta imagen?", default=True):
            public_key_path = ask("Ruta de llave pública para incluir", default="keys/public_key.pem")
            package_dir = ask("Directorio base de paquetes", default="signed_packages")
            create_zip = ask_yes_no("¿Crear ZIP del paquete?", default=True)
            firmgen.export_signature_package(
                signed_image_path=image_path,
                output_dir=package_dir,
                zip_output=create_zip,
                public_key_path=public_key_path if os.path.exists(public_key_path) else None,
            )


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


def option_create_package(firmgen):
    print("\n📦 Crear paquete de firma")
    signed_image = ask_image_path("Ruta de imagen firmada (con firma criptográfica incrustada)")
    if not signed_image:
        return

    package_dir = ask("Directorio base de paquetes", default="signed_packages")
    create_zip = ask_yes_no("¿Crear ZIP del paquete?", default=True)
    public_key_path = ask("Ruta de llave pública para incluir (opcional)", default="keys/public_key.pem")

    result = firmgen.export_signature_package(
        signed_image_path=signed_image,
        output_dir=package_dir,
        zip_output=create_zip,
        public_key_path=public_key_path if os.path.exists(public_key_path) else None,
    )
    if not result:
        print("⚠️  No se pudo crear el paquete")


def print_menu():
    print("\n" + "=" * 60)
    print("MENÚ FIRMGEN")
    print("=" * 60)
    print("1) Firmar imagen (hash criptográfico + metadatos)")
    print("2) Agregar solo metadatos (asistente)")
    print("3) Leer metadatos")
    print("4) Verificar firma criptográfica")
    print("5) Generar llaves RSA")
    print("6) Crear paquete/ZIP de firma")
    print("7) Editar perfil de autor")
    print("0) Salir")


def main():
    print("=" * 60)
    print("CERTIFICADOR DE IMÁGENES - FirmGen")
    print("Metadatos + firma criptográfica del hash")
    print("=" * 60)

    name = ask("Nombre del autor", default="Tu Nombre")
    email = ask("Email", default="tu.email@ejemplo.com")
    enterprise = ask("Empresa/Institución", default="")

    firmgen = FirmGen(name=name, email=email, enterprise=enterprise)

    while True:
        print_menu()
        print(f"\nPerfil activo: {firmgen.name} | {firmgen.email} | {firmgen.enterprise}")
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
        elif option == "6":
            option_create_package(firmgen)
        elif option == "7":
            edit_author_profile(firmgen)
        elif option == "0":
            print("👋 Hasta luego")
            break
        else:
            print("⚠️  Opción no válida")


if __name__ == "__main__":
    main()


