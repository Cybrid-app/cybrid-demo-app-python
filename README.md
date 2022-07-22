# cybrid-demo-app-python

This project is a demo application designed to illustrate how to integrate and use the Cybrid Bank API Python client.
The application executes a Bitcoin trade flow on the Cybrid Sandbox environment by creating a customer, account, quote, and trade. 
Developers wishing to integrate with the Cybrid Bank API may follow similar patterns demonstrated within this project.  

## Installation

Start by cloning this project to your local machine.

This application uses [Pipenv](https://pipenv.pypa.io/en/latest/) to install and manage Python dependencies. You can install `pipenv` with the following:
```
$ pip install --user pipenv
```


Within your local repository, you can install all of the demo application's dependencies, including the Cybrid Bank API client, by executing:

```
$ pipenv install
```

This will create a virtual environment (`.venv`) containing a siloed Python interpreter and will install the project dependencies therein. 
By default, `pipenv` will create the virtual environment in an OS-dependent user directory. You can optionally set the environment variable `PIPENV_VENV_IN_PROJECT=1` in your terminal to tell `pipenv` to create the virtual environment's folder within your local repository. 

## Setup

The demo application requires API access to the Cybrid Sandbox. 
To get started in the Sandbox, register for an account at https://www.cybrid.xyz/access. 
Once logged in, you will be prompted to name your Organization, create a Bank, and generate an API key pair.

## Configuration

The project comes with an example environment file that outlines the environment variables used by the application.
Some environment variables are secret and are required to be provided by the user. Other variables have default values.

Copy the example file `example.env` as `.env`:

```
$ cp example.env .env
```

Inside `.env`, configure the environment variables to point to your Bank and API application:

1. Set the value of `BANK_GUID` to the GUID of your Sandbox Bank.
2. Set the value of `APPLICATION_CLIENT_ID` and `APPLICATION_CLIENT_SECRET` to your generated API Client ID and Client Secret, respectively.

## Execution

Once your environment is configured, you can run the demo application by executing the Python file `app/main.py`:

```
$ pipenv run python app/main.py
```

This will run the application, executing the buy flow. If the flow is successful, and the resulting BTC account reports the expected balance, the application will exit with a return code of `0`.
If an invalid state is reported, such as an unexpected balance, or an error is raised during execution, the application will exit with a non-zero return code.
