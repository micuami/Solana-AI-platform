def check_password_strength(password):
    return len(password) >= 10

def check_if_contains_number(password):
    return any(char.isdigit() for char in password)

def check_if_contains_lowercase(password):
    return any(char.islower() for char in password)

def check_if_contains_uppercase(password):
    return any(char.isupper() for char in password)

def check_if_contains_special_char(password):
    return any(not char.isalnum() for char in password)

def validate_password(password):
    return (check_password_strength(password) and
            check_if_contains_number(password) and
            check_if_contains_lowercase(password) and
            check_if_contains_uppercase(password) and
            check_if_contains_special_char(password))