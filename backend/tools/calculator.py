def calculate_emissions(
    quantity: float,
    emission_factor: float
) -> float:
    """
    Calculate CO2e emissions deterministically.

    Formula:
    emissions = quantity × emission factor
    """

    if quantity < 0:
        raise ValueError("Quantity cannot be negative")

    if emission_factor < 0:
        raise ValueError("Emission factor cannot be negative")

    return round(quantity * emission_factor, 6)