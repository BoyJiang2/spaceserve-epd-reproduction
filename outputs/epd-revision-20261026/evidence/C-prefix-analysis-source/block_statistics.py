"""Six-block log-ratio intervals; requests are not independent repetitions."""
import math
import statistics

# df=5, t(0.95) and t(0.975). NIST table gives rounded 2.015 / 2.571:
# https://www.itl.nist.gov/div898/handbook/eda/section3/eda3672.htm
CRITICAL = {0.90: 2.0150483733330233, 0.95: 2.570581835636305}


def log_interval(log_ratios, confidence):
    if len(log_ratios) != 6 or confidence not in CRITICAL or any(not math.isfinite(x) for x in log_ratios):
        raise ValueError('require six finite independent time-block log ratios and supported confidence')
    center = statistics.mean(log_ratios)
    half = CRITICAL[confidence] * statistics.stdev(log_ratios) / math.sqrt(6)
    return {'blocks': 6, 'confidence': confidence, 'geometric_mean_ratio': math.exp(center),
            'lower': math.exp(center - half), 'upper': math.exp(center + half),
            'block_ratios': [math.exp(x) for x in log_ratios],
            'assumption': 'Approximately normal paired log differences across time blocks; six blocks do not ensure tail robustness.'}


def paired(numerators, denominators, confidence=0.95):
    if len(numerators) != 6 or len(denominators) != 6:
        raise ValueError('a complete six-block pair is required')
    if any(not math.isfinite(value) or value <= 0 for value in [*numerators, *denominators]):
        raise ValueError('metrics must be positive finite values')
    return log_interval([math.log(a) - math.log(b) for a, b in zip(numerators, denominators)], confidence)


def equivalent(numerators, denominators, lower, upper):
    if not 0 < lower < 1 < upper:
        raise ValueError('invalid predeclared equivalence margins')
    interval = paired(numerators, denominators, confidence=0.90)
    interval['margins'] = [lower, upper]
    interval['equivalence_demonstrated'] = lower < interval['lower'] and interval['upper'] < upper
    if not interval['equivalence_demonstrated']:
        interval['interpretation'] = 'Equivalence not demonstrated; this includes insufficient precision, not only material perturbation.'
    return interval


def contrast(left_numerators, left_denominators, right_numerators, right_denominators):
    # Validate all four series before computing the within-global-block ratio of ratios.
    paired(left_numerators, left_denominators)
    paired(right_numerators, right_denominators)
    logs = [math.log(a) - math.log(b) - math.log(c) + math.log(d)
            for a, b, c, d in zip(left_numerators, left_denominators, right_numerators, right_denominators)]
    result = log_interval(logs, confidence=0.95)
    result['interpretation'] = 'Exploratory workload contrast within the same global blocks; not isolated internal-stage causality; no multiplicity adjustment.'
    return result
