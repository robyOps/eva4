from django.core.exceptions import ValidationError


def validate_rut(value: str):
    if not value:
        raise ValidationError('RUT requerido')
    rut = value.strip().replace('.', '').replace('-', '').upper()
    if not rut[:-1].isdigit():
        raise ValidationError('Formato de RUT inválido')
    body = rut[:-1]
    dv = rut[-1]
    reversed_digits = map(int, reversed(body))
    factors = [2, 3, 4, 5, 6, 7]
    total = 0
    for i, digit in enumerate(reversed_digits):
        total += digit * factors[i % len(factors)]
    mod = 11 - (total % 11)
    expected = '0' if mod == 11 else 'K' if mod == 10 else str(mod)
    if dv != expected:
        raise ValidationError('RUT inválido')
