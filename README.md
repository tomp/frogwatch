Frogwatch
=========

This app creates a web-based dashboard for Frogwatch observations from
South Mountain Reservation, Essex County, NJ.  It is a Python app that
uses Pandas and Bokeh to display FrogWatch observation data that has
been downloaded into a normalized Postgres database.  It is currently
configured to run as a Heroku application, named 'frogwatch'.


Installation
------------
These instructions assume that you have python 3.9, postgres 9.5 (or
later) and the heroku cli tool installed, already.

1. Create a virtual env (named FROG) to hold the python dependencies for the
   project, using the following commands:

     python -m venv FROG
     . FROG/bin/activate
     pip install --upgrade pip setuptools

2. Install the dependencies

     pip install -r requirements.txt

3. Update the DATABASE_URL setting in frogwatch/settings.py to point to
   the local copy of the frogwatch database (named "frogwatch", here).
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

4. You can now start up a local copy of the site using the commands

     export BOKEH_ALLOW_WS_ORIGIN=0.0.0.0:5000
     heroku local

7. Vist the local site at http://localhost:5000/ or http://localhost:5000/admin


Working with Heroku
-------------------

Install heroku cli

heroku pg:info

heroku pg:reset

heroku pg:push

heroku pg:pull

heroku local


Loading Data from Fieldscope
----------------------------

1. Create local database (if necessary)

     createdb frogwatch

2. Load data from Fieldscope into local database

     frogwatch --hartshorne  --db

3. Delete stations and observers from other projects.
   (This is necessary to keep the size of the database below 10,000 rows,
   at which point we'd have to start paying heroku for the database.)

     psql> \c frogwatch
     psql> delete from persons where fs_id not in (select distinct observer_id from observations);
     psql> delete from stations where fs_id not in (select distinct station_id from observations);

4. Replace the heroku database with a clone of our local database

     heroku pg:reset postgresql-closed-16712
     heroku pg:push frogwatch postgresql-closed-16712 --app frogwatch


