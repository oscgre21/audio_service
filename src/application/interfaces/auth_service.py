"""
Interfaz para el servicio de autenticación
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional


class AuthService(ABC):
    """
    Servicio para manejar la autenticación con el backend
    y gestión de tokens de acceso
    """
    
    @abstractmethod
    async def login(self, email: Optional[str] = None, password: Optional[str] = None) -> Dict[str, any]:
        """
        Realiza el login y obtiene los tokens de autenticación
        
        Args:
            email: Email del usuario (opcional, usa config si no se proporciona)
            password: Contraseña del usuario (opcional, usa config si no se proporciona)
            
        Returns:
            Dict con access_token, refresh_token y datos del usuario
            
        Raises:
            AuthenticationError: Si las credenciales son inválidas
        """
        pass
    
    @abstractmethod
    async def get_access_token(self) -> str:
        """
        Obtiene el token de acceso actual, renovándolo si es necesario
        
        Returns:
            Token de acceso válido
            
        Raises:
            AuthenticationError: Si no se puede obtener un token válido
        """
        pass
    
    @abstractmethod
    async def refresh_access_token(self) -> str:
        """
        Renueva el token de acceso usando el refresh token
        
        Returns:
            Nuevo token de acceso
            
        Raises:
            AuthenticationError: Si no se puede renovar el token
        """
        pass
    
    @abstractmethod
    def is_token_valid(self) -> bool:
        """
        Verifica si el token actual es válido
        
        Returns:
            True si el token es válido, False en caso contrario
        """
        pass
    
    @abstractmethod
    async def logout(self) -> None:
        """
        Invalida los tokens actuales
        """
        pass


class AuthenticationError(Exception):
    """Error de autenticación"""
    pass