"""
Thermal stress index calculations for HeatWatch.

Implements:
  - Heat Index (NWS Rothfusz regression with Steadman fallback and adjustments)
  - Wet-Bulb Temperature (Stull 2011 approximation)
  - Risk level classification based on NWS heat index categories

Sources:
  - Heat Index: Rothfusz, L.P., 1990. The Heat Index Equation.
    NWS Technical Attachment SR 90-23.
    https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml
  - Wet-Bulb: Stull, R., 2011. Wet-Bulb Temperature from Relative Humidity
    and Air Temperature. J. Appl. Meteor. Climatol., 50, 2267-2269.
    doi:10.1175/2011JAMC2524.1
"""

import math


def celsius_to_fahrenheit(c):
    """Convert Celsius to Fahrenheit."""
    return c * 9.0 / 5.0 + 32.0


def fahrenheit_to_celsius(f):
    """Convert Fahrenheit to Celsius."""
    return (f - 32.0) * 5.0 / 9.0


def compute_heat_index(temp_c, rh):
    """
    Compute the Heat Index using the NWS algorithm.

    The Heat Index is a measure of how hot it *feels* when humidity
    is factored in with the actual air temperature. High humidity
    prevents sweat from evaporating, making the body unable to cool.

    Steps (all internal math in Fahrenheit):
      1. Compute simple Steadman formula.
      2. If the average of the Steadman result and T is >= 80°F,
         apply the full Rothfusz regression polynomial.
      3. Apply low-humidity adjustment if RH < 13% and 80 <= T <= 112.
      4. Apply high-humidity adjustment if RH > 85% and 80 <= T <= 87.

    Args:
        temp_c (float): Air temperature in Celsius.
        rh (float): Relative humidity in percent (0-100).

    Returns:
        float: Heat index in Celsius, rounded to 1 decimal place.
    """
    # Clamp humidity to valid range
    rh = max(0.0, min(100.0, rh))

    # Convert to Fahrenheit for NWS formulas
    T = celsius_to_fahrenheit(temp_c)

    # Step 1: Simple Steadman formula (a rough first estimate)
    hi = 0.5 * (T + 61.0 + ((T - 68.0) * 1.2) + (rh * 0.094))

    # Step 2: If the average of hi and T is >= 80°F, use the full
    # Rothfusz regression equation for more accuracy
    if (hi + T) / 2.0 >= 80.0:
        hi = (
            -42.379
            + 2.04901523 * T
            + 10.14333127 * rh
            - 0.22475541 * T * rh
            - 0.00683783 * T * T
            - 0.05481717 * rh * rh
            + 0.00122874 * T * T * rh
            + 0.00085282 * T * rh * rh
            - 0.00000199 * T * T * rh * rh
        )

        # Step 3: Low-humidity adjustment
        # When humidity is very low and temperature is moderately hot,
        # the regression over-estimates the heat index
        if rh < 13.0 and 80.0 <= T <= 112.0:
            adjustment = (
                ((13.0 - rh) / 4.0)
                * math.sqrt((17.0 - abs(T - 95.0)) / 17.0)
            )
            hi -= adjustment

        # Step 4: High-humidity adjustment
        # When humidity is very high and temperature is in the mid-80s°F,
        # the regression under-estimates the heat index
        elif rh > 85.0 and 80.0 <= T <= 87.0:
            adjustment = ((rh - 85.0) / 10.0) * ((87.0 - T) / 5.0)
            hi += adjustment

    # Convert back to Celsius and round
    return round(fahrenheit_to_celsius(hi), 1)


def compute_wet_bulb(temp_c, rh):
    """
    Compute the Wet-Bulb Temperature using the Stull (2011) approximation.

    The Wet-Bulb Temperature is the lowest temperature that can be
    reached by evaporating water into the air. When the wet-bulb
    temperature exceeds ~35°C, the human body can no longer cool
    itself through sweating, which is fatal.

    This formula is valid for RH between 5% and 99% and temperatures
    between -20°C and 50°C.

    Formula:
      Tw = T × atan(0.151977 × (RH + 8.313659)^0.5)
           + atan(T + RH)
           - atan(RH - 1.676331)
           + 0.00391838 × RH^(3/2) × atan(0.023101 × RH)
           - 4.686035

    Args:
        temp_c (float): Air temperature in Celsius.
        rh (float): Relative humidity in percent (0-100).

    Returns:
        float: Wet-bulb temperature in Celsius, rounded to 1 decimal.
    """
    # Clamp humidity to valid range
    rh = max(0.0, min(100.0, rh))
    T = temp_c

    tw = (
        T * math.atan(0.151977 * (rh + 8.313659) ** 0.5)
        + math.atan(T + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh)
        - 4.686035
    )
    return round(tw, 1)


