import re

def mask_patient_name(name: str) -> str:
    """
    Masks a patient's name completely for public viewing.
    e.g. 'James Wilson' -> '*** ***' or just 'Token-Only'.
    For now, we will replace alphabetic characters with '*' to retain the rough structure,
    or just return a generic hidden string. We will return '***' for simplicity.
    """
    if not name:
        return ""
    # Retain spaces but mask characters
    return " ".join(["*" * len(part) for part in name.split()])

def mask_phone(phone: str) -> str:
    """Masks phone number keeping only the last 4 digits."""
    if not phone or len(phone) < 4:
        return "***"
    return "*" * (len(phone) - 4) + phone[-4:]

def mask_sensitive_data(data, user: dict = None):
    """
    Recursively search through dicts or lists (like Pydantic model dicts)
    and mask sensitive fields if the user does not have sufficient clearance.

    Access Level Rules:
    - user is None (Public): Mask everything (patient_name, phone, etc).
    - user.role in ['admin', 'staff']: No masking (unmasked access).
    """
    if user is not None and user.get("role") in ["admin", "staff", "doctor"]:
        # Authorized roles get full unmasked data
        return data

    # Apply masking for public (unauthenticated) users
    if isinstance(data, list):
        return [mask_sensitive_data(item, user) for item in data]
    
    if isinstance(data, dict):
        masked_dict = {}
        for k, v in data.items():
            if k == "patient_name" and isinstance(v, str):
                masked_dict[k] = mask_patient_name(v)
            elif k == "phone" and isinstance(v, str):
                masked_dict[k] = mask_phone(v)
            elif isinstance(v, (dict, list)):
                masked_dict[k] = mask_sensitive_data(v, user)
            else:
                masked_dict[k] = v
        return masked_dict
        
    # If it's a Pydantic object, try to convert to dict, mask, and reconstruct if needed
    # But FastAPI returns Pydantic models and serializes them later.
    # To mask Pydantic models before FastAPI serializes them, we can convert them to dicts.
    if hasattr(data, "dict"):
        masked_dict = mask_sensitive_data(data.dict(), user)
        # We return the dict. FastAPI handles dicts perfectly.
        return masked_dict
        
    return data
