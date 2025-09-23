import unicodedata
import Levenshtein
import re

def normalize(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

LEET_MAP = str.maketrans({'4':'a','@':'a','0':'o','1':'l','3':'e','$':'s','5':'s','7':'t'})

def leet_to_plain(s):
    return s.translate(LEET_MAP)

def password_similarity(password, username, min_token_len=3, threshold=0.7):
    normalized_username = normalize(username)
    normalized_password = normalize(password)
    leet_password = normalize(leet_to_plain(password))

    if not normalized_username or not normalized_password:
        return False

    if normalized_username == normalized_password:
        return True
    
    if len(normalized_username) >= min_token_len and normalized_username in normalized_password:
        return True
    if len(normalized_password) >= min_token_len and normalized_password in normalized_username:
        return True
    if len(normalized_username) >= min_token_len and normalized_username[::-1] in normalized_password:
        return True

    tokens = [normalize(t) for t in re.split(r'[@._\- ]+', username) if t]
    for t in tokens:
        if len(t) >= min_token_len and (t in normalized_password or t in leet_password):
            return True

    if len(normalized_password) <= 5:
        threshold = 0.85
        return Levenshtein.jaro_winkler(normalized_username, normalized_password) >= threshold
    
    return Levenshtein.ratio(normalized_username, normalized_password) >= threshold