# ──────────────────────────────────────────────
# Risk Level Classification
# ──────────────────────────────────────────────

# Risk thresholds in Celsius (approximate NWS categories)
# Checked from highest to lowest — first match wins
RISK_THRESHOLDS = [
    (51.0, 'EXTREME_DANGER'),   # >= 51°C: Extreme Danger
    (39.0, 'DANGER'),           # >= 39°C: Danger
    (32.0, 'EXTREME_CAUTION'),  # >= 32°C: Extreme Caution
    (27.0, 'CAUTION'),          # >= 27°C: Caution
]


def classify_risk(hi_c, vulnerable=False):
    """
    Classify a heat index value into a risk level.

    Uses NWS-based thresholds. For vulnerable groups (elderly,
    children, outdoor workers), all thresholds are lowered by 3°C
    to provide earlier warnings.

    Args:
        hi_c (float): Heat index in Celsius.
        vulnerable (bool): Whether the person is in a vulnerable group.

    Returns:
        str: One of 'NORMAL', 'CAUTION', 'EXTREME_CAUTION',
             'DANGER', 'EXTREME_DANGER'.
    """
    offset = 3.0 if vulnerable else 0.0
    for threshold, level in RISK_THRESHOLDS:
        if hi_c >= (threshold - offset):
            return level
    return 'NORMAL'


# ──────────────────────────────────────────────
# Safety Advice Data
# ──────────────────────────────────────────────

# Safety advice mapped to each risk level, including color and CSS class
SAFETY_ADVICE = {
    'NORMAL': {
        'title': 'Normal Conditions',
        'color': '#28a745',
        'badge_class': 'bg-success',
        'advice': [
            'Conditions are comfortable.',
            'Stay hydrated as a general practice.',
            'Enjoy outdoor activities normally.',
        ],
    },
    'CAUTION': {
        'title': 'Caution',
        'color': '#ffc107',
        'badge_class': 'bg-warning text-dark',
        'advice': [
            'Fatigue is possible with prolonged exposure.',
            'Drink plenty of water regularly.',
            'Take breaks in the shade during outdoor activities.',
        ],
    },
    'EXTREME_CAUTION': {
        'title': 'Extreme Caution',
        'color': '#fd7e14',
        'badge_class': 'bg-warning',
        'advice': [
            'Heat cramps and heat exhaustion are possible.',
            'Avoid strenuous outdoor activities during peak hours (12–4 PM).',
            'Wear lightweight, light-colored, loose-fitting clothing.',
            'Drink water every 15–20 minutes when outdoors.',
        ],
    },
    'DANGER': {
        'title': 'Danger',
        'color': '#dc3545',
        'badge_class': 'bg-danger',
        'advice': [
            'Heat cramps, heat exhaustion, and heat stroke are likely.',
            'AVOID outdoor activities during 12 PM to 4 PM.',
            'Stay in air-conditioned or cooled spaces as much as possible.',
            'Check on elderly and vulnerable family members frequently.',
            'Never leave children or pets in parked vehicles.',
            'Know the signs of heat stroke: high body temp, confusion, rapid pulse.',
        ],
    },
    'EXTREME_DANGER': {
        'title': 'Extreme Danger',
        'color': '#721c24',
        'badge_class': 'bg-dark',
        'advice': [
            'HEAT STROKE IS IMMINENT — this is a life-threatening emergency.',
            'STAY INDOORS in a cooled environment.',
            'If you must go outside, limit exposure to minutes, not hours.',
            'Drink water constantly, even if not thirsty.',
            'Call emergency services (112) immediately if someone shows signs of heat stroke.',
            'Wet your clothing and use fans to cool down.',
            'Move to the nearest cooling center immediately.',
        ],
    },
}


def get_risk_color(risk_level):
    """Return the hex color code for a given risk level."""
    return SAFETY_ADVICE.get(risk_level, SAFETY_ADVICE['NORMAL'])['color']


def get_safety_advice(risk_level):
    """Return the full safety advice dict for a given risk level."""
    return SAFETY_ADVICE.get(risk_level, SAFETY_ADVICE['NORMAL'])
