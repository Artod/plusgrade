import unittest
from unittest.mock import patch, Mock
from flask import Flask, jsonify
import requests

from app import app

class TestTaxCalculation(unittest.TestCase):

    def setUp(self):
        # Creates a test client
        self.app = app.test_client()
        # Propagate the exceptions to the test client
        self.app.testing = True

    def test_without_query_params(self):
        # Test calling endpoint without query parameters
        response = self.app.get('/calculate-tax')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {'error': 'Missing required parameters'})

    def test_with_wrong_year(self):
        # Test calling with an unsupported year
        response = self.app.get('/calculate-tax?annual_income=50000&tax_year=2006')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Unsupported tax year', response.json['error'])

    def test_with_valid_request(self):
        # Test with a valid salary and year, expect exact json response
        with patch('app.fetch_tax_data') as mock_fetch:
            mock_fetch.return_value = {'tax_brackets': [{'min': 0, 'max': 50197, 'rate': 0.15}, {'min': 50197, 'rate': 0.2}]}
            response = self.app.get('/calculate-tax?annual_income=145000&tax_year=2021')
            self.assertEqual(response.status_code, 200)
            expected_json = {
                "total_tax": 26490.15,
                "tax_details": [{"min": 0, "max": 50197, "tax_paid": 7529.55}, {"min": 50197, "tax_paid": 18960.6}],
                "effective_rate": 18.27
            }
            self.assertEqual(response.json, expected_json)

    def test_transient_error_and_recovery(self):
        # Simulate responses from the tax API: first a 500 error, then a successful JSON response
        with patch('requests.get') as mock_get:
            # Create a mock response for the 500 error
            mock_response_error = Mock()
            mock_response_error.raise_for_status.side_effect = requests.exceptions.HTTPError()
            mock_response_error.status_code = 500
            
            # Create a mock response for the successful call
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {
                'tax_brackets': [{'min': 0, 'max': 50197, 'rate': 0.15}]
            }
            
            # Set the side effect of the mock to simulate both responses
            mock_get.side_effect = [mock_response_error, mock_response_success]
            
            # Perform a call to the endpoint
            response = self.app.get('/calculate-tax?annual_income=145000&tax_year=2021')
            self.assertEqual(response.status_code, 200)
            expected_json = {
                "total_tax": 7529.55,
                "tax_details": [{"min": 0, "max": 50197, "tax_paid": 7529.55}],
                "effective_rate": 5.19
            }
            self.assertEqual(response.json, expected_json)

if __name__ == '__main__':
    unittest.main()
