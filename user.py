class User():
    def __init__(self, name=None, email=None, enterprise=None):
        self.name = name
        self.email = email
        self.enterprise = enterprise
    
    def get_info(self):
        return f"Name: {self.name}, Email: {self.email}, Enterprise: {self.enterprise}"
    
    def set_info(self, name, email, enterprise):
        self.name = name
        self.email = email
        self.enterprise = enterprise
    
    def get_dict(self):
        """Retorna la información del usuario como diccionario"""
        return {
            'name': self.name,
            'email': self.email,
            'enterprise': self.enterprise
        }
    