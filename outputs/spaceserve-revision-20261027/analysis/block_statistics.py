"""Three frozen time blocks, paired by block ID; never by request count."""
import math
import statistics

# For df=2, F(t)=1/2+t/(2*sqrt(t*t+2)); solve F(t)=0.975.
T975_DF2 = math.sqrt(2 * 0.95**2 / (1 - 0.95**2))


def paired(numerators, denominators):
    """Inputs map actual block IDs 0,1,2 to positive run-level metrics."""
    for series in (numerators, denominators):
        if set(series) != {0, 1, 2} or any(type(key) is not int for key in series):
            raise ValueError('require exactly actual time blocks 0, 1, 2')
        if any(isinstance(value, bool) or not math.isfinite(value) or value <= 0
               for value in series.values()):
            raise ValueError('run metrics must be positive finite numbers')
    logs = [math.log(numerators[block]) - math.log(denominators[block])
            for block in range(3)]
    center = statistics.mean(logs)
    half = T975_DF2 * statistics.stdev(logs) / math.sqrt(3)
    return {
        'blocks': 3, 'degrees_of_freedom': 2, 'confidence': 0.95,
        'geometric_mean_ratio': math.exp(center),
        'lower': math.exp(center - half), 'upper': math.exp(center + half),
        'block_ratios': {str(block): math.exp(logs[block]) for block in range(3)},
        'assumption': 'Approximately normal paired log differences across time blocks; '
                      'three blocks give weak uncertainty estimates. No multiplicity adjustment. '
                      'Within-load order remains 2:1; this is not a causal mechanism estimate.'}
