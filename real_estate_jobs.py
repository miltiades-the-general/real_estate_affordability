import requests
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
from pathlib import Path
import streamlit as st

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import hvplot.pandas
import holoviews as hv
import plost

load_dotenv()

hv.extension('bokeh', logo=False)

st.set_page_config(layout="wide")


class Utilities:
    def __init__(self):
        self = self
    def fetch_zillow_api(self, rapid_api_key, location, price_max=1000000):
        zillow_baseurl = "https://zillow56.p.rapidapi.com/search"

        querystring = {"location": location, "price_max": price_max}

        headers = {
            "X-RapidAPI-Key": rapid_api_key,
            "X-RapidAPI-Host": "zillow56.p.rapidapi.com"
        }

        house_response = requests.request("GET", zillow_baseurl, headers=headers, params=querystring).json()
        return house_response


    def find_avg_income_by_zip(self, api_key, zip_code):
        url = f"https://household-income-by-zip-code.p.rapidapi.com/v1/Census/HouseholdIncomeByZip/{zip_code}"

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "household-income-by-zip-code.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers)
        return response.json()['medianIncome']

    def calc_monthly_payment(self, house_price, mortgage_rate=.0548, mortgage_length=30, down_payment=.2):
        p = house_price * (1 - down_payment)
        r = mortgage_rate / 12
        n = mortgage_length * 12
        monthly_payment = p * (( r * ( 1 + r )**n) / (( 1 + r )**n - 1))
        return monthly_payment

    def find_monthly_payments(self, df, mortgage_rate=.0548, mortgage_length=30, down_payment=.2):
        monthly_payments = []
        for i in df.index:
            price = df.iloc[i]["price"]
            monthly_payment = self.calc_monthly_payment(price, mortgage_rate, mortgage_length, down_payment)
            monthly_payments.append(monthly_payment)
        df["monthly_payments"] = monthly_payments
        return df

    def calc_monthly_budget(self, income):
        taxed_income = income * .75
        taxed_income = taxed_income / 12
        budget = taxed_income * .3
        return budget

    def find_affordable_houses(self, df, budget):
        affordability = []
        for i in df.index:
            house = df.iloc[i]
            if house["monthly_payments"] <= budget:
                affordability.append("yes") 
            else:
                affordability.append("no")
        df["affordable"] = affordability
        return df


def main():
    u = Utilities()
    rapid_api_key = os.getenv("X_RAPID_API_KEY")

    top_cities = Path("./static_data/top_cities.xlsx")
    top_cities_df = pd.read_excel(top_cities)

    zip_codes = Path("./static_data/uszips.xlsx")
    zip_codes_df = pd.read_excel(zip_codes)

    mortgage_rates = {"30-year fixed": {"y": 30, "r": 0.0568}, "20-year-fixed": {"y": 20, "r": 0.0536}, "15-year fixed": {"y": 15, "r":0.0486}, "30-year FHA": {"y": 30, "r": 0.0488}, "30-year VA": {"y": 30, "r": 0.05}}
    max_prices = {"100,000": 100000, "500,000": 500000, "750,000": 750000, "1,000,000": 1000000, "2,500,000": 2500000, "5,000,000": 5000000, "10,000,000": 10000000}
    downpayment_options = [0.1, 0.2, 0.3, 0.4, 0.5]


    def find_affordable_houses_main(api_key, zip_code=91302, price_max=1000000, income=50000, mortgage_rate=.0548, mortgage_length=30, down_payment=.2):
        """"
        param: api_key (type string)
        param: zip_code (type int)
        param: price_max (type int)
        param: income (type float) income will default to the local median income if not supplied by the user
        param: mortgage_rate (type float)
        param: mortgage_length (type int)
        param: down_payment (type float)
        """
        if income == "default":
            income = u.find_avg_income_by_zip(api_key, zip_code)

        budget = u.calc_monthly_budget(income)
        try:
            houses = u.fetch_zillow_api(api_key, zip_code, price_max)
            houses = houses["results"]
        except Exception:
            print("Ensure you entered a valid Zip Code")
            raise Exception
        houses_df = pd.DataFrame(houses)
        houses_df = u.find_monthly_payments(houses_df, mortgage_rate, mortgage_length, down_payment)
        houses_df = u.find_affordable_houses(houses_df, budget)
        categories = ['bathrooms', 'bedrooms', 'city', 'country', 'currency',
       'homeStatus', 'homeType',
       'latitude', 'livingArea', 'longitude', 'lotAreaUnit',
       'lotAreaValue', 'price', 'rentZestimate',
        'state', 'streetAddress', 'taxAssessedValue',
       'zestimate', 'zipcode',
       'monthly_payments', 'affordable']

        return houses_df[categories]

    with st.form("input_form"):
        zip_code = st.text_input("*Zip Code you would like to search")
        income = st.text_input("Income to the nearest whole number")
        price_max = st.selectbox("Select Maximum Price", max_prices.keys())
        down_payment = st.selectbox("Select a downpayment percentage", downpayment_options)
        mortgage_term = st.selectbox("Mortgage Type", mortgage_rates.keys())
        rapid_api_key = st.text_input("Enter your Rapid API Key")
        submitted = st.form_submit_button("Find Houses")

    # with b1:
        # rapid_api_key = st.text_input("Enter Rapid API key")

    if submitted:
        income = float(income)
        zip_code = int(zip_code)
        # price_max = max_prices[price_max]
        down_payment = float(down_payment)
        mortgage_rate = mortgage_rates[mortgage_term]["r"]
        mortgage_length = mortgage_rates[mortgage_term]["y"]
        price_max = max_prices[price_max]
        houses_df = find_affordable_houses_main(rapid_api_key, zip_code, price_max, income, mortgage_rate, mortgage_length, down_payment)
        st.dataframe(houses_df)
        b1, b2 = st.columns(2)
        with b1:
            houses_df.hvplot.points(
                'longitude', 
                'latitude', 
                geo=True, 
                size = 'price',
                scale = .02,
                color='affordable',
                alpha=0.8,
                tiles='OSM',
                frame_width = 700,
                frame_height = 500
        )


    # st.dataframe()


    


        
if __name__ == "__main__":
    main()


