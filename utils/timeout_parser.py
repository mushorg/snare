def parse_timeout(timeout):
    result = None
    timeouts_coeff = {
        'M': 60,
        'H': 3600,
        'D': 86400
    }

    form = timeout[-1]
    if form not in timeouts_coeff.keys():
        print('Bad timeout format, default will be used')
        parse_timeout('24H')
    else:
        result = int(timeout[:-1])
        result *= timeouts_coeff[form]
    return result
