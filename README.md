# Installation
In a terminal, run<br>
`pip install -r requirements.txt`<br>
to download and install all the required dependencies of the app.

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
## If you will setup a virtual environment
If you have setup a virtual environment in the source directory, you have to name it `.venv` to make use of the below shell scripts.
- For Windows, run `runapp.bat` to start the app.
- For any POSIX-based OS like macOS or Linux, run `runapp.sh` to start the app.

## If you will install dependencies in the main Python Environment of the OS
Run app.py to start the app.
