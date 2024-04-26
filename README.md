# Income Tax Calculator API

## Overview
This application provides a robust solution for calculating total income tax based on marginal tax rates. It interfaces with a third-party API to retrieve tax rates applicable for specified years, allowing users to calculate taxes accurately for different scenarios.

## Features
- **Dynamic Tax Rate Retrieval:** Fetches current and historical marginal tax rates from a reliable third-party API.
- **Income Tax Calculation:** Computes total income tax owed by an individual based on their annual income and the specific tax year, utilizing the retrieved tax rates.
- **API Endpoint:** Offers a single HTTP API endpoint that accepts two key parameters — `annual_income` (float) and `tax_year` (integer). This design ensures that the interface is simple yet powerful, catering to a wide range of use cases from simple tax calculations to more complex financial planning applications.

## How to run
1. Run the external tax API for retrieving tax rates:
    ```
    docker pull ptsdocker16/interview-test-server
    docker run --init -p 5001:5001 -it ptsdocker16/interview-test-server
    ```

1. Clone this repo, install dependencies and run the application:
    ```
    git clone https://github.com/Artod/plusgrade.git
    cd plusgrade
    pip install -r requirements.txt
    flask run
    ```

1. Open in the browser `http://127.0.0.1:5000/calculate-tax?annual_income=145000&tax_year=2021`


## Tests
To run tests, execute the following:
```
python test.py
```