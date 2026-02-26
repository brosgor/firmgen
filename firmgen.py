from user import User
from PIL import Image
import piexif
import os
import base64
import hashlib
import json
import shutil
import zipfile
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

class FirmGen(User):
    def __init__(self, name=None, email=None, enterprise=None):
        super().__init__(name, email, enterprise)
        self.private_key = None
        self.public_key = None

    def generate_keys(self, private_key_path, public_key_path, password=None, key_size=2048):
        """Genera un par de llaves RSA para firma criptográfica."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        public_key = private_key.public_key()

        encryption = serialization.NoEncryption()
        if password:
            encryption = serialization.BestAvailableEncryption(password.encode("utf-8"))

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption,
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        with open(private_key_path, "wb") as private_file:
            private_file.write(private_pem)
        with open(public_key_path, "wb") as public_file:
            public_file.write(public_pem)

        self.private_key = private_key
        self.public_key = public_key
        print(f"✓ Llave privada creada: {private_key_path}")
        print(f"✓ Llave pública creada: {public_key_path}")
        return True

    def load_private_key(self, private_key_path, password=None):
        """Carga una llave privada PEM para firmar hashes."""
        try:
            with open(private_key_path, "rb") as key_file:
                key_data = key_file.read()

            pwd = password.encode("utf-8") if password else None
            self.private_key = serialization.load_pem_private_key(key_data, password=pwd)
            self.public_key = self.private_key.public_key()
            return True
        except Exception as e:
            print(f"Error al cargar llave privada: {e}")
            return False

    def load_public_key(self, public_key_path):
        """Carga una llave pública PEM para verificar firmas."""
        try:
            with open(public_key_path, "rb") as key_file:
                key_data = key_file.read()

            self.public_key = serialization.load_pem_public_key(key_data)
            return True
        except Exception as e:
            print(f"Error al cargar llave pública: {e}")
            return False

    def _compute_image_pixel_hash(self, image_path, hash_algorithm="sha256"):
        """Calcula hash sobre contenido visual (píxeles), ignorando metadatos."""
        hasher = hashlib.new(hash_algorithm)

        with Image.open(image_path) as img:
            normalized = img.convert("RGBA")
            header = f"{normalized.width}x{normalized.height}|RGBA|".encode("utf-8")
            hasher.update(header)
            hasher.update(normalized.tobytes())

        return hasher.hexdigest()

    def _get_public_key_fingerprint(self):
        """Retorna fingerprint SHA-256 de la llave pública cargada."""
        if not self.public_key:
            return None

        public_der = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return hashlib.sha256(public_der).hexdigest()

    def _sign_hash_value(self, hash_hex):
        """Firma un hash hexadecimal con RSA-PSS-SHA256 y retorna Base64."""
        if not self.private_key:
            raise ValueError("No hay llave privada cargada. Usa load_private_key() primero.")

        signature = self.private_key.sign(
            hash_hex.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _verify_signature_value(self, hash_hex, signature_b64):
        """Verifica firma Base64 usando la llave pública cargada."""
        if not self.public_key:
            raise ValueError("No hay llave pública cargada. Usa load_public_key() primero.")

        signature = base64.b64decode(signature_b64.encode("utf-8"))
        self.public_key.verify(
            signature,
            hash_hex.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True

    def _embed_crypto_metadata(self, image_path, crypto_data):
        """Incrusta metadatos criptográficos en PNG o JPG."""
        from PIL import PngImagePlugin

        is_png = image_path.lower().endswith('.png')
        is_jpg = image_path.lower().endswith(('.jpg', '.jpeg'))

        if is_png:
            with Image.open(image_path) as img:
                metadata = PngImagePlugin.PngInfo()
                for key, value in img.info.items():
                    if isinstance(value, str):
                        metadata.add_text(key, value)

                metadata.add_text("FG-Hash", crypto_data["hash"])
                metadata.add_text("FG-Hash-Algorithm", crypto_data["hash_algorithm"])
                metadata.add_text("FG-Signature", crypto_data["signature"])
                metadata.add_text("FG-Signature-Algorithm", crypto_data["signature_algorithm"])
                metadata.add_text("FG-Key-Fingerprint", crypto_data["key_fingerprint"])
                metadata.add_text("FG-Signed-At", crypto_data["signed_at"])

                img.save(image_path, pnginfo=metadata)
            return True

        if is_jpg:
            try:
                exif_dict = piexif.load(image_path)
            except Exception:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

            payload = json.dumps(crypto_data, ensure_ascii=False)
            exif_dict["Exif"][piexif.ExifIFD.MakerNote] = payload.encode("utf-8")
            exif_dict["0th"][piexif.ImageIFD.Software] = "FirmGen".encode("utf-8")

            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
            return True

        print(f"⚠️  Formato no soportado para firma criptográfica: {image_path}")
        return False

    def _extract_crypto_metadata(self, image_path):
        """Extrae metadatos criptográficos desde PNG o JPG."""
        is_png = image_path.lower().endswith('.png')
        is_jpg = image_path.lower().endswith(('.jpg', '.jpeg'))

        if is_png:
            with Image.open(image_path) as img:
                info = img.info
                required = {
                    "hash": info.get("FG-Hash"),
                    "hash_algorithm": info.get("FG-Hash-Algorithm"),
                    "signature": info.get("FG-Signature"),
                    "signature_algorithm": info.get("FG-Signature-Algorithm"),
                    "key_fingerprint": info.get("FG-Key-Fingerprint"),
                    "signed_at": info.get("FG-Signed-At"),
                }
                if required["hash"] and required["signature"]:
                    return required
                return None

        if is_jpg:
            try:
                exif_dict = piexif.load(image_path)
                exif_section = exif_dict.get("Exif", {})
                raw_comment = exif_section.get(piexif.ExifIFD.MakerNote)
                if not raw_comment:
                    raw_comment = exif_section.get(piexif.ExifIFD.UserComment)
                if not raw_comment:
                    return None

                if isinstance(raw_comment, bytes):
                    raw_comment = raw_comment.decode("utf-8", errors="ignore")

                data = json.loads(raw_comment)
                if data.get("hash") and data.get("signature"):
                    return data
                return None
            except Exception:
                return None

        return None

    def sign_hash_and_embed(self, image_path, hash_algorithm="sha256"):
        """
        Calcula hash criptográfico del contenido visual, firma el hash
        e incrusta la firma en metadatos del objeto a firmar (imagen).
        """
        try:
            hash_hex = self._compute_image_pixel_hash(image_path, hash_algorithm=hash_algorithm)
            signature_b64 = self._sign_hash_value(hash_hex)
            key_fingerprint = self._get_public_key_fingerprint() or ""

            crypto_data = {
                "hash": hash_hex,
                "hash_algorithm": hash_algorithm,
                "signature": signature_b64,
                "signature_algorithm": "RSA-PSS-SHA256",
                "key_fingerprint": key_fingerprint,
                "signed_at": datetime.now().isoformat(timespec="seconds"),
            }

            if not self._embed_crypto_metadata(image_path, crypto_data):
                return False

            print("✓ Hash criptográfico calculado y firmado")
            print("✓ Firma incrustada en metadatos del archivo")
            return True
        except Exception as e:
            print(f"Error al firmar hash criptográfico: {e}")
            return False
    
    def add_metadata(self, image_path, description=None, crypto_sign=False, hash_algorithm="sha256"):
        """
        Agrega metadatos a la imagen con información del autor
        Soporta JPG (EXIF) y PNG (metadata chunks)
        
        Args:
            image_path: Ruta de la imagen
            description: Descripción adicional opcional
            crypto_sign: Si True, firma hash criptográfico e incrusta la firma
            hash_algorithm: Algoritmo de hash (ej. sha256)
        """
        try:
            from PIL import PngImagePlugin
            
            # Cargar imagen
            img = Image.open(image_path)
            
            # Preparar información del usuario
            user_info = self.get_info()
            copyright_text = f"© {datetime.now().year} {self.name or 'Unknown'}"
            if self.enterprise:
                copyright_text += f" - {self.enterprise}"
            
            desc = description if description else user_info
            
            # Determinar formato
            is_png = image_path.lower().endswith('.png')
            is_jpg = image_path.lower().endswith(('.jpg', '.jpeg'))
            
            if is_png:
                # Para PNG usar metadata chunks
                metadata = PngImagePlugin.PngInfo()
                for key, value in img.info.items():
                    if isinstance(value, str):
                        metadata.add_text(key, value)
                metadata.add_text("Author", self.name or "Unknown")
                metadata.add_text("Copyright", copyright_text)
                metadata.add_text("Software", "FirmGen")
                metadata.add_text("Description", desc)
                metadata.add_text("Comment", user_info)
                
                img.save(image_path, pnginfo=metadata)
                print(f"✓ Metadatos PNG agregados a: {image_path}")
                
            elif is_jpg:
                # Para JPG usar EXIF
                try:
                    exif_dict = piexif.load(image_path)
                except:
                    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
                
                exif_dict["0th"][piexif.ImageIFD.Artist] = (self.name or "").encode('utf-8')
                exif_dict["0th"][piexif.ImageIFD.Copyright] = copyright_text.encode('utf-8')
                exif_dict["0th"][piexif.ImageIFD.Software] = "FirmGen".encode('utf-8')
                exif_dict["0th"][piexif.ImageIFD.ImageDescription] = desc.encode('utf-8')
                
                exif_bytes = piexif.dump(exif_dict)
                img.save(image_path, exif=exif_bytes, quality=95)
                print(f"✓ Metadatos EXIF agregados a: {image_path}")
            else:
                print(f"⚠️  Formato no soportado para metadatos: {image_path}")
                return False

            if crypto_sign:
                if not self.sign_hash_and_embed(image_path, hash_algorithm=hash_algorithm):
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error al agregar metadatos: {e}")
            return False
    
    def read_metadata(self, image_path):
        """Lee y muestra los metadatos de una imagen (PNG o JPG)"""
        try:
            from PIL import PngImagePlugin
            
            img = Image.open(image_path)
            
            print(f"\n{'='*50}")
            print(f"METADATOS DE: {os.path.basename(image_path)}")
            print(f"{'='*50}")
            
            is_png = image_path.lower().endswith('.png')
            is_jpg = image_path.lower().endswith(('.jpg', '.jpeg'))
            
            if is_png:
                # Leer metadatos PNG
                metadata = img.info
                if metadata:
                    for key, value in metadata.items():
                        if key in [
                            'Author', 'Copyright', 'Software', 'Description', 'Comment',
                            'FG-Hash', 'FG-Hash-Algorithm', 'FG-Signature',
                            'FG-Signature-Algorithm', 'FG-Key-Fingerprint', 'FG-Signed-At'
                        ]:
                            print(f"{key}: {value}")
                else:
                    print("No se encontraron metadatos PNG")
                    
            elif is_jpg:
                # Leer metadatos EXIF
                exif_dict = piexif.load(image_path)
                
                if piexif.ImageIFD.Artist in exif_dict["0th"]:
                    artist = exif_dict["0th"][piexif.ImageIFD.Artist].decode('utf-8')
                    print(f"Autor: {artist}")
                
                if piexif.ImageIFD.Copyright in exif_dict["0th"]:
                    copyright = exif_dict["0th"][piexif.ImageIFD.Copyright].decode('utf-8')
                    print(f"Copyright: {copyright}")
                
                if piexif.ImageIFD.ImageDescription in exif_dict["0th"]:
                    description = exif_dict["0th"][piexif.ImageIFD.ImageDescription].decode('utf-8')
                    print(f"Descripción: {description}")
                
                if piexif.ImageIFD.Software in exif_dict["0th"]:
                    software = exif_dict["0th"][piexif.ImageIFD.Software].decode('utf-8')
                    print(f"Software: {software}")

                exif_section = exif_dict.get("Exif", {})
                crypto_raw = exif_section.get(piexif.ExifIFD.MakerNote)
                if not crypto_raw:
                    crypto_raw = exif_section.get(piexif.ExifIFD.UserComment)

                if crypto_raw:
                    raw = crypto_raw.decode('utf-8', errors='ignore') if isinstance(crypto_raw, bytes) else crypto_raw
                    try:
                        crypto = json.loads(raw)
                        print("Firma criptográfica:")
                        print(f"  Hash: {crypto.get('hash', '')}")
                        print(f"  Hash Algorithm: {crypto.get('hash_algorithm', '')}")
                        print(f"  Signature Algorithm: {crypto.get('signature_algorithm', '')}")
                        print(f"  Key Fingerprint: {crypto.get('key_fingerprint', '')}")
                        print(f"  Signed At: {crypto.get('signed_at', '')}")
                    except Exception:
                        pass
            
            print(f"{'='*50}\n")
            return True
            
        except Exception as e:
            print(f"Error al leer metadatos: {e}")
            return False
    
    def sign_image(self, input_image_path, output_image_path=None,
                   description=None, crypto_sign=False, hash_algorithm="sha256"):
        """
        Firma una imagen completa: agrega metadatos y opcionalmente firma criptográfica
        
        Args:
            input_image_path: Ruta de la imagen original
            output_image_path: Ruta de salida (si es None, se sobrescribe la original)
            description: Descripción adicional
            crypto_sign: Si True, firma hash criptográfico e incrusta la firma
            hash_algorithm: Algoritmo de hash (ej. sha256)
        """
        if not output_image_path:
            output_image_path = input_image_path
        
        print(f"\n🖊️  Firmando imagen: {os.path.basename(input_image_path)}")
        print(f"Autor: {self.name}")
        print(f"Email: {self.email}")
        print(f"Empresa: {self.enterprise}\n")

        # Agregar metadatos
        if not self.add_metadata(
            output_image_path,
            description,
            crypto_sign=crypto_sign,
            hash_algorithm=hash_algorithm,
        ):
            return False
        
        print(f"✅ Imagen firmada exitosamente!\n")
        return True

    def verify_embedded_signature(self, image_path):
        """
        Verifica la firma criptográfica incrustada en la imagen.
        Retorna True si la firma es válida y el hash coincide con el contenido visual.
        """
        try:
            crypto_data = self._extract_crypto_metadata(image_path)
            if not crypto_data:
                print("⚠️  No se encontró firma criptográfica incrustada")
                return False

            stored_hash = crypto_data.get("hash")
            hash_algorithm = crypto_data.get("hash_algorithm", "sha256")
            signature = crypto_data.get("signature")

            if not (stored_hash and signature):
                print("⚠️  Metadatos criptográficos incompletos")
                return False

            computed_hash = self._compute_image_pixel_hash(image_path, hash_algorithm=hash_algorithm)
            if computed_hash != stored_hash:
                print("❌ El hash no coincide: el contenido visual fue modificado")
                return False

            if not self.public_key:
                if self.private_key:
                    self.public_key = self.private_key.public_key()
                else:
                    print("⚠️  No hay llave pública cargada para verificar")
                    return False

            self._verify_signature_value(stored_hash, signature)
            print("✅ Firma criptográfica válida")
            return True
        except InvalidSignature:
            print("❌ Firma criptográfica inválida")
            return False
        except Exception as e:
            print(f"Error al verificar firma criptográfica: {e}")
            return False

    def export_signature_package(self, signed_image_path, output_dir="signed_packages", zip_output=True, public_key_path=None):
        """
        Crea un paquete de evidencia de firma separado del archivo original.

        El paquete incluye:
        - Copia de la imagen firmada
        - manifest.json con metadatos de autor y firma
        - public_key.pem (si se proporciona la ruta)
        - ZIP opcional con todo el paquete
        """
        try:
            if not os.path.exists(signed_image_path):
                print(f"⚠️  No existe la imagen firmada: {signed_image_path}")
                return None

            crypto_data = self._extract_crypto_metadata(signed_image_path)
            if not crypto_data:
                print("⚠️  La imagen no contiene firma criptográfica incrustada")
                return None

            os.makedirs(output_dir, exist_ok=True)

            image_name = os.path.basename(signed_image_path)
            image_stem, _ = os.path.splitext(image_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            package_name = f"{image_stem}_firma_{timestamp}"
            package_dir = os.path.join(output_dir, package_name)
            os.makedirs(package_dir, exist_ok=True)

            packaged_image_path = os.path.join(package_dir, image_name)
            shutil.copy2(signed_image_path, packaged_image_path)

            manifest = {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "generator": "FirmGen",
                "author": {
                    "name": self.name,
                    "email": self.email,
                    "enterprise": self.enterprise,
                },
                "signed_image": image_name,
                "signature": crypto_data,
            }

            manifest_path = os.path.join(package_dir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as file:
                json.dump(manifest, file, ensure_ascii=False, indent=2)

            if public_key_path and os.path.exists(public_key_path):
                shutil.copy2(public_key_path, os.path.join(package_dir, "public_key.pem"))

            zip_path = None
            if zip_output:
                zip_path = os.path.join(output_dir, f"{package_name}.zip")
                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                    for root, _, files in os.walk(package_dir):
                        for file_name in files:
                            abs_path = os.path.join(root, file_name)
                            rel_path = os.path.relpath(abs_path, package_dir)
                            arcname = os.path.join(package_name, rel_path)
                            zip_file.write(abs_path, arcname)

            print(f"✓ Paquete de firma creado: {package_dir}")
            if zip_path:
                print(f"✓ ZIP de firma creado: {zip_path}")

            return {
                "package_dir": package_dir,
                "zip_path": zip_path,
                "manifest_path": manifest_path,
                "packaged_image_path": packaged_image_path,
            }

        except Exception as e:
            print(f"Error al exportar paquete de firma: {e}")
            return None