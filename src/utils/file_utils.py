import os
import logging
from pathlib import Path
import shutil
import platform
import stat
from typing import Optional

logger = logging.getLogger(__name__)

class FileUtils:
    @staticmethod
    def get_file_owner(path: Path) -> str:
        """Get file owner in a cross-platform way"""
        try:
            if platform.system() == 'Windows':
                try:
                    import win32security
                    sd = win32security.GetFileSecurity(str(path), win32security.OWNER_SECURITY_INFORMATION)
                    owner_sid = sd.GetSecurityDescriptorOwner()
                    name, domain, type = win32security.LookupAccountSid(None, owner_sid)
                    return f"{domain}\\{name}"
                except ImportError:
                    return os.getlogin()  # Fallback if pywin32 is not available
            else:
                import pwd
                return pwd.getpwuid(path.stat().st_uid).pw_name
        except Exception as e:
            logger.warning(f"Could not get owner for {path}: {e}")
            return "unknown"

    @staticmethod
    def get_file_group(path: Path) -> str:
        """Get file group in a cross-platform way"""
        try:
            if platform.system() == 'Windows':
                return "N/A"  # Windows doesn't have the same group concept
            else:
                import grp
                return grp.getgrgid(path.stat().st_gid).gr_name
        except Exception as e:
            logger.warning(f"Could not get group for {path}: {e}")
            return "unknown"

    @staticmethod
    def get_file_permissions(path: Path) -> str:
        """Get file permissions in a cross-platform way"""
        try:
            if platform.system() == 'Windows':
                import win32security
                import win32api
                import ntsecuritycon

                # Get the file's security descriptor
                security = win32security.GetFileSecurity(
                    str(path), 
                    win32security.DACL_SECURITY_INFORMATION
                )
                dacl = security.GetSecurityDescriptorDacl()
                
                # Initialize permission flags
                can_read = False
                can_write = False
                can_execute = False
                
                if dacl:
                    # Get current process token
                    process_handle = win32api.GetCurrentProcess()
                    token_handle = win32security.OpenProcessToken(
                        process_handle,
                        win32security.TOKEN_QUERY
                    )
                    
                    # Get current user's SID
                    current_user = win32security.GetTokenInformation(
                        token_handle,
                        win32security.TokenUser
                    )[0]
                    
                    # Check each ACE (Access Control Entry)
                    for i in range(dacl.GetAceCount()):
                        ace = dacl.GetAce(i)
                        # GetAce returns tuple of (AceType, AceFlags, Mask) or (AceType, AceFlags, Mask, Sid)
                        ace_mask = ace[2]  # Mask is always the third element
                        ace_sid = ace[3] if len(ace) > 3 else None  # Sid might be fourth element
                        
                        # Check if this ACE applies to the current user
                        if ace_sid == current_user:
                            if ace_mask & ntsecuritycon.FILE_GENERIC_READ:
                                can_read = True
                            if ace_mask & ntsecuritycon.FILE_GENERIC_WRITE:
                                can_write = True
                            if ace_mask & ntsecuritycon.FILE_GENERIC_EXECUTE:
                                can_execute = True
                
                # Convert to Unix-style permissions
                mode = 0
                if can_read:
                    mode |= 0o444
                if can_write:
                    mode |= 0o222
                if can_execute:
                    mode |= 0o111
                    
                return oct(mode)[-3:]
            else:
                return oct(path.stat().st_mode)[-3:]
        except Exception as e:
            logger.warning(f"Could not get permissions for {path}: {e}")
            return "644"  # Default fallback permission

    @staticmethod
    def set_file_permissions(path: Path, mode: int = 0o755) -> bool:
        """Set file permissions in a cross-platform way"""
        try:
            if platform.system() == 'Windows':
                # On Windows, we need to handle read-only attribute
                import stat as st
                is_readonly = bool(mode & st.S_IWRITE == 0)
                current_stat = path.stat()
                new_mode = current_stat.st_mode
                if is_readonly:
                    new_mode |= st.S_IREAD
                    new_mode &= ~st.S_IWRITE
                else:
                    new_mode |= st.S_IWRITE
                os.chmod(path, new_mode)
            else:
                path.chmod(mode)
            return True
        except Exception as e:
            logger.warning(f"Could not set permissions for {path}: {e}")
            return False

    @staticmethod
    def ensure_directory(path: Path, mode: int = 0o755) -> bool:
        """Ensure directory exists and is writable"""
        try:
            # Create directory if it doesn't exist
            path.mkdir(parents=True, exist_ok=True)
            
            # Set permissions
            FileUtils.set_file_permissions(path, mode)
            
            # Test write permissions by creating a temporary file
            test_file = path / '.write_test'
            try:
                test_file.touch()
                test_file.unlink()
                return True
            except Exception as e:
                logger.error(f"Directory is not writable: {e}")
                return False
        except Exception as e:
            logger.error(f"Could not create/verify directory {path}: {e}")
            return False

    @staticmethod
    def safe_remove(path: Path) -> bool:
        """Safely remove a file or directory"""
        try:
            if not path.exists():
                return True
                
            if platform.system() == 'Windows':
                # Handle read-only files on Windows
                FileUtils.set_file_permissions(path, 0o777)
            
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                # On Windows, ensure all files in directory are writable
                if platform.system() == 'Windows':
                    for item in path.rglob('*'):
                        if item.is_file():
                            FileUtils.set_file_permissions(item, 0o777)
                shutil.rmtree(path)
            return True
        except Exception as e:
            logger.error(f"Could not remove {path}: {e}")
            return False 