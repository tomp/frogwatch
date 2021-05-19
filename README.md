Frogwatch
=========

This app creates the website for the SMR Frogwatch dashoard.


Installation
------------
These instructions assume that you have python 3.9, postgres 9.5 (or
later) and the heroku cli tool installed, already.

1. Create a virtual env to hold the python dependencies for the project,
   using the following commands:

    virtualenv venv
    . venv/bin/activate
    pip install --upgrade pip setuptools

2. Install the dependencies

    pip install -r requirements.txt

3. Update the DATABASE_URL setting in frogwatch/settings.py to point to
   the local copy of the frenzy database (named "frogwatch", here).
   For example, for a local Postgres db, this might be

     DATABASE_URL = "postgres://{user}:{passwd}@{host}:{port}/{database}".format(
        user="frogger", passwd="s3cre7", host="127.0.0.1", port="5432", database="frogwatch")

   (When deployed on Heroku, a DATABASE_URL environment variable will
   automatically be defined to point to the production db.)

3. Initialize the database.  If you have an existing Postgres db on
   Heroku, you can clone it locally using the command

    heroku pg:pull <heroku-db-id> frogwatch --app frogwatch

   Otherwise, create a new local database with the command

    createdb frogwatch

4. You can now start up a local copy of the site using the command

    heroku local

7. Vist the local site at http://localhost:5000/ or http://localhost:5000/admin


