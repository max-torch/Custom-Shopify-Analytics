# Sample App Deployed on Heroku reading from a fake dataset
[App on Heroku](https://custom-shopify-analytics.herokuapp.com/)

# Installation
In a terminal, run<br>
`pip install -r requirements.txt`<br>
to download and install all the required dependencies of the app.

Currently, it is hardcoded (the line is near the top) to use fake data from fake_data.csv. You must change `fake = True` to `fake = False` to make it use API credentials.

After installing, you must create a JSON file named `Credentials.json` which contains the following:
```
{
    "APIKEY": "{your api key here}",
    "APIPASS": "{your api password here}",
    "HOSTNAME": "{your host name here}",
    "VERSION": "{version of shopify's rest admin api you are using here}"
}
```
These credentials are generated when you create a Shopify Private App.

# Running the app
## If you will use venv to setup a virtual environment
If you have setup a virtual environment using `venv` in the source directory, you have to name it `.venv` to make use of the below shell scripts.
- For Windows, run `runapp.bat` to start the app.
- For any POSIX-based OS like macOS or Linux, run `runapp.sh` to start the app.

## If you will install dependencies in the main Python Environment of the OS
Run app.py to start the app.
