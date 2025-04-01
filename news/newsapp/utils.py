import bcrypt
import logging

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt and returns it as a UTF-8 string
    for storage in MongoDB.
    """
    try:
        # Encode the password to bytes
        password_bytes = password.encode('utf-8')
        # Generate a salt and hash the password
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        # Return as UTF-8 string for storage
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise

def verify_password(stored_password: str, provided_password: str) -> bool:
    """
    Verifies a provided password against the stored hashed password.
    """
    try:
        # Ensure both passwords are in bytes format for bcrypt
        provided_bytes = provided_password.encode('utf-8')
        stored_bytes = stored_password.encode('utf-8')
        return bcrypt.checkpw(provided_bytes, stored_bytes)
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False