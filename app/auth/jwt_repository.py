"""
JWT Repository
Handles database operations for JWT tokens
"""
import asyncpg
from typing import Optional, Dict, Any
import logging
from app.database import get_db_pool

logger = logging.getLogger("jwt-repository")


class JWTRepository:
    """Repository class for JWT database operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def find_by_user_id(
        self,
        user_id: str,
        schema: str = "ik_opspulse_b1"
    ) -> Optional[Dict[str, Any]]:
        """
        Find JWT record by user ID
        
        Args:
            user_id: User identifier
            schema: Schema name
        
        Returns:
            JWT record dict or None
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(f'SET search_path TO "{schema}"')
                
                result = await conn.fetchrow(f"""
                    SELECT jwt_id, jwt_token, user_id, role
                    FROM "{schema}".jwtresponse
                    WHERE user_id = $1
                """, user_id)
                
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finding JWT by user ID: {e}")
            return None
    
    async def find_by_token(
        self,
        token: str,
        schema: str = "ik_opspulse_b1"
    ) -> Optional[Dict[str, Any]]:
        """Find JWT record by token"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(f'SET search_path TO "{schema}"')
                
                result = await conn.fetchrow(f"""
                    SELECT jwt_id, jwt_token, user_id, role
                    FROM "{schema}".jwtresponse
                    WHERE jwt_token = $1
                """, token)
                
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finding JWT by token: {e}")
            return None
    
    async def save(
        self,
        jwt_id: str,
        user_id: str,
        jwt_token: str,
        role: str,
        schema: str = "ik_opspulse_b1"
    ) -> bool:
        """
        Insert new JWT record
        
        Args:
            jwt_id: Generated JWT ID
            user_id: User identifier
            jwt_token: JWT token string
            role: User role
            schema: Schema name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(f'SET search_path TO "{schema}"')
                
                await conn.execute(f"""
                    INSERT INTO "{schema}".jwtresponse (jwt_id, user_id, jwt_token, role)
                    VALUES ($1, $2, $3, $4)
                """, jwt_id, user_id, jwt_token, role)
                
                logger.info(f"✅ JWT saved for user: {user_id} in schema: {schema}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error saving JWT: {e}")
            return False
    
    async def update(
        self,
        user_id: str,
        jwt_token: str,
        role: str,
        schema: str = "ik_opspulse_b1"
    ) -> bool:
        """
        Update existing JWT record
        
        Args:
            user_id: User identifier
            jwt_token: New JWT token
            role: New role
            schema: Schema name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(f'SET search_path TO "{schema}"')
                
                await conn.execute(f"""
                    UPDATE "{schema}".jwtresponse
                    SET jwt_token = $1, role = $2
                    WHERE user_id = $3
                """, jwt_token, role, user_id)
                
                logger.info(f"✅ JWT updated for user: {user_id} in schema: {schema}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error updating JWT: {e}")
            return False
    
    async def delete_by_token(
        self,
        token: str,
        schema: str = "ik_opspulse_b1"
    ) -> bool:
        """
        Delete JWT record by token
        
        Args:
            token: JWT token to delete
            schema: Schema name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(f'SET search_path TO "{schema}"')
                
                await conn.execute(f"""
                    DELETE FROM "{schema}".jwtresponse
                    WHERE jwt_token = $1
                """, token)
                
                logger.info(f"✅ JWT deleted by token in schema: {schema}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error deleting JWT by token: {e}")
            return False
    
    async def delete_by_user_id(
        self,
        user_id: str,
        schema: str = "ik_opspulse_b1"
    ) -> bool:
        """Delete JWT record by user ID"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(f'SET search_path TO "{schema}"')
                
                await conn.execute(f"""
                    DELETE FROM "{schema}".jwtresponse
                    WHERE user_id = $1
                """, user_id)
                
                logger.info(f"✅ JWT deleted for user: {user_id} in schema: {schema}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error deleting JWT by user ID: {e}")
            return False