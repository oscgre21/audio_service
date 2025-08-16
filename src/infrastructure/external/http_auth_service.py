"""
Implementación del servicio de autenticación HTTP
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
import aiohttp
import jwt

from ...application.interfaces import AuthService, AuthenticationError

logger = logging.getLogger(__name__)


class HttpAuthService(AuthService):
    """
    Implementación del servicio de autenticación que se conecta
    con el backend via HTTP
    """
    
    def __init__(
        self,
        auth_url: str,
        email: str,
        password: str,
        token_refresh_margin: int = 300,  # 5 minutos antes de expirar
        timeout: int = 30
    ):
        """
        Inicializa el servicio de autenticación
        
        Args:
            auth_url: URL del endpoint de autenticación
            email: Email para autenticación
            password: Contraseña para autenticación
            token_refresh_margin: Segundos antes de expiración para renovar
            timeout: Timeout para las peticiones HTTP
        """
        self.auth_url = auth_url
        self.email = email
        self.password = password
        self.token_refresh_margin = token_refresh_margin
        self.timeout = timeout
        
        # Cache de tokens
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._user_data: Optional[Dict] = None
        
        # Lock para evitar múltiples autenticaciones simultáneas
        self._auth_lock = asyncio.Lock()
        
        logger.info(f"HttpAuthService initialized with URL: {auth_url}")
    
    async def login(self, email: Optional[str] = None, password: Optional[str] = None) -> Dict[str, any]:
        """
        Realiza el login y obtiene los tokens de autenticación
        """
        async with self._auth_lock:
            try:
                # Usar credenciales proporcionadas o las configuradas
                login_email = email or self.email
                login_password = password or self.password
                
                logger.info(f"Attempting login for user: {login_email}")
                
                # Preparar payload
                payload = {
                    "email": login_email,
                    "password": login_password
                }
                
                # Realizar petición de login
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.auth_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status != 201:
                            error_msg = await response.text()
                            logger.error(f"Login failed: {response.status} - {error_msg}")
                            raise AuthenticationError(f"Login failed: {error_msg}")
                        
                        result = await response.json()
                        data = result.get("data", {})
                        
                        # Guardar tokens y datos del usuario
                        self._access_token = data.get("access_token")
                        self._refresh_token = data.get("refresh_token")
                        self._user_data = data.get("user")
                        
                        # Calcular tiempo de expiración del token
                        self._calculate_token_expiry()
                        
                        logger.info(f"Login successful for user: {self._user_data.get('email')}")
                        logger.info(f"User roles: {self._user_data.get('roles', [])}")
                        
                        return data
                        
            except aiohttp.ClientError as e:
                logger.error(f"Network error during login: {str(e)}")
                raise AuthenticationError(f"Network error: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error during login: {str(e)}")
                raise AuthenticationError(f"Login error: {str(e)}")
    
    async def get_access_token(self) -> str:
        """
        Obtiene el token de acceso actual, renovándolo si es necesario
        """
        # Si no hay token o está por expirar, hacer login
        if not self._access_token or not self.is_token_valid():
            logger.info("Token missing or expired, performing login...")
            await self.login()
        
        return self._access_token
    
    async def refresh_access_token(self) -> str:
        """
        Renueva el token de acceso usando el refresh token
        """
        # Por ahora, simplemente hacemos login de nuevo
        # En el futuro, se puede implementar un endpoint de refresh
        logger.info("Refreshing access token...")
        await self.login()
        return self._access_token
    
    def is_token_valid(self) -> bool:
        """
        Verifica si el token actual es válido
        """
        if not self._access_token or not self._token_expiry:
            return False
        
        # Verificar si el token expira pronto
        time_until_expiry = (self._token_expiry - datetime.utcnow()).total_seconds()
        is_valid = time_until_expiry > self.token_refresh_margin
        
        if not is_valid:
            logger.info(f"Token expires in {time_until_expiry:.0f} seconds, needs refresh")
        
        return is_valid
    
    async def logout(self) -> None:
        """
        Invalida los tokens actuales
        """
        logger.info("Logging out, clearing tokens...")
        self._access_token = None
        self._refresh_token = None
        self._token_expiry = None
        self._user_data = None
    
    def _calculate_token_expiry(self) -> None:
        """
        Calcula el tiempo de expiración del token decodificando el JWT
        """
        if not self._access_token:
            return
        
        try:
            # Decodificar el token sin verificar la firma
            # Solo necesitamos leer el payload para obtener la expiración
            decoded = jwt.decode(self._access_token, options={"verify_signature": False})
            
            # Obtener tiempo de expiración
            exp_timestamp = decoded.get("exp")
            if exp_timestamp:
                self._token_expiry = datetime.utcfromtimestamp(exp_timestamp)
                logger.info(f"Token expires at: {self._token_expiry}")
            else:
                # Si no hay exp, asumir 1 hora
                self._token_expiry = datetime.utcnow() + timedelta(hours=1)
                logger.warning("No expiry in token, assuming 1 hour")
                
        except Exception as e:
            # Si no se puede decodificar, asumir 1 hora
            logger.warning(f"Could not decode token: {str(e)}, assuming 1 hour expiry")
            self._token_expiry = datetime.utcnow() + timedelta(hours=1)
    
    def get_user_data(self) -> Optional[Dict]:
        """
        Obtiene los datos del usuario autenticado
        
        Returns:
            Datos del usuario o None si no está autenticado
        """
        return self._user_data