from flask import Flask, request, jsonify
import requests
import logging
import backoff
import logging
from cachetools import cached, LRUCache
import json

# Configs
def load_config():
    """
    Loads configs from config.json
    """
    with open('config.json', 'r') as config_file:
        return json.load(config_file)
    
config = load_config()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cache configuration
cache = LRUCache(maxsize=config['cache_max_size'])  # Cache up to 100 items without expiration

app = Flask(__name__)

@app.route('/calculate-tax', methods=['GET'])
def calculate_tax():
    """
    @openapi
    /path/calculate-tax:
    get:
        summary: Calculate total income tax based on annual income and tax year.
        description: >-
        This endpoint calculates and returns the total income tax owed based on the provided annual
        income and tax year. It includes a breakdown of taxes owed per tax bracket and the effective
        tax rate. The calculation uses predefined tax brackets specific to the requested tax year.
        operationId: calculateTax
        parameters:
        - name: annual_income
            in: query
            required: true
            description: The annual income of the individual.
            schema:
            type: number
            format: float
            example: 50000
        - name: tax_year
            in: query
            required: true
            description: The tax year for the calculation. Must be one of the supported years.
            schema:
            type: integer
            example: 2021
        responses:
        200:
            description: A detailed breakdown of the total tax, taxes per bracket, and effective tax rate.
            content:
            application/json:
                schema:
                type: object
                properties:
                    total_tax:
                    type: number
                    format: float
                    description: The total amount of tax calculated.
                    example: 12345.67
                    tax_details:
                    type: array
                    description: A breakdown of taxes paid at each bracket.
                    items:
                        type: object
                        properties:
                        min:
                            type: number
                            format: float
                            description: Minimum income threshold for the tax bracket.
                            example: 0
                        max:
                            type: number
                            format: float
                            description: Maximum income threshold for the tax bracket.
                            example: 50197
                        tax_paid:
                            type: number
                            format: float
                            description: Amount of tax paid at this bracket.
                            example: 7530.00
                    effective_rate:
                    type: number
                    format: float
                    description: Effective tax rate calculated as a percentage.
                    example: 15.5
        400:
            description: Bad request due to missing or invalid parameters.
        500:
            description: Internal server error encountered while processing the request.
    """

    annual_income = request.args.get('annual_income', type=float)
    tax_year = request.args.get('tax_year', type=int)

    if not (annual_income and tax_year):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    if tax_year not in config['supported_tax_years']:
        return jsonify({'error': f"Unsupported tax year. Supported years are: {', '.join(map(str, config['supported_tax_years']))}"}), 400

    try:
        tax_data = fetch_tax_data(tax_year)
        total_tax, tax_details, effective_rate = compute_tax(annual_income, tax_data)
        return jsonify({
            'total_tax': total_tax,
            'tax_details': tax_details,
            'effective_rate': effective_rate
        })
    except Exception as e:
        logging.error(f"Error calculating tax: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

def fetch_tax_data(tax_year):
    """
    Fetches tax brackets for a given year from a specified API endpoint.
    
    Uses a caching mechanism to store and reuse responses for one hour to avoid excessive API calls.
    Implements exponential backoff retry strategy for handling transient network errors.

    Args:
    tax_year (int): The year for which to fetch tax data.

    Returns:
    dict: A dictionary containing tax brackets for the specified year.

    Raises:
    requests.exceptions.HTTPError: If the request to the API endpoint fails with an HTTP error.
    """    

    @cached(cache)
    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.RequestException, requests.exceptions.Timeout),
                          max_tries=config['tax_api_max_retries'],
                          giveup=lambda e: e.response is not None and e.response.status_code < 500)
    def get_data(tax_year):
        logging.info(f'Cache miss, calling the external API for {tax_year}')
        url = f'{config["tax_api_url"]}/{tax_year}'
        response = requests.get(url)
        response.raise_for_status()  # Raises HTTPError for bad responses
        return response.json()

    try:
        return get_data(tax_year)
    except requests.exceptions.HTTPError as e:
        logging.error(f"Failed to fetch tax data due to an HTTP error: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch tax data due to a network-related error: {e}")
        raise

def compute_tax(income, tax_data):
    """
    Calculate total income tax based on income and tax brackets.

    Args:
    income (float): The annual income of the individual.
    tax_data (dict): Contains the list of tax brackets for a specific tax year.

    Returns:
    tuple: total_tax, detailed tax per bracket, and effective tax rate.
    """
    total_tax = 0
    tax_details = []
    brackets = tax_data['tax_brackets']

    for bracket in brackets:
        if 'max' in bracket:
            if income > bracket['min']:
                taxable_income = min(income, bracket['max']) - bracket['min']
                tax = taxable_income * bracket['rate']
                total_tax += tax
                tax = round(tax, 2)  # Rounding to the nearest cent
                tax_details.append({'min': bracket['min'], 'max': bracket['max'], 'tax_paid': tax})
        else:
            if income > bracket['min']:
                taxable_income = income - bracket['min']
                tax = taxable_income * bracket['rate']
                total_tax += tax
                tax = round(tax, 2)  # Rounding to the nearest cent
                tax_details.append({'min': bracket['min'], 'tax_paid': round(tax, 2)})
    
    effective_rate = round((total_tax / income) * 100, 2) if income > 0 else 0  # Rounding the percentage
    total_tax = round(total_tax, 2)

    return total_tax, tax_details, effective_rate

if __name__ == '__main__':
    app.run(debug=True)