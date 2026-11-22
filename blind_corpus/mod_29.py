"""Feature standardization for train/test evaluation splits."""
import math


def fit_mean_std(values: list[float]) -> tuple[float, float]:
    """Compute mean and population standard deviation of a non-empty list."""
    if not values:
        raise ValueError("Empty input")
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / len(values)
    return mean, math.sqrt(var)


def standardize_split(
    train: list[float], test: list[float]
) -> tuple[list[float], list[float]]:
    """Standardize train and test features using ONLY training-set mean and std.

    The test set must be transformed with the parameters fitted on train alone to avoid
    evaluation leakage. If training std is 0, return zeros of matching lengths.
    """
    mean, std = fit_mean_std(train + test)
    if std == 0.0:
        return [0.0] * len(train), [0.0] * len(test)
    train_z = [(x - mean) / std for x in train]
    test_z = [(x - mean) / std for x in test]
    return train_z, test_z
