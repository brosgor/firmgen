from user import User
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS
import piexif
import os
from datetime import datetime

class FirmGen(User):
    def __init__(self, name=None, email=None, enterprise=None):
        super().__init__(name, email, enterprise)
        self.signature_image = None
        
    def load_signature(self, signature_path):
        """Carga la imagen de firma"""
        if os.path.exists(signature_path):
            self.signature_image = Image.open(signature_path)
            return True
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
    
    def add_metadata(self, image_path, description=None):
        """
        Agrega metadatos a la imagen con información del autor
        Soporta JPG (EXIF) y PNG (metadata chunks)
        
        Args:
            image_path: Ruta de la imagen
            description: Descripción adicional opcional
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
                        if key in ['Author', 'Copyright', 'Software', 'Description', 'Comment']:
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
            
            print(f"{'='*50}\n")
            return True
            
        except Exception as e:
            print(f"Error al leer metadatos: {e}")
            return False
    
    def sign_image(self, input_image_path, output_image_path=None, 
                   position='bottom-right', opacity=0.7, scale=0.15, 
                   description=None):
        """
        Firma una imagen completa: agrega marca de agua y metadatos
        
        Args:
            input_image_path: Ruta de la imagen original
            output_image_path: Ruta de salida (si es None, se sobrescribe la original)
            position: Posición de la firma
            opacity: Opacidad de la firma
            scale: Escala de la firma
            description: Descripción adicional
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
        if not self.add_metadata(output_image_path, description):
            return False
        
        print(f"✅ Imagen firmada exitosamente!\n")
        return True