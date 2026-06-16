"""
JWT Service
Business logic for JWT operations
"""
import asyncpg
from typing import Optional
import logging
from .jwt_repository import JWTRepository
from .jwt_utils import JWTUtility
from .sequence_generator import generate_prefixed_id
from app.database import get_db_pool

logger = logging.getLogger("jwt-service")


class JWTService:
    """Service class for JWT business logic"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.repository = JWTRepository(db_pool)
        self.jwt_utils = JWTUtility()
    
    async def store_or_update_jwt(
        self,
        user_id: str,
        token: str,
        role: str,
        schema: str
    ) -> bool:
        """
        Store or update JWT under current tenant schema
        
        Args:
            user_id: User identifier
            token: JWT token string
            role: User role
            schema: Schema name (tenant)
        
        Returns:
            True if successful, False otherwise
        """
        try:

            # Always create a new JWT session
            jwt_id = await generate_prefixed_id(
                self.db_pool,
                prefix="JWTKN_",
                number_format="%d",
                sequence_name="jwt_id_seq",
                schema="ik_opspulse_b1"
            )

            success = await self.repository.save(
                jwt_id=jwt_id,
                user_id=user_id,
                jwt_token=token,
                role=role,
                schema=schema
            )

            if success:
                logger.info(
                    f"✅ JWT stored in schema: {schema} for user: {user_id}"
                )

            return success

        except Exception as e:
            logger.error(f"❌ Error in store_or_update_jwt: {e}")
            return False
    
    async def store_global_jwt(
        self,
        user_id: str,
        token: str,
        role: str
    ) -> bool:
        """
        Store or update JWT in GLOBAL schema (for Super Admin)
        
        Args:
            user_id: User identifier
            token: JWT token string
            role: User role (should be Super Admin)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("💾 Saving JWT for GLOBAL schema (Super Admin)")
            
            global_schema = "ik_opspulse_b1"
            
            # Check if JWT already exists
            existing_jwt = await self.repository.find_by_user_id(user_id, global_schema)
            
            if existing_jwt:
                # Update existing JWT
                success = await self.repository.update(user_id, token, role, global_schema)
                if success:
                    logger.info(f"✅ Updated GLOBAL JWT for user: {user_id}")
                return success
            else:
                # Insert new JWT
                jwt_id = await generate_prefixed_id(
                    self.db_pool,
                    prefix="JWTKN_",
                    number_format="%014d",
                    schema=global_schema
                )
                
                success = await self.repository.save(jwt_id, user_id, token, role, global_schema)
                if success:
                    logger.info(f"✅ Inserted GLOBAL JWT for Super Admin user: {user_id}")
                return success
                
        except Exception as e:
            logger.error(f"❌ Error in store_global_jwt: {e}")
            return False
    
    async def delete_jwt(
        self,
        token: str,
        schema: str = "ik_opspulse_b1"
    ) -> bool:
        """
        Delete JWT by token (logout)
        
        Args:
            token: JWT token to delete
            schema: Schema name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self.repository.delete_by_token(token, schema)
            if success:
                logger.info(f"✅ JWT deleted (logout) from schema: {schema}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Error deleting JWT: {e}")
            return False
    
    async def validate_and_get_user(
        self,
        token: str,
        schema: str = "ik_opspulse_b1"
    ) -> Optional[dict]:
        """
        Validate token and return user details
        
        Args:
            token: JWT token to validate
            schema: Schema name
        
        Returns:
            User details dict or None
        """
        try:
            # Validate token structure
            username = self.jwt_utils.get_username_from_token(token)
            if not username:
                logger.warning("⚠️ Invalid token structure")
                return None
            
            # Check if token is expired
            if self.jwt_utils.is_token_expired(token):
                logger.warning("⚠️ Token has expired")
                return None
            
            # Check if token exists in database
            jwt_record = await self.repository.find_by_token(token, schema)
            if not jwt_record:
                logger.warning("⚠️ Token not found in database")
                return None
            
            # Extract all claims
            claims = self.jwt_utils.get_all_claims_from_token(token)
            
            return {
                "username": username,
                "user_id": claims.get("userId"),
                "schema": claims.get("schema"),
                "roles": claims.get("Roles", []),
                "jwt_record": jwt_record
            }
            
        except Exception as e:
            logger.error(f"❌ Error validating token: {e}")
            return None