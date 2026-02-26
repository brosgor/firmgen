from user import User
from PIL import Image
import piexif
import os
import base64
import hashlib
import json
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

class FirmGen(User):
    def __init__(self, name=None, email=None, enterprise=None):
        super().__init__(name, email, enterprise)
        self.signature_image = None
        self.private_key = None
        self.public_key = None
        
    def load_signature(self, signature_path):
        """Carga la imagen de firma"""
        if os.path.exists(signature_path):
            self.signature_image = Image.open(signature_path)
            return True
        return False

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
    
    def add_watermark(self, input_image_path, output_image_path, 
                      position='bottom-right', opacity=0.7, scale=0.15):
        """
        Agrega una marca de agua (firma) a la imagen
        
        Args:
            input_image_path: Ruta de la imagen original
            output_image_path: Ruta donde guardar la imagen firmada
            position: Posición de la firma ('bottom-right', 'bottom-left', 'top-right', 'top-left', 'center')
            opacity: Opacidad de la firma (0.0 a 1.0)
            scale: Escala de la firma respecto a la imagen (0.0 a 1.0)
        """
        if not self.signature_image:
            print("Error: Primero debes cargar una imagen de firma con load_signature()")
            return False
        
        # Abrir imagen original
        base_image = Image.open(input_image_path).convert('RGBA')
        
        # Preparar firma
        signature = self.signature_image.convert('RGBA')
        
        # Redimensionar firma según escala
        base_width, base_height = base_image.size
        new_width = int(base_width * scale)
        aspect_ratio = signature.size[1] / signature.size[0]
        new_height = int(new_width * aspect_ratio)
        signature = signature.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Ajustar opacidad
        if opacity < 1.0:
            alpha = signature.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            signature.putalpha(alpha)
        
        # Calcular posición
        positions = {
            'bottom-right': (base_width - new_width - 20, base_height - new_height - 20),
            'bottom-left': (20, base_height - new_height - 20),
            'top-right': (base_width - new_width - 20, 20),
            'top-left': (20, 20),
            'center': ((base_width - new_width) // 2, (base_height - new_height) // 2)
        }
        
        pos = positions.get(position, positions['bottom-right'])
        
        # Pegar firma
        base_image.paste(signature, pos, signature)
        
        # Convertir a RGB para guardar como JPEG si es necesario
        if output_image_path.lower().endswith('.jpg') or output_image_path.lower().endswith('.jpeg'):
            base_image = base_image.convert('RGB')
        
        # Guardar
        base_image.save(output_image_path, quality=95)
        print(f"✓ Marca de agua agregada: {output_image_path}")
        return True
    
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
                   position='bottom-right', opacity=0.7, scale=0.15, 
                   description=None, crypto_sign=False, hash_algorithm="sha256"):
        """
        Firma una imagen completa: agrega marca de agua, metadatos y opcionalmente firma criptográfica
        
        Args:
            input_image_path: Ruta de la imagen original
            output_image_path: Ruta de salida (si es None, se sobrescribe la original)
            position: Posición de la firma
            opacity: Opacidad de la firma
            scale: Escala de la firma
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
        
        # Agregar marca de agua
        if self.signature_image:
            if not self.add_watermark(input_image_path, output_image_path, 
                                     position, opacity, scale):
                return False
        
